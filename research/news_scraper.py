"""
News Scraper — multi-source real-time news intelligence.

Priority chain:
  1. NewsAPI (newsapi.org)   — structured, dated, deduplicated news from 70k+ sources
  2. Finnhub                 — company-specific news feed + sentiment
  3. DuckDuckGo (ddgs)       — fallback for India-specific queries not covered above

Combines all sources, deduplicates by URL, and scores sentiment using
India-credit-domain word lists.
"""
import re
import concurrent.futures
from typing import List, Dict, Any
from loguru import logger
from backend.config import MAX_NEWS_ARTICLES, NEWS_LOOKBACK_DAYS, LITIGATION_KEYWORDS, NEWSAPI_KEY, FINNHUB_KEY


POSITIVE_WORDS = {
    "revenue", "profit", "growth", "expansion", "award", "win", "export",
    "strong", "record", "dividend", "orders", "contract", "upgrade", "increase",
    "surplus", "positive", "improvement", "success", "milestone", "approved",
}
NEGATIVE_WORDS = {
    "fraud", "default", "npa", "lawsuit", "penalty", "raid", "loss", "closure",
    "insolvency", "nclt", "ed", "cbi", "investigation", "arrest", "cheque bounce",
    "winding up", "bankrupt", "shutdown", "fir", "complaint", "wilful defaulter",
    "sebi", "drt", "drat", "pmla", "money laundering", "fake", "bogus",
    "overdue", "interest rate hike", "decline", "downgrade", "restructuring",
}


