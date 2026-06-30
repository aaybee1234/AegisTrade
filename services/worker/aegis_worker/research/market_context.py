import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from aegis_worker.config import settings
from aegis_worker.portfolio_config import PORTFOLIOS, portfolio_for_symbol

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CACHE_PATH = PROJECT_ROOT / "runtime" / "research" / "market_context.json"
USER_AGENT = "AegisTrade/0.1 research"
RSS_SOURCES = (
    {
        "name": "Federal Reserve",
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "symbols": [*PORTFOLIOS["forex"], *PORTFOLIOS["metals"], *PORTFOLIOS["crypto"]]
    },
    {
        "name": "U.S. Energy Information Administration",
        "url": "https://www.eia.gov/rss/todayinenergy.xml",
        "symbols": [*PORTFOLIOS["energy"], *PORTFOLIOS["metals"]]
    }
)
COINGECKO_TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read()


def _parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return value


def _rss_items(source: dict[str, Any]) -> list[dict[str, Any]]:
    root = ET.fromstring(_fetch(source["url"]))
    items = []
    for item in root.findall(".//item")[:12]:
        items.append({
            "source": source["name"],
            "title": (item.findtext("title") or "").strip(),
            "url": (item.findtext("link") or "").strip(),
            "published_at": _parse_date(item.findtext("pubDate")),
            "symbols": source["symbols"]
        })
    return items


def _crypto_trending() -> list[dict[str, Any]]:
    payload = json.loads(_fetch(COINGECKO_TRENDING_URL).decode("utf-8"))
    projects = []
    for entry in payload.get("coins", [])[:10]:
        item = entry.get("item", {})
        data = item.get("data", {})
        projects.append({
            "name": item.get("name"),
            "symbol": item.get("symbol"),
            "market_cap_rank": item.get("market_cap_rank"),
            "score": item.get("score"),
            "price_usd": data.get("price"),
            "research_only": True,
            "source": "CoinGecko trending"
        })
    return projects


def _read_cache() -> dict[str, Any] | None:
    if not CACHE_PATH.exists():
        return None
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _cache_is_fresh(payload: dict[str, Any]) -> bool:
    try:
        fetched = datetime.fromisoformat(payload["fetched_at"])
        return (_utc_now() - fetched).total_seconds() < settings.news_refresh_seconds
    except (KeyError, TypeError, ValueError):
        return False


def refresh_market_context(force: bool = False) -> dict[str, Any]:
    cached = _read_cache()
    if cached and not force and _cache_is_fresh(cached):
        return cached

    headlines: list[dict[str, Any]] = []
    errors = []
    successful_sources = 0
    for source in RSS_SOURCES:
        try:
            headlines.extend(_rss_items(source))
            successful_sources += 1
        except Exception as error:
            errors.append(f"{source['name']}: {error}")

    try:
        crypto = _crypto_trending()
        successful_sources += 1
    except Exception as error:
        crypto = (cached or {}).get("crypto_trending", [])
        errors.append(f"CoinGecko: {error}")

    if not headlines and cached:
        headlines = cached.get("headlines", [])

    payload = {
        "fetched_at": _utc_now().isoformat(),
        "successful_sources": successful_sources,
        "source_count": len(RSS_SOURCES) + 1,
        "errors": errors,
        "headlines": headlines,
        "crypto_trending": crypto
    }
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = CACHE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    temporary.replace(CACHE_PATH)
    return payload


def context_for_symbol(symbol: str) -> dict[str, Any]:
    payload = refresh_market_context()
    headlines = [item for item in payload.get("headlines", []) if symbol in item.get("symbols", [])][:10]
    portfolio = portfolio_for_symbol(symbol)
    return {
        "fetched_at": payload.get("fetched_at"),
        "successful_sources": payload.get("successful_sources", 0),
        "source_count": payload.get("source_count", 0),
        "errors": payload.get("errors", []),
        "headlines": headlines,
        "crypto_trending": payload.get("crypto_trending", []) if portfolio == "crypto" else [],
        "portfolio": portfolio,
        "policy": "Research context may veto or reduce confidence. It cannot create a symbol or trade."
    }
