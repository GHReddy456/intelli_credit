"""
MCA Parser — extracts director/charge/status data from MCA21 filings.
Handles both uploaded MCA documents and simulated MCA data.
"""
import re
from typing import List, Dict, Any, Optional
from loguru import logger


class MCAParser:
    def parse(self, company_name: str, segmented_docs: List) -> Dict[str, Any]:
        logger.info(f"[MCA] Parsing MCA data for: {company_name}")

        directors    = []
        charges      = []
        company_info = {}

        # Parse from uploaded documents
        for doc in segmented_docs:
            text = doc.text_content

            # Director Identification Numbers
            din_matches = re.findall(r"DIN[\s:]*([0-9]{8})", text, re.IGNORECASE)
            name_re = re.compile(
                r"(?:Mr\.|Ms\.|Dr\.|Shri|Smt\.|CA\s|CS\s)"
                r"([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)",
            )
            director_names = name_re.findall(text)

            for name in director_names[:10]:
                directors.append({
                    "name": name.strip(),
                    "din":  "DIN" + din_matches.pop(0) if din_matches else None,
                    "source": doc.file_name,
                })

            # Charges / hypothecation
            charge_re = re.compile(
                r"(?:charge|hypothecation|mortgage|pledge)[^.]*?(?:₹|Rs\.?)\s*([\d,]+)[^.]*?(?:in favour of|to)\s*([A-Za-z &.]{5,50})",
                re.IGNORECASE,
            )
            for m in charge_re.finditer(text):
                charges.append({
                    "amount":  m.group(1).replace(",", ""),
                    "lender":  m.group(2).strip(),
                    "source":  doc.file_name,
                })

            # CIN
            cin = re.search(r"\b[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\b", text)
            if cin:
                company_info["cin"] = cin.group(0)

            # Company status keywords
            if "struck off" in text.lower():
                company_info["status"] = "STRUCK_OFF"
            elif "active" in text.lower():
                company_info.setdefault("status", "ACTIVE")

        # Try online lookup if no CIN found
        if not company_info.get("cin"):
            company_info["cin"] = self._lookup_cin(company_name)

        # Deduplicate directors
        seen = set()
        unique_directors = []
        for d in directors:
            if d["name"] not in seen:
                seen.add(d["name"])
                unique_directors.append(d)

        disqualified_flag = self._check_disqualifications(unique_directors)

        return {
            "company_name":   company_name,
            "cin":            company_info.get("cin"),
            "status":         company_info.get("status", "UNKNOWN"),
            "director_list":  unique_directors[:15],
            "director_count": len(unique_directors),
            "company_charges": charges[:10],
            "charge_count":   len(charges),
            "disqualification_flag": disqualified_flag,
        }

    def _lookup_cin(self, company_name: str) -> Optional[str]:
        """Attempt web lookup for CIN. Returns None if unavailable."""
        try:
            from ddgs import DDGS
            query = f'"{company_name}" CIN site:mca.gov.in OR "MCA21"'
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=3):
                    m = re.search(r"\b[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\b", r.get("body", ""))
                    if m:
                        return m.group(0)
        except Exception:
            pass
        return None

    def _check_disqualifications(self, directors: List[Dict]) -> bool:
        """Placeholder — real impl would query MCA DIN check API."""
        return False
