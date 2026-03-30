"""gRPC server implementation for agent-daemon."""

from __future__ import annotations

import logging
import os
import uuid
from concurrent import futures
from datetime import UTC, datetime
from pathlib import Path

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc

from agent_daemon.contracts_runtime import load_contract_modules
from agent_daemon.logging_utils import set_correlation_id
from agent_daemon.services.memory import ConversationRecord, MemoryService, MessageRecord

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

    def __init__(self, memory_service: MemoryService) -> None:
        self._memory = memory_service

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _create_placeholder_assistant_reply(self, user_content: str) -> str:
        prompt_summary = user_content.strip() or "your last message"
        return (
            "Thanks! I received your message and the daemon chat loop is working. "
            f"(Echo summary: \"{prompt_summary[:120]}\")"
        )

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
        )

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
        )

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

        assistant_message = MessageRecord(
            message_id=assistant_message_id,
            conversation_id=conversation.conversation_id,
            role=pb2.MESSAGE_ROLE_ASSISTANT,
            content=self._create_placeholder_assistant_reply(request.content),
            created_at=accepted_at,
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
        _ = (request, context)
        return pb2.StartTaskResponse(
            task=pb2.TaskSummaryDto(
                task_id="task-placeholder",
                conversation_id=request.conversation_id,
                task_status=pb2.TASK_STATUS_PENDING,
                approval_status=pb2.APPROVAL_STATUS_REQUIRED,
                title=request.title or "Placeholder task",
                created_at=self._now(),
                updated_at=self._now(),
            )
        )

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
        _ = (request, context)
        yield pb2.SystemStateEvent(
            event_id="event-placeholder",
            observed_at=self._now(),
            workspace=pb2.WorkspaceDto(
                workspace_id=request.workspace_id or "workspace-placeholder",
                root_path="/workspace",
                active_task_id="task-placeholder",
                created_at=self._now(),
                updated_at=self._now(),
            ),
            tasks=[
                pb2.TaskSummaryDto(
                    task_id="task-placeholder",
                    conversation_id="conv-placeholder",
                    task_status=pb2.TASK_STATUS_RUNNING,
                    approval_status=pb2.APPROVAL_STATUS_PENDING,
                    title="Placeholder observed task",
                    created_at=self._now(),
                    updated_at=self._now(),
                )
            ],
            services=[
                pb2.ServiceHealthDto(
                    service_name="agent-daemon",
                    status=pb2.HEALTH_STATUS_HEALTHY,
                    observed_at=self._now(),
                    detail="placeholder event snapshot",
                )
            ],
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

    pb2_grpc.add_DaemonContractServicer_to_server(DaemonContractService(memory_service), server)

    health_servicer = health.HealthServicer()
    health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
    health_servicer.set(
        "sinapse.contracts.v1.DaemonContract",
        health_pb2.HealthCheckResponse.SERVING,
    )
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    return server