class NewsScraper:
    """
    Multi-source real-time news scraper.
    NewsAPI + Finnhub primary; DuckDuckGo fallback.
    """

    def scrape(self, company_name: str, promoter_names: List[str] = None) -> Dict[str, Any]:
        logger.info(f"[NewsScraper] Scraping news for: {company_name}")
        promoter_names = promoter_names or []
        all_articles: List[Dict] = []

        # ── Run all three sources in parallel ─────────────────────────────────
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            f_newsapi  = ex.submit(self._newsapi_search,  company_name, promoter_names)
            f_finnhub  = ex.submit(self._finnhub_search,  company_name)
            f_ddgs     = ex.submit(self._ddgs_search,     company_name, promoter_names)

            for f in concurrent.futures.as_completed([f_newsapi, f_finnhub, f_ddgs], timeout=40):
                try:
                    all_articles.extend(f.result())
                except Exception as e:
                    logger.warning(f"[NewsScraper] Source failed: {e}")

        # ── Deduplicate by URL ────────────────────────────────────────────────
        seen_urls: set = set()
        unique: List[Dict] = []
        for a in all_articles:
            url = a.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(a)
            elif not url:
                unique.append(a)   # keep URL-less items (e.g. Finnhub entries)

        # ── Sort: negative first, then by snippet length ──────────────────────
        unique.sort(key=lambda x: (x["sentiment"] != "NEGATIVE", -len(x.get("snippet", ""))))
        unique = unique[:MAX_NEWS_ARTICLES]

        negative = [a for a in unique if a["sentiment"] == "NEGATIVE"]
        positive = [a for a in unique if a["sentiment"] == "POSITIVE"]
        litigation_news = [a for a in unique if a.get("has_litigation_signal")]

        # Weighted sentiment score
        if unique:
            raw = (len(positive) - len(negative) * 1.5) / len(unique)
            sentiment_score = max(-1.0, min(1.0, raw))
        else:
            sentiment_score = 0.0

        logger.info(
            f"[NewsScraper] {len(unique)} articles — "
            f"{len(negative)} neg, {len(positive)} pos, "
            f"{len(litigation_news)} litigation — sentiment={sentiment_score:+.2f}"
        )

        return {
            "total_articles":       len(unique),
            "articles":             unique,
            "negative_count":       len(negative),
            "positive_count":       len(positive),
            "litigation_news":      litigation_news,
            "sentiment_score":      round(sentiment_score, 4),
            "news_sentiment_score": round((1 - sentiment_score) / 2, 4),
        }

    # ── NewsAPI ───────────────────────────────────────────────────────────────

    def _newsapi_search(self, company: str, promoters: List[str]) -> List[Dict]:
        if not NEWSAPI_KEY:
            return []
        articles: List[Dict] = []
        queries = [
            f'"{company}" fraud OR NPA OR NCLT OR default OR penalty',
            f'"{company}" financial results revenue growth',
        ]
        for p in promoters[:2]:
            queries.append(f'"{p}" arrest OR fraud OR NPA')
        try:
            import requests
            for q in queries:
                resp = requests.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q":        q,
                        "language": "en",
                        "sortBy":   "publishedAt",
                        "pageSize": 10,
                        "apiKey":   NEWSAPI_KEY,
                    },
                    timeout=10,
                )
                if resp.status_code != 200:
                    logger.warning(f"[NewsAPI] HTTP {resp.status_code} for query: {q[:50]}")
                    continue
                for art in resp.json().get("articles", []):
                    title   = art.get("title", "") or ""
                    desc    = art.get("description", "") or ""
                    url     = art.get("url", "") or ""
                    source  = art.get("source", {}).get("name", "NewsAPI")
                    combined = f"{title} {desc}".lower()
                    articles.append({
                        "title":                 title,
                        "snippet":               desc,
                        "url":                   url,
                        "source":                source,
                        "sentiment":             self._classify_sentiment(combined),
                        "has_litigation_signal": any(kw.lower() in combined for kw in LITIGATION_KEYWORDS),
                        "relevant":              company.lower().split()[0] in combined,
                        "provider":              "NewsAPI",
                    })
        except Exception as e:
            logger.warning(f"[NewsAPI] Failed: {e}")
        logger.debug(f"[NewsAPI] Retrieved {len(articles)} articles")
        return articles

    # ── Finnhub ───────────────────────────────────────────────────────────────

    def _finnhub_search(self, company: str) -> List[Dict]:
        if not FINNHUB_KEY:
            return []
        articles: List[Dict] = []
        try:
            import requests, time as _time
            from datetime import datetime, timedelta
            date_from = (datetime.now() - timedelta(days=NEWS_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
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
                for item in resp.json()[:15]:
                    title   = item.get("headline", "") or ""
                    snippet = item.get("summary", "") or ""
                    url     = item.get("url", "") or ""
                    combined = f"{title} {snippet}".lower()
                    articles.append({
                        "title":                 title,
                        "snippet":               snippet[:300],
                        "url":                   url,
                        "source":                item.get("source", "Finnhub"),
                        "sentiment":             self._classify_sentiment(combined),
                        "has_litigation_signal": any(kw.lower() in combined for kw in LITIGATION_KEYWORDS),
                        "relevant":              True,
                        "provider":              "Finnhub",
                    })
            # Also query general India credit news
            resp2 = requests.get(
                "https://finnhub.io/api/v1/news",
                params={"category": "business", "token": FINNHUB_KEY},
                timeout=8,
            )
            if resp2.status_code == 200:
                cname = company.lower().split()[0]
                for item in resp2.json()[:30]:
                    title  = item.get("headline", "") or ""
                    snippet = item.get("summary", "") or ""
                    if cname not in title.lower() and cname not in snippet.lower():
                        continue
                    combined = f"{title} {snippet}".lower()
                    articles.append({
                        "title":                 title,
                        "snippet":               snippet[:300],
                        "url":                   item.get("url", ""),
                        "source":                item.get("source", "Finnhub"),
                        "sentiment":             self._classify_sentiment(combined),
                        "has_litigation_signal": any(kw.lower() in combined for kw in LITIGATION_KEYWORDS),
                        "relevant":              True,
                        "provider":              "Finnhub",
                    })
        except Exception as e:
            logger.warning(f"[Finnhub] Failed: {e}")
        logger.debug(f"[Finnhub] Retrieved {len(articles)} articles")
        return articles

    # ── DuckDuckGo fallback ───────────────────────────────────────────────────

    def _ddgs_search(self, company: str, promoters: List[str]) -> List[Dict]:
        queries = self._build_queries(company, promoters)
        articles: List[Dict] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(queries), 5)) as ex:
            futs = {ex.submit(self._ddgs_query, q, company): q for q in queries}
            for f in concurrent.futures.as_completed(futs, timeout=25):
                try:
                    articles.extend(f.result())
                except Exception:
                    pass
        logger.debug(f"[DDGS] Retrieved {len(articles)} articles")
        return articles

    def _ddgs_query(self, query: str, company_name: str) -> List[Dict]:
        items: List[Dict] = []
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=8):
                    title   = r.get("title", "")
                    snippet = r.get("body", "")
                    url     = r.get("href", "")
                    combined = f"{title} {snippet}".lower()
                    items.append({
                        "title":                 title,
                        "snippet":               snippet,
                        "url":                   url,
                        "source":                "DuckDuckGo",
                        "sentiment":             self._classify_sentiment(combined),
                        "has_litigation_signal": any(kw.lower() in combined for kw in LITIGATION_KEYWORDS),
                        "relevant":              company_name.lower().split()[0] in combined,
                        "provider":              "DDGS",
                    })
        except Exception as e:
            logger.warning(f"[DDGS] Query failed: {e}")
        return items

    def _build_queries(self, company: str, promoters: List[str]) -> List[str]:
        queries = [
            f'"{company}" fraud OR default OR NPA OR NCLT OR "cheque bounce" OR ED OR CBI',
            f'"{company}" financial results revenue profit loss 2024 2025',
            f'"{company}" court case legal notice penalty SEBI DRT winding',
            f'"{company}" CRISIL OR ICRA OR CARE rating downgrade upgrade 2024 2025',
            f'"{company}" bank loan restructuring moratorium overdraft',
            f'"{company}" expansion order win export award contract 2024 2025',
        ]
        for p in promoters[:2]:
            queries.append(f'"{p}" fraud OR arrest OR case OR NPA OR default OR NCLT')
        return queries

    def _classify_sentiment(self, text: str) -> str:
        neg = sum(1 for w in NEGATIVE_WORDS if w in text)
        pos = sum(1 for w in POSITIVE_WORDS if w in text)
        if neg > pos:   return "NEGATIVE"
        if pos > neg:   return "POSITIVE"
        return "NEUTRAL"



