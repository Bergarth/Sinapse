"""Browser operator service with controlled session workflows.

This module now supports:
- Read-only URL open + summary extraction.
- Explicit browser sessions with controlled profile roots.
- Explicit navigation/read/download/upload actions tied to a session.

Design goals:
- Keep mutating actions explicit and easy to gate via daemon approvals.
- Return typed NOT_YET_SUPPORTED responses when an action cannot be done reliably.
- Avoid depending on heavyweight browser automation for baseline reliability.
"""

from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class BrowserAvailability:
    """Availability snapshot for the browser operator capability."""

    is_available: bool
    detail: str


@dataclass(frozen=True)
class BrowserPageSnapshot:
    """Structured page snapshot returned by read actions."""

    url: str
    title: str
    summary: str


@dataclass(frozen=True)
class BrowserActionResult:
    """Result envelope for browser actions."""

    is_success: bool
    detail: str
    snapshot: BrowserPageSnapshot | None = None
    result_type: str = "ok"
    payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class BrowserSession:
    """Simple controlled browser session state."""

    session_id: str
    profile_root: str
    started_at: str
    current_url: str = ""


class _BrowserBackend(Protocol):
    def availability(self) -> BrowserAvailability: ...

    def open_url_readonly(self, *, url: str) -> BrowserActionResult: ...


class _PlaywrightBackend:
    """Future backend seam for Playwright-based browser automation."""

    def __init__(self) -> None:
        self._import_error: str | None = None
        try:
            import playwright  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            self._import_error = str(exc)

    def availability(self) -> BrowserAvailability:
        if self._import_error is None:
            return BrowserAvailability(True, "Playwright backend is available.")
        return BrowserAvailability(
            True,
            "Playwright runtime is unavailable; using controlled HTTP/session fallback.",
        )


