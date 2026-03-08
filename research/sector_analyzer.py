"""
Sector Analyzer — classifies sector from company docs and scores sector risk.
Searches for sector-specific news, RBI/SEBI regulatory changes.
"""
import re
from typing import List, Dict, Any, Optional
from loguru import logger
from backend.config import SECTOR_RISK


SECTOR_KEYWORDS = {
    # ── Existing sectors (expanded) ──────────────────────────────────────────
    "steel":          ["steel", "iron", "rolling mill", "sponge iron", "blast furnace",
                       "hot rolled", "cold rolled", "tmt bar", "wire rod", "pig iron"],
    "textile":        ["textile", "garment", "yarn", "fabric", "spinning", "weaving",
                       "apparel", "hosiery", "knitting", "dyeing", "cotton", "polyester"],
    "real_estate":    ["real estate", "developer", "housing", "construction", "builder",
                       "realty", "township", "residential project", "commercial property",
                       "warehouse", "reit", "plotted development"],
    "it":             ["information technology", "software", "it services", "saas", "bpo",
                       "ites", "data center", "cloud", "cybersecurity", "ai", "fintech",
                       "tech", "digital", "platform", "erp"],
    "pharma":         ["pharma", "pharmaceutical", "drug", "api", "active pharmaceutical",
                       "medicine", "hospital", "healthcare", "biotech", "formulation",
                       "clinical", "nutraceutical", "ayurvedic", "medical device"],
    "nbfc":           ["nbfc", "microfinance", "lending", "financial services", "mfi",
                       "asset finance", "gold loan", "housing finance", "hfc",
                       "vehicle finance", "consumer lending"],
    "infrastructure": ["infrastructure", "road", "highway", "port", "airport", "power",
                       "shipyard", "maritime", "shipping", "vessel", "dockyard",
                       "naval", "offshore", "rig", "bridge", "metro", "tunnel",
                       "transmission line", "substation", "irrigation", "dam"],
    "agri":           ["agriculture", "agri", "farm", "crop", "fertilizer", "seeds",
                       "pesticide", "irrigation", "dairy", "poultry", "aquaculture",
                       "food processing", "sugar mill", "rice mill", "cold chain"],
    "auto":           ["automobile", "auto", "vehicle", "car", "truck", "two-wheeler",
                       "three-wheeler", "ev", "electric vehicle", "tyre", "ancillary",
                       "forging", "casting", "auto component", "transmission"],
    "cement":         ["cement", "concrete", "rmc", "ready mix", "clinker", "fly ash",
                       "lime", "gypsum", "asbestos"],
    # ── New sectors ───────────────────────────────────────────────────────────
    "fmcg":           ["fmcg", "fast moving consumer", "consumer goods", "beverage",
                       "packaged food", "personal care", "home care", "bakery",
                       "snack", "biscuit", "noodle", "soap", "detergent", "shampoo",
                       "toothpaste", "edible oil", "spice", "masala", "confectionery"],
    "energy":         ["oil", "gas", "petroleum", "refinery", "lng", "lpg", "cng",
                       "solar", "wind", "renewable", "thermal power", "coal power",
                       "hydro", "nuclear", "biofuel", "pipeline", "exploration",
                       "upstream", "downstream", "petrochemical", "ongc", "iocl"],
    "mining":         ["mining", "coal", "quarry", "mineral", "bauxite", "copper",
                       "zinc", "lead", "gold", "silver", "diamond", "granite",
                       "sand", "stone", "iron ore", "manganese", "chromite"],
    "chemicals":      ["chemical", "specialty chemical", "dye", "pigment",
                       "agrochemical", "basic chemical", "polymer", "resin",
                       "adhesive", "coating", "paint", "solvent", "chlor-alkali"],
    "telecom":        ["telecom", "telecommunication", "mobile", "wireless", "tower",
                       "fiber", "broadband", "isp", "satellite", "spectrum",
                       "airtel", "jio", "bsnl", "dth", "cable"],
    "logistics":      ["logistics", "warehousing", "freight", "cargo", "courier",
                       "transport", "trucking", "fleet", "supply chain", "3pl",
                       "last mile", "cold storage", "air cargo", "rail freight"],
}


