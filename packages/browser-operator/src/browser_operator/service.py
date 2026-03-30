"""Read-only browser operator service.

This module implements the first real browser action: opening a URL in a
controlled, read-only context and returning a visible text summary.

Design notes:
- Keeps a backend seam so Playwright can be added later.
- Defaults to a safe HTTP reader backend that performs no form/login/clicking.
- Surfaces clear errors when optional browser dependencies are unavailable.
"""

from __future__ import annotations

import html
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Protocol


@dataclass(frozen=True)
class BrowserAvailability:
    """Availability snapshot for the browser operator capability."""

    is_available: bool
    detail: str


@dataclass(frozen=True)
class BrowserPageSnapshot:
    """Structured page snapshot returned by read-only open-url actions."""

    url: str
    title: str
    summary: str


@dataclass(frozen=True)
class BrowserActionResult:
    """Result envelope for browser actions."""

    is_success: bool
    detail: str
    snapshot: BrowserPageSnapshot | None = None


class _BrowserBackend(Protocol):
    """Backend contract used by the browser operator service."""

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
            "Playwright runtime is unavailable; using safe HTTP fallback for read-only open-url actions.",
        )

    def open_url_readonly(self, *, url: str) -> BrowserActionResult:
        return BrowserActionResult(
            False,
            "Playwright backend is not implemented yet. Use HTTP fallback backend.",
        )


class _VisibleTextExtractor(HTMLParser):
    """Extract visible title/text content while ignoring non-visible tags."""

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
        merged = " ".join(self._chunks)
        return _normalize_whitespace(merged)


class _HttpReadOnlyBackend:
    """Safe, read-only backend using HTTP fetch + HTML text extraction."""

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
                "User-Agent": "SinapseBrowserOperator/0.1 (+read-only)",
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
            )

        text = _decode_html_bytes(data)
        parser = _VisibleTextExtractor()
        parser.feed(text)

        title = parser.title or _fallback_title_from_url(final_url)
        summary = _summarize_text(parser.visible_text())
        if not summary:
            summary = "The page loaded, but no visible text content could be extracted."

        snapshot = BrowserPageSnapshot(url=final_url, title=title, summary=summary)
        return BrowserActionResult(
            True,
            f"Opened {final_url} in read-only mode and extracted visible content.",
            snapshot=snapshot,
        )


class BrowserOperatorService:
    """Browser operator with first safe read-only action implementation."""

    name = "browser-operator"

    def __init__(self) -> None:
        self._playwright_backend = _PlaywrightBackend()
        self._readonly_backend: _BrowserBackend = _HttpReadOnlyBackend()

    def availability(self) -> BrowserAvailability:
        readonly_status = self._readonly_backend.availability()
        playwright_status = self._playwright_backend.availability()
        detail = f"{readonly_status.detail} {playwright_status.detail}"
        return BrowserAvailability(is_available=readonly_status.is_available, detail=detail.strip())

    def search_web(self, *, query: str) -> BrowserActionResult:
        _ = query
        return BrowserActionResult(False, "Not implemented yet: search_web")

    def open_url(self, *, url: str) -> BrowserActionResult:
        return self._readonly_backend.open_url_readonly(url=url)

    def click(self, *, selector: str) -> BrowserActionResult:
        _ = selector
        return BrowserActionResult(False, "Blocked: click is not enabled yet (read-only mode only).")

    def fill(self, *, selector: str, value: str) -> BrowserActionResult:
        _ = (selector, value)
        return BrowserActionResult(False, "Blocked: fill is not enabled yet (read-only mode only).")

    def download(self, *, url: str, destination_path: str) -> BrowserActionResult:
        _ = (url, destination_path)
        return BrowserActionResult(False, "Not implemented yet: download")

    def upload(self, *, selector: str, source_path: str) -> BrowserActionResult:
        _ = (selector, source_path)
        return BrowserActionResult(False, "Blocked: upload is not enabled yet (read-only mode only).")

    def collect_sources(self) -> BrowserActionResult:
        return BrowserActionResult(False, "Not implemented yet: collect_sources")


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _normalize_url(raw_url: str) -> str | None:
    candidate = (raw_url or "").strip()
    if not candidate:
        return None

    if not re.match(r"^https?://", candidate, flags=re.IGNORECASE):
        candidate = f"https://{candidate}"

    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    if not parsed.netloc:
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
    host = parsed.netloc or url
    return f"Page at {host}"


def _summarize_text(text: str, *, max_sentences: int = 3, max_chars: int = 420) -> str:
    normalized = _normalize_whitespace(html.unescape(text))
    if not normalized:
        return ""

    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    picked = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        picked.append(sentence)
        if len(picked) >= max_sentences:
            break

    summary = " ".join(picked) if picked else normalized
    if len(summary) > max_chars:
        summary = summary[: max_chars - 1].rstrip() + "…"
    return summary
