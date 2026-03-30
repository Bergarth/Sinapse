"""Minimal REW integration bridge with explicit support boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RewOperationResult:
    operation: str
    status: str
    detail: str
    payload: dict


class RewIntegrationService:
    def __init__(self, windows_operator) -> None:
        self._windows_operator = windows_operator

    def attach_or_launch(self) -> RewOperationResult:
        windows = self._windows_operator.enumerate_open_windows()
        if windows.is_success:
            for item in windows.payload or []:
                title = str(item.get("title", "")).lower()
                if "room eq wizard" in title or title.startswith("rew") or " rew" in title:
                    return RewOperationResult(
                        operation="attach_or_launch",
                        status="attached",
                        detail="Attached to an already-running REW window.",
                        payload={"window": item},
                    )

        launch = self._windows_operator.launch_application(app_name="REW", executable_path=None)
        if launch.is_success:
            return RewOperationResult(
                operation="attach_or_launch",
                status="launched",
                detail=launch.detail,
                payload=launch.payload or {},
            )

        return RewOperationResult(
            operation="attach_or_launch",
            status="failed",
            detail=launch.detail,
            payload={},
        )

    def import_measurement_files(self, file_paths: list[Path]) -> RewOperationResult:
        imported: list[str] = []
        failed: list[str] = []
        for file_path in file_paths:
            result = self._windows_operator.open_file(file_path=str(file_path))
            if result.is_success:
                imported.append(str(file_path))
            else:
                failed.append(f"{file_path}: {result.detail}")

        status = "completed" if not failed else "partial" if imported else "failed"
        detail = f"Imported {len(imported)} file(s) into REW import flow."
        if failed:
            detail = f"Imported {len(imported)} file(s), {len(failed)} failed."

        return RewOperationResult(
            operation="import_measurements",
            status=status,
            detail=detail,
            payload={"imported": imported, "failed": failed},
        )

    @staticmethod
    def export_artifacts_not_yet_supported() -> RewOperationResult:
        return RewOperationResult(
            operation="export_artifacts",
            status="not_yet_supported",
            detail=(
                "REW export automation is not wired yet in this integration path. "
                "Sinapse returns explicit typed status instead of guessing export behavior."
            ),
            payload={"supported": False, "next_step": "Use REW export manually; attach exported files back to workspace."},
        )
