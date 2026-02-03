import json
from pathlib import Path

from requests_stats.openapi.coverage import Coverage
from requests_stats.recorder.base import Recording


class ListRecorder:
    def __init__(self, recordings: list[Recording]) -> None:
        self._recordings = recordings

    def load(self) -> list[Recording]:
        return list(self._recordings)


def write_spec(tmp_path: Path) -> Path:
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Petstore", "version": "1.0.0"},
        "servers": [{"url": "http://localhost:8080/api/v3"}],
        "paths": {
            "/pet/{petId}": {
                "get": {
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            },
            "/hello": {"get": {"responses": {"200": {"description": "ok"}}}},
        },
    }
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps(spec))
    return spec_file


def test_coverage_normalizes_server_prefix_and_templates(tmp_path: Path) -> None:
    spec_file = write_spec(tmp_path)
    recordings = [
        Recording(
            method="GET",
            url="/api/v3/pet/1001",
            response_code=200,
            duration=0.1,
        )
    ]
    coverage = Coverage(openapi_file_path=str(spec_file))
    coverage.load(ListRecorder(recordings))

    assert ("GET", "/pet/{petId}", 200) in coverage.covered
    assert coverage.extra == set()


def test_coverage_strips_query_string(tmp_path: Path) -> None:
    spec_file = write_spec(tmp_path)
    recordings = [
        Recording(
            method="GET",
            url="/api/v3/hello?status=available",
            response_code=200,
            duration=0.1,
        )
    ]
    coverage = Coverage(openapi_file_path=str(spec_file))
    coverage.load(ListRecorder(recordings))

    assert ("GET", "/hello", 200) in coverage.covered
    assert coverage.extra == set()
