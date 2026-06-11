"""LLM Pricing Scraper Agent — collects public pricing from major LLM providers.

Maintains a static pricing baseline (curated, reliable) and optionally
attempts to scrape provider pricing pages for updates. Results are stored
in the ``llm_pricing`` database table and rendered on the dashboard.

Runs weekly via the ``weekly`` pipeline.
"""

import logging
import re
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)

# ── Static pricing baseline ──────────────────────────────────────────────
# Updated June 2026. This serves as the reliable fallback when scraping fails.
# Each provider has a dict with 'url' and 'models' list.
_PROVIDER_PRICING: dict[str, dict] = {
    "openai": {
        "url": "https://openai.com/api/pricing/",
        "models": [
            {
                "model_name": "GPT-4.1 Nano",
                "model_id": "gpt-4.1-nano",
                "input_price_per_1m": 0.10,
                "output_price_per_1m": 0.40,
                "context_window": 1000000,
                "modality": "text",
                "notes": "Cheapest OpenAI model",
            },
            {
                "model_name": "GPT-4.1 Mini",
                "model_id": "gpt-4.1-mini",
                "input_price_per_1m": 0.40,
                "output_price_per_1m": 1.60,
                "context_window": 1000000,
                "modality": "text+vision",
            },
            {
                "model_name": "GPT-4.1",
                "model_id": "gpt-4.1",
                "input_price_per_1m": 2.00,
                "output_price_per_1m": 8.00,
                "context_window": 1000000,
                "modality": "text+vision",
            },
            {
                "model_name": "GPT-4o",
                "model_id": "gpt-4o",
                "input_price_per_1m": 2.50,
                "output_price_per_1m": 10.00,
                "context_window": 128000,
                "modality": "text+vision",
                "notes": "50% price cut Oct 2024",
            },
            {
                "model_name": "GPT-4o-mini",
                "model_id": "gpt-4o-mini",
                "input_price_per_1m": 0.15,
                "output_price_per_1m": 0.60,
                "context_window": 128000,
                "modality": "text+vision",
            },
            {
                "model_name": "o3",
                "model_id": "o3",
                "input_price_per_1m": 2.00,
                "output_price_per_1m": 8.00,
                "context_window": 200000,
                "modality": "text+vision",
                "notes": "80% price cut from original",
            },
            {
                "model_name": "o3-mini",
                "model_id": "o3-mini",
                "input_price_per_1m": 1.10,
                "output_price_per_1m": 4.40,
                "context_window": 200000,
                "modality": "text+vision",
            },
            {
                "model_name": "o3-pro",
                "model_id": "o3-pro",
                "input_price_per_1m": 20.00,
                "output_price_per_1m": 80.00,
                "context_window": 200000,
                "modality": "text+vision",
                "notes": "86% cheaper than o1-pro",
            },
            {
                "model_name": "o1",
                "model_id": "o1",
                "input_price_per_1m": 15.00,
                "output_price_per_1m": 60.00,
                "context_window": 200000,
                "modality": "text+vision",
            },
        ],
    },
    "anthropic": {
        "url": "https://platform.claude.com/docs/en/about-claude/pricing",
        "models": [
            {
                "model_name": "Claude Haiku 4.5",
                "model_id": "claude-haiku-4-5-20250514",
                "input_price_per_1m": 1.00,
                "output_price_per_1m": 5.00,
                "context_window": 200000,
                "modality": "text+vision",
            },
            {
                "model_name": "Claude Sonnet 4.6",
                "model_id": "claude-sonnet-4-6-20250514",
                "input_price_per_1m": 3.00,
                "output_price_per_1m": 15.00,
                "context_window": 200000,
                "modality": "text+vision",
            },
            {
                "model_name": "Claude Opus 4.6",
                "model_id": "claude-opus-4-6-20250514",
                "input_price_per_1m": 5.00,
                "output_price_per_1m": 25.00,
                "context_window": 200000,
                "modality": "text+vision",
            },
        ],
    },
    "google": {
        "url": "https://ai.google.dev/gemini-api/docs/pricing",
        "models": [
            {
                "model_name": "Gemini 2.0 Flash-Lite",
                "model_id": "gemini-2.0-flash-lite",
                "input_price_per_1m": 0.075,
                "output_price_per_1m": 0.30,
                "context_window": 1000000,
                "modality": "text+vision",
                "notes": "Cheapest Gemini tier",
            },
            {
                "model_name": "Gemini 2.5 Flash",
                "model_id": "gemini-2.5-flash",
                "input_price_per_1m": 0.30,
                "output_price_per_1m": 2.50,
                "context_window": 1000000,
                "modality": "text+vision",
            },
            {
                "model_name": "Gemini 2.5 Pro",
                "model_id": "gemini-2.5-pro",
                "input_price_per_1m": 1.25,
                "output_price_per_1m": 10.00,
                "context_window": 1000000,
                "modality": "text+vision",
            },
        ],
    },
    "deepseek": {
        "url": "https://api-docs.deepseek.com/quick_start/pricing",
        "models": [
            {
                "model_name": "DeepSeek V3.2",
                "model_id": "deepseek-v3-2",
                "input_price_per_1m": 0.14,
                "output_price_per_1m": 0.28,
                "context_window": 131072,
                "modality": "text",
                "notes": "Best value for output pricing",
            },
            {
                "model_name": "DeepSeek-R1",
                "model_id": "deepseek-reasoner",
                "input_price_per_1m": 0.55,
                "output_price_per_1m": 2.19,
                "context_window": 131072,
                "modality": "text",
            },
        ],
    },
    "meta": {
        "url": "https://www.together.ai/pricing",
        "models": [
            {
                "model_name": "Llama 4 Scout (hosted)",
                "model_id": "meta-llama/Llama-4-Scout-17B-16E",
                "input_price_per_1m": 0.10,
                "output_price_per_1m": 0.40,
                "context_window": 10000000,
                "modality": "text+vision",
                "notes": "Via Together AI; 10M context",
                "pricing_tier": "hosted",
            },
            {
                "model_name": "Llama 4 Maverick (hosted)",
                "model_id": "meta-llama/Llama-4-Maverick-17B-128E",
                "input_price_per_1m": 0.27,
                "output_price_per_1m": 0.80,
                "context_window": 1000000,
                "modality": "text+vision",
                "notes": "Via Together AI",
                "pricing_tier": "hosted",
            },
            {
                "model_name": "Llama 3.1 8B (self-hosted)",
                "model_id": "llama3.1:8b",
                "input_price_per_1m": 0.00,
                "output_price_per_1m": 0.00,
                "context_window": 128000,
                "modality": "text",
                "notes": "Open-source; free self-hosted",
                "pricing_tier": "self-hosted",
            },
        ],
    },
    "mistral": {
        "url": "https://mistral.ai/pricing/",
        "models": [
            {
                "model_name": "Mistral Small 3",
                "model_id": "mistral-small-3",
                "input_price_per_1m": 0.10,
                "output_price_per_1m": 0.30,
                "context_window": 128000,
                "modality": "text+vision",
                "notes": "50% batch discount available",
            },
            {
                "model_name": "Mistral Medium",
                "model_id": "mistral-medium-latest",
                "input_price_per_1m": 0.40,
                "output_price_per_1m": 2.00,
                "context_window": 128000,
                "modality": "text",
            },
            {
                "model_name": "Mistral Large",
                "model_id": "mistral-large-latest",
                "input_price_per_1m": 2.00,
                "output_price_per_1m": 6.00,
                "context_window": 128000,
                "modality": "text",
            },
        ],
    },
    "xai": {
        "url": "https://docs.x.ai/developers/models",
        "models": [
            {
                "model_name": "Grok 3",
                "model_id": "grok-3",
                "input_price_per_1m": 1.25,
                "output_price_per_1m": 2.50,
                "context_window": 1000000,
                "modality": "text",
            },
        ],
    },
    "cohere": {
        "url": "https://cohere.com/pricing",
        "models": [
            {
                "model_name": "Command R",
                "model_id": "command-r",
                "input_price_per_1m": 0.50,
                "output_price_per_1m": 1.50,
                "context_window": 128000,
                "modality": "text",
                "notes": "Best for RAG",
            },
            {
                "model_name": "Command R+",
                "model_id": "command-r-plus",
                "input_price_per_1m": 2.50,
                "output_price_per_1m": 10.00,
                "context_window": 128000,
                "modality": "text",
            },
        ],
    },
    "ollama_local": {
        "url": "http://localhost:11434",
        "models": [
            {
                "model_name": "Ollama (local)",
                "model_id": "local",
                "input_price_per_1m": 0.00,
                "output_price_per_1m": 0.00,
                "context_window": 8192,
                "modality": "text",
                "notes": "Self-hosted; hardware cost only",
                "pricing_tier": "self-hosted",
            },
        ],
    },
}

