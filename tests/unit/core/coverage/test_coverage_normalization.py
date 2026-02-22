import json
from pathlib import Path

from requests_stats.core.coverage import Coverage
from requests_stats.core.recording import Recording
from requests_stats.storage.in_memory_storage import InMemoryStorage


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
    storage = InMemoryStorage()
    storage.store(
        Recording(
            method="GET",
            scheme="https",
            netloc="example.com",
            path="/api/v3/pet/1001",
            params="",
            query="",
            response_code=200,
            duration=0.1,
        )
    )
    coverage = Coverage(openapi_file_path=str(spec_file))
    coverage.load(storage)

    assert ("GET", "/pet/{petId}", 200) in coverage.covered
    assert coverage.extra == set()


def test_coverage_strips_query_string(tmp_path: Path) -> None:
    spec_file = write_spec(tmp_path)
    storage = InMemoryStorage()
    storage.store(
        Recording(
            method="GET",
            scheme="https",
            netloc="example.com",
            path="/api/v3/hello",
            params="",
            query="status=available",
            response_code=200,
            duration=0.1,
        )
    )
    coverage = Coverage(openapi_file_path=str(spec_file))
    coverage.load(storage)

    assert ("GET", "/hello", 200) in coverage.covered
    assert coverage.extra == set()
