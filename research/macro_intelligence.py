"""
Macro Intelligence — real macroeconomic signals for credit appraisal.

Primary:  Alpha Vantage  — real-time news sentiment feed (India economy / sector)
Fallback: DuckDuckGo     — scrapes RBI / SEBI / GDP headlines

Covers: RBI monetary policy stance, GDP growth trajectory, sector PMI / IIP,
inflation, commodity / input price trends for key sectors.
"""
from __future__ import annotations

import concurrent.futures
from typing import Dict, Any, List

from loguru import logger
from backend.config import ALPHAVANTAGE_KEY


# ── Sector-specific commodity / input price query templates ──────────────────
_SECTOR_COMMODITY_QUERIES: Dict[str, str] = {
    "steel":         "India HRC CRC steel price outlook 2025",
    "textile":       "India cotton yarn price trend 2025",
    "chemicals":     "India specialty chemicals raw material price 2025",
    "pharma":        "India API bulk drug import price 2025",
    "real_estate":   "India cement steel construction cost 2025",
    "auto":          "India auto steel aluminium EV transition cost 2025",
    "agri":          "India fertilizer food inflation MSP 2025",
    "energy":        "India crude oil gas price impact 2025",
    "cement":        "India cement demand price infrastructure 2025",
    "nbfc":          "India NBFC credit funding cost RBI 2025",
    "infrastructure":"India infrastructure capex government spending 2025",
    "fmcg":          "India FMCG commodity palm oil wheat price 2025",
    "mining":        "India mining iron ore coal royalty cost 2025",
    "telecom":       "India telecom spectrum ARPU revenue 2025",
    "logistics":     "India logistics diesel fuel cost fleet 2025",
    "default":       "India manufacturing input cost inflation 2025",
}

# ── Macro signal queries (category, query) ───────────────────────────────────
_MACRO_QUERIES: List[tuple] = [
    ("rbi_policy", "RBI repo rate monetary policy stance 2025 India credit"),
    ("gdp_growth", "India GDP growth rate forecast 2025 2026 economy"),
    ("inflation",  "India CPI WPI inflation 2025 impact lending rates"),
    ("banking",    "India banking credit growth NPA GNPA 2025 outlook"),
    ("global",     "global recession risk India exports trade 2025"),
]

# ── Sentiment word sets ───────────────────────────────────────────────────────
_HAWKISH = {"hike", "tighten", "restrictive", "inflation", "elevated",
            "caution", "withdraw", "liquidity absorption"}
_DOVISH  = {"cut", "ease", "accommodative", "pause", "stable", "lower",
            "reduce", "support", "surplus liquidity"}

_POSITIVE_MACRO = {"growth", "recovery", "expansion", "strong", "acceleration",
                   "surplus", "gdp beat", "record", "buoyant"}
_NEGATIVE_MACRO = {"slowdown", "contraction", "recession", "downside", "weak",
                   "stress", "crisis", "decline", "stagflation", "pressure"}


