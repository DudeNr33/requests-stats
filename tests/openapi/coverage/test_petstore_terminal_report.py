import re
import time
from pathlib import Path

import requests
from testcontainers.core.container import DockerContainer

from requests_stats.adapter import RecordingHTTPAdapter
from requests_stats.openapi.coverage import Coverage
from requests_stats.openapi.terminal_reporter import TerminalReporter
from requests_stats.recorder.base import Recording

PETSTORE_IMAGE = "swaggerapi/petstore3"
OPENAPI_PATH = "/api/v3/openapi.json"
API_PREFIX = "/api/v3"


def wait_for_petstore(base_url: str) -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}{OPENAPI_PATH}", timeout=2)
            if response.status_code == 200:
                return
        except requests.RequestException:
            time.sleep(0.5)
    raise RuntimeError("petstore container did not become ready")


def build_path_templates(paths: dict[str, object]) -> list[tuple[re.Pattern[str], str]]:
    templates = []
    for path in paths:
        pattern = "^" + re.sub(r"\{[^/]+\}", "[^/]+", path) + "$"
        templates.append((re.compile(pattern), path))
    return templates


class PrefixStrippingRecorder:
    def __init__(
        self, prefix: str, templates: list[tuple[re.Pattern[str], str]]
    ) -> None:
        self.prefix = prefix
        self.templates = templates
        self.recordings: list[Recording] = []

    def record(self, request, response) -> None:
        path_url = (request.path_url or "").split("?", 1)[0]
        if path_url.startswith(self.prefix):
            path_url = path_url[len(self.prefix) :]
        for pattern, template in self.templates:
            if pattern.match(path_url):
                path_url = template
                break
        self.recordings.append(
            Recording(
                method=request.method or "",
                url=path_url,
                response_code=response.status_code,
                duration=response.elapsed.total_seconds(),
            )
        )

    def load(self) -> list[Recording]:
        return list(self.recordings)


def test_petstore_terminal_report(tmp_path: Path, capsys) -> None:
    with DockerContainer(PETSTORE_IMAGE).with_exposed_ports(8080) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(8080)
        base_url = f"http://{host}:{port}"
        wait_for_petstore(base_url)

        spec_response = requests.get(f"{base_url}{OPENAPI_PATH}", timeout=5)
        spec_response.raise_for_status()
        spec_data = spec_response.json()
        spec_path = tmp_path / "spec.json"
        spec_path.write_text(spec_response.text)

        templates = build_path_templates(spec_data.get("paths", {}))
        recorder = PrefixStrippingRecorder(API_PREFIX, templates)
        session = requests.Session()
        session.mount(base_url, RecordingHTTPAdapter(recorder=recorder))

        pet_payload = {
            "id": 1001,
            "name": "Test Pet",
            "photoUrls": ["https://example.com/photo"],
            "status": "available",
        }

        session.post(f"{base_url}/api/v3/pet", json=pet_payload, timeout=5)
        session.put(f"{base_url}/api/v3/pet", json=pet_payload, timeout=5)
        session.get(f"{base_url}/api/v3/pet/1001", timeout=5)
        session.get(f"{base_url}/api/v3/pet/999999", timeout=5)
        session.get(
            f"{base_url}/api/v3/pet/findByStatus",
            params={"status": "available"},
            timeout=5,
        )
        session.get(f"{base_url}/api/v3/store/inventory", timeout=5)
        session.delete(f"{base_url}/api/v3/pet/1001", timeout=5)

        coverage = Coverage(openapi_file_path=str(spec_path))
        coverage.load(recorder)
        reporter = TerminalReporter(coverage)
        reporter.create()

        captured = capsys.readouterr()

    expected_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "petstore_terminal_report.txt"
    )
    assert captured.out == expected_path.read_text()
