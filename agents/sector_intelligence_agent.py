"""
Sector Intelligence Agent
Synthesises sector_analyzer output + RBI/SEBI news into sector_conditions_score.
"""
from typing import List, Dict, Any
from loguru import logger
from backend.llm import llm_call, ollama_available


class SectorIntelligenceAgent:
    def run(self, company_name: str, research: Dict) -> Dict[str, Any]:
        logger.info(f"[SectorAgent] Synthesizing sector intelligence for: {company_name}")

        sector_data = research.get("sector", {})
        news_data   = research.get("news", {})

        sector              = sector_data.get("sector", "default")
        sector_risk         = sector_data.get("sector_risk_score", 0.5)
        outlook             = sector_data.get("sector_outlook", "NEUTRAL")
        regulatory_mentions = sector_data.get("regulatory_mentions", [])
        reg_count           = len(regulatory_mentions)

        # Adjust risk for regulatory headwinds
        reg_adjustment = min(reg_count * 0.05, 0.15)
        final_risk     = round(min(sector_risk + reg_adjustment, 1.0), 4)

        # Headwinds/tailwinds summary
        headwinds  = [r["title"] for r in regulatory_mentions[:3]]
        tailwinds  = [a["title"] for a in news_data.get("articles", []) if a.get("sentiment") == "POSITIVE"][:3]

        return {
            "sector":                       sector,
            "sector_risk_score":            final_risk,
            "sector_outlook":               outlook,
            "regulatory_violation_count":   reg_count,
            "headwinds":                    headwinds,
            "tailwinds":                    tailwinds,
            "conditions_summary":           self._conditions_narrative(sector, outlook, headwinds, tailwinds),
        }

    def _conditions_narrative(self, sector: str, outlook: str, headwinds: List, tailwinds: List) -> str:
        hw = "; ".join(headwinds) if headwinds else "None identified"
        tw = "; ".join(tailwinds) if tailwinds else "None identified"
        # Try LLM for a richer narrative; fall back to template
        if ollama_available():
            prompt = (
                f"Write 2 sentences about the Indian {sector.replace('_',' ')} sector credit outlook. "
                f"Outlook: {outlook}. Key headwinds: {hw}. Key tailwinds: {tw}. "
                f"Be specific to Indian macroeconomic context (RBI, SEBI, PLI, GST)."
            )
            llm_text = llm_call(prompt, max_tokens=120)
            if llm_text:
                return llm_text
        # Rule-based fallback
        return (
            f"The {sector.replace('_',' ').title()} sector outlook is {outlook}. "
            f"Key headwinds: {hw}. Key tailwinds: {tw}."
        )
