"""
Research Agent — Orchestrates all research modules.
Runs news, litigation, MCA, and sector analysis in parallel threads.
"""
import concurrent.futures
from typing import List, Dict, Any
from loguru import logger

from research.news_scraper import NewsScraper
from research.litigation_detector import LitigationDetector
from research.mca_parser import MCAParser
from research.sector_analyzer import SectorAnalyzer


class ResearchAgent:
    def run(self, company_name: str, segmented_docs: List) -> Dict[str, Any]:
        logger.info(f"[ResearchAgent] Starting research for: {company_name}")

        news       = NewsScraper()
        litigation = LitigationDetector()
        mca        = MCAParser()
        sector     = SectorAnalyzer()

        # Extract promoter names from docs for targeted search
        promoter_names = self._extract_promoters(segmented_docs)

        # Run all research in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            f_news  = ex.submit(news.scrape, company_name, promoter_names)
            f_mca   = ex.submit(mca.parse, company_name, segmented_docs)
            f_lit   = None  # needs news result first — run after
            f_sector = None

            news_result = f_news.result()
            mca_result  = f_mca.result()

            f_lit    = ex.submit(litigation.detect, company_name, segmented_docs, news_result)
            f_sector = ex.submit(sector.analyze, company_name, segmented_docs, news_result.get("articles", []))

            lit_result    = f_lit.result()
            sector_result = f_sector.result()

        # Aggregate all flags
        all_flags = (
            lit_result.get("flags", []) +
            sector_result.get("regulatory_mentions", [])
        )

        # Combined research risk score
        research_risk = (
            (1 - news_result.get("news_sentiment_score", 0.5)) * 0.3 +
            lit_result.get("litigation_severity_score", 0.0)   * 0.5 +
            sector_result.get("sector_risk_score", 0.5)        * 0.2
        )

        logger.info(f"[ResearchAgent] Complete. research_risk={research_risk:.3f}")

        return {
            "company_name":              company_name,
            "promoter_names":            promoter_names,
            "news":                      news_result,
            "litigation":                lit_result,
            "mca":                       mca_result,
            "sector":                    sector_result,
            "all_flags":                 all_flags,
            "research_risk_score":       round(research_risk, 4),
            # Flat fields consumed by FeatureEngine
            "news_sentiment_score":       news_result.get("news_sentiment_score", 0.5),
            "litigation_count":           lit_result.get("litigation_count", 0),
            "litigation_severity_score":  lit_result.get("litigation_severity_score", 0.0),
            "sector_risk_score":          sector_result.get("sector_risk_score", 0.5),
            "regulatory_violation_count": sector_result.get("regulatory_violation_count", 0),
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