class SectorAnalyzer:
    def analyze(self, company_name: str, segmented_docs: List, news_articles: List[Dict] = None) -> Dict[str, Any]:
        logger.info(f"[Sector] Analyzing sector for: {company_name}")

        # 1. Detect sector
        sector = self._detect_sector(segmented_docs, company_name)

        # 2. Base risk from config
        base_risk = SECTOR_RISK.get(sector, SECTOR_RISK["default"])

        # 3. Adjust from news sentiment
        adjustment  = 0.0
        news_sample = (news_articles or [])[:20]
        neg_sector  = sum(1 for a in news_sample if a.get("sentiment") == "NEGATIVE")
        pos_sector  = sum(1 for a in news_sample if a.get("sentiment") == "POSITIVE")

        if len(news_sample) > 0:
            news_ratio  = (neg_sector - pos_sector) / len(news_sample)
            adjustment  = news_ratio * 0.10   # max ±10% adjustment

        # 4. Search for regulatory news in parallel
        regulatory_mentions, headwinds, tailwinds = self._search_regulatory_parallel(sector, company_name)

        final_risk = round(min(max(base_risk + adjustment, 0.0), 1.0), 4)
        outlook    = "NEGATIVE" if final_risk > 0.60 else ("POSITIVE" if final_risk < 0.40 else "NEUTRAL")

        return {
            "sector":                     sector,
            "sector_risk_score":          final_risk,
            "base_risk":                  base_risk,
            "news_adjustment":            round(adjustment, 4),
            "sector_outlook":             outlook,
            "regulatory_mentions":        regulatory_mentions,
            "regulatory_violation_count": len(regulatory_mentions),
            "headwinds":                  headwinds,
            "tailwinds":                  tailwinds,
            "conditions_summary":         self._build_summary(sector, final_risk, headwinds, tailwinds),
        }

    def _build_summary(self, sector: str, risk: float, headwinds: List, tailwinds: List) -> str:
        outlook = "challenging" if risk > 0.60 else ("positive" if risk < 0.40 else "mixed")
        hw = f" Key headwinds: {'; '.join(headwinds[:2])}." if headwinds else ""
        tw = f" Key tailwinds: {'; '.join(tailwinds[:2])}." if tailwinds else ""
        return f"The {sector} sector presents a {outlook} environment (risk {risk:.0%}).{hw}{tw}"

    def _detect_sector(self, docs: List, company_name: str) -> str:
        text = company_name.lower()
        for doc in docs:
            text += " " + doc.text_content.lower()
        scores = {sector: sum(kw in text for kw in kws) for sector, kws in SECTOR_KEYWORDS.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "default"

    def _search_regulatory_parallel(self, sector: str, company_name: str):
        import concurrent.futures
        queries = [
            (f"India {sector} sector RBI SEBI regulation penalty 2024 2025", "regulatory"),
            (f"India {sector} sector growth demand outlook 2025", "outlook"),
            (f"India {sector} industry risk challenges headwinds 2025", "headwinds"),
        ]

        regulatory_mentions = []
        headwinds = []
        tailwinds = []

        HEADWIND_WORDS = {"risk", "challenge", "decline", "slowdown", "pressure", "penalty", "ban", "crisis"}
        TAILWIND_WORDS = {"growth", "demand", "expansion", "boost", "positive", "recovery", "export"}

        def run(q, category):
            out = []
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    for r in ddgs.text(q, max_results=6):
                        body = r.get("body", "").lower()
                        title = r.get("title", "")
                        if any(kw in body for kw in ["regulation", "rbi", "sebi", "penalty", "circular",
                                                      "guideline", "risk", "growth", "demand"]):
                            out.append({"title": title, "url": r.get("href", ""), "category": category, "body": body})
            except Exception as e:
                logger.warning(f"[Sector] Query failed: {e}")
            return out

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            futs = {ex.submit(run, q, cat): cat for q, cat in queries}
            for f in concurrent.futures.as_completed(futs, timeout=20):
                try:
                    for item in f.result():
                        if item["category"] == "regulatory":
                            regulatory_mentions.append({"title": item["title"], "url": item["url"]})
                        body = item["body"]
                        for w in HEADWIND_WORDS:
                            if w in body and item["title"] not in headwinds:
                                headwinds.append(item["title"])
                                break
                        for w in TAILWIND_WORDS:
                            if w in body and item["title"] not in tailwinds:
                                tailwinds.append(item["title"])
                                break
                except Exception:
                    pass

        return regulatory_mentions[:8], headwinds[:5], tailwinds[:5]
