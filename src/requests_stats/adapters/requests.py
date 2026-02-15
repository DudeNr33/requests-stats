from typing import Mapping, cast
from urllib.parse import ParseResult, urlparse

from requests import PreparedRequest, Response
from requests.adapters import HTTPAdapter, Retry

from requests_stats.core.base_storage import Storage
from requests_stats.core.recording import Recording

MISSING = "UNKNOWN"


class RecordingHTTPAdapter(HTTPAdapter):
    def __init__(
        self,
        storage: Storage,
        pool_connections: int = 10,
        pool_maxsize: int = 10,
        max_retries: Retry | int | None = 0,
        pool_block: bool = False,
    ) -> None:
        super().__init__(pool_connections, pool_maxsize, max_retries, pool_block)
        self.storage = storage

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: None | float | tuple[float, float] | tuple[float, None] = None,
        verify: bool | str = True,
        cert: None | bytes | str | tuple[bytes | str, bytes | str] = None,
        proxies: Mapping[str, str] | None = None,
    ) -> Response:
        parsed = cast(ParseResult, urlparse(request.url))
        response = super().send(request, stream, timeout, verify, cert, proxies)
        recording = Recording(
            method=request.method or MISSING,
            url=parsed.path or MISSING,
            params=parsed.params or MISSING,
            response_code=response.status_code,
            duration=response.elapsed.total_seconds(),
        )
        self.storage.store(recording)
        return response
