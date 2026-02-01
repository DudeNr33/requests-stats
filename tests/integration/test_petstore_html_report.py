import time
from pathlib import Path

import pytest
import requests
from testcontainers.core.container import DockerContainer

from requests_stats.adapter import RecordingHTTPAdapter
from requests_stats.openapi.coverage import Coverage
from requests_stats.openapi.html_reporter import HtmlReporter
from requests_stats.recorder.sqlite_recorder import SQLiteRecorder

PETSTORE_IMAGE = "swaggerapi/petstore3"
OPENAPI_PATH = "/api/v3/openapi.json"


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


def generate_petstore_html_report(output_path: Path, workdir: Path) -> str:
    with DockerContainer(PETSTORE_IMAGE).with_exposed_ports(8080) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(8080)
        base_url = f"http://{host}:{port}"
        wait_for_petstore(base_url)

        spec_response = requests.get(f"{base_url}{OPENAPI_PATH}", timeout=5)
        spec_response.raise_for_status()
        spec_path = workdir / "spec.json"
        spec_path.write_text(spec_response.text)

        db_path = workdir / "requests.db"
        recorder = SQLiteRecorder(filepath=str(db_path))

        session = requests.Session()
        session.mount(base_url, RecordingHTTPAdapter(recorder=recorder))

        pet_payload = {
            "id": 1001,
            "name": "Test Pet",
            "photoUrls": ["https://example.com/photo"],
            "status": "available",
        }

        session.get(f"{base_url}{OPENAPI_PATH}", timeout=5)
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
        HtmlReporter(coverage).create(output_path)

        return output_path.read_text()


def test_petstore_html_report(tmp_path: Path) -> None:
    output_path = tmp_path / "coverage.html"
    html = generate_petstore_html_report(output_path, tmp_path)

    reference_path = (
        Path(__file__).resolve().parent / "fixtures" / "petstore_html_report.html"
    )
    if not reference_path.exists():
        pytest.skip("Reference report missing. Generate and approve it first.")

    assert html == reference_path.read_text()
