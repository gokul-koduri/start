"""Shared HTTP client with automatic retry and backoff."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

_logger = logging.getLogger(__name__)

_session_cache = None


def get_http_session(
    user_agent: str | None = None, timeout: int = 30
) -> requests.Session:
    """Get a configured requests.Session with retry logic.

    Args:
        user_agent: Custom User-Agent header.
        timeout: Default request timeout in seconds.

    Returns:
        A requests.Session with retry adapter mounted.
    """
    global _session_cache
    if _session_cache is not None and user_agent is None:
        return _session_cache

    session = requests.Session()

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    default_headers = {
        "User-Agent": user_agent or "StartupResearchBot/1.0 (educational research)",
        "Accept": "application/json, text/html, application/xml, text/xml, */*",
    }
    session.headers.update(default_headers)
    session.timeout = timeout

    if user_agent is None:
        _session_cache = session

    return session
