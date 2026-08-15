import logging

from app.logging import configure_logging


def test_http_transport_request_urls_are_not_logged_at_info() -> None:
    configure_logging("INFO")

    assert not logging.getLogger("httpx").isEnabledFor(logging.INFO)
    assert not logging.getLogger("httpcore").isEnabledFor(logging.INFO)
