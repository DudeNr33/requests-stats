import re
from dataclasses import dataclass
from urllib.parse import urlparse

import openapi_parser

from requests_stats.core.recording import Recording
from requests_stats.core.base_storage import Storage


@dataclass(frozen=True)
class NormalizedRecording:
    method: str
    original_path: str
    normalized_path: str
    response_code: int


class Coverage:
    def __init__(self, openapi_file_path: str) -> None:
        self.spec = openapi_parser.parse(openapi_file_path, strict_enum=False)
        self.covered: set[tuple[str, str, int]] = set()
        self.uncovered: set[tuple[str, str, int]] = set()
        self.extra: set[tuple[str, str, int]] = set()
        self.extra_details: list[tuple[str, str, str, int]] = []
        self._path_templates = self._build_path_templates()
        self._server_base_paths = self._build_server_base_paths()

    def load(self, storage: Storage) -> None:
        normalized_recordings = [
            self._normalize_recording(rec) for rec in storage.load()
        ]
        recorded_requests = {
            (rec.method, rec.normalized_path, rec.response_code)
            for rec in normalized_recordings
        }
        all_endpoints = self._all_endpoints()
        self.covered = recorded_requests & all_endpoints
        self.uncovered = all_endpoints - recorded_requests
        self.extra = recorded_requests - all_endpoints
        extra_map: dict[tuple[str, str, int], NormalizedRecording] = {}
        for rec in normalized_recordings:
            key = (rec.method, rec.normalized_path, rec.response_code)
            extra_map.setdefault(key, rec)
        self.extra_details = [
            (rec.method, rec.original_path, rec.normalized_path, rec.response_code)
            for key, rec in extra_map.items()
            if key in self.extra
        ]

    def _all_endpoints(self) -> set[tuple[str, str, int]]:
        endpoints = set()
        for path in self.spec.paths:
            for operation in path.operations:
                for response in operation.responses:
                    if response.is_default or response.code is None:
                        continue
                    endpoints.add(
                        (
                            operation.method.name,
                            path.url,
                            int(response.code),
                        )
                    )
        return endpoints

    def _normalize_recording(self, recording: Recording) -> NormalizedRecording:
        # TODO: check what is actually needed - maybe only path params?
        method = (recording.method or "").upper()
        original_path = recording.url or ""
        path = original_path
        if (
            "://" in path
        ):  # TODO: should be taken care of by adapter, check how to enforce this
            parsed_url = urlparse(path)
            path = parsed_url.path
            if parsed_url.query:
                path = f"{path}?{parsed_url.query}"
        path = path.split("?", 1)[0]
        path = self._strip_server_base_path(path)
        path = self._apply_template(path)
        return NormalizedRecording(
            method=method,
            original_path=original_path,
            normalized_path=path,
            response_code=recording.response_code,
        )

    def _build_path_templates(self) -> list[tuple[re.Pattern[str], str]]:
        templates = []
        for path in self.spec.paths:
            pattern = "^" + re.sub(r"\{[^/]+\}", "[^/]+", path.url) + "$"
            templates.append((re.compile(pattern), path.url))
        return templates

    def _build_server_base_paths(self) -> list[str]:
        base_paths: list[str] = []
        for server in getattr(self.spec, "servers", []) or []:
            url = getattr(server, "url", "")
            if not url:
                continue
            base_path = urlparse(url).path or ""
            if not base_path or base_path == "/":
                continue
            base_paths.append(base_path.rstrip("/"))
        return sorted(set(base_paths), key=len, reverse=True)

    def _strip_server_base_path(self, path: str) -> str:
        for base_path in self._server_base_paths:
            if path == base_path:
                return "/"
            if path.startswith(base_path + "/"):
                return path[len(base_path) :]
        return path

    def _apply_template(self, path: str) -> str:
        for pattern, template in self._path_templates:
            if pattern.match(path):
                return template
        return path
