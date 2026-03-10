"""
Table Extractor — pdfplumber-based structured data extraction.
Maps table rows to canonical financial line items.
"""
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
from ingestion.numeric_normalizer import parse_indian_currency


# ── Canonical financial metric aliases ──────────────────────────────────────
METRIC_ALIASES: Dict[str, List[str]] = {
    "revenue":              ["revenue from operations", "net revenue", "total revenue", "turnover", "sales"],
    "other_income":         ["other income", "non-operating income"],
    "total_income":         ["total income", "gross income"],
    "cogs":                 ["cost of goods", "cost of materials", "raw material consumed", "purchases"],
    "gross_profit":         ["gross profit"],
    "ebitda":               ["ebitda", "operating profit", "pbdit", "earnings before interest"],
    "depreciation":         ["depreciation", "amortisation", "d&a"],
    "ebit":                 ["ebit", "operating income"],
    "interest":             ["interest", "finance cost", "finance charges", "borrowing cost"],
    "pbt":                  ["profit before tax", "pbt", "earnings before tax"],
    "tax":                  ["tax expense", "income tax", "deferred tax", "current tax"],
    "pat":                  ["profit after tax", "pat", "net profit", "net income"],
    # Balance sheet
    "total_assets":         ["total assets"],
    "fixed_assets":         ["fixed assets", "ppne", "property plant equipment", "net block"],
    "current_assets":       ["current assets", "total current assets",
                             "total current assets (a)", "current assets (a)",
                             "ii current assets"],
    "inventories":          ["inventories", "inventory", "stock", "stock-in-trade",
                             "finished goods", "raw materials", "work-in-progress", "wip",
                             "(a) inventories", "(i) inventories"],
    "receivables":          ["trade receivables", "debtors", "accounts receivable",
                             "sundry debtors", "book debts", "bills receivable",
                             "(b) trade receivables", "(ii) trade receivables"],
    "cash":                 ["cash and cash equivalents", "cash and bank", "cash equivalents",
                             "bank balance", "cash in hand",
                             "(c) cash and cash equivalents", "(iv) cash"],
    "total_liabilities":    ["total liabilities"],
    "equity":               ["shareholders equity", "net worth", "total equity",
                             "equity share capital and reserves", "shareholders funds",
                             "reserves and surplus", "total equity and liabilities",
                             "equity and liabilities", "net worth (a+b)"],
    "long_term_debt":       ["long term borrowings", "long-term debt", "term loans",
                             "non-current borrowings", "non current borrowings",
                             "(a) long term borrowings"],
    "short_term_debt":      ["short term borrowings", "short-term debt", "working capital loans",
                             "cash credit", "overdraft", "bank overdraft",
                             "(a) short term borrowings", "(i) short-term borrowings"],
    "total_debt":           ["total debt", "total borrowings",
                             "total indebtedness", "aggregate borrowings"],
    "current_liabilities":  ["current liabilities", "total current liabilities",
                             "total current liabilities (b)", "current liabilities (b)",
                             "ii current liabilities and provisions"],
    "trade_payables":       ["trade payables", "creditors", "accounts payable",
                             "sundry creditors", "other payables", "bills payable"],
    # Cash flow
    "cfo":                  ["cash from operations", "operating cash flow", "net cash from operating"],
    "cfi":                  ["investing activities", "net cash from investing", "capex"],
    "cff":                  ["financing activities", "net cash from financing"],
    # GST
    "gst_turnover":         ["aggregate turnover", "taxable turnover", "outward supplies"],
    "itc_claimed":          ["input tax credit", "itc claimed", "itc availed"],
    "gst_paid":             ["tax paid", "gst deposited", "total gst paid"],
}


