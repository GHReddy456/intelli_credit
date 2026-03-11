"""
Credit Rating Scraper - CRISIL / ICRA / CARE / India Ratings signals.

Primary:  Finnhub company news (fast, structured)
Secondary: NewsAPI filtered for rating keywords
Fallback:  DuckDuckGo

Detects: recent rating actions, downgrade / upgrade / watch signals, trend direction.
"""
from __future__ import annotations

import re
import concurrent.futures
from typing import Dict, Any, List

from loguru import logger
from backend.config import FINNHUB_KEY, NEWSAPI_KEY


_RATING_AGENCIES = ["CRISIL", "ICRA", "CARE", "India Ratings", "Fitch India"]

_RATING_PATTERN = re.compile(
    r"\b(AAA|AA[+-]?|A[+-]?|BBB[+-]?|BB[+-]?|B[+-]?|CCC|CC|C|D"
    r"|IND [A-D][+-]?|CRISIL [A-D][+-]?|ICRA [A-D][+-]?|CARE [A-D][+-]?)\b"
)

_DOWNGRADE_WORDS = {
    "downgrade", "lower", "negative outlook", "watch negative", "default",
    "withdrawn", "suspend", "junk", "speculative grade", "below investment grade",
    "credit watch", "review for downgrade", "npa",
}
_UPGRADE_WORDS = {
    "upgrade", "improve", "positive outlook", "watch positive", "affirm",
    "raise", "investment grade", "outlook stable", "outlook positive",
    "removed from watch", "reaffirm",
}


class CreditRatingScraper:
    """Searches for rating agency signals for a company and its sector."""

    def scrape(self, company_name: str, sector: str = "default") -> Dict[str, Any]:
        logger.info(f"[CreditRating] Scraping for: {company_name} [{sector}]")

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            f_finnhub = ex.submit(self._finnhub_news,   company_name)
            f_newsapi = ex.submit(self._newsapi_rating, company_name, sector)
            f_ddgs    = ex.submit(self._ddgs_rating,    company_name, sector)

            all_hits: List[Dict] = []
            for f in concurrent.futures.as_completed([f_finnhub, f_newsapi, f_ddgs], timeout=30):
                try:
                    all_hits.extend(f.result())
                except Exception as e:
                    logger.warning(f"[CreditRating] Source failed: {e}")

        company_hits = [h for h in all_hits if h.get("scope") == "company"]
        sector_hits  = [h for h in all_hits if h.get("scope") == "sector"]

        company_text    = " ".join(h.get("text", "") for h in company_hits)
        company_ratings = list(dict.fromkeys(_RATING_PATTERN.findall(company_text)))[:5]
        company_trend   = self._classify_trend(company_text)

        sector_text    = " ".join(h.get("text", "") for h in sector_hits)
        sector_quality = self._classify_trend(sector_text)

        seen: set = set()
        unique_signals: List[Dict] = []
        for hit in all_hits[:10]:
            title = hit.get("title", "").strip()
            if not title:
                continue
            key = title[:60]
            if key in seen:
                continue
            seen.add(key)
            unique_signals.append({
                "title":  title,
                "source": hit.get("source", ""),
                "trend":  self._classify_trend(hit.get("text", "")),
            })

        logger.info(
            f"[CreditRating] company_trend={company_trend}, "
            f"sector_quality={sector_quality}, signals={len(unique_signals)}"
        )

        return {
            "company_rating_mentions": company_ratings,
            "company_rating_trend":    company_trend,
            "sector_credit_quality":   sector_quality,
            "agency_signals":          unique_signals[:6],
            "signal_count":            len(unique_signals),
        }

    # ── Finnhub ───────────────────────────────────────────────────────────────

    def _finnhub_news(self, company: str) -> List[Dict]:
        if not FINNHUB_KEY:
            return []
        hits: List[Dict] = []
        try:
            import requests
            from datetime import datetime, timedelta
            date_from = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            date_to   = datetime.now().strftime("%Y-%m-%d")
            resp = requests.get(
                "https://finnhub.io/api/v1/company-news",
                params={
                    "symbol": company[:10].upper().replace(" ", ""),
                    "from":   date_from,
                    "to":     date_to,
                    "token":  FINNHUB_KEY,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                for item in resp.json()[:20]:
                    title    = item.get("headline", "") or ""
                    summary  = item.get("summary", "") or ""
                    combined = f"{title} {summary}".lower()
                    if any(w in combined for w in [
                        "crisil", "icra", "care", "rating",
                        "downgrade", "upgrade", "npa", "default",
                    ]):
                        hits.append({
                            "title":  title,
                            "text":   combined,
                            "source": item.get("source", "Finnhub"),
                            "scope":  "company",
                        })
        except Exception as e:
            logger.warning(f"[Finnhub/Rating] Failed: {e}")
        return hits

    # ── NewsAPI ───────────────────────────────────────────────────────────────

    def _newsapi_rating(self, company: str, sector: str) -> List[Dict]:
        if not NEWSAPI_KEY:
            return []
        hits: List[Dict] = []
        queries = [
            (f'"{company}" CRISIL ICRA CARE rating', "company"),
            (f"India {sector} NPA credit quality CRISIL ICRA 2025", "sector"),
        ]
        try:
            import requests
            for q, scope in queries:
                resp = requests.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q":        q,
                        "language": "en",
                        "pageSize": 8,
                        "apiKey":   NEWSAPI_KEY,
                    },
                    timeout=10,
                )
                if resp.status_code != 200:
                    continue
                for art in resp.json().get("articles", []):
                    title = art.get("title", "") or ""
                    desc  = art.get("description", "") or ""
                    hits.append({
                        "title":  title,
                        "text":   f"{title} {desc}".lower(),
                        "source": art.get("source", {}).get("name", "NewsAPI"),
                        "scope":  scope,
                    })
        except Exception as e:
            logger.warning(f"[NewsAPI/Rating] Failed: {e}")
        return hits

    # ── DuckDuckGo fallback ───────────────────────────────────────────────────

    def _ddgs_rating(self, company: str, sector: str) -> List[Dict]:
        queries = [
            (f'"{company}" CRISIL OR ICRA OR CARE rating 2024 2025', "company"),
            (f"India {sector} sector CRISIL ICRA CARE credit quality 2025", "sector"),
            (f"India {sector} NPA GNPA banking credit risk stress 2025", "sector"),
            (f'"{company}" rating downgrade upgrade outlook 2024 2025', "company"),
        ]
        hits: List[Dict] = []
        try:
            from ddgs import DDGS
            for q, scope in queries:
                with DDGS() as ddgs:
                    for r in ddgs.text(q, max_results=5):
                        title = r.get("title", "")
                        body  = r.get("body", "")
                        hits.append({
                            "title":  title,
                            "text":   f"{title} {body}".lower(),
                            "source": r.get("href", ""),
                            "scope":  scope,
                        })
        except Exception as e:
            logger.warning(f"[DDGS/Rating] Failed: {e}")
        return hits

    # ── Trend classifier ─────────────────────────────────────────────────────

    def _classify_trend(self, text: str) -> str:
        t = text.lower()
        down = sum(1 for w in _DOWNGRADE_WORDS if w in t)
        up   = sum(1 for w in _UPGRADE_WORDS   if w in t)
        if down > up:
            return "DETERIORATING"
        if up > down:
            return "IMPROVING"
        return "STABLE"
