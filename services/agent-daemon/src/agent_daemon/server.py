"""gRPC server implementation for agent-daemon."""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
import uuid
from concurrent import futures
from datetime import UTC, datetime
from pathlib import Path

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from agent_daemon.browser_operator_runtime import load_browser_operator_service_class
from agent_daemon.contracts_runtime import load_contract_modules
from agent_daemon.logging_utils import set_correlation_id
from agent_daemon.windows_operator_runtime import load_windows_operator_service_class
from agent_daemon.services.memory import (
    AppSettingRecord,
    ConversationRecord,
    MemoryService,
    MessageRecord,
    TaskRecord,
    TaskStepRecord,
    WorkspaceFileRecord,
    WorkspaceRootRecord,
)
from agent_daemon.services.model_router import ChatCompletion, ModelRouter
from agent_daemon.services.search_adapter import SearchResult, create_search_adapter

pb2, pb2_grpc = load_contract_modules()


class CorrelationIdInterceptor(grpc.ServerInterceptor):
    """Inject correlation IDs from metadata into request context."""

    def intercept_service(self, continuation, handler_call_details):
        handler = continuation(handler_call_details)
        if handler is None:
            return None

        method = handler_call_details.method
        metadata = dict(handler_call_details.invocation_metadata or ())

        def wrap_unary_unary(behavior):
            def inner(request, context):
                correlation_id = set_correlation_id(metadata.get("x-correlation-id"))
                logging.getLogger("agent_daemon").info(
                    "request received",
                    extra={
                        "grpc_method": method,
                        "peer": context.peer(),
                    },
                )
                context.set_trailing_metadata((("x-correlation-id", correlation_id),))
                return behavior(request, context)

            return inner

        def wrap_unary_stream(behavior):
            def inner(request, context):
                correlation_id = set_correlation_id(metadata.get("x-correlation-id"))
                logging.getLogger("agent_daemon").info(
                    "stream request received",
                    extra={
                        "grpc_method": method,
                        "peer": context.peer(),
                    },
                )
                context.set_trailing_metadata((("x-correlation-id", correlation_id),))
                yield from behavior(request, context)

            return inner

        if handler.unary_unary:
            return grpc.unary_unary_rpc_method_handler(
                wrap_unary_unary(handler.unary_unary),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        if handler.unary_stream:
            return grpc.unary_stream_rpc_method_handler(
                wrap_unary_stream(handler.unary_stream),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        return handler


class DaemonContractService(pb2_grpc.DaemonContractServicer):
    """Daemon contract service with SQLite-backed conversation/message persistence."""

    def __init__(self, memory_service: MemoryService, windows_operator_service, browser_operator_service) -> None:
        self._memory = memory_service
        self._windows_operator = windows_operator_service
        self._browser_operator = browser_operator_service
        self._model_router = ModelRouter(
            ollama_base_url=os.environ.get("AGENT_DAEMON_OLLAMA_URL", "http://127.0.0.1:11434"),
            default_ollama_model=os.environ.get("AGENT_DAEMON_OLLAMA_MODEL", "llama3.2"),
        )
        self._event_subscribers: list[queue.Queue] = []
        self._event_subscribers_lock = threading.Lock()

    _APP_SETTINGS_KEY = "model_provider_settings_v1"

    @staticmethod
    def _default_settings_payload(observed_at: str) -> dict:
        return {
            "model_mode": "MODEL_MODE_GUIDED",
            "provider_preference": "PROVIDER_PREFERENCE_LOCAL_PREFERRED",
            "providers": [
                {"provider_id": "ollama", "display_name": "Ollama (local)"},
                {"provider_id": "placeholder", "display_name": "Built-in Placeholder"},
            ],
            "api_key_entries": [],
            "search_settings": {
                "enabled": False,
                "provider_id": "duckduckgo",
                "endpoint": "https://api.duckduckgo.com/",
                "api_key_placeholder_ref": "",
            },
            "updated_at": observed_at,
        }

    def _load_app_settings_payload(self) -> dict:
        stored = self._memory.get_app_setting(self._APP_SETTINGS_KEY)
        if stored is None:
            return self._default_settings_payload(self._now())

        try:
            payload = json.loads(stored.setting_value)
        except json.JSONDecodeError:
            return self._default_settings_payload(self._now())

        if not isinstance(payload, dict):
            return self._default_settings_payload(self._now())

        return payload

    def _to_app_settings_dto(self, payload: dict):
        providers = payload.get("providers", [])
        api_key_entries = payload.get("api_key_entries", [])
        search_settings = payload.get("search_settings", {})
        if not isinstance(search_settings, dict):
            search_settings = {}
        return pb2.AppSettingsDto(
            model_mode=getattr(pb2, payload.get("model_mode", "MODEL_MODE_GUIDED"), pb2.MODEL_MODE_GUIDED),
            provider_preference=getattr(
                pb2,
                payload.get("provider_preference", "PROVIDER_PREFERENCE_LOCAL_PREFERRED"),
                pb2.PROVIDER_PREFERENCE_LOCAL_PREFERRED,
            ),
            providers=[
                pb2.ProviderConfigDto(
                    provider_id=str(provider.get("provider_id", "")).strip(),
                    display_name=str(provider.get("display_name", "")).strip(),
                )
                for provider in providers
                if isinstance(provider, dict)
            ],
            api_key_entries=[
                pb2.ApiKeyEntryDto(
                    entry_id=str(entry.get("entry_id", "")).strip(),
                    provider_id=str(entry.get("provider_id", "")).strip(),
                    display_name=str(entry.get("display_name", "")).strip(),
                    placeholder_ref=str(entry.get("placeholder_ref", "")).strip(),
                    created_at=str(entry.get("created_at", "")).strip(),
                )
                for entry in api_key_entries
                if isinstance(entry, dict)
            ],
            updated_at=str(payload.get("updated_at", self._now())),
            search_settings=pb2.SearchSettingsDto(
                enabled=bool(search_settings.get("enabled", False)),
                provider_id=str(search_settings.get("provider_id", "duckduckgo")).strip(),
                endpoint=str(search_settings.get("endpoint", "https://api.duckduckgo.com/")).strip(),
                api_key_placeholder_ref=str(search_settings.get("api_key_placeholder_ref", "")).strip(),
            ),
        )

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _to_conversation_dto(conversation: ConversationRecord):
        return pb2.ConversationDto(
            conversation_id=conversation.conversation_id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    @staticmethod
    def _to_message_dto(message: MessageRecord):
        return pb2.ChatMessageDto(
            message_id=message.message_id,
            conversation_id=message.conversation_id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            provider_id=message.provider_id,
            model_id=message.model_id,
        )

    @staticmethod
    def _to_task_dto(task: TaskRecord):
        return pb2.TaskSummaryDto(
            task_id=task.task_id,
            conversation_id=task.conversation_id,
            task_status=task.task_status,
            approval_status=task.approval_status,
            title=task.title,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    def _to_workspace_mode(self, access_mode: str) -> int:
        normalized = access_mode.strip().lower()
        if normalized == "read_write":
            return pb2.WORKSPACE_ACCESS_MODE_READ_WRITE
        return pb2.WORKSPACE_ACCESS_MODE_READ_ONLY

    def _to_workspace_root_dto(self, root: WorkspaceRootRecord):
        sample_files = [item.relative_path for item in self._memory.list_workspace_files(root.root_id, limit=20)]
        return pb2.WorkspaceRootDto(
            root_id=root.root_id,
            conversation_id=root.conversation_id,
            display_name=root.display_name,
            root_path=root.root_path,
            access_mode=self._to_workspace_mode(root.access_mode),
            file_count=max(root.file_count, 0),
            sample_files=sample_files,
            attached_at=root.attached_at,
            last_scanned_at=root.last_scanned_at,
        )

    @staticmethod
    def _resolve_workspace_mode(mode: int) -> str:
        if mode == pb2.WORKSPACE_ACCESS_MODE_READ_WRITE:
            return "read_write"
        return "read_only"

    def _scan_workspace_root(self, root_id: str, root_path: Path, observed_at: str) -> tuple[int, list[WorkspaceFileRecord]]:
        scanned_files: list[WorkspaceFileRecord] = []
        total_files = 0
        max_persisted_files = 1000

        for current_root, _, files in os.walk(root_path):
            current_path = Path(current_root)
            for filename in files:
                absolute_path = current_path / filename
                total_files += 1

                if len(scanned_files) >= max_persisted_files:
                    continue

                try:
                    relative_path = str(absolute_path.relative_to(root_path))
                    size_bytes = absolute_path.stat().st_size
                except (OSError, ValueError):
                    continue

                scanned_files.append(
                    WorkspaceFileRecord(
                        file_id=f"{root_id}:{relative_path}",
                        root_id=root_id,
                        relative_path=relative_path,
                        size_bytes=size_bytes,
                        discovered_at=observed_at,
                    )
                )

        return total_files, scanned_files

    def _publish_task_event(
        self,
        *,
        task_id: str,
        event_type: int,
        task_status: int,
        title: str,
        detail: str,
        step_id: str = "",
    ) -> None:
        observed_at = self._now()
        event = pb2.TaskTimelineEvent(
            task_id=task_id,
            step_id=step_id,
            title=title,
            detail=detail,
            event_type=event_type,
            task_status=task_status,
            observed_at=observed_at,
        )

        with self._event_subscribers_lock:
            subscribers = list(self._event_subscribers)

        for subscriber in subscribers:
            subscriber.put(event)

    def _ensure_conversation(self, conversation_id: str, title: str = "Chat") -> ConversationRecord:
        if conversation_id:
            conversation = self._memory.get_conversation(conversation_id)
            if conversation is not None:
                return conversation

        now = self._now()
        new_conversation_id = conversation_id or f"conv-{uuid.uuid4().hex[:8]}"
        return self._memory.upsert_conversation(
            ConversationRecord(
                conversation_id=new_conversation_id,
                title=title,
                created_at=now,
                updated_at=now,
            )
        )

    def _capabilities(self):
        windows_operator = self._windows_operator.availability()
        browser_operator = self._browser_operator.availability()
        ollama_status = next((item for item in self._model_router.get_status() if item.provider_id == "ollama"), None)
        return [
            pb2.CapabilityStatusDto(
                capability_name="chat",
                is_available=True,
                detail="Conversation loop with local model routing is available.",
            ),
            pb2.CapabilityStatusDto(
                capability_name="web search",
                is_available=True,
                detail="Search-enabled chat requests are supported when search is enabled in settings.",
            ),
            pb2.CapabilityStatusDto(
                capability_name="tasks",
                is_available=True,
                detail="Task timeline scaffold is available.",
            ),
            pb2.CapabilityStatusDto(
                capability_name="workspaces",
                is_available=True,
                detail="Workspace root attachment scaffold is available.",
            ),
            pb2.CapabilityStatusDto(
                capability_name="windows operator",
                is_available=windows_operator.is_available,
                detail=windows_operator.detail,
            ),
            pb2.CapabilityStatusDto(
                capability_name="browser support",
                is_available=browser_operator.is_available,
                detail=browser_operator.detail,
            ),
            pb2.CapabilityStatusDto(
                capability_name="ollama",
                is_available=ollama_status.is_available if ollama_status else False,
                detail=ollama_status.detail if ollama_status else "Ollama status is unavailable.",
            ),
        ]

    def HealthCheck(self, request, context):
        _ = (request, context)
        observed_at = self._now()
        return pb2.HealthCheckResponse(
            daemon=pb2.ServiceHealthDto(
                service_name="agent-daemon",
                status=pb2.HEALTH_STATUS_HEALTHY,
                observed_at=observed_at,
                detail="daemon grpc service is ready",
            ),
            shell=pb2.ServiceHealthDto(
                service_name="desktop-shell",
                status=pb2.HEALTH_STATUS_HEALTHY,
                observed_at=observed_at,
                detail="shell requested startup health",
            ),
            daemon_version=os.environ.get("AGENT_DAEMON_VERSION", "0.1.0-dev"),
            system=pb2.SystemStatusDto(
                environment=os.environ.get("AGENT_ENVIRONMENT", "development"),
                status=pb2.HEALTH_STATUS_HEALTHY,
                observed_at=observed_at,
                detail=f"python {os.sys.version.split()[0]}",
            ),
            capabilities=self._capabilities(),
        )

    def GetAppSettings(self, request, context):
        _ = (request, context)
        payload = self._load_app_settings_payload()
        return pb2.GetAppSettingsResponse(settings=self._to_app_settings_dto(payload))

    def UpdateAppSettings(self, request, context):
        settings = request.settings

        providers = []
        seen_provider_ids: set[str] = set()
        for provider in settings.providers:
            provider_id = provider.provider_id.strip().lower()
            display_name = provider.display_name.strip()

            if not provider_id:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Each provider needs a provider ID.")
            if not display_name:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Each provider needs a display name.")
            if provider_id in seen_provider_ids:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Duplicate provider ID: {provider_id}")

            seen_provider_ids.add(provider_id)
            providers.append({"provider_id": provider_id, "display_name": display_name})

        entries = []
        seen_entry_ids: set[str] = set()
        for entry in settings.api_key_entries:
            entry_id = entry.entry_id.strip().lower()
            provider_id = entry.provider_id.strip().lower()
            display_name = entry.display_name.strip()
            placeholder_ref = entry.placeholder_ref.strip()
            created_at = entry.created_at.strip() or self._now()

            if not entry_id:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Each API key entry needs an ID.")
            if entry_id in seen_entry_ids:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"Duplicate API key entry ID: {entry_id}")
            if provider_id not in seen_provider_ids:
                context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    f"API key entry {entry_id} references unknown provider {provider_id}.",
                )
            if not display_name:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Each API key entry needs a label.")
            if not placeholder_ref.startswith("placeholder://"):
                context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "API key entries are placeholder refs only (must start with placeholder://).",
                )

            seen_entry_ids.add(entry_id)
            entries.append(
                {
                    "entry_id": entry_id,
                    "provider_id": provider_id,
                    "display_name": display_name,
                    "placeholder_ref": placeholder_ref,
                    "created_at": created_at,
                }
            )

        search_settings = settings.search_settings
        search_provider_id = search_settings.provider_id.strip().lower() or "duckduckgo"
        search_endpoint = search_settings.endpoint.strip() or "https://api.duckduckgo.com/"
        search_api_key_placeholder_ref = search_settings.api_key_placeholder_ref.strip()
        if search_api_key_placeholder_ref and not search_api_key_placeholder_ref.startswith("placeholder://"):
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Search API key placeholder must start with placeholder://.",
            )

        updated_at = self._now()
        payload = {
            "model_mode": pb2.ModelMode.Name(settings.model_mode or pb2.MODEL_MODE_GUIDED),
            "provider_preference": pb2.ProviderPreference.Name(
                settings.provider_preference or pb2.PROVIDER_PREFERENCE_LOCAL_PREFERRED
            ),
            "providers": providers,
            "api_key_entries": entries,
            "search_settings": {
                "enabled": bool(search_settings.enabled),
                "provider_id": search_provider_id,
                "endpoint": search_endpoint,
                "api_key_placeholder_ref": search_api_key_placeholder_ref,
            },
            "updated_at": updated_at,
        }

        self._memory.upsert_app_setting(
            AppSettingRecord(
                setting_key=self._APP_SETTINGS_KEY,
                setting_value=json.dumps(payload),
                updated_at=updated_at,
            )
        )

        return pb2.UpdateAppSettingsResponse(settings=self._to_app_settings_dto(payload))

    def StartConversation(self, request, context):
        _ = context
        conversation = self._ensure_conversation(
            conversation_id="",
            title=request.title or "New conversation",
        )
        return pb2.StartConversationResponse(
            conversation=self._to_conversation_dto(conversation),
            started_at=self._now(),
        )

    def SendUserMessage(self, request, context):
        _ = context
        conversation = self._ensure_conversation(request.conversation_id)
        accepted_at = self._now()

        user_message_id = request.user_message_id or f"user-{uuid.uuid4().hex[:8]}"
        assistant_message_id = f"assistant-{uuid.uuid4().hex[:8]}"

        user_message = MessageRecord(
            message_id=user_message_id,
            conversation_id=conversation.conversation_id,
            role=pb2.MESSAGE_ROLE_USER,
            content=request.content,
            created_at=request.sent_at or accepted_at,
        )

        settings_payload = self._load_app_settings_payload()
        search_result = self._try_run_search(request.content, settings_payload)
        if search_result is None:
            completion = self._model_router.complete(request.content, settings_payload)
        else:
            completion = self._build_search_completion(search_result)
        assistant_message = MessageRecord(
            message_id=assistant_message_id,
            conversation_id=conversation.conversation_id,
            role=pb2.MESSAGE_ROLE_ASSISTANT,
            content=completion.content,
            created_at=accepted_at,
            provider_id=completion.provider_id,
            model_id=completion.model_id,
        )

        self._memory.add_message(user_message)
        self._memory.add_message(assistant_message)

        updated_conversation = self._memory.upsert_conversation(
            ConversationRecord(
                conversation_id=conversation.conversation_id,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=accepted_at,
            )
        )

        return pb2.SendUserMessageResponse(
            daemon_message_id=assistant_message_id,
            accepted_at=accepted_at,
            conversation=self._to_conversation_dto(updated_conversation),
            user_message=self._to_message_dto(user_message),
            assistant_message=self._to_message_dto(assistant_message),
            search_result=self._to_search_result_dto(search_result),
        )

    @staticmethod
    def _build_search_completion(search_result: SearchResult):
        source_lines = [f"- {source.title}: {source.url}" for source in search_result.sources]
        sources_block = "\n".join(source_lines)
        content = search_result.answer
        if sources_block:
            content = f"{content}\n\nSources:\n{sources_block}"

        return ChatCompletion(
            content=content,
            provider_id=search_result.provider_id,
            model_id="web-search-v1",
        )

    @staticmethod
    def _is_search_request(content: str) -> bool:
        normalized = content.strip().lower()
        if normalized.startswith("search "):
            return True

        search_markers = ("look up ", "find on web ", "web search ", "search for ")
        return any(marker in normalized for marker in search_markers)

    def _try_run_search(self, content: str, settings_payload: dict) -> SearchResult | None:
        if not self._is_search_request(content):
            return None

        search_settings = settings_payload.get("search_settings", {})
        if not isinstance(search_settings, dict):
            search_settings = {}
        enabled = bool(search_settings.get("enabled", False))
        if not enabled:
            return SearchResult(
                query=content.strip(),
                answer=(
                    "Web search is currently turned off in Settings. "
                    "Open Settings → Search and enable it, then try again."
                ),
                provider_id="search-disabled",
                sources=[],
            )

        provider_id = str(search_settings.get("provider_id", "duckduckgo")).strip() or "duckduckgo"
        endpoint = str(search_settings.get("endpoint", "https://api.duckduckgo.com/")).strip()
        if not endpoint:
            return SearchResult(
                query=content.strip(),
                answer=(
                    "Search is enabled, but no search endpoint is configured yet. "
                    "Add an endpoint in Settings → Search (for DuckDuckGo, use https://api.duckduckgo.com/)."
                ),
                provider_id="search-misconfigured",
                sources=[],
            )

        try:
            adapter = create_search_adapter(provider_id=provider_id, endpoint=endpoint)
            return adapter.search(content.strip())
        except ValueError as ex:
            return SearchResult(
                query=content.strip(),
                answer=(
                    f"I couldn't use search provider '{provider_id}'. {ex} "
                    "Choose duckduckgo for now while provider support is still minimal."
                ),
                provider_id="search-misconfigured",
                sources=[],
            )
        except (OSError, TimeoutError, json.JSONDecodeError):
            return SearchResult(
                query=content.strip(),
                answer=(
                    "I couldn't reach the web search service right now. "
                    "Please check your network connection and try again."
                ),
                provider_id=provider_id,
                sources=[],
            )

    @staticmethod
    def _to_search_result_dto(search_result: SearchResult | None):
        if search_result is None:
            return pb2.SearchResultDto()

        return pb2.SearchResultDto(
            query=search_result.query,
            answer=search_result.answer,
            provider_id=search_result.provider_id,
            sources=[pb2.SearchSourceDto(title=item.title, url=item.url) for item in search_result.sources],
        )

    def AttachWorkspaceRoot(self, request, context):
        requested_path = request.root_path.strip()
        if not requested_path:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "root_path is required")

        root_path = Path(requested_path).expanduser().resolve()
        if not root_path.exists() or not root_path.is_dir():
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "root_path must be an existing folder")

        conversation = self._ensure_conversation(
            request.conversation_id.strip(),
            title="Workspace conversation",
        )
        observed_at = self._now()
        root_id = f"root-{uuid.uuid4().hex[:8]}"
        display_name = request.display_name.strip() or root_path.name or str(root_path)
        access_mode = self._resolve_workspace_mode(request.access_mode)

        file_count, inventory_files = self._scan_workspace_root(root_id, root_path, observed_at)
        root_record = self._memory.upsert_workspace_root(
            WorkspaceRootRecord(
                root_id=root_id,
                conversation_id=conversation.conversation_id,
                root_path=str(root_path),
                display_name=display_name,
                access_mode=access_mode,
                file_count=file_count,
                attached_at=observed_at,
                last_scanned_at=observed_at,
            )
        )
        self._memory.replace_workspace_files(root_record.root_id, inventory_files)

        return pb2.AttachWorkspaceRootResponse(
            conversation=self._to_conversation_dto(conversation),
            root=self._to_workspace_root_dto(root_record),
        )

    def GetConversationWorkspace(self, request, context):
        if not request.conversation_id.strip():
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "conversation_id is required")

        roots = self._memory.list_workspace_roots(request.conversation_id.strip())
        return pb2.GetConversationWorkspaceResponse(
            conversation_id=request.conversation_id.strip(),
            roots=[self._to_workspace_root_dto(root) for root in roots],
        )

    def ListConversations(self, request, context):
        _ = context
        conversations = self._memory.list_conversations()
        if request.limit > 0:
            conversations = conversations[: request.limit]

        return pb2.ListConversationsResponse(
            conversations=[self._to_conversation_dto(conversation) for conversation in conversations]
        )

    def GetConversation(self, request, context):
        conversation = self._memory.get_conversation(request.conversation_id)
        if conversation is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "Conversation not found")

        messages = self._memory.list_messages(request.conversation_id)
        return pb2.GetConversationResponse(
            conversation=self._to_conversation_dto(conversation),
            messages=[self._to_message_dto(message) for message in messages],
        )

    def StartTask(self, request, context):
        _ = context
        conversation = self._ensure_conversation(
            request.conversation_id,
            title="Task conversation",
        )
        now = self._now()
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        task = self._memory.upsert_task(
            TaskRecord(
                task_id=task_id,
                conversation_id=conversation.conversation_id,
                task_status=pb2.TASK_STATUS_RUNNING,
                approval_status=pb2.APPROVAL_STATUS_PENDING,
                title=request.title or "Run first task flow",
                created_at=now,
                updated_at=now,
            )
        )
        self._publish_task_event(
            task_id=task.task_id,
            event_type=pb2.TASK_EVENT_TYPE_TASK_STARTED,
            task_status=task.task_status,
            title=task.title,
            detail="Task started. Setting up first-time placeholder execution.",
        )

        executor = threading.Thread(
            target=self._run_placeholder_task,
            args=(task.task_id,),
            daemon=True,
        )
        executor.start()
        return pb2.StartTaskResponse(task=self._to_task_dto(task))

    def ApproveStep(self, request, context):
        _ = context
        return pb2.ApproveStepResponse(
            task_id=request.task_id,
            step_id=request.step_id,
            approval_status=pb2.APPROVAL_STATUS_APPROVED,
        )

    def CancelTask(self, request, context):
        _ = context
        return pb2.CancelTaskResponse(
            task=pb2.TaskSummaryDto(
                task_id=request.task_id,
                conversation_id="conv-placeholder",
                task_status=pb2.TASK_STATUS_CANCELED,
                approval_status=pb2.APPROVAL_STATUS_REJECTED,
                title="Canceled placeholder task",
                created_at=self._now(),
                updated_at=self._now(),
            )
        )

    def ResumeTask(self, request, context):
        _ = context
        return pb2.ResumeTaskResponse(
            task=pb2.TaskSummaryDto(
                task_id=request.task_id,
                conversation_id="conv-placeholder",
                task_status=pb2.TASK_STATUS_RUNNING,
                approval_status=pb2.APPROVAL_STATUS_PENDING,
                title="Resumed placeholder task",
                created_at=self._now(),
                updated_at=self._now(),
            )
        )

    def ListArtifacts(self, request, context):
        _ = context
        return pb2.ListArtifactsResponse(
            artifacts=[
                pb2.ArtifactMetadata(
                    artifact_id="artifact-placeholder",
                    task_id=request.task_id,
                    name="placeholder.txt",
                    mime_type="text/plain",
                    size_bytes=0,
                    checksum_sha256="",
                    created_at=self._now(),
                )
            ]
        )

    def ObserveSystemState(self, request, context):
        event_queue: queue.Queue = queue.Queue()
        with self._event_subscribers_lock:
            self._event_subscribers.append(event_queue)

        initial_tasks = [self._to_task_dto(task) for task in self._memory.list_tasks()]
        yield pb2.SystemStateEvent(
            event_id=f"event-{uuid.uuid4().hex[:8]}",
            observed_at=self._now(),
            workspace=pb2.WorkspaceDto(
                workspace_id=request.workspace_id or "desktop-shell-workspace",
                root_path="/workspace/Sinapse",
                active_task_id=initial_tasks[0].task_id if initial_tasks else "",
                created_at=self._now(),
                updated_at=self._now(),
            ),
            tasks=initial_tasks,
            services=[
                pb2.ServiceHealthDto(
                    service_name="agent-daemon",
                    status=pb2.HEALTH_STATUS_HEALTHY,
                    observed_at=self._now(),
                    detail="stream connected",
                )
            ],
        )

        try:
            while context.is_active():
                try:
                    timeline_event = event_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                yield pb2.SystemStateEvent(
                    event_id=f"event-{uuid.uuid4().hex[:8]}",
                    observed_at=self._now(),
                    workspace=pb2.WorkspaceDto(
                        workspace_id=request.workspace_id or "desktop-shell-workspace",
                        root_path="/workspace/Sinapse",
                        active_task_id=timeline_event.task_id,
                        created_at=self._now(),
                        updated_at=self._now(),
                    ),
                    tasks=[self._to_task_dto(task) for task in self._memory.list_tasks()[:5]],
                    services=[
                        pb2.ServiceHealthDto(
                            service_name="agent-daemon",
                            status=pb2.HEALTH_STATUS_HEALTHY,
                            observed_at=self._now(),
                            detail="task timeline update",
                        )
                    ],
                    task_timeline_events=[timeline_event],
                )
        finally:
            with self._event_subscribers_lock:
                self._event_subscribers = [item for item in self._event_subscribers if item is not event_queue]

    def _run_placeholder_task(self, task_id: str) -> None:
        task = self._memory.get_task(task_id)
        if task is None:
            return

        fake_steps = [
            "Understanding your request",
            "Preparing a safe placeholder plan",
            "Finalizing timeline output",
        ]

        try:
            for index, step_title in enumerate(fake_steps, start=1):
                started_at = self._now()
                step_id = f"{task_id}-step-{index}"
                self._memory.upsert_task_step(
                    TaskStepRecord(
                        step_id=step_id,
                        task_id=task_id,
                        sequence_number=index,
                        title=step_title,
                        status="running",
                        detail="In progress",
                        created_at=started_at,
                        updated_at=started_at,
                    )
                )
                self._publish_task_event(
                    task_id=task_id,
                    step_id=step_id,
                    event_type=pb2.TASK_EVENT_TYPE_STEP_STARTED,
                    task_status=pb2.TASK_STATUS_RUNNING,
                    title=step_title,
                    detail="Started",
                )
                time.sleep(0.6)

                finished_at = self._now()
                self._memory.upsert_task_step(
                    TaskStepRecord(
                        step_id=step_id,
                        task_id=task_id,
                        sequence_number=index,
                        title=step_title,
                        status="completed",
                        detail="Done",
                        created_at=started_at,
                        updated_at=finished_at,
                    )
                )
                self._publish_task_event(
                    task_id=task_id,
                    step_id=step_id,
                    event_type=pb2.TASK_EVENT_TYPE_STEP_FINISHED,
                    task_status=pb2.TASK_STATUS_RUNNING,
                    title=step_title,
                    detail="Completed successfully",
                )

            completed_at = self._now()
            completed_task = self._memory.upsert_task(
                TaskRecord(
                    task_id=task.task_id,
                    conversation_id=task.conversation_id,
                    task_status=pb2.TASK_STATUS_COMPLETED,
                    approval_status=pb2.APPROVAL_STATUS_APPROVED,
                    title=task.title,
                    created_at=task.created_at,
                    updated_at=completed_at,
                )
            )
            self._publish_task_event(
                task_id=task_id,
                event_type=pb2.TASK_EVENT_TYPE_TASK_FINISHED,
                task_status=completed_task.task_status,
                title=completed_task.title,
                detail="Task finished. Placeholder flow complete.",
            )
        except Exception as exc:  # noqa: BLE001
            failed_at = self._now()
            self._memory.upsert_task(
                TaskRecord(
                    task_id=task.task_id,
                    conversation_id=task.conversation_id,
                    task_status=pb2.TASK_STATUS_FAILED,
                    approval_status=pb2.APPROVAL_STATUS_PENDING,
                    title=task.title,
                    created_at=task.created_at,
                    updated_at=failed_at,
                )
            )
            self._publish_task_event(
                task_id=task_id,
                event_type=pb2.TASK_EVENT_TYPE_TASK_FAILED,
                task_status=pb2.TASK_STATUS_FAILED,
                title=task.title,
                detail=f"Task failed: {exc}",
            )


def create_server() -> grpc.Server:
    """Create and wire the daemon gRPC server."""

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[CorrelationIdInterceptor()],
    )

    repo_root = Path(__file__).resolve().parents[4]
    migrations_path = repo_root / "packages" / "memory-store" / "migrations"
    database_path = os.environ.get(
        "AGENT_MEMORY_DB_PATH",
        str(repo_root / ".sinapse" / "memory.db"),
    )
    memory_service = MemoryService(database_path=database_path, migrations_path=migrations_path)
    windows_operator_service_class = load_windows_operator_service_class()
    windows_operator_service = windows_operator_service_class()
    browser_operator_service_class = load_browser_operator_service_class()
    browser_operator_service = browser_operator_service_class()

    pb2_grpc.add_DaemonContractServicer_to_server(
        DaemonContractService(memory_service, windows_operator_service, browser_operator_service),
        server,
    )

    health_servicer = health.HealthServicer()
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set(
        "sinapse.contracts.v1.DaemonContract",
        health_pb2.HealthCheckResponse.SERVING,
    )
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    return server