POSITIVE_WORDS = {
    "revenue", "profit", "growth", "expansion", "award", "win", "export",
    "strong", "record", "dividend", "orders", "contract", "upgrade", "increase",
    "surplus", "positive", "improvement", "success", "milestone", "approved",
}
NEGATIVE_WORDS = {
    "fraud", "default", "npa", "lawsuit", "penalty", "raid", "loss", "closure",
    "insolvency", "nclt", "ed", "cbi", "investigation", "arrest", "cheque bounce",
    "winding up", "bankrupt", "shutdown", "fir", "complaint", "wilful defaulter",
    "sebi", "drt", "drat", "pmla", "money laundering", "fake", "bogus",
    "overdue", "interest rate hike", "decline", "downgrade", "restructuring",
}


class NewsScraper:
    """
    Real-time news scraper using DuckDuckGo search.
    Runs multiple targeted queries in parallel.
    """

    def scrape(self, company_name: str, promoter_names: List[str] = None) -> Dict[str, Any]:
        logger.info(f"[NewsScraper] Real-time web search for: {company_name}")
        promoter_names = promoter_names or []
        all_articles = []

        queries = self._build_queries(company_name, promoter_names)

        # Run all queries in parallel using threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(queries), 6)) as ex:
            futures = {ex.submit(self._search, q, company_name): q for q in queries}
            for future in concurrent.futures.as_completed(futures, timeout=30):
                try:
                    all_articles.extend(future.result())
                except Exception as e:
                    logger.warning(f"[NewsScraper] Query failed: {e}")

        # Deduplicate by URL
        seen_urls = set()
        unique = []
        for a in all_articles:
            url = a.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(a)

        # Sort: negative first, then by title length (more detailed = better)
        unique.sort(key=lambda x: (x["sentiment"] != "NEGATIVE", -len(x.get("snippet", ""))))
        unique = unique[:MAX_NEWS_ARTICLES]

        negative = [a for a in unique if a["sentiment"] == "NEGATIVE"]
        positive = [a for a in unique if a["sentiment"] == "POSITIVE"]
        litigation_news = [a for a in unique if a["has_litigation_signal"]]

        # Weighted sentiment: each negative counts double
        if unique:
            raw = (len(positive) - len(negative) * 1.5) / len(unique)
            sentiment_score = max(-1.0, min(1.0, raw))
        else:
            sentiment_score = 0.0

        logger.info(
            f"[NewsScraper] {len(unique)} unique articles — "
            f"{len(negative)} negative, {len(positive)} positive, "
            f"{len(litigation_news)} litigation signals — "
            f"sentiment={sentiment_score:+.2f}"
        )

        return {
            "total_articles":   len(unique),
            "articles":         unique,
            "negative_count":   len(negative),
            "positive_count":   len(positive),
            "litigation_news":  litigation_news,
            "sentiment_score":  round(sentiment_score, 4),
            # 0-1 risk score: 0 = very positive coverage, 1 = very negative
            "news_sentiment_score": round((1 - sentiment_score) / 2, 4),
        }

    def _build_queries(self, company: str, promoters: List[str]) -> List[str]:
        queries = [
            # Core adverse intelligence
            f'"{company}" fraud OR default OR NPA OR NCLT OR "cheque bounce" OR ED OR CBI',
            # Financial performance
            f'"{company}" financial results revenue profit loss 2024 2025',
            # Legal exposure
            f'"{company}" court case legal notice penalty SEBI DRT winding',
            # Credit rating
            f'"{company}" CRISIL OR ICRA OR CARE rating downgrade upgrade 2024 2025',
            # Banking relationship
            f'"{company}" bank loan restructuring moratorium overdraft',
            # Promoter integrity
            f'"{company}" promoter director arrest investigation wilful defaulter',
            # Regulatory
            f'"{company}" GST penalty income tax seizure raid customs',
            # Positive signals
            f'"{company}" expansion order win export award contract 2024 2025',
        ]
        for p in promoters[:3]:
            queries.append(f'"{p}" fraud OR arrest OR case OR NPA OR default OR NCLT')
        return queries

    def _search(self, query: str, company_name: str) -> List[Dict]:
        articles = []
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=8))

            for r in results:
                title   = r.get("title", "")
                snippet = r.get("body", "")
                url     = r.get("href", "")
                if not title and not snippet:
                    continue

                combined_text = f"{title} {snippet}".lower()
                sentiment = self._classify_sentiment(combined_text)
                has_litigation = any(kw.lower() in combined_text for kw in LITIGATION_KEYWORDS)
                relevance = company_name.lower().split()[0] in combined_text

                articles.append({
                    "title":                 title,
                    "snippet":               snippet,
                    "url":                   url,
                    "sentiment":             sentiment,
                    "has_litigation_signal": has_litigation,
                    "relevant":              relevance,
                })

        except Exception as e:
            logger.warning(f"[NewsScraper] Search failed for '{query[:50]}': {type(e).__name__}: {e}")

        return articles

    def _classify_sentiment(self, text: str) -> str:
        neg = sum(1 for w in NEGATIVE_WORDS if w in text)
        pos = sum(1 for w in POSITIVE_WORDS if w in text)
        if neg > pos:
            return "NEGATIVE"
        if pos > neg:
            return "POSITIVE"
        return "NEUTRAL"
