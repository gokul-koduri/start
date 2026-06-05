"""Website Monitor collector — monitors startup websites for business signals.

Fetches configured website URLs and scans page content for signal keywords:
funding announcements, hiring signals, product launches, and pricing changes.

No external APIs required — uses standard HTTP GET with regex-based HTML parsing.
Change detection via SHA-256 content hashing across runs.
"""

import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

# Default signal keyword categories
_DEFAULT_SIGNAL_KEYWORDS = {
    "funding": ["raised", "funding", "series a", "series b", "investment", "seed round"],
    "hiring": ["we're hiring", "careers", "join our team", "open positions"],
    "launch": ["now available", "launching", "public beta", "early access"],
    "pricing": ["pricing", "plans starting at"],
}

# Signal category weights for scoring
_SIGNAL_WEIGHTS = {
    "funding": 35,
    "hiring": 25,
    "launch": 20,
    "pricing": 15,
}


class WebsiteMonitorCollector(BaseCollector):
    """Monitors startup/company websites for business signals.

    Fetches configured URLs, extracts page content, and scans for
    signal keywords across categories (funding, hiring, launch, pricing).

    Config options:
        website_monitor.watch_urls: list of {url, label} dicts
        website_monitor.signal_keywords: dict of category -> keyword list
        website_monitor.timeout_seconds: HTTP timeout (default: 15)
        website_monitor.user_agent: custom User-Agent string
        website_monitor.min_delay_seconds: delay between fetches (default: 2)
    """

    @property
    def name(self) -> str:
        return "website_monitor"

    def _extract_title(self, html: str) -> str:
        """Extract page title from HTML using regex."""
        match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if match:
            return re.sub(r'\s+', ' ', match.group(1)).strip()
        return ""

    def _extract_meta_description(self, html: str) -> str:
        """Extract meta description from HTML."""
        match = re.search(
            r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
            html, re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        # Try reversed attribute order
        match = re.search(
            r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']',
            html, re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        return ""

    def _extract_text(self, html: str) -> str:
        """Strip HTML tags and extract plain text."""
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _find_signals(self, text: str, keywords: dict[str, list[str]]) -> list[dict]:
        """Search for signal keywords in text.

        Returns list of {keyword, category, weight} dicts.
        """
        text_lower = text.lower()
        signals = []
        seen = set()

        for category, kws in keywords.items():
            weight = _SIGNAL_WEIGHTS.get(category, 10)
            for kw in kws:
                if kw.lower() not in seen and kw.lower() in text_lower:
                    signals.append({"keyword": kw, "category": category, "weight": weight})
                    seen.add(kw.lower())

        return signals

    def _compute_score(self, signals: list[dict]) -> float:
        """Compute signal strength (0-100) based on detected signals."""
        if not signals:
            return 0.0

        score = 0.0
        categories_seen = set()
        for sig in signals:
            cat = sig["category"]
            weight = sig["weight"]
            if cat not in categories_seen:
                score += weight
                categories_seen.add(cat)
            else:
                score += 5  # Extra signal in same category

        return min(score, 100.0)

    def _compute_hash(self, text: str) -> str:
        """Compute SHA-256 hash of text content."""
        return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()

    def _fetch_page(self, session, url: str,
                    timeout: int = 15) -> tuple[int, str]:
        """Fetch a web page. Returns (status_code, html)."""
        try:
            resp = session.get(url, timeout=timeout)
            return resp.status_code, resp.text
        except Exception as e:
            _logger.warning("WebsiteMonitor: failed to fetch %s — %s", url, e)
            return 0, ""

    def _insert_snapshot(self, cursor, url: str, label: str,
                         title: str, meta_desc: str, text: str,
                         content_hash: str, signals: list[dict],
                         http_status: int,
                         result: CollectionResult) -> None:
        """Insert snapshot into website_monitor_snapshots and raw_signals."""
        signal_keywords = [s["keyword"] for s in signals]
        raw_score = self._compute_score(signals)

        cursor.execute(
            """INSERT INTO website_monitor_snapshots
               (url, page_title, meta_description, content_hash, signals_found,
                body_text_excerpt, http_status, snapshot_at, collected_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                url,
                title or None,
                meta_desc or None,
                content_hash,
                json.dumps(signal_keywords) if signal_keywords else None,
                text[:1000] if text else None,
                http_status,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Only create raw_signal and Kafka event if signals were found
        if signal_keywords:
            signal_categories = [s["category"] for s in signals]
            signal_text = f"Website signals: {', '.join(signal_keywords[:5])}"

            cursor.execute(
                """INSERT IGNORE INTO raw_signals
                   (signal_type, source_name, source_url, title, body_text,
                    entity_name, published_at, collected_at, processed)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""",
                (
                    "website_monitor",
                    label or url,
                    url,
                    f"{label or url} — {', '.join(signal_keywords[:3])}",
                    signal_text,
                    label or "",
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

            self.publish_signal(
                "website_monitor",
                title=f"{label} — {signal_keywords[0]}",
                entity_name=label or "",
                source_url=url,
                body_text=signal_text,
                raw_score=raw_score,
                signal_categories=signal_categories,
            )

        result.records_collected += 1

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        config = self.config.get("website_monitor", {})

        if self.dry_run:
            result.status = "success"
            return result

        watch_urls = config.get("watch_urls", [])
        keywords = config.get("signal_keywords", _DEFAULT_SIGNAL_KEYWORDS)
        timeout = config.get("timeout_seconds", 15)
        user_agent = config.get("user_agent", "StartupResearchBot/1.0")
        min_delay = config.get("min_delay_seconds", 2)

        if not watch_urls:
            _logger.info("WebsiteMonitorCollector: no watch_urls configured")
            result.status = "partial"
            return result

        session = get_http_session(timeout=timeout)
        session.headers["User-Agent"] = user_agent

        cursor = conn.cursor()

        for entry in watch_urls:
            url = entry.get("url", "")
            label = entry.get("label", url)

            if not url:
                continue

            http_status, html = self._fetch_page(session, url, timeout)

            if not html:
                result.errors.append(f"Failed to fetch {url}")
                time.sleep(min_delay)
                continue

            title = self._extract_title(html)
            meta_desc = self._extract_meta_description(html)
            text = self._extract_text(html)
            content_hash = self._compute_hash(text)
            signals = self._find_signals(text, keywords)

            try:
                self._insert_snapshot(
                    cursor, url, label, title, meta_desc, text,
                    content_hash, signals, http_status, result,
                )
            except Exception as e:
                result.errors.append(f"Error processing {url}: {e}")

            _logger.info(
                "WebsiteMonitor: %s — %d signals, hash=%s",
                url, len(signals), content_hash[:12],
            )

            time.sleep(min_delay)

        result.records_inserted = result.records_collected
        cursor.close()
        conn.commit()
        result.status = "success" if result.records_inserted > 0 else "partial"
        return result