class TableExtractor:
    """
    Extracts tables from PDFs using pdfplumber, maps them to structured
    financial dicts with canonical keys, and returns per-year data.
    """

    def extract(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Returns a list of structured table dicts, each containing:
          {headers, rows, financial_data, source_file, page}
        """
        fp = Path(file_path)
        logger.info(f"[TableExtractor] Extracting tables: {fp.name}")

        results = []
        try:
            import pdfplumber
            with pdfplumber.open(str(fp)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    for tbl in page.extract_tables() or []:
                        if not tbl or len(tbl) < 2:
                            continue
                        cleaned = self._clean_table(tbl)
                        if not cleaned["rows"]:
                            continue
                        fin_data = self._map_to_financials(cleaned)
                        results.append({
                            "source_file": fp.name,
                            "page": page_num,
                            "headers": cleaned["headers"],
                            "rows": cleaned["rows"],
                            "financial_data": fin_data,
                        })
        except Exception as e:
            logger.error(f"[TableExtractor] pdfplumber failed: {e}")

        logger.info(f"[TableExtractor] Found {len(results)} tables in {fp.name}")
        return results

    # ── Table cleaning ────────────────────────────────────────────────────
    def _clean_table(self, raw: List[List]) -> Dict:
        if not raw:
            return {"headers": [], "rows": []}

        # Use first non-empty row as headers, fill None cells
        headers = [
            str(c).strip() if c else f"col_{i}"
            for i, c in enumerate(raw[0])
        ]

        rows = []
        for raw_row in raw[1:]:
            if not raw_row or all(not c for c in raw_row):
                continue
            row = {}
            for i, cell in enumerate(raw_row):
                key = headers[i] if i < len(headers) else f"col_{i}"
                row[key] = str(cell).strip() if cell is not None else ""
            rows.append(row)

        return {"headers": headers, "rows": rows}

    # ── Financial mapping ─────────────────────────────────────────────────
    def _detect_table_scale(self, table: Dict) -> float:
        """Return a multiplier derived from "₹ in Lakhs / Crores" hints
        found in the table headers or first two data rows.
        Returns 100_000 for Lakhs, 10_000_000 for Crores, 1_000 for Thousands,
        and 1.0 when no hint is found.
        """
        header_text = " ".join(table.get("headers", []))
        first_rows  = " ".join(
            " ".join(str(v) for v in row.values())
            for row in table.get("rows", [])[:2]
        )
        combined = (header_text + " " + first_rows).lower()

        if re.search(r"in\s+crore|(?:₹|rs\.?)\s*crore|crores?\b|(?:₹|rs\.?)\s*cr\b", combined):
            return 10_000_000.0   # 1 Crore = 10 million
        if re.search(r"in\s+lakh|(?:₹|rs\.?)\s*lakh|lakhs?\b|(?:₹|rs\.?)\s*l\b|rs\.\s*in\s*lakh", combined):
            return 100_000.0       # 1 Lakh = 100,000
        if re.search(r"in\s+thousand|000s\b|'000\b", combined):
            return 1_000.0
        return 1.0

    def _map_to_financials(self, table: Dict) -> Dict[str, Any]:
        """
        Walk each row. First column = label, subsequent = year values.
        Try to match label to a canonical metric.
        Returns {metric: {year_header: value, ...}, ...}
        """
        scale = self._detect_table_scale(table)
        result: Dict[str, Dict[str, Optional[float]]] = {}
        headers = table.get("headers", [])
        # Year columns = all headers after the first
        year_cols = headers[1:] if len(headers) > 1 else []

        for row in table.get("rows", []):
            label_raw = list(row.values())[0] if row else ""
            if not label_raw:
                continue
            canon = self._canonicalise(label_raw)
            if canon is None:
                continue

            year_values: Dict[str, Optional[float]] = {}
            for yc in year_cols:
                val = self._parse_number(row.get(yc, ""))
                # Apply scale only when parse_amount_robust did NOT detect a unit itself
                # (i.e., keep existing Cr/Lakh-suffixed values as-is; scale raw integers).
                if val is not None and scale != 1.0:
                    raw_cell = str(row.get(yc, "")).strip().lower()
                    has_unit = re.search(r"\b(cr|crore|lakh|lac|thousand)\b", raw_cell)
                    if not has_unit:
                        val = val * scale
                year_values[yc] = val

            if any(v is not None for v in year_values.values()):
                result[canon] = year_values

        return result

    def _canonicalise(self, label: str) -> Optional[str]:
        """Return canonical metric name or None if unknown."""
        l = label.lower().strip()
        for canon, aliases in METRIC_ALIASES.items():
            for alias in aliases:
                if alias in l:
                    return canon
        return None

    def _parse_number(self, s: str) -> Optional[float]:
        """Parse Indian number/currency format using the central normalizer.
        Also handles bracket-negative accounting format: (1,234) → -1234.
        """
        if not s:
            return None

        # Bracket-negative: (1,23,456) or (1234.56) → negative
        bracket_match = re.match(r"^\(\s*([\d,]+\.?\d*)\s*\)$", s.strip())
        if bracket_match:
            clean = bracket_match.group(1).replace(",", "")
            try:
                return -float(clean)
            except ValueError:
                pass

        # Try the robust parser which handles Cr/Lakh units in the string
        from ingestion.numeric_normalizer import parse_amount_robust
        val = parse_amount_robust(s)
        if val is not None:
            return val
        # Pure numeric fallback (table cells with no unit)
        clean = re.sub(r"[^\d.\-]", "", s.replace(",", ""))
        if clean in ("", "-", "."):
            return None
        try:
            return float(clean)
        except ValueError:
            return None
