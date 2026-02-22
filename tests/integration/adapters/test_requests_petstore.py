from urllib.parse import urlparse

import requests

from requests_stats.adapters.requests import RecordingHTTPAdapter
from requests_stats.storage.in_memory_storage import InMemoryStorage


def test_recording_adapter(petstore_container: str) -> None:
    storage = InMemoryStorage()
    session = requests.Session()
    session.mount(petstore_container, RecordingHTTPAdapter(storage=storage))
    parsed_base = urlparse(petstore_container)

    pet_payload = {
        "id": 1001,
        "name": "Test Pet",
        "photoUrls": ["https://example.com/photo"],
        "status": "available",
    }

    responses = [
        (
            "POST",
            "/api/v3/pet",
            "",
            "",
            session.post(
                f"{petstore_container}/api/v3/pet",
                json=pet_payload,
                timeout=5,
            ),
        ),
        (
            "PUT",
            "/api/v3/pet",
            "",
            "",
            session.put(
                f"{petstore_container}/api/v3/pet",
                json=pet_payload,
                timeout=5,
            ),
        ),
        (
            "GET",
            "/api/v3/pet/1001",
            "",
            "",
            session.get(f"{petstore_container}/api/v3/pet/1001", timeout=5),
        ),
        (
            "GET",
            "/api/v3/pet/999999",
            "",
            "",
            session.get(f"{petstore_container}/api/v3/pet/999999", timeout=5),
        ),
        (
            "GET",
            "/api/v3/pet/findByStatus",
            "",
            "status=available",
            session.get(
                f"{petstore_container}/api/v3/pet/findByStatus",
                params={"status": "available"},
                timeout=5,
            ),
        ),
        (
            "GET",
            "/api/v3/store/inventory",
            "",
            "",
            session.get(f"{petstore_container}/api/v3/store/inventory", timeout=5),
        ),
        (
            "DELETE",
            "/api/v3/pet/1001",
            "",
            "",
            session.delete(f"{petstore_container}/api/v3/pet/1001", timeout=5),
        ),
    ]

    recordings = storage.load()
    assert len(recordings) == len(responses)

    for recording, (method, url, params, query, response) in zip(
        recordings,
        responses,
        strict=True,
    ):
        assert recording.method == method
        assert recording.scheme == parsed_base.scheme
        assert recording.netloc == parsed_base.netloc
        assert recording.path == url
        assert recording.params == params
        assert recording.query == query
        assert recording.response_code == response.status_code
        assert recording.duration >= 0

    query_recording = recordings[4]
    assert "status" not in query_recording.path
    assert query_recording.query == "status=available"
