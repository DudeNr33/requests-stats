from playwright.sync_api import Page

from requests_stats.adapters.playwright import SyncRequestHandler
from requests_stats.storage.in_memory_storage import InMemoryStorage


def test_stores_unfiltered_requests(page: Page):
    storage = InMemoryStorage()
    handler = SyncRequestHandler(storage)
    handler.register_on(page)
    page.goto("https://automationintesting.online")
    page.get_by_role(role="link", name="Admin", exact=True).click()
    assert len(storage.recordings) > 0
    assert any(x.path.startswith("/api") for x in storage.recordings)
    assert any(x.path == "/" for x in storage.recordings)


def test_stores_filtered_requests(page: Page):
    storage = InMemoryStorage()
    handler = SyncRequestHandler(storage, path_pattern=r"/api/.*")
    handler.register_on(page)
    page.goto("https://automationintesting.online")
    page.get_by_role(role="link", name="Admin", exact=True).click()
    assert len(storage.recordings) > 0
    assert all(x.path.startswith("/api") for x in storage.recordings)
