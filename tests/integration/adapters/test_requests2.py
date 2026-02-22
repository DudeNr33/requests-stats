import time
from pathlib import Path

import requests
from testcontainers.core.container import DockerContainer

from requests_stats.adapters.requests import RecordingHTTPAdapter
from requests_stats.core.coverage import Coverage
from requests_stats.reporters.coverage.terminal_reporter import TerminalReporter
from requests_stats.storage.in_memory_storage import InMemoryStorage

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


def test_petstore_terminal_report(tmp_path: Path, capsys) -> None:
    with DockerContainer(PETSTORE_IMAGE).with_exposed_ports(8080) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(8080)
        base_url = f"http://{host}:{port}"
        wait_for_petstore(base_url)

        spec_response = requests.get(f"{base_url}{OPENAPI_PATH}", timeout=5)
        spec_response.raise_for_status()
        spec_path = tmp_path / "spec.json"
        spec_path.write_text(spec_response.text)

        storage = InMemoryStorage()
        session = requests.Session()
        session.mount(base_url, RecordingHTTPAdapter(storage=storage))

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
        coverage.load(storage)
        reporter = TerminalReporter(coverage)
        reporter.create()

        captured = capsys.readouterr()

    expected_path = Path(__file__).resolve().parent / "petstore_terminal_report.txt"
    assert captured.out == expected_path.read_text()