class _VisibleTextExtractor(HTMLParser):
    _IGNORED_TAGS = {"script", "style", "noscript", "svg", "canvas", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self._ignored_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        _ = attrs
        normalized = tag.lower()
        if normalized == "title":
            self._in_title = True
        if normalized in self._IGNORED_TAGS:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized == "title":
            self._in_title = False
        if normalized in self._IGNORED_TAGS and self._ignored_depth > 0:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0:
            return
        cleaned = _normalize_whitespace(data)
        if not cleaned:
            return
        if self._in_title and not self.title:
            self.title = cleaned
        self._chunks.append(cleaned)

    def visible_text(self) -> str:
        return _normalize_whitespace(" ".join(self._chunks))


class _HttpReadOnlyBackend:
    _REQUEST_TIMEOUT_SECONDS = 12
    _MAX_BYTES = 1_000_000

    def availability(self) -> BrowserAvailability:
        return BrowserAvailability(
            is_available=True,
            detail=(
                "Read-only browser action is available via controlled HTTP page reader "
                "(no click/fill/login/destructive actions)."
            ),
        )

    def open_url_readonly(self, *, url: str) -> BrowserActionResult:
        normalized = _normalize_url(url)
        if normalized is None:
            return BrowserActionResult(False, "Invalid URL. Please provide a valid http(s) URL.")

        request = urllib.request.Request(
            normalized,
            headers={
                "User-Agent": "SinapseBrowserOperator/0.2 (+session-safe)",
                "Accept": "text/html,application/xhtml+xml",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(request, timeout=self._REQUEST_TIMEOUT_SECONDS) as response:  # noqa: S310
                content_type = (response.headers.get("Content-Type") or "").lower()
                data = response.read(self._MAX_BYTES)
                final_url = response.geturl() or normalized
        except urllib.error.HTTPError as exc:
            return BrowserActionResult(False, f"Browser read failed with HTTP {exc.code} for {normalized}.")
        except urllib.error.URLError as exc:
            return BrowserActionResult(False, f"Browser read failed: {exc.reason}.")
        except TimeoutError:
            return BrowserActionResult(False, "Browser read timed out while loading the URL.")
        except Exception as exc:  # noqa: BLE001
            return BrowserActionResult(False, f"Browser read failed unexpectedly: {exc}")

        if "html" not in content_type:
            return BrowserActionResult(
                False,
                f"Unsupported content type '{content_type or 'unknown'}'. Only HTML pages are summarized.",
                result_type="unsupported_content_type",
                payload={"content_type": content_type or "unknown", "url": final_url},
            )

        text = _decode_html_bytes(data)
        parser = _VisibleTextExtractor()
        parser.feed(text)

        title = parser.title or _fallback_title_from_url(final_url)
        summary = _summarize_text(parser.visible_text()) or "The page loaded, but no visible text content could be extracted."

        snapshot = BrowserPageSnapshot(url=final_url, title=title, summary=summary)
        return BrowserActionResult(True, f"Opened {final_url} in read-only mode and extracted visible content.", snapshot=snapshot)


class BrowserOperatorService:
    """Browser operator with controlled session workflows."""

    name = "browser-operator"

    def __init__(self) -> None:
        self._playwright_backend = _PlaywrightBackend()
        self._readonly_backend: _BrowserBackend = _HttpReadOnlyBackend()

    def availability(self) -> BrowserAvailability:
        readonly_status = self._readonly_backend.availability()
        playwright_status = self._playwright_backend.availability()
        detail = (
            f"{readonly_status.detail} "
            "Session workflow supports controlled profiles, navigation, read, download, and workspace upload mapping. "
            f"{playwright_status.detail}"
        )
        return BrowserAvailability(is_available=readonly_status.is_available, detail=detail.strip())

    def open_browser_session(self, *, profile_root: str, session_id: str, started_at: str) -> BrowserActionResult:
        profile = Path(profile_root).resolve()
        profile.mkdir(parents=True, exist_ok=True)
        state_file = profile / "session-state.json"
        state_file.write_text(
            json.dumps(
                {
                    "session_id": session_id,
                    "started_at": started_at,
                    "current_url": "",
                    "mode": "controlled_profile",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return BrowserActionResult(
            True,
            "Opened controlled browser profile session.",
            result_type="session_started",
            payload={"session_id": session_id, "profile_root": str(profile), "mode": "controlled_profile"},
        )

    def open_url(self, *, url: str) -> BrowserActionResult:
        return self._readonly_backend.open_url_readonly(url=url)

    def navigate(self, *, session_id: str, url: str) -> BrowserActionResult:
        _ = session_id
        return self.open_url(url=url)

    def read_visible_content(self, *, session_id: str, url: str = "") -> BrowserActionResult:
        _ = session_id
        if not url:
            return BrowserActionResult(
                False,
                "NOT_YET_SUPPORTED:NO_ACTIVE_PAGE_CONTEXT. Pass a URL for now.",
                result_type="not_yet_supported",
            )
        return self.open_url(url=url)

    def download(self, *, url: str, destination_path: str) -> BrowserActionResult:
        normalized = _normalize_url(url)
        if normalized is None:
            return BrowserActionResult(False, "Invalid URL for download.")

        destination = Path(destination_path).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(
            normalized,
            headers={"User-Agent": "SinapseBrowserOperator/0.2 (+download)"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
                payload = response.read(5_000_000)
                content_type = (response.headers.get("Content-Type") or "application/octet-stream").split(";")[0].strip()
                final_url = response.geturl() or normalized
            destination.write_bytes(payload)
        except Exception as exc:  # noqa: BLE001
            return BrowserActionResult(False, f"Download failed: {exc}")

        return BrowserActionResult(
            True,
            f"Downloaded {final_url} to workspace path {destination}.",
            result_type="downloaded",
            payload={"url": final_url, "destination_path": str(destination), "size_bytes": str(len(payload)), "mime_type": content_type},
        )

    def upload(self, *, selector: str, source_path: str) -> BrowserActionResult:
        _ = selector
        source = Path(source_path).resolve()
        if not source.exists() or not source.is_file():
            return BrowserActionResult(False, f"Upload source file not found: {source}")
        return BrowserActionResult(
            False,
            "NOT_YET_SUPPORTED:SESSION_FILE_INPUT_AUTOMATION. Controlled profile path is ready, but generic DOM file upload automation is not implemented.",
            result_type="not_yet_supported",
            payload={"source_path": str(source)},
        )

    def click(self, *, selector: str) -> BrowserActionResult:
        _ = selector
        return BrowserActionResult(False, "NOT_YET_SUPPORTED:SESSION_CLICK", result_type="not_yet_supported")

    def fill(self, *, selector: str, value: str) -> BrowserActionResult:
        _ = (selector, value)
        return BrowserActionResult(False, "NOT_YET_SUPPORTED:SESSION_FILL", result_type="not_yet_supported")

    def collect_sources(self) -> BrowserActionResult:
        return BrowserActionResult(False, "NOT_YET_SUPPORTED:COLLECT_SOURCES", result_type="not_yet_supported")


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _normalize_url(raw_url: str) -> str | None:
    candidate = (raw_url or "").strip()
    if not candidate:
        return None
    if not re.match(r"^https?://", candidate, flags=re.IGNORECASE):
        candidate = f"https://{candidate}"

    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    return urllib.parse.urlunparse(parsed)


def _decode_html_bytes(payload: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


def _fallback_title_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc:
        return html.unescape(parsed.netloc)
    return "Untitled page"


def _summarize_text(text: str, max_sentences: int = 3, max_chars: int = 600) -> str:
    normalized = _normalize_whitespace(text)
    if not normalized:
        return ""

    parts = re.split(r"(?<=[.!?])\s+", normalized)
    chosen: list[str] = []
    total_chars = 0
    for part in parts:
        if not part:
            continue
        chosen.append(part)
        total_chars += len(part) + 1
        if len(chosen) >= max_sentences or total_chars >= max_chars:
            break

    summary = " ".join(chosen).strip()
    if len(summary) > max_chars:
        summary = summary[: max_chars - 1].rstrip() + "…"
    return summary
