"""
News Scraper — DuckDuckGo (ddgs) + newspaper3k article fetching
Real-time web scraping for company news, fraud signals, litigation, sector trends.
"""
import re
import time
import concurrent.futures
from typing import List, Dict, Any
from loguru import logger
from backend.config import MAX_NEWS_ARTICLES, NEWS_LOOKBACK_DAYS, LITIGATION_KEYWORDS


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
            f'"{company}" fraud OR default OR NPA OR NCLT OR "cheque bounce"',
            f'"{company}" financial results revenue profit 2024 2025',
            f'"{company}" court case legal notice penalty',
            f'"{company}" credit rating downgrade OR upgrade',
        ]
        for p in promoters[:3]:
            queries.append(f'"{p}" fraud OR arrest OR case OR default OR NPA')
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
