from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

import grpc

from agent_daemon.server import DaemonContractService, pb2
from agent_daemon.services.memory import (
    ApprovalRecord,
    ConversationRecord,
    MemoryService,
    TaskRecord,
    TaskStepRecord,
)
from agent_daemon.services.secret_store import SecretStore


class _DummyWindowsOperator:
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

    def open_url(self, url: str):
        _ = url
        return type("Result", (), {"is_success": False, "detail": "not used", "snapshot": None})()


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
        self.service = DaemonContractService(
            memory_service=self.memory,
            windows_operator_service=_DummyWindowsOperator(),
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
        for _ in range(50):
            completed = self.memory.get_task(task.task_id)
            if completed is not None and completed.task_status == pb2.TASK_STATUS_COMPLETED:
                break
            time.sleep(0.02)
        self.assertIsNotNone(completed)
        self.assertEqual(pb2.TASK_STATUS_COMPLETED, completed.task_status)
        artifacts = self.service.ListArtifacts(pb2.ListArtifactsRequest(task_id=task.task_id), _FakeContext())
        names = {item.name for item in artifacts.artifacts}
        self.assertIn("launch_application-summary.txt", names)
        self.assertIn("launch_application-result.json", names)


if __name__ == "__main__":
    unittest.main()
