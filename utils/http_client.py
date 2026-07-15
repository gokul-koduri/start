"""Shared HTTP client with automatic retry and backoff."""

from __future__ import annotations

import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from typing import Any

_logger = logging.getLogger(__name__)

_session_cache = None


class MalformedApiResponseError(RuntimeError):
    """Raised when an upstream 200 response is empty or not valid JSON."""


def _response_status(response: Any) -> int | None:
    status = getattr(response, "status", None)
    if isinstance(status, int):
        return status
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    return None


def read_json_response(response: Any, *, provider_name: str) -> Any:
    """Read and parse a JSON response body with a proxy/gateway-friendly error."""
    raw_body = response.read()
    if isinstance(raw_body, bytes):
        body_text = raw_body.decode("utf-8", errors="replace")
    else:
        body_text = str(raw_body)

    status = _response_status(response)
    status_label = status if status is not None else "unknown"

    # Check HTTP status first - return proper error for 4xx/5xx
    if status is not None and status >= 400:
        preview = body_text.strip().replace("\n", " ")
        if len(preview) > 200:
            preview = f"{preview[:200].rstrip()}..."
        raise MalformedApiResponseError(
            f"{provider_name} API returned HTTP {status} - {preview}"
        )

    stripped = body_text.strip()

    if not stripped:
        raise MalformedApiResponseError(
            f"{provider_name} API returned an empty or malformed response (HTTP {status_label}) - "
            "check for a proxy or gateway intercepting the request"
        )

    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        preview = stripped.replace("\n", " ")
        if len(preview) > 200:
            preview = f"{preview[:200].rstrip()}..."
        raise MalformedApiResponseError(
            f"{provider_name} API returned an empty or malformed response (HTTP {status_label}) - "
            "check for a proxy or gateway intercepting the request. "
            f"Body preview: {preview}"
        ) from exc


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


def make_request_with_retry(
    session: requests.Session,
    method: str,
    url: str,
    max_retries: int = 3,
    backoff_base: float = 1.0,
    status_forcelist: tuple = (429, 500, 502, 503, 504),
    **kwargs
) -> requests.Response:
    """Make HTTP request with retry on transient failures.

    Args:
        session: A requests.Session to use for the request.
        method: HTTP method (GET, POST, etc.).
        url: Target URL.
        max_retries: Maximum retry attempts.
        backoff_base: Base for exponential backoff in seconds.
        status_forcelist: HTTP status codes that trigger retry.
        **kwargs: Additional arguments passed to session.request().

    Returns:
        The response object (caller must check status).

    Raises:
        requests.HTTPError: After max retries exhausted.
    """
    import time

    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            response = session.request(method, url, **kwargs)
            response_status = response.status_code

            # Check if we should retry based on status
            if response_status in status_forcelist:
                last_exception = requests.HTTPError(
                    f"HTTP {response_status} on {method} {url}"
                )

                # Respect Retry-After header if present
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait = int(retry_after)
                    except ValueError:
                        wait = backoff_base * (2 ** (attempt - 1))
                else:
                    wait = backoff_base * (2 ** (attempt - 1))

                if attempt < max_retries:
                    _logger.warning(
                        "HTTP %d on %s %s, retrying in %.1fs (attempt %d/%d)",
                        response_status,
                        method,
                        url,
                        wait,
                        attempt,
                        max_retries,
                    )
                    time.sleep(wait)
                    continue
                else:
                    raise last_exception

            return response

        except requests.RequestException as e:
            last_exception = e
            if attempt < max_retries:
                wait = backoff_base * (2 ** (attempt - 1))
                _logger.warning(
                    "Request error on %s %s: %s, retrying in %.1fs (attempt %d/%d)",
                    method,
                    url,
                    e,
                    wait,
                    attempt,
                    max_retries,
                )
                time.sleep(wait)
            else:
                _logger.error(
                    "Request failed on %s %s after %d attempts: %s",
                    method,
                    url,
                    max_retries,
                    e,
                )

    raise last_exception or requests.RequestException(f"Request to {url} failed")
