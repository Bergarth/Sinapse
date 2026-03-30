"""Local secret storage with Windows DPAPI at rest encryption."""

from __future__ import annotations

import base64
import ctypes
import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredSecret:
    secret_ref: str
    created_at: str


class SecretStore:
    """Persist API secrets in a local encrypted file.

    On Windows this uses DPAPI (CryptProtectData/CryptUnprotectData). On
    non-Windows systems this fails closed with an explicit error.
    """

    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

    def put_secret(self, *, key: str, secret_value: str, created_at: str) -> StoredSecret:
        normalized_key = key.strip().lower()
        if not normalized_key:
            raise ValueError("Secret key is required.")
        if not secret_value.strip():
            raise ValueError("Secret value is required.")

        if os.name != "nt":
            raise ValueError(
                "Secure API key storage requires Windows. Run the daemon on Windows to save API keys securely."
            )

        payload = self._read_payload()
        encrypted = _encrypt_for_current_user(secret_value.encode("utf-8"))
        payload[normalized_key] = {
            "ciphertext_b64": base64.b64encode(encrypted).decode("ascii"),
            "created_at": created_at,
        }
        self._storage_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return StoredSecret(secret_ref=f"secret://local/{normalized_key}", created_at=created_at)

    def has_secret(self, key: str) -> bool:
        normalized_key = key.strip().lower()
        if not normalized_key:
            return False
        return normalized_key in self._read_payload()

    def _read_payload(self) -> dict:
        if not self._storage_path.exists():
            return {}
        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(data, dict):
            return {}
        return data


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob_from_bytes(data: bytes) -> _DATA_BLOB:
    buffer = ctypes.create_string_buffer(data, len(data))
    return _DATA_BLOB(
        cbData=len(data),
        pbData=ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)),
    )


def _bytes_from_blob(blob: _DATA_BLOB) -> bytes:
    if not blob.pbData or blob.cbData == 0:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def _encrypt_for_current_user(payload: bytes) -> bytes:
    in_blob = _blob_from_bytes(payload)
    out_blob = _DATA_BLOB()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise ValueError("Windows DPAPI encryption failed while storing API key.")
    try:
        return _bytes_from_blob(out_blob)
    finally:
        if out_blob.pbData:
            kernel32.LocalFree(out_blob.pbData)
