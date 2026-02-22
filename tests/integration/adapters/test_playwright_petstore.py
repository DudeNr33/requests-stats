from playwright.sync_api import Page

from requests_stats.adapters.playwright import SyncRequestHandler
from requests_stats.storage.in_memory_storage import InMemoryStorage


def test_stores_unfiltered_requests(page: Page, petstore_container: str):
    storage = InMemoryStorage()
    handler = SyncRequestHandler(storage)
    handler.register_on(page)
    page.goto(petstore_container)
    assert len(storage.recordings) > 0
    assert any(x.path.startswith("/swagger-ui") for x in storage.recordings)
    assert any(x.path == "/" for x in storage.recordings)


def test_stores_filtered_requests(page: Page, petstore_container: str):
    storage = InMemoryStorage()
    handler = SyncRequestHandler(storage, path_pattern=r"/swagger-ui.*")
    handler.register_on(page)
    page.goto(petstore_container)
    assert len(storage.recordings) > 0
    assert all(x.path.startswith("/swagger-ui") for x in storage.recordings)
