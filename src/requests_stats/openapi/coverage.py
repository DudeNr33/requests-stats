import openapi_parser

from requests_stats.recorder.base import Recorder


class Coverage:
    def __init__(self, openapi_file_path: str) -> None:
        self.spec = openapi_parser.parse(openapi_file_path)
        self.covered: set[tuple[str, str, int]] = set()
        self.uncovered: set[tuple[str, str, int]] = set()
        self.extra: set[tuple[str, str, int]] = set()

    def load(self, recorder: Recorder) -> None:
        recorded_requests = set(
            (rec.method, rec.url, rec.response_code) for rec in recorder.load()
        )
        all_endpoints = self._all_endpoints()
        self.covered = recorded_requests & all_endpoints
        self.uncovered = all_endpoints - recorded_requests
        self.extra = recorded_requests - all_endpoints

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
