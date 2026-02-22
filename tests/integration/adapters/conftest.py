from collections.abc import Generator
import time

import pytest
import requests
from testcontainers.core.container import DockerContainer

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


@pytest.fixture(scope="session")
def petstore_container() -> Generator[str, None, None]:
    with DockerContainer(PETSTORE_IMAGE).with_exposed_ports(8080) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(8080)
        base_url = f"http://{host}:{port}"
        wait_for_petstore(base_url)
        yield base_url
