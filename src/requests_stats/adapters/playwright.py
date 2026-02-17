import re
from typing import cast
from urllib.parse import urlparse, ParseResult
from playwright.sync_api import Page as SyncPage, Request as SyncRequest

# from playwright.async_api import Page as AsyncPage, Request as AsyncRequest

from requests_stats.core.base_storage import Storage
from requests_stats.core.recording import Recording


class SyncRequestHandler:
    def __init__(self, storage: Storage, path_pattern: str | None = None) -> None:
        self.storage = storage
        self.path_pattern = re.compile(path_pattern) if path_pattern else None

    def register_on(self, page: SyncPage) -> None:
        page.on("requestfinished", self._capture_request)

    def _capture_request(self, request: SyncRequest) -> None:
        response = request.response()
        if not response:
            return  # TODO: when would this happen?
        parsed = cast(ParseResult, urlparse(request.url))
        if self.path_pattern and not self.path_pattern.match(parsed.path):
            return
        # TODO: https://developer.mozilla.org/en-US/docs/Web/API/PerformanceResourceTiming lists this for "request time", but is this the same as requests `elapsed`?
        duration_ms = request.timing["responseStart"] - request.timing["requestStart"]
        self.storage.store(
            Recording(
                method=request.method,
                url=parsed.path,
                params=parsed.params,
                response_code=response.status,
                duration=duration_ms / 1000,
            )
        )
