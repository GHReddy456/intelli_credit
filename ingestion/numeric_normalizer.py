"""
Numeric Normalizer
==================
Central utility for converting Indian-format currency strings to float rupee values.

Handles all formats encountered in PDFs:
  • ₹1,41,00,000         → 141000000.0
  • 1.41 Cr / 1.41 crore → 14100000.0
  • 14.1 crore           → 141000000.0
  • Rs. 5,000 lakhs      → 500000000.0
  • 141000000            → 141000000.0
  • 1,41,000.50          → 141000.5  (Indian comma grouping)
  • 2023                 → None  (rejected — looks like a year, not a financial figure)
  • 300.00               → 300.0 (transaction row amount — caller decides if valid)

Key protection: if the parsed absolute value is < MIN_PLAUSIBLE_RUPEES and no unit
multiplier was detected, the value is returned as-is (bare integer from table rows).
Callers in the aggregation layer should apply their own min-value filters.
"""
import re
from typing import Optional
from loguru import logger


# ------------------------------------------------------------------
# Multiplier table (unit string → rupee multiplier)
# ------------------------------------------------------------------
_UNIT_MAP = {
    "crore":  10_000_000,
    "crores": 10_000_000,
    "cr":     10_000_000,
    "cr.":    10_000_000,
    "lakh":   100_000,
    "lakhs":  100_000,
    "lacs":   100_000,
    "lac":    100_000,
    "l":      100_000,   # "l" by itself (only used when adjacent to number)
    "l.":     100_000,
    "k":      1_000,
    "thousand": 1_000,
}

# Currency prefixes to strip
_CURRENCY_RE = re.compile(r"^(?:₹|Rs\.?|INR)\s*", re.IGNORECASE)

# Full parse pattern: optional currency prefix, number, optional unit
_FULL_RE = re.compile(
    r"(?:₹|Rs\.?|INR)?\s*"
    r"([\d,]+(?:\.\d+)?)"
    r"\s*(crores?|cr\.?|lakhs?|lacs?|l\.?|k|thousands?)?",
    re.IGNORECASE,
)

# Four-digit year pattern (2000–2029) — we skip bare numbers in this range
_YEAR_RE = re.compile(r"^20[0-2]\d$")


def parse_indian_currency(raw: str, context_unit: str = "") -> Optional[float]:
    """
    Parse a raw string from a PDF/OCR into an absolute rupee float.

    Parameters
    ----------
    raw          : The raw string, e.g. "₹1,41,00,000", "1.41 Cr", "14.1 crore"
    context_unit : Optional unit hint that was captured separately (e.g. "Cr")

    Returns
    -------
    Absolute rupee value or None if unparseable.
    """
    if not raw:
        return None

    raw = str(raw).strip()

    # Strip currency prefix
    cleaned = _CURRENCY_RE.sub("", raw).strip()

    # Remove Indian comma grouping (e.g. 1,41,00,000 → 14100000)
    # First capture any trailing unit before removing commas
    unit_match = re.search(
        r"\s+(crores?|cr\.?|lakhs?|lacs?|l\.?|k|thousands?)$",
        cleaned, re.IGNORECASE
    )
    trailing_unit = unit_match.group(1).lower() if unit_match else ""
    if trailing_unit:
        cleaned = cleaned[:unit_match.start()].strip()

    # Use context_unit if no trailing unit found
    effective_unit = trailing_unit or context_unit.lower().strip().rstrip(".")

    # Remove commas (handle both Western 1,234 and Indian 1,23,456)
    number_str = re.sub(r",", "", cleaned).strip()

    # Reject bare years (2000–2029) when no unit
    if _YEAR_RE.match(number_str) and not effective_unit:
        return None

    try:
        val = float(number_str)
    except ValueError:
        return None

    multiplier = _UNIT_MAP.get(effective_unit, 1)
    return val * multiplier


def parse_amount_robust(raw: str, context_unit: str = "") -> Optional[float]:
    """
    More aggressive parser — tries full_re match across the whole string,
    then falls back to parse_indian_currency.  Use for free-text extraction.
    """
    if not raw:
        return None
    raw = str(raw).strip()

    m = _FULL_RE.search(raw)
    if m:
        num_str = re.sub(r",", "", m.group(1))
        unit_str = (m.group(2) or context_unit or "").lower().strip().rstrip(".")
        try:
            val = float(num_str)
        except ValueError:
            return None

        # Reject bare years
        if _YEAR_RE.match(num_str.split(".")[0]) and not unit_str:
            return None

        multiplier = _UNIT_MAP.get(unit_str, 1)
        return val * multiplier

    return None


def normalize_amounts(amounts: list, min_value: float = 1_000) -> list:
    """
    Filter a list of floats, removing clearly incorrect values:
    - Values that look like years (2000–2029)
    - Values below min_value (default ₹1,000 — noise threshold)
    """
    result = []
    for v in amounts:
        if v is None:
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if fv < min_value:
            continue
        s = str(int(fv))
        if _YEAR_RE.match(s):
            continue
        result.append(fv)
    return result
