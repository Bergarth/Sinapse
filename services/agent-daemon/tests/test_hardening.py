from __future__ import annotations

import tempfile
import threading
import time
import unittest
import zipfile
import json
from pathlib import Path

import grpc

from agent_daemon.server import DaemonContractService, pb2
from agent_daemon.services.memory import (
    ApprovalRecord,
    AppSettingRecord,
    ConversationRecord,
    MemoryService,
    TaskRecord,
    TaskStepRecord,
)
from agent_daemon.services.secret_store import SecretStore


class _DummyWindowsOperator:
    def __init__(self) -> None:
        self.opened_files: list[str] = []

    def availability(self):
        return type("Availability", (), {"is_available": True, "detail": "ok"})()

    def enumerate_open_windows(self):
        return type("Result", (), {"is_success": True, "detail": "ok", "payload": []})()

    def launch_application(self, *, app_name: str | None = None, executable_path: str | None = None):
        launched = executable_path or app_name or "unknown"
        return type(
            "Result",
            (),
            {"is_success": True, "detail": f"Launched application: {launched}", "payload": {"launched": launched}},
        )()

    def focus_window(self, *, window_ref: str):
        return type("Result", (), {"is_success": True, "detail": f"Focused {window_ref}", "payload": {"window": window_ref}})()

    def open_file(self, *, file_path: str):
        self.opened_files.append(file_path)
        return type("Result", (), {"is_success": True, "detail": f"Opened {file_path}", "payload": {"file": file_path}})()

    def type_text(self, *, target: str, text: str):
        return type(
            "Result",
            (),
            {"is_success": True, "detail": f"Typed {len(text)} chars into {target}", "payload": {"target": target}},
        )()


class _DummyBrowserOperator:
    def availability(self):
        return type("Availability", (), {"is_available": True, "detail": "ok"})()

    def open_browser_session(self, *, profile_root: str, session_id: str, started_at: str):
        _ = (profile_root, session_id, started_at)
        return type("Result", (), {"is_success": True, "detail": "session started", "result_type": "session_started"})()

    def open_url(self, url: str):
        return type(
            "Result",
            (),
            {
                "is_success": True,
                "detail": "ok",
                "snapshot": type("Snapshot", (), {"url": url, "title": "title", "summary": "summary"})(),
                "result_type": "ok",
                "payload": {},
            },
        )()

    def navigate(self, *, session_id: str, url: str):
        _ = session_id
        return self.open_url(url)

    def download(self, *, url: str, destination_path: str):
        Path(destination_path).parent.mkdir(parents=True, exist_ok=True)
        Path(destination_path).write_text("downloaded", encoding="utf-8")
        return type(
            "Result",
            (),
            {
                "is_success": True,
                "detail": "downloaded",
                "snapshot": None,
                "result_type": "downloaded",
                "payload": {"url": url, "destination_path": destination_path},
            },
        )()

    def upload(self, *, selector: str, source_path: str):
        _ = selector
        if not source_path:
            return type(
                "Result",
                (),
                {"is_success": False, "detail": "missing source", "snapshot": None, "result_type": "not_yet_supported", "payload": {}},
            )()
        return type(
            "Result",
            (),
            {
                "is_success": False,
                "detail": "NOT_YET_SUPPORTED:SESSION_FILE_INPUT_AUTOMATION",
                "snapshot": None,
                "result_type": "not_yet_supported",
                "payload": {"source_path": source_path},
            },
        )()


class _AbortError(RuntimeError):
    pass


class _FakeContext:
    def abort(self, status_code, detail):
        raise _AbortError(f"{status_code}: {detail}")


class HardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        root = Path(self._temp_dir.name)
        migrations = Path(__file__).resolve().parents[3] / "packages" / "memory-store" / "migrations"
        self.memory = MemoryService(str(root / "memory.db"), migrations)
        self.windows = _DummyWindowsOperator()
        self.service = DaemonContractService(
            memory_service=self.memory,
            windows_operator_service=self.windows,
            browser_operator_service=_DummyBrowserOperator(),
            artifacts_root=root / "artifacts",
            secret_store=SecretStore(root / "secrets.json"),
        )

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_list_artifacts_reads_persisted_artifacts(self) -> None:
        task_id = "task-artifacts"
        self.memory.upsert_conversation(
            ConversationRecord("conv-1", "Test", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")
        )
        self.memory.upsert_task(
            TaskRecord(
                task_id=task_id,
                conversation_id="conv-1",
                task_status=pb2.TASK_STATUS_RUNNING,
                approval_status=pb2.APPROVAL_STATUS_PENDING,
                title="test",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
        )

        self.service._persist_artifact(  # noqa: SLF001
            task_id=task_id,
            name="result.txt",
            mime_type="text/plain",
            payload=b"hello",
            labels={"kind": "test"},
        )

        response = self.service.ListArtifacts(pb2.ListArtifactsRequest(task_id=task_id), _FakeContext())
        self.assertEqual(1, len(response.artifacts))
        self.assertEqual("result.txt", response.artifacts[0].name)
        self.assertEqual("test", response.artifacts[0].labels["kind"])

    def test_pending_approvals_are_restored_on_startup(self) -> None:
        self.memory.upsert_conversation(
            ConversationRecord("conv-2", "Approvals", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")
        )
        self.memory.upsert_task(
            TaskRecord(
                task_id="task-approval",
                conversation_id="conv-2",
                task_status=pb2.TASK_STATUS_WAITING_FOR_APPROVAL,
                approval_status=pb2.APPROVAL_STATUS_REQUIRED,
                title="Write file",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        self.memory.upsert_task_step(
            TaskStepRecord(
                step_id="task-approval-approval-gate",
                task_id="task-approval",
                sequence_number=0,
                title="Approval gate",
                status="waiting_for_approval",
                detail="awaiting",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        self.memory.upsert_approval(
            ApprovalRecord(
                approval_id="approval-1",
                task_id="task-approval",
                step_id="task-approval-approval-gate",
                risk_class="write",
                action_title="Write file",
                action_target="workspace",
                reason="writes data",
                status="pending",
                requested_by="daemon",
                requested_at="2026-01-01T00:00:00Z",
            )
        )

        restored = DaemonContractService(
            memory_service=self.memory,
            windows_operator_service=_DummyWindowsOperator(),
            browser_operator_service=_DummyBrowserOperator(),
            artifacts_root=Path(self._temp_dir.name) / "artifacts-restored",
            secret_store=SecretStore(Path(self._temp_dir.name) / "secrets-restored.json"),
        )
        self.assertIn("task-approval-approval-gate", restored._pending_approvals)  # noqa: SLF001

    def test_placeholder_api_key_ref_is_rejected(self) -> None:
        settings = pb2.AppSettingsDto(
            providers=[pb2.ProviderConfigDto(provider_id="ollama", display_name="Ollama")],
            api_key_entries=[
                pb2.ApiKeyEntryDto(
                    entry_id="entry1",
                    provider_id="ollama",
                    display_name="key",
                    placeholder_ref="placeholder://old",
                )
            ],
        )

        with self.assertRaises(_AbortError) as ex:
            self.service.UpdateAppSettings(pb2.UpdateAppSettingsRequest(settings=settings), _FakeContext())

        self.assertIn(str(grpc.StatusCode.INVALID_ARGUMENT), str(ex.exception))

    def test_operator_write_action_requires_approval_then_persists_artifacts(self) -> None:
        self.memory.upsert_conversation(
            ConversationRecord("conv-operator", "Operator", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")
        )
        task = self.memory.upsert_task(
            TaskRecord(
                task_id="task-open-notepad",
                conversation_id="conv-operator",
                task_status=pb2.TASK_STATUS_RUNNING,
                approval_status=pb2.APPROVAL_STATUS_PENDING,
                title="Open Notepad",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
        )

        worker = threading.Thread(target=self.service._run_task, args=(task.task_id, True), daemon=True)  # noqa: SLF001
        worker.start()

        pending = []
        for _ in range(20):
            pending = self.memory.list_pending_approvals()
            if pending:
                break
            time.sleep(0.01)
        self.assertEqual(1, len(pending))
        self.assertIn("launch", pending[0].action_title.lower())

        self.service.ApproveStep(
            pb2.ApproveStepRequest(
                task_id=task.task_id,
                step_id=pending[0].step_id,
                approved_by="tests",
                note="approved",
            ),
            _FakeContext(),
        )
        worker.join(timeout=2)

        completed = None
        for _ in range(150):
            completed = self.memory.get_task(task.task_id)
            if completed is not None and completed.task_status == pb2.TASK_STATUS_COMPLETED:
                break
            time.sleep(0.02)
        if completed is not None and completed.task_status == pb2.TASK_STATUS_RUNNING:
            self.service._run_task(task.task_id, False)  # noqa: SLF001
            completed = self.memory.get_task(task.task_id)
        self.assertIsNotNone(completed)
        self.assertEqual(pb2.TASK_STATUS_COMPLETED, completed.task_status)
        artifacts = self.service.ListArtifacts(pb2.ListArtifactsRequest(task_id=task.task_id), _FakeContext())
        names = {item.name for item in artifacts.artifacts}
        self.assertIn("launch_application-summary.txt", names)
        self.assertIn("launch_application-result.json", names)

    def test_workspace_summary_handles_mixed_types_and_zip_inventory(self) -> None:
        conv = self.memory.upsert_conversation(
            ConversationRecord("conv-workspace", "Workspace", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")
        )
        root_dir = Path(self._temp_dir.name) / "speaker-folder"
        root_dir.mkdir(parents=True, exist_ok=True)
        (root_dir / "README.md").write_text("# Project", encoding="utf-8")
        (root_dir / "notes.txt").write_text("todo", encoding="utf-8")
        (root_dir / "data.csv").write_text("f,db\n100,82", encoding="utf-8")
        (root_dir / "config.json").write_text("{bad json", encoding="utf-8")
        (root_dir / "diagram.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (root_dir / "unknown.bin").write_bytes(b"abc")
        with zipfile.ZipFile(root_dir / "bundle.zip", "w") as archive:
            archive.writestr("inside/woofer.frd", "100 82")

        self.service.AttachWorkspaceRoot(
            pb2.AttachWorkspaceRootRequest(
                conversation_id=conv.conversation_id,
                root_path=str(root_dir),
                display_name="Speaker folder",
                access_mode=pb2.WORKSPACE_ACCESS_MODE_READ_ONLY,
            ),
            _FakeContext(),
        )

        completion = self.service._build_workspace_summary_completion(conv.conversation_id)  # noqa: SLF001
        self.assertIn("mixed-file summary", completion.content)
        self.assertIn("unsupported", completion.content.lower())
        self.assertIn("Zip inventory", completion.content)

    def test_rew_workflow_task_imports_workspace_measurements_and_persists_artifacts(self) -> None:
        conv = self.memory.upsert_conversation(
            ConversationRecord("conv-rew", "REW", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")
        )
        root_dir = Path(self._temp_dir.name) / "rew-folder"
        root_dir.mkdir(parents=True, exist_ok=True)
        (root_dir / "woofer.frd").write_text("100 82\n200 84", encoding="utf-8")
        (root_dir / "woofer.zma").write_text("100 6.4 12\n200 7.1 9", encoding="utf-8")
        with zipfile.ZipFile(root_dir / "extra.zip", "w") as archive:
            archive.writestr("inside/tweeter.frd", "1000 90\n2000 88")

        self.service.AttachWorkspaceRoot(
            pb2.AttachWorkspaceRootRequest(
                conversation_id=conv.conversation_id,
                root_path=str(root_dir),
                display_name="REW folder",
                access_mode=pb2.WORKSPACE_ACCESS_MODE_READ_ONLY,
            ),
            _FakeContext(),
        )
        task = self.memory.upsert_task(
            TaskRecord(
                task_id="task-rew",
                conversation_id=conv.conversation_id,
                task_status=pb2.TASK_STATUS_RUNNING,
                approval_status=pb2.APPROVAL_STATUS_PENDING,
                title="Open REW and import these files",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        worker = threading.Thread(target=self.service._run_task, args=(task.task_id, True), daemon=True)  # noqa: SLF001
        worker.start()

        pending = []
        for _ in range(20):
            pending = self.memory.list_pending_approvals()
            if pending:
                break
            time.sleep(0.01)
        self.assertTrue(pending)
        self.service.ApproveStep(
            pb2.ApproveStepRequest(task_id=task.task_id, step_id=pending[0].step_id, approved_by="tests", note="yes"),
            _FakeContext(),
        )
        worker.join(timeout=2)
        artifacts = self.service.ListArtifacts(pb2.ListArtifactsRequest(task_id=task.task_id), _FakeContext())
        names = {item.name for item in artifacts.artifacts}
        self.assertIn("rew-workflow-result.json", names)
        self.assertIn("rew-workflow-summary.md", names)

    def test_email_task_is_approval_gated_and_can_be_denied(self) -> None:
        self.memory.upsert_conversation(
            ConversationRecord("conv-email", "Email", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")
        )
        task = self.memory.upsert_task(
            TaskRecord(
                task_id="task-email-denied",
                conversation_id="conv-email",
                task_status=pb2.TASK_STATUS_RUNNING,
                approval_status=pb2.APPROVAL_STATUS_PENDING,
                title="Send email to jane@example.com subject: Hello body: Test",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
        )

        worker = threading.Thread(target=self.service._run_task, args=(task.task_id, True), daemon=True)  # noqa: SLF001
        worker.start()
        pending = []
        for _ in range(20):
            pending = self.memory.list_pending_approvals()
            if pending:
                break
            time.sleep(0.02)
        self.assertTrue(pending)
        self.service.ApproveStep(
            pb2.ApproveStepRequest(task_id=task.task_id, step_id=pending[0].step_id, approved_by="tests", note="deny"),
            _FakeContext(),
        )
        worker.join(timeout=2)
        updated = self.memory.get_task(task.task_id)
        self.assertIsNotNone(updated)
        self.assertEqual(pb2.TASK_STATUS_CANCELED, updated.task_status)
        artifacts = self.service.ListArtifacts(pb2.ListArtifactsRequest(task_id=task.task_id), _FakeContext())
        names = {item.name for item in artifacts.artifacts}
        self.assertIn("email-draft-preview.json", names)

    def test_browser_download_and_upload_artifacts_are_persisted(self) -> None:
        conv = self.memory.upsert_conversation(
            ConversationRecord("conv-browser", "Browser", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")
        )
        root_dir = Path(self._temp_dir.name) / "browser-workspace"
        root_dir.mkdir(parents=True, exist_ok=True)
        (root_dir / "note.txt").write_text("hello", encoding="utf-8")
        self.service.AttachWorkspaceRoot(
            pb2.AttachWorkspaceRootRequest(
                conversation_id=conv.conversation_id,
                root_path=str(root_dir),
                display_name="Browser workspace",
                access_mode=pb2.WORKSPACE_ACCESS_MODE_READ_ONLY,
            ),
            _FakeContext(),
        )
        download_task = self.memory.upsert_task(
            TaskRecord(
                task_id="task-browser-download",
                conversation_id=conv.conversation_id,
                task_status=pb2.TASK_STATUS_RUNNING,
                approval_status=pb2.APPROVAL_STATUS_PENDING,
                title="Browser download https://example.com/file.txt",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        self.service._run_task(download_task.task_id, True)  # noqa: SLF001
        artifacts = self.service.ListArtifacts(pb2.ListArtifactsRequest(task_id=download_task.task_id), _FakeContext())
        names = {item.name for item in artifacts.artifacts}
        self.assertIn("browser-download-record.json", names)
        self.assertIn("browser-session-result.json", names)

        upload_task = self.memory.upsert_task(
            TaskRecord(
                task_id="task-browser-upload",
                conversation_id=conv.conversation_id,
                task_status=pb2.TASK_STATUS_RUNNING,
                approval_status=pb2.APPROVAL_STATUS_PENDING,
                title="Browser upload to https://example.com/upload",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        self.service._run_task(upload_task.task_id, True)  # noqa: SLF001
        artifacts = self.service.ListArtifacts(pb2.ListArtifactsRequest(task_id=upload_task.task_id), _FakeContext())
        names = {item.name for item in artifacts.artifacts}
        self.assertIn("browser-upload-record.json", names)

    def test_messaging_provider_not_supported_failure_is_typed(self) -> None:
        payload = self.service._default_settings_payload("2026-01-01T00:00:00Z")  # noqa: SLF001
        payload["communications"]["messaging"]["provider"] = "sms"
        self.memory.upsert_app_setting(
            AppSettingRecord(
                setting_key="model_provider_settings_v1",
                setting_value=json.dumps(payload),
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        result = self.service._send_message_via_supported_path(  # noqa: SLF001
            type("Intent", (), {"provider": "sms", "destination": "+15551234567", "body": "Hi"})()
        )
        self.assertFalse(result["is_success"])
        self.assertIn("NOT_YET_SUPPORTED", str(result["detail"]))

    def test_email_send_fails_with_missing_config(self) -> None:
        result = self.service._send_email_via_supported_path(  # noqa: SLF001
            type(
                "EmailIntent",
                (),
                {
                    "provider": "smtp",
                    "to": "jane@example.com",
                    "subject": "Hello",
                    "body": "Body",
                    "attachments": [],
                },
            )()
        )
        self.assertFalse(result["is_success"])
        self.assertEqual("missing_config", result["result_type"])

    def test_frd_zma_analysis_task_persists_crossover_recommendations(self) -> None:
        conv = self.memory.upsert_conversation(
            ConversationRecord("conv-xo", "XO", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")
        )
        root_dir = Path(self._temp_dir.name) / "xo-folder"
        root_dir.mkdir(parents=True, exist_ok=True)
        (root_dir / "driver.frd").write_text("100 82\n500 87\n1000 86\n2000 83", encoding="utf-8")
        (root_dir / "driver.zma").write_text("80 5.8 10\n500 7.1 20\n1500 8.5 30\n2500 10.1 32", encoding="utf-8")
        self.service.AttachWorkspaceRoot(
            pb2.AttachWorkspaceRootRequest(
                conversation_id=conv.conversation_id,
                root_path=str(root_dir),
                display_name="XO folder",
                access_mode=pb2.WORKSPACE_ACCESS_MODE_READ_ONLY,
            ),
            _FakeContext(),
        )

        task = self.memory.upsert_task(
            TaskRecord(
                task_id="task-xo",
                conversation_id=conv.conversation_id,
                task_status=pb2.TASK_STATUS_RUNNING,
                approval_status=pb2.APPROVAL_STATUS_PENDING,
                title="Suggest a crossover region",
                created_at="2026-01-01T00:00:00Z",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        self.service._run_task(task.task_id, False)  # noqa: SLF001
        artifacts = self.service.ListArtifacts(pb2.ListArtifactsRequest(task_id=task.task_id), _FakeContext())
        names = {item.name for item in artifacts.artifacts}
        self.assertIn("frd-zma-analysis.md", names)
        self.assertIn("crossover-recommendations.json", names)


if __name__ == "__main__":
    unittest.main()
