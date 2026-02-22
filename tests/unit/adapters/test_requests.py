import requests
from unittest.mock import MagicMock

from pytest_httpserver import HTTPServer

from requests_stats.adapters.requests import RecordingHTTPAdapter
from requests_stats.core.base_storage import Storage


def test_custom_recorder(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/test").respond_with_json({}, 200)
    recorder = MagicMock(spec=Storage)
    adapter = RecordingHTTPAdapter(storage=recorder)
    session = requests.Session()
    session.mount(httpserver.url_for("/test"), adapter)
    session.get(httpserver.url_for("/test"))
    recorder.store.assert_called_once()