# Models to attempt to scrape (best-effort)
_SCRAPE_TARGETS = {
    "openai": "https://openai.com/api/pricing/",
    "anthropic": "https://platform.claude.com/docs/en/about-claude/pricing",
    "google": "https://ai.google.dev/gemini-api/docs/pricing",
    "deepseek": "https://api-docs.deepseek.com/quick_start/pricing",
    "mistral": "https://mistral.ai/pricing/",
}


class LLMPricingAgent(BaseAgent):
    """Agent that collects LLM pricing from public sources.

    Uses a curated static baseline as the primary data source, with
    best-effort scraping to detect price changes. Results are upserted
    into the ``llm_pricing`` database table.

    Config options:
        request_delay_seconds: delay between scrape requests (default: 2)
        timeout_seconds: HTTP timeout (default: 15)
    """

    @property
    def name(self) -> str:
        return "llm_pricing"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        request_delay = self.config.get("request_delay_seconds", 2)
        timeout = self.config.get("timeout_seconds", 15)

        _logger.info("LLMPricingAgent: Starting pricing collection")

        # Collect all models from static baseline
        all_models: list[dict] = []
        for provider, data in _PROVIDER_PRICING.items():
            for m in data["models"]:
                all_models.append(
                    {
                        "provider": provider,
                        "pricing_url": data["url"],
                        **m,
                        "pricing_tier": m.get("pricing_tier", "standard"),
                    }
                )

        # Best-effort scrape for updates
        scraped_updates = self._scrape_all(request_delay, timeout)
        if scraped_updates:
            _logger.info(
                "LLMPricingAgent: Got %d scraped price entries", len(scraped_updates)
            )
            # Merge scraped data into all_models (override static baseline)
            scraped_by_key = {
                (r["provider"], r["model_name"]): r for r in scraped_updates
            }
            for i, m in enumerate(all_models):
                key = (m["provider"], m["model_name"])
                if key in scraped_by_key:
                    upd = scraped_by_key[key]
                    all_models[i]["input_price_per_1m"] = upd["input_price_per_1m"]
                    all_models[i]["output_price_per_1m"] = upd["output_price_per_1m"]
                    all_models[i]["context_window"] = upd.get(
                        "context_window", m.get("context_window")
                    )
                    all_models[i]["notes"] = upd.get("notes", m.get("notes", ""))

        # Upsert into database
        inserted = 0
        updated = 0
        try:
            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            for m in all_models:
                cursor.execute(
                    """INSERT INTO llm_pricing
                       (provider, model_name, model_id, input_price_per_1m, output_price_per_1m,
                        context_window, training_data_cutoff, modality, pricing_tier, pricing_url, notes, collected_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                        input_price_per_1m = VALUES(input_price_per_1m),
                        output_price_per_1m = VALUES(output_price_per_1m),
                        context_window = VALUES(context_window),
                        modality = VALUES(modality),
                        pricing_url = VALUES(pricing_url),
                        notes = VALUES(notes),
                        collected_at = VALUES(collected_at)""",
                    (
                        m["provider"],
                        m["model_name"],
                        m.get("model_id", ""),
                        m["input_price_per_1m"],
                        m["output_price_per_1m"],
                        m.get("context_window"),
                        m.get("training_data_cutoff", ""),
                        m.get("modality", "text"),
                        m.get("pricing_tier", "standard"),
                        m.get("pricing_url", ""),
                        m.get("notes", ""),
                        now,
                    ),
                )
                if cursor.rowcount == 1:
                    inserted += 1
                elif cursor.rowcount == 2:
                    updated += 1

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            _logger.error("LLMPricingAgent: Database error: %s", e)
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[str(e)],
            )

        total = len(all_models)
        _logger.info(
            "LLMPricingAgent: Done — %d providers, %d models (%d new, %d updated)",
            len(_PROVIDER_PRICING),
            total,
            inserted,
            updated,
        )

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "providers": len(_PROVIDER_PRICING),
                "models": total,
                "inserted": inserted,
                "updated": updated,
                "records_affected": total,
            },
        )

    def _scrape_all(self, delay: float, timeout: float) -> list[dict]:
        """Attempt to scrape all configured provider pricing pages."""
        results: list[dict] = []
        for provider, url in _SCRAPE_TARGETS.items():
            try:
                scraped = self._scrape_provider(provider, url, timeout)
                if scraped:
                    results.extend(scraped)
            except Exception as e:
                _logger.debug("LLMPricingAgent: Scrape failed for %s: %s", provider, e)
            if delay > 0:
                time.sleep(delay)
        return results

    def _scrape_provider(self, provider: str, url: str, timeout: float) -> list[dict]:
        """Best-effort scrape of a provider's pricing page.

        Returns a list of model dicts with updated pricing, or an empty
        list if scraping fails.
        """
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "StartupResearchBot/1.0 (educational research project)",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            _logger.debug("LLMPricingAgent: Cannot fetch %s: %s", url, e)
            return []

        # Try to extract dollar amounts near model names
        models: list[dict] = []
        if provider == "openai":
            models = self._parse_openai(html)
        elif provider == "anthropic":
            models = self._parse_anthropic(html)
        elif provider == "google":
            models = self._parse_google(html)
        elif provider == "deepseek":
            models = self._parse_deepseek(html)
        elif provider == "mistral":
            models = self._parse_mistral(html)
        else:
            models = self._parse_generic(html)

        return models

    def _extract_prices(self, html: str) -> list[tuple[float, float]]:
        """Extract (input, output) price pairs from HTML text.

        Looks for patterns like ``$2.50`` and ``$10.00`` appearing near
        each other, which is how most pricing pages list input/output rates.
        """
        prices = re.findall(r"\$(\d+\.?\d*)", html)
        pairs: list[tuple[float, float]] = []
        for i in range(0, len(prices) - 1, 2):
            try:
                inp = float(prices[i])
                out = float(prices[i + 1])
                if 0 <= inp <= 500 and 0 <= out <= 2000:
                    pairs.append((inp, out))
            except ValueError:
                continue
        return pairs

    def _parse_openai(self, html: str) -> list[dict]:
        """Parse OpenAI pricing page for model names and prices."""
        models: list[dict] = []
        # Match model names followed by price patterns
        pattern = re.compile(
            r"(?:GPT-4\.?\d?[\w.-]*|o[13][\w-]*|gpt-[\w.-]+)"
            r".*?\$(\d+\.?\d*)[^\$]*?\$(\d+\.?\d*)",
            re.DOTALL | re.IGNORECASE,
        )
        for match in pattern.finditer(html):
            name = match.group(0).strip()[:60].split("\n")[0].strip().strip("$").strip()
            # Extract just the model name
            name = re.sub(r"\s*\$[\d.]+.*", "", name).strip()
            if not name:
                continue
            try:
                models.append(
                    {
                        "provider": "openai",
                        "model_name": name,
                        "input_price_per_1m": float(match.group(1)),
                        "output_price_per_1m": float(match.group(2)),
                    }
                )
            except ValueError:
                continue
        return models

    def _parse_anthropic(self, html: str) -> list[dict]:
        return self._parse_generic_named(html, "anthropic")

    def _parse_google(self, html: str) -> list[dict]:
        return self._parse_generic_named(html, "google")

    def _parse_deepseek(self, html: str) -> list[dict]:
        return self._parse_generic_named(html, "deepseek")

    def _parse_mistral(self, html: str) -> list[dict]:
        return self._parse_generic_named(html, "mistral")

    def _parse_generic(self, html: str) -> list[dict]:
        """Generic parser that extracts $X.XX / $Y.YY pairs near model-like strings."""
        models: list[dict] = []
        blocks = re.split(r"</tr>|</div>", html)
        for block in blocks[:200]:  # Limit to avoid processing huge pages
            prices = re.findall(r"\$(\d+\.?\d*)", block)
            model_match = re.search(
                r"(?:model|GPT|Claude|Gemini|DeepSeek|Mistral|Grok|Llama|Command)[\w\s.-]{2,30}",
                block,
                re.IGNORECASE,
            )
            if len(prices) >= 2 and model_match:
                try:
                    models.append(
                        {
                            "provider": "unknown",
                            "model_name": model_match.group(0).strip(),
                            "input_price_per_1m": float(prices[0]),
                            "output_price_per_1m": float(prices[1]),
                        }
                    )
                except ValueError:
                    continue
        return models

    def _parse_generic_named(self, html: str, provider: str) -> list[dict]:
        """Generic parser for a known provider."""
        results = self._parse_generic(html)
        for m in results:
            m["provider"] = provider
        return results
