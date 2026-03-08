"""
Benford's Law Analyzer
Checks if invoice/transaction amounts follow Benford's distribution.
High chi-square deviation = possible fabrication of numbers.
"""
import re
import math
from collections import Counter
from typing import List, Dict, Any, Optional
from loguru import logger
from backend.config import BENFORD_CHI2_THRESHOLD


# Expected Benford probabilities for digits 1-9
BENFORD_EXPECTED = {
    d: math.log10(1 + 1 / d) for d in range(1, 10)
}


class BenfordAnalyzer:
    """
    Applies Benford's Law to:
    - Invoice amounts from GST data
    - Transaction amounts from bank statements
    - Revenue figures from financial statements

    Chi-square test statistic > 15.51 (p=0.05, df=8) = significant deviation.
    """

    def analyze(self, segmented_docs: List, tables: List[Dict]) -> Dict[str, Any]:
        amounts = self._collect_amounts(segmented_docs, tables)

        if len(amounts) < 30:
            logger.warning(f"[Benford] Only {len(amounts)} amounts — insufficient for reliable test")
            return {
                "benford_deviation_score": 0.0,
                "chi2_statistic":          0.0,
                "sample_size":             len(amounts),
                "status":                  "insufficient_data",
                "flags":                   [],
            }

        chi2, observed_dist = self._chi2_test(amounts)
        score = self._chi2_to_score(chi2)
        flags = []

        if chi2 > BENFORD_CHI2_THRESHOLD:
            severity = "HIGH" if chi2 > BENFORD_CHI2_THRESHOLD * 2 else "MEDIUM"
            flags.append({
                "flag":     "BENFORD_DEVIATION",
                "severity": severity,
                "detail":   (
                    f"Chi-square {chi2:.2f} exceeds threshold {BENFORD_CHI2_THRESHOLD} — "
                    f"possible fabricated financial figures (n={len(amounts)})"
                ),
            })

        logger.info(f"[Benford] chi2={chi2:.2f}, score={score:.3f}, n={len(amounts)}")

        return {
            "benford_deviation_score": score,
            "chi2_statistic":          round(chi2, 4),
            "sample_size":             len(amounts),
            "observed_distribution":   {str(d): round(observed_dist.get(d, 0), 4) for d in range(1, 10)},
            "expected_distribution":   {str(d): round(BENFORD_EXPECTED[d], 4) for d in range(1, 10)},
            "status":                  "checked",
            "flags":                   flags,
        }

    # ── Chi-square test ───────────────────────────────────────────────────
    def _chi2_test(self, amounts: List[float]):
        first_digits = [self._first_digit(a) for a in amounts if self._first_digit(a)]
        n = len(first_digits)
        if n == 0:
            return 0.0, {}

        observed_count = Counter(first_digits)
        chi2 = 0.0
        observed_dist = {}

        for d in range(1, 10):
            observed = observed_count.get(d, 0)
            expected = BENFORD_EXPECTED[d] * n
            observed_dist[d] = observed / n
            if expected > 0:
                chi2 += ((observed - expected) ** 2) / expected

        return chi2, observed_dist

    def _first_digit(self, n: float) -> Optional[int]:
        if n <= 0:
            return None
        s = str(int(abs(n))).lstrip("0")
        return int(s[0]) if s else None

    def _chi2_to_score(self, chi2: float) -> float:
        """Normalise chi2 to 0-1 risk score."""
        # chi2 of 15.51 → score 0.5;  31+ → score 1.0
        return round(min(chi2 / 31.0, 1.0), 4)

    # ── Amount collection ─────────────────────────────────────────────────
    def _collect_amounts(self, docs: List, tables: List[Dict]) -> List[float]:
        amounts = []

        # From tables
        for tbl in tables:
            for row in tbl.get("rows", []):
                for val in row.values():
                    n = self._to_float(str(val))
                    if n and n > 1000:   # Only non-trivial amounts
                        amounts.append(n)

        # From text: all currency amounts
        currency_re = re.compile(r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
        for doc in docs:
            for m in currency_re.finditer(doc.text_content):
                n = self._to_float(m.group(1))
                if n and n > 1000:
                    amounts.append(n)

        return amounts

    def _to_float(self, s: str) -> Optional[float]:
        clean = re.sub(r"[^\d.]", "", str(s))
        try:
            return float(clean) if clean else None
        except ValueError:
            return None
