"""
Research Agent — Orchestrates all research modules for 360-degree intelligence.

Runs in parallel:
  • NewsScraper         — DuckDuckGo news scraping for company / promoter / sector
  • MCAParser           — Director / charge / CIN extraction
  • LitigationDetector  — Court cases from docs + web
  • SectorAnalyzer      — Sector risk, regulatory news
  • MacroIntelligence   — RBI stance, GDP, inflation, commodity signals
  • CreditRatingScraper — CRISIL / ICRA / CARE rating signals

Results feed: FeatureEngine → TriangulationEngine → PreCognitiveRiskEngine → CAMGenerator
"""
import concurrent.futures
from typing import List, Dict, Any
from loguru import logger

from research.news_scraper import NewsScraper
from research.litigation_detector import LitigationDetector
from research.mca_parser import MCAParser
from research.sector_analyzer import SectorAnalyzer
from research.macro_intelligence import MacroIntelligence
from research.credit_rating_scraper import CreditRatingScraper


class ResearchAgent:
    def run(self, company_name: str, segmented_docs: List, sector_hint: str = "default") -> Dict[str, Any]:
        logger.info(f"[ResearchAgent] Starting 360° research for: {company_name}")

        news_scraper    = NewsScraper()
        litigation_det  = LitigationDetector()
        mca_parser      = MCAParser()
        sector_analyzer = SectorAnalyzer()
        macro           = MacroIntelligence()
        credit_ratings  = CreditRatingScraper()

        # Extract promoter names from docs for targeted search
        promoter_names = self._extract_promoters(segmented_docs)

        # ── Phase A: run all scraping in parallel ─────────────────────────────
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            f_news   = ex.submit(news_scraper.scrape, company_name, promoter_names)
            f_mca    = ex.submit(mca_parser.parse, company_name, segmented_docs)
            f_macro  = ex.submit(macro.analyze, sector_hint)

            news_result  = f_news.result(timeout=45)
            mca_result   = f_mca.result(timeout=30)
            macro_result = f_macro.result(timeout=35)

            # ── Phase B: litigation + sector need news result first ───────────
            f_lit    = ex.submit(litigation_det.detect, company_name, segmented_docs, news_result)
            f_sector = ex.submit(
                sector_analyzer.analyze, company_name, segmented_docs,
                news_result.get("articles", [])
            )
            f_cr = ex.submit(credit_ratings.scrape, company_name, sector_hint)

            lit_result    = f_lit.result(timeout=40)
            sector_result = f_sector.result(timeout=35)
            cr_result     = f_cr.result(timeout=30)

        # ── Aggregate flags ───────────────────────────────────────────────────
        all_flags = (
            lit_result.get("flags", []) +
            sector_result.get("regulatory_mentions", [])
        )

        # ── Composite research risk (weighted) ────────────────────────────────
        cr_penalty = 0.10 if cr_result.get("company_rating_trend") == "DETERIORATING" else 0.0
        research_risk = round(
            news_result.get("news_sentiment_score",      0.5) * 0.25 +
            lit_result.get("litigation_severity_score",  0.0) * 0.35 +
            sector_result.get("sector_risk_score",       0.5) * 0.20 +
            macro_result.get("macro_risk_score",         0.5) * 0.10 +
            cr_penalty                                         * 0.10,
            4,
        )

        logger.info(
            f"[ResearchAgent] Complete. research_risk={research_risk:.3f}, "
            f"sector={sector_result.get('sector', '?')}, "
            f"macro_risk={macro_result.get('macro_risk_score', 0):.2f}, "
            f"rating_trend={cr_result.get('company_rating_trend', 'STABLE')}"
        )

        return {
            "company_name":              company_name,
            "promoter_names":            promoter_names,
            "news":                      news_result,
            "litigation":                lit_result,
            "mca":                       mca_result,
            "sector":                    sector_result,
            "macro":                     macro_result,
            "credit_ratings":            cr_result,
            "all_flags":                 all_flags,
            "research_risk_score":       research_risk,
            # ── Flat fields consumed by FeatureEngine ─────────────────────────
            "news_sentiment_score":       news_result.get("news_sentiment_score",      0.5),
            "litigation_count":           lit_result.get("litigation_count",           0),
            "litigation_severity_score":  lit_result.get("litigation_severity_score",  0.0),
            "sector_risk_score":          sector_result.get("sector_risk_score",       0.5),
            "regulatory_violation_count": sector_result.get("regulatory_violation_count", 0),
            "macro_risk_score":           macro_result.get("macro_risk_score",         0.5),
        }

    def _extract_promoters(self, docs: List) -> List[str]:
        import re
        names = []
        pattern = re.compile(
            r"(?:promoter|managing director|chairman|cmd|ceo|cfo)[:\s]+"
            r"(?:Mr\.|Ms\.|Dr\.|Shri|Smt\.)?\s*([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,})",
            re.IGNORECASE,
        )
        for doc in docs:
            for m in pattern.finditer(doc.text_content):
                name = m.group(1).strip()
                if name not in names:
                    names.append(name)
        return names[:5]
