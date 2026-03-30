"""Browser operator placeholder service.

No real browser automation is performed yet. This module exposes the contract
surface that the daemon can wire into capability/status APIs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserAvailability:
    """Availability snapshot for the browser operator capability."""

    is_available: bool
    detail: str


@dataclass(frozen=True)
class BrowserActionResult:
    """Placeholder result for future browser actions."""

    is_success: bool
    detail: str


class BrowserOperatorService:
    """Placeholder browser operator service.

    This service is intentionally contract-first with no runtime browser
    dependency yet, so the daemon/shell can wire status and future actions
    before Playwright implementation lands.
    """

    name = "browser-operator"

    def availability(self) -> BrowserAvailability:
        return BrowserAvailability(
            is_available=True,
            detail="Web browsing support is connected and ready for future automation.",
        )

    def search_web(self, *, query: str) -> BrowserActionResult:
        _ = query
        return BrowserActionResult(False, "Not implemented yet: search_web")

    def open_url(self, *, url: str) -> BrowserActionResult:
        _ = url
        return BrowserActionResult(False, "Not implemented yet: open_url")

    def click(self, *, selector: str) -> BrowserActionResult:
        _ = selector
        return BrowserActionResult(False, "Not implemented yet: click")

    def fill(self, *, selector: str, value: str) -> BrowserActionResult:
        _ = (selector, value)
        return BrowserActionResult(False, "Not implemented yet: fill")

    def download(self, *, url: str, destination_path: str) -> BrowserActionResult:
        _ = (url, destination_path)
        return BrowserActionResult(False, "Not implemented yet: download")

    def upload(self, *, selector: str, source_path: str) -> BrowserActionResult:
        _ = (selector, source_path)
        return BrowserActionResult(False, "Not implemented yet: upload")

    def collect_sources(self) -> BrowserActionResult:
        return BrowserActionResult(False, "Not implemented yet: collect_sources")
