"""Workspace file intake helpers for mixed speaker-design folders."""

from __future__ import annotations

import csv
import json
import mimetypes
import zipfile
from dataclasses import dataclass
from pathlib import Path


_TEXT_EXTENSIONS = {".txt", ".md", ".frd", ".zma", ".csv", ".json"}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
_SUPPORTED_EXTENSIONS = _TEXT_EXTENSIONS | _IMAGE_EXTENSIONS | {".zip"}


@dataclass(frozen=True)
class FileIntakeInfo:
    relative_path: str
    file_type: str
    mime_type: str
    is_supported: bool
    warning: str = ""


@dataclass(frozen=True)
class ZipInventory:
    file_path: str
    entries: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class WorkspaceSummary:
    total_files: int
    supported_files: int
    unsupported_files: int
    counts_by_type: dict[str, int]
    sample_supported: list[str]
    sample_unsupported: list[str]
    zip_inventories: list[ZipInventory]
    warnings: list[str]


def detect_file_intake_info(root_path: Path, relative_path: str) -> FileIntakeInfo:
    full_path = (root_path / relative_path).resolve()
    suffix = Path(relative_path).suffix.lower()
    mime = mimetypes.guess_type(relative_path)[0] or "application/octet-stream"

    if suffix in {".frd", ".zma"}:
        return FileIntakeInfo(relative_path, suffix[1:].upper(), mime, True)
    if suffix in {".txt", ".md"}:
        return FileIntakeInfo(relative_path, "text", mime, True)
    if suffix == ".json":
        warning = ""
        try:
            json.loads(full_path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            warning = "Could not read JSON file during intake."
        except json.JSONDecodeError:
            warning = "JSON syntax appears invalid."
        return FileIntakeInfo(relative_path, "json", mime, True, warning=warning)
    if suffix == ".csv":
        warning = ""
        try:
            text = full_path.read_text(encoding="utf-8", errors="replace")
            rows = list(csv.reader(text.splitlines()[:5]))
            if rows and len(rows[0]) < 2:
                warning = "CSV appears to have very few columns."
        except OSError:
            warning = "Could not read CSV file during intake."
        return FileIntakeInfo(relative_path, "csv", mime, True, warning=warning)
    if suffix in _IMAGE_EXTENSIONS:
        return FileIntakeInfo(relative_path, "image", mime, True)
    if suffix == ".zip":
        return FileIntakeInfo(relative_path, "zip", "application/zip", True)

    warning = f"Unsupported file type: {suffix or 'no extension'}"
    return FileIntakeInfo(relative_path, "unsupported", mime, False, warning=warning)


def inventory_zip_file(zip_path: Path, *, max_entries: int = 250) -> ZipInventory:
    entries: list[str] = []
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            names = archive.namelist()
            entries = names[:max_entries]
            if len(names) > max_entries:
                warnings.append(f"Zip inventory truncated to first {max_entries} entries.")
            if any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
                warnings.append("Zip contains unsafe traversal-like paths; extraction requires strict filtering.")
    except (OSError, zipfile.BadZipFile) as exc:
        warnings.append(f"Could not read zip inventory: {exc}")

    return ZipInventory(file_path=str(zip_path), entries=entries, warnings=warnings)


def controlled_extract_zip(
    zip_path: Path,
    *,
    destination_root: Path,
    allowed_extensions: set[str],
    max_files: int = 50,
) -> tuple[list[Path], list[str]]:
    """Extract a limited subset into a controlled destination path."""
    destination_root.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    warnings: list[str] = []

    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            for member in archive.infolist():
                if len(extracted) >= max_files:
                    warnings.append(f"Extraction limited to {max_files} files.")
                    break
                member_path = Path(member.filename)
                if member.is_dir():
                    continue
                if member_path.is_absolute() or ".." in member_path.parts:
                    warnings.append(f"Skipped unsafe zip member: {member.filename}")
                    continue
                if member_path.suffix.lower() not in allowed_extensions:
                    continue

                target = (destination_root / member_path).resolve()
                if destination_root.resolve() not in target.parents and target != destination_root.resolve():
                    warnings.append(f"Skipped out-of-root extraction target: {member.filename}")
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member, "r") as source, target.open("wb") as sink:
                    sink.write(source.read())
                extracted.append(target)
    except (OSError, zipfile.BadZipFile) as exc:
        warnings.append(f"Extraction failed: {exc}")

    return extracted, warnings


def summarize_workspace(root_path: Path, relative_paths: list[str]) -> WorkspaceSummary:
    counts_by_type: dict[str, int] = {}
    supported = 0
    unsupported = 0
    sample_supported: list[str] = []
    sample_unsupported: list[str] = []
    warnings: list[str] = []
    zip_inventories: list[ZipInventory] = []

    for relative_path in relative_paths:
        info = detect_file_intake_info(root_path, relative_path)
        counts_by_type[info.file_type] = counts_by_type.get(info.file_type, 0) + 1
        if info.is_supported:
            supported += 1
            if len(sample_supported) < 12:
                sample_supported.append(relative_path)
        else:
            unsupported += 1
            if len(sample_unsupported) < 12:
                sample_unsupported.append(f"{relative_path} ({info.warning})")

        if info.warning:
            warnings.append(f"{relative_path}: {info.warning}")

        if info.file_type == "zip":
            zip_inventories.append(inventory_zip_file((root_path / relative_path).resolve()))

    return WorkspaceSummary(
        total_files=len(relative_paths),
        supported_files=supported,
        unsupported_files=unsupported,
        counts_by_type=counts_by_type,
        sample_supported=sample_supported,
        sample_unsupported=sample_unsupported,
        zip_inventories=zip_inventories,
        warnings=warnings[:25],
    )
