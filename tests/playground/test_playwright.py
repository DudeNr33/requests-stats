import re
from playwright.sync_api import Page, expect, Request


requests = []


def _capture_requests(request: Request) -> None:
    response = request.response()
    if not response:
        return
    requests.append(
        (
            request.method,
            request.url,
            response.status,
        )
    )


def test_has_title(page: Page):
    page.on("requestfinished", _capture_requests)
    page.goto("https://playwright.dev")
    page.expect_request
    expect(page).to_have_title(re.compile("Playwright"))
    assert len(requests) > 0
    print(requests)