class MacroIntelligence:
    """Scrapes macro-environment signals for credit context."""

    def analyze(self, sector: str = "default") -> Dict[str, Any]:
        logger.info(f"[Macro] Analyzing macro environment for sector: {sector}")

        commodity_query = _SECTOR_COMMODITY_QUERIES.get(
            sector, _SECTOR_COMMODITY_QUERIES["default"]
        )
        all_queries = _MACRO_QUERIES + [("commodity", commodity_query)]

        raw_signals: Dict[str, List[str]] = {}

        # ── Try Alpha Vantage first for structured news sentiment ─────────────
        av_titles = self._alphavantage_news(sector)
        if av_titles:
            raw_signals["rbi_policy"] = [t for t in av_titles if any(
                w in t.lower() for w in ["rbi", "repo", "monetary", "rate", "inflation"])][:4]
            raw_signals["gdp_growth"] = [t for t in av_titles if any(
                w in t.lower() for w in ["gdp", "growth", "economy", "output"])][:4]
            raw_signals["banking"] = [t for t in av_titles if any(
                w in t.lower() for w in ["bank", "npa", "credit", "lending"])][:4]
            raw_signals["global"] = [t for t in av_titles if any(
                w in t.lower() for w in ["global", "us", "china", "export", "fed"])][:4]
            raw_signals["commodity"] = [t for t in av_titles if any(
                w in t.lower() for w in ["price", "commodity", "oil", "steel", "cost", sector])][:4]
            logger.info(f"[Macro] Alpha Vantage provided {len(av_titles)} news items")

        # ── Fill gaps with DuckDuckGo ─────────────────────────────────────────
        missing = [(cat, q) for cat, q in all_queries if not raw_signals.get(cat)]
        if missing:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
                futs = {ex.submit(self._search, q): cat for cat, q in missing}
                for f in concurrent.futures.as_completed(futs, timeout=30):
                    cat = futs[f]
                    try:
                        raw_signals[cat] = f.result()
                    except Exception as e:
                        logger.warning(f"[Macro] DDGS query '{cat}' failed: {e}")
                        raw_signals[cat] = []

        # ── Classify RBI stance ───────────────────────────────────────────────
        rbi_text        = " ".join(raw_signals.get("rbi_policy", [])).lower()
        rate_environment = self._classify_rate_env(rbi_text)

        # ── Classify GDP trajectory ───────────────────────────────────────────
        gdp_text   = " ".join(raw_signals.get("gdp_growth", [])).lower()
        gdp_signal = self._classify_gdp(gdp_text)

        # ── Banking health ────────────────────────────────────────────────────
        banking_text   = " ".join(raw_signals.get("banking", [])).lower()
        banking_signal = (
            "STRESSED" if any(w in banking_text for w in ["npa rise", "stress", "defaults climb"])
            else "STABLE"
        )

        # ── Global risk ───────────────────────────────────────────────────────
        global_text = " ".join(raw_signals.get("global", [])).lower()
        global_risk = (
            "HIGH" if any(w in global_text for w in ["recession", "war", "sanction", "slowdown"])
            else "MODERATE"
        )

        # ── Composite macro risk score ────────────────────────────────────────
        macro_risk = 0.45
        if rate_environment == "HAWKISH":     macro_risk += 0.10
        elif rate_environment == "DOVISH":    macro_risk -= 0.05
        if gdp_signal == "DECELERATING":      macro_risk += 0.10
        elif gdp_signal == "ACCELERATING":    macro_risk -= 0.05
        if banking_signal == "STRESSED":      macro_risk += 0.08
        if global_risk == "HIGH":             macro_risk += 0.07
        macro_risk = round(min(max(macro_risk, 0.0), 1.0), 4)

        # ── Commodity headlines ───────────────────────────────────────────────
        commodity_headlines = raw_signals.get("commodity", [])[:4]

        # ── Aggregate macro headlines ─────────────────────────────────────────
        macro_headlines: List[str] = []
        for cat in ("rbi_policy", "gdp_growth", "inflation", "banking", "global"):
            macro_headlines.extend(raw_signals.get(cat, [])[:2])
        macro_headlines = macro_headlines[:10]

        macro_summary = self._build_summary(rate_environment, gdp_signal, sector, macro_risk)

        logger.info(
            f"[Macro] rate={rate_environment}, gdp={gdp_signal}, "
            f"banking={banking_signal}, global={global_risk}, risk={macro_risk:.3f}"
        )

        return {
            "macro_risk_score":     macro_risk,
            "rate_environment":     rate_environment,
            "gdp_signal":           gdp_signal,
            "banking_health":       banking_signal,
            "global_risk":          global_risk,
            "commodity_headlines":  commodity_headlines,
            "macro_headlines":      macro_headlines,
            "macro_summary":        macro_summary,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _search(self, query: str) -> List[str]:
        try:
            from ddgs import DDGS
            titles = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=6):
                    t = r.get("title", "").strip()
                    if t:
                        titles.append(t)
            return titles
        except Exception as e:
            logger.warning(f"[Macro] DDGS search failed: {e}")
            return []

    def _classify_rate_env(self, text: str) -> str:
        hawkish = sum(1 for w in _HAWKISH if w in text)
        dovish  = sum(1 for w in _DOVISH  if w in text)
        if hawkish > dovish:  return "HAWKISH"
        if dovish  > hawkish: return "DOVISH"
        return "NEUTRAL"

    def _classify_gdp(self, text: str) -> str:
        pos = sum(1 for w in _POSITIVE_MACRO if w in text)
        neg = sum(1 for w in _NEGATIVE_MACRO if w in text)
        if pos > neg:  return "ACCELERATING"
        if neg > pos:  return "DECELERATING"
        return "STEADY"

    def _build_summary(self, rate_env: str, gdp_signal: str, sector: str, risk: float) -> str:
        rate_desc = {
            "HAWKISH": "tightening monetary conditions (higher borrowing costs)",
            "DOVISH":  "easing monetary environment (supportive for credit growth)",
            "NEUTRAL": "stable monetary policy stance",
        }.get(rate_env, "neutral monetary conditions")
        gdp_desc = {
            "ACCELERATING": "strong GDP growth trajectory",
            "DECELERATING": "moderating/slowing GDP growth",
            "STEADY":       "steady economic growth",
        }.get(gdp_signal, "steady economic activity")
        risk_level = "elevated" if risk > 0.60 else ("moderate" if risk > 0.40 else "benign")
        return (
            f"India's macro environment presents {risk_level} credit risk. "
            f"The RBI signals {rate_desc} with {gdp_desc}. "
            f"Macro composite risk score: {risk:.0%}."
        )

    def _alphavantage_news(self, sector: str) -> List[str]:
        """Fetch real macro/finance news headlines from Alpha Vantage News Sentiment API."""
        if not ALPHAVANTAGE_KEY:
            return []
        try:
            import requests
            topics = "economy_macro,financial_markets,finance"
            resp = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "NEWS_SENTIMENT",
                    "topics":   topics,
                    "limit":    50,
                    "apikey":   ALPHAVANTAGE_KEY,
                },
                timeout=12,
            )
            if resp.status_code != 200:
                logger.warning(f"[AlphaVantage] HTTP {resp.status_code}")
                return []
            data = resp.json()
            feed = data.get("feed", [])
            titles: List[str] = []
            for item in feed[:50]:
                title = item.get("title", "").strip()
                summary = item.get("summary", "").strip()
                combined = f"{title} {summary}"
                if combined:
                    titles.append(combined[:200])
            logger.info(f"[AlphaVantage] Retrieved {len(titles)} news items")
            return titles
        except Exception as e:
            logger.warning(f"[AlphaVantage] News fetch failed: {e}")
            return []
