"""
Document Segmenter
==================
Segments uploaded documents into labelled logical sections.
Works on the raw ParsedDocument output from pdf_parser.py.

Priority: This is Phase-1 processing. Every document is:
  1. Type-classified
  2. Split into named sections
  3. Each section given a label + confidence score
  4. Financial figures pulled section-by-section
  5. Cross-document references resolved

Supported section types per document type are defined in SECTION_SCHEMAS below.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from loguru import logger

from ingestion.pdf_parser import ParsedDocument


# ─────────────────────────────────────────────
# SECTION SCHEMAS PER DOCUMENT TYPE
# ─────────────────────────────────────────────
SECTION_SCHEMAS: Dict[str, List[Dict]] = {
    "annual_report": [
        {"label": "corporate_overview",       "keywords": ["corporate overview", "company overview", "about us", "company profile", "history"]},
        {"label": "directors_report",         "keywords": ["directors' report", "directors report", "board's report", "board report"]},
        {"label": "management_discussion",    "keywords": ["management discussion", "mda", "management's discussion", "business overview"]},
        {"label": "auditors_report",          "keywords": ["independent auditor", "auditor's report", "statutory auditor", "audit report"]},
        {"label": "balance_sheet",            "keywords": ["balance sheet", "statement of financial position", "assets and liabilities"]},
        {"label": "profit_loss",              "keywords": ["profit and loss", "statement of profit", "income statement", "p&l", "revenue from operations"]},
        {"label": "cash_flow",                "keywords": ["cash flow statement", "cash flows from", "operating activities", "investing activities"]},
        {"label": "notes_to_accounts",        "keywords": ["notes to accounts", "notes forming part", "significant accounting policies", "note no"]},
        {"label": "related_party",            "keywords": ["related party", "related parties", "transactions with related", "arm's length"]},
        {"label": "contingent_liabilities",   "keywords": ["contingent liabilities", "contingent assets", "commitments and contingencies"]},
        {"label": "segment_reporting",        "keywords": ["segment reporting", "segment information", "reportable segments", "business segments"]},
        {"label": "corporate_governance",     "keywords": ["corporate governance", "board composition", "audit committee", "nomination", "remuneration"]},
        {"label": "shareholding_pattern",     "keywords": ["shareholding pattern", "share capital", "promoter holding", "public holding"]},
    ],
    "gst": [
        {"label": "gstr1_outward_supplies",   "keywords": ["outward supplies", "gstr-1", "taxable supplies", "b2b invoices", "b2c invoices"]},
        {"label": "gstr3b_summary",           "keywords": ["gstr-3b", "3b", "summary of outward", "tax payable", "tax paid"]},
        {"label": "gstr2a_reconciliation",    "keywords": ["gstr-2a", "2a", "inward supplies", "itc available", "auto drafted"]},
        {"label": "itc_details",              "keywords": ["input tax credit", "itc claimed", "itc reversed", "itc utilised", "itc availed"]},
        {"label": "demand_notices",           "keywords": ["demand notice", "show cause notice", "scn", "gst demand", "penalty", "interest payable"]},
        {"label": "annual_return",            "keywords": ["gstr-9", "annual return", "gstr9", "aggregate turnover"]},
    ],
    "bank_statement": [
        {"label": "account_summary",          "keywords": ["account summary", "account details", "account number", "account holder", "opening balance"]},
        {"label": "transaction_history",      "keywords": ["transaction", "debit", "credit", "balance", "narration", "date", "particulars"]},
        {"label": "emi_payments",             "keywords": ["emi", "loan repayment", "installment", "equated monthly", "principal", "interest"]},
        {"label": "cash_withdrawals",         "keywords": ["cash withdrawal", "atm", "cash deposit", "cash cdm", "cash crm"]},
        {"label": "cheque_returns",           "keywords": ["cheque return", "chq return", "dishonor", "insufficient funds", "ecs return", "nach return"]},
        {"label": "salary_credits",           "keywords": ["salary", "payroll", "neft", "imps cr", "rtgs cr"]},
        {"label": "gst_payments",             "keywords": ["gst payment", "cpin", "challan", "gst", "igst", "cgst", "sgst"]},
    ],
    "itr": [
        {"label": "basic_information",        "keywords": ["pan", "assessment year", "return type", "itr", "filing date"]},
        {"label": "income_from_business",     "keywords": ["income from business", "business income", "net profit", "gross profit", "schedule bp"]},
        {"label": "income_from_other",        "keywords": ["other income", "capital gains", "house property", "salary", "schedule os"]},
        {"label": "deductions",               "keywords": ["deductions", "chapter vi-a", "80c", "80d", "80g", "80gg"]},
        {"label": "tax_computation",          "keywords": ["tax computation", "total tax", "advance tax", "tds", "self assessment tax", "tax liability"]},
        {"label": "depreciation",             "keywords": ["depreciation", "schedule dpi", "block of assets", "written down value", "additional depreciation"]},
    ],
    "legal": [
        {"label": "case_header",              "keywords": ["before the", "in the court", "high court", "supreme court", "district court", "tribunal", "nclt", "drat", "drt"]},
        {"label": "parties",                  "keywords": ["plaintiff", "petitioner", "appellant", "respondent", "defendant", "applicant", "opposite party"]},
        {"label": "facts",                    "keywords": ["facts of the case", "brief facts", "background", "whereas", "it is alleged"]},
        {"label": "relief_claimed",           "keywords": ["relief", "prayer", "order and decree", "injunction", "recovery of", "writ of"]},
        {"label": "court_order",              "keywords": ["ordered", "directed", "disposed of", "allowed", "dismissed", "judgment", "decree"]},
        {"label": "financial_claim",          "keywords": ["amount in dispute", "claim amount", "outstanding dues", "principal amount", "interest thereon"]},
    ],
    "sanction_letter": [
        {"label": "borrower_details",         "keywords": ["borrower", "name of the borrower", "applicant", "constituent"]},
        {"label": "facility_details",         "keywords": ["facility", "nature of facility", "limit", "amount sanctioned", "working capital", "term loan"]},
        {"label": "interest_rate",            "keywords": ["rate of interest", "interest rate", "roi", "spread", "mclr", "repo rate", "base rate"]},
        {"label": "repayment_terms",          "keywords": ["repayment", "tenure", "moratorium", "emi schedule", "bullet payment", "door to door"]},
        {"label": "security_details",         "keywords": ["security", "collateral", "primary security", "collateral security", "mortgage", "hypothecation", "pledge"]},
        {"label": "covenants_conditions",     "keywords": ["covenant", "condition", "terms and conditions", "condition precedent", "condition subsequent", "undertaking"]},
        {"label": "disbursement",             "keywords": ["disbursement", "drawdown", "utilisation", "end use", "disbursed amount"]},
    ],
}


# ─────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────
@dataclass
class DocumentSection:
    label: str
    raw_text: str
    page_hint: Optional[int]
    confidence: float                   # 0-1 how confident we are in this label
    entities: Dict[str, List[str]]      # named entities inside this section
    financial_figures: List[Dict]       # {label, value, unit, context}
    flags: List[str]                    # red-flag strings found
    word_count: int = 0


@dataclass
class SegmentedDocument:
    source_file: str
    doc_type: str
    sections: List[DocumentSection]
    section_index: Dict[str, DocumentSection]   # label → section (first match)
    global_entities: Dict[str, List[str]]
    all_financial_figures: List[Dict]
    red_flags: List[str]
    segment_summary: Dict[str, Any]

    @property
    def text_content(self) -> str:
        """Backwards-compat: aggregate all section text so modules that
        expect ParsedDocument.text_content still work."""
        return "\n".join(s.raw_text for s in self.sections)

    @property
    def file_name(self) -> str:
        return self.source_file


# ─────────────────────────────────────────────
# SEGMENTER
# ─────────────────────────────────────────────
class DocumentSegmenter:
    """
    Splits a ParsedDocument into labelled sections.
    Uses keyword-based boundary detection + contextual heuristics.
    """

    # Universal red-flag patterns for ALL document types
    RED_FLAG_PATTERNS = [
        (r"emphasis of matter",             "AUDIT: Emphasis of Matter"),
        (r"qualified opinion",              "AUDIT: Qualified Opinion"),
        (r"basis for qualified",            "AUDIT: Basis for Qualified Opinion"),
        (r"unable to obtain sufficient",    "AUDIT: Scope limitation"),
        (r"going concern",                  "AUDIT: Going concern doubt"),
        (r"material uncertainty",           "AUDIT: Material uncertainty"),
        (r"material weakness",              "AUDIT: Material weakness in internal controls"),
        (r"adverse opinion",                "AUDIT: Adverse Opinion"),
        (r"caro\b|companies auditor.s report", "AUDIT: CARO qualification"),
        (r"reconciliation.*differ|differ.*reconciliation", "AUDIT: Reconciliation difference"),
        (r"non.compliance.*(?:act|regulation|rule)|(?:act|regulation|rule).*non.compliance",
                                            "AUDIT: Non-compliance with regulations"),
        (r"wilful default(?:er)?",          "LEGAL: Wilful defaulter"),
        (r"non.performing asset|npa",       "CREDIT: NPA classification"),
        (r"insolvency.*proceedings|ibc",    "LEGAL: Insolvency proceedings"),
        (r"enforcement directorate|ed raid","LEGAL: ED investigation"),
        (r"central bureau|cbi",             "LEGAL: CBI investigation"),
        (r"money laundering|pmla",          "LEGAL: PMLA case"),
        (r"cheque.*dishonor|dishonour.*cheque|section 138", "LEGAL: Cheque dishonour"),
        (r"fraud.*classif|classif.*fraud",  "CREDIT: Fraud classification"),
        (r"sebi.*debarr|debarr.*sebi",      "REGULATORY: SEBI debarment"),
        (r"circular trading|round.tripping","FINANCIAL: Circular trading suspicion"),
        (r"related party.*exceed|exceed.*related party", "FINANCIAL: Excessive RPT"),
        (r"pledge.*promot|promot.*pledge",  "FINANCIAL: Promoter pledge"),
        (r"overdue|past due|days past due", "CREDIT: Payment overdue"),
        (r"restructur|one time settlement|ots", "CREDIT: Restructuring/OTS"),
        (r"suit filed|recovery suit|legal action", "LEGAL: Recovery suit"),
        (r"attachment.*order|order.*attachment", "LEGAL: Attachment order"),
    ]

    # Structured auditor remark patterns (returns {type, keyword, severity})
    _AUDIT_REMARK_PATTERNS = [
        (re.compile(r"qualified opinion",            re.IGNORECASE), "QUALIFIED_OPINION",       "HIGH"),
        (re.compile(r"basis for qualified",          re.IGNORECASE), "QUALIFIED_OPINION",       "HIGH"),
        (re.compile(r"adverse opinion",              re.IGNORECASE), "ADVERSE_OPINION",         "CRITICAL"),
        (re.compile(r"going concern",                re.IGNORECASE), "GOING_CONCERN",           "CRITICAL"),
        (re.compile(r"material uncertainty",         re.IGNORECASE), "GOING_CONCERN",           "CRITICAL"),
        (re.compile(r"emphasis of matter",           re.IGNORECASE), "EMPHASIS_OF_MATTER",      "MEDIUM"),
        (re.compile(r"material weakness",            re.IGNORECASE), "MATERIAL_WEAKNESS",       "HIGH"),
        (re.compile(r"scope.?limitation|unable to obtain sufficient", re.IGNORECASE), "SCOPE_LIMITATION", "HIGH"),
        (re.compile(r"caro\b|companies auditor.?s report order", re.IGNORECASE), "CARO_QUALIFICATION", "MEDIUM"),
        (re.compile(r"reconciliation.*differ|differ.*reconciliation", re.IGNORECASE), "RECONCILIATION_DIFFERENCE", "MEDIUM"),
        (re.compile(r"non.compliance.*(?:act|regulation|rule)|(?:act|regulation).*non.compliance", re.IGNORECASE), "NON_COMPLIANCE", "HIGH"),
        (re.compile(r"internal financial controls.*(?:inadequate|deficient|not adequate)", re.IGNORECASE), "INTERNAL_CONTROL_DEFICIENCY", "HIGH"),
        (re.compile(r"provision.*not made|not provided for|not provisioned", re.IGNORECASE), "UNDER_PROVISIONING", "MEDIUM"),
    ]

    # Indian financial figure patterns
    FIGURE_PATTERNS = [
        # ₹1,23,45,678 or Rs. 12,34,567
        {"pattern": r"(?P<label>[A-Za-z ]{3,40}?)[:\s]+(?:Rs\.?|₹|INR)\s*(?P<value>[\d,]+\.?\d*)\s*(?P<unit>Cr\.?|Crore|L\.?|Lakh|Lakhs|Crores|K)?",
         "type": "currency"},
        # Table-style: label   1,23,456   2,34,567
        {"pattern": r"(?P<label>[A-Za-z &()/-]{4,50})\s{2,}(?P<val1>[\d,]+\.?\d*)\s{2,}(?P<val2>[\d,]+\.?\d*)",
         "type": "tabular"},
        # Percentage figures
        {"pattern": r"(?P<label>[A-Za-z ]{3,40}?)[:\s]+(?P<value>\d{1,3}\.?\d*)\s*%",
         "type": "percentage"},
        # Ratios
        {"pattern": r"(?P<label>[A-Za-z ]{3,40}?)[:\s]+(?P<value>\d{1,2}\.?\d*)\s*(?:x|times)",
         "type": "ratio"},
    ]

    # Key financial labels to track
    KEY_LABELS = {
        "revenue":           ["revenue from operations", "net revenue", "total revenue", "turnover"],
        "ebitda":            ["ebitda", "operating profit", "earnings before interest"],
        "pat":               ["profit after tax", "pat", "net profit", "net income"],
        "gross_profit":      ["gross profit", "gross margin"],
        "total_debt":        ["total debt", "total borrowings", "long term debt", "short term borrowings"],
        "net_worth":         ["net worth", "shareholders equity", "share capital and reserves", "total equity"],
        "current_assets":    ["current assets", "total current assets"],
        "current_liab":      ["current liabilities", "total current liabilities"],
        "cash":              ["cash and cash equivalents", "cash and bank"],
        "capex":             ["capital expenditure", "capex", "purchase of fixed assets", "additions to ppne"],
        "dscr":              ["debt service coverage", "dscr"],
        "interest_coverage": ["interest coverage", "icr", "interest service"],
        "debt_equity":       ["debt equity ratio", "d/e ratio", "leverage ratio"],
        "current_ratio":     ["current ratio"],
        "gst_turnover":      ["aggregate turnover", "taxable turnover", "outward supplies turnover"],
        "itc":               ["input tax credit", "itc"],
        "tax_paid":          ["tax paid", "gst deposited", "gst paid"],
    }

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        self._red_flag_compiled = [
            (re.compile(p, re.IGNORECASE), label)
            for p, label in self.RED_FLAG_PATTERNS
        ]
        self._figure_compiled = [
            (re.compile(fp["pattern"], re.IGNORECASE | re.MULTILINE), fp["type"])
            for fp in self.FIGURE_PATTERNS
        ]

    # ─── PUBLIC API ───────────────────────────────────────────────────────────

    def segment(self, parsed_doc: ParsedDocument) -> SegmentedDocument:
        """
        Main entry point.
        Takes a ParsedDocument → returns SegmentedDocument with rich sections.
        """
        logger.info(f"[Segmenter] Segmenting '{parsed_doc.file_name}' (type={parsed_doc.doc_type})")

        schema = SECTION_SCHEMAS.get(parsed_doc.doc_type, [])
        text = parsed_doc.text_content

        # Step 1: Split text into candidate section blocks
        raw_blocks = self._split_into_blocks(text)

        # Step 2: Classify each block against schema
        sections = self._classify_blocks(raw_blocks, schema)

        # Step 3: Extract financial figures per section
        for sec in sections:
            sec.financial_figures = self._extract_figures(sec.raw_text)
            sec.entities = self._extract_entities(sec.raw_text)
            sec.flags = self._detect_flags(sec.raw_text)
            sec.word_count = len(sec.raw_text.split())

        # Step 4: Include table data as extra financial figures
        table_figures = self._extract_table_figures(parsed_doc.tables)

        # Step 5: Include structured financial_data from PDFParser (already absolute values)
        parser_figures = self._extract_parser_financial_data(parsed_doc)

        # Step 6: Structured auditor remarks (for fraud/feature engines)
        # Scan all meaningful section types; fall back to full-doc text if needed.
        _AUDIT_SECTION_LABELS = (
            "auditors_report", "directors_report", "unclassified",
            "notes_to_accounts", "management_discussion", "corporate_overview",
            "annual_report",
        )
        audit_remarks = self._extract_audit_remarks(
            "\n".join(s.raw_text for s in sections
                      if s.label in _AUDIT_SECTION_LABELS)
        )
        # Full-document fallback when section classification missed the auditor page
        if not audit_remarks:
            audit_remarks = self._extract_audit_remarks(parsed_doc.text_content or "")
        # Merge legacy audit_qualifications field from PDFParser (avoids duplicates by type)
        _seen_types = {r["type"] for r in audit_remarks}
        for q in (parsed_doc.financial_data or {}).get("audit_qualifications", []):
            rtype = "QUALIFIED_OPINION"
            if rtype not in _seen_types:
                audit_remarks.append({
                    "type": rtype,
                    "severity": "HIGH",
                    "context": q.get("context", ""),
                })
                _seen_types.add(rtype)

        # Step 7: Global aggregation
        all_figs = [fig for sec in sections for fig in sec.financial_figures] + table_figures + parser_figures
        all_flags = list({flag for sec in sections for flag in sec.flags})
        global_entities = self._merge_entities(sections)
        section_index = {sec.label: sec for sec in reversed(sections)}  # last wins

        segment_summary = self._build_summary(sections, all_figs, all_flags, parsed_doc)
        segment_summary["audit_remarks"] = audit_remarks

        logger.info(
            f"[Segmenter] Done: {len(sections)} sections, "
            f"{len(all_figs)} figures ({len(parser_figures)} from parser), {len(all_flags)} flags"
        )

        return SegmentedDocument(
            source_file=parsed_doc.file_name,
            doc_type=parsed_doc.doc_type,
            sections=sections,
            section_index=section_index,
            global_entities=global_entities,
            all_financial_figures=all_figs,
            red_flags=all_flags,
            segment_summary=segment_summary,
        )

    # ─── BLOCK SPLITTING ──────────────────────────────────────────────────────

    def _split_into_blocks(self, text: str) -> List[Dict]:
        """
        Split text into candidate blocks using:
        - Blank line separators (≥2 consecutive blank lines)
        - ALL-CAPS headings
        - Numbered headings  (1. / 1.1 / i. etc.)
        - Page break markers
        """
        blocks = []
        current_lines: List[str] = []
        blank_streak = 0

        for line in text.split("\n"):
            stripped = line.strip()

            if not stripped:
                blank_streak += 1
                if blank_streak >= 2 and current_lines:
                    # Flush current block
                    blocks.append({"text": "\n".join(current_lines), "heading": None})
                    current_lines = []
                continue

            blank_streak = 0

            # Detect headings
            if self._is_heading(stripped):
                if current_lines:
                    blocks.append({"text": "\n".join(current_lines), "heading": None})
                    current_lines = []
                blocks.append({"text": stripped, "heading": stripped})
                continue

            current_lines.append(line)

        if current_lines:
            blocks.append({"text": "\n".join(current_lines), "heading": None})

        # Merge heading block with the content block that immediately follows
        merged = []
        i = 0
        while i < len(blocks):
            b = blocks[i]
            if b["heading"] and i + 1 < len(blocks):
                merged.append({"text": b["heading"] + "\n" + blocks[i + 1]["text"],
                                "heading": b["heading"]})
                i += 2
            else:
                merged.append(b)
                i += 1

        return merged

    def _is_heading(self, line: str) -> bool:
        """Detect if a line is a section heading."""
        if len(line) < 4 or len(line) > 120:
            return False
        # ALL CAPS
        if line.isupper() and len(line.split()) >= 2:
            return True
        # Numbered heading: "1.", "1.1", "A.", "Section 1"
        if re.match(r"^(?:\d{1,2}\.?\d{0,2}\.?|[A-Z]\.)\s+[A-Z]", line):
            return True
        # Title case with no punctuation
        if (line.istitle() and len(line.split()) >= 3
                and not re.search(r"[.,:;?]", line)):
            return True
        return False

    # ─── BLOCK CLASSIFICATION ─────────────────────────────────────────────────

    # Fallback header patterns when keyword match fails — catches common headers
    _HEADER_FALLBACKS = [
        (re.compile(r"balance\s*sheet|statement of.*assets", re.IGNORECASE), "balance_sheet"),
        (re.compile(r"profit\s*(?:&|and)\s*loss|income\s*statement|statement of.*(?:income|P&L)", re.IGNORECASE), "profit_loss"),
        (re.compile(r"cash\s*flow", re.IGNORECASE), "cash_flow"),
        (re.compile(r"auditor.?s?\s*report|independent\s*auditor", re.IGNORECASE), "auditors_report"),
        (re.compile(r"director.?s?\s*report", re.IGNORECASE), "directors_report"),
        (re.compile(r"notes\s*(to|on)\s*(the\s*)?(?:financial|account)", re.IGNORECASE), "notes_to_accounts"),
        (re.compile(r"related\s*party", re.IGNORECASE), "related_party"),
        (re.compile(r"contingent\s*liabilit", re.IGNORECASE), "contingent_liabilities"),
        (re.compile(r"corporate\s*governance", re.IGNORECASE), "corporate_governance"),
        (re.compile(r"management.*discussion|md\s*&\s*a", re.IGNORECASE), "management_discussion"),
        (re.compile(r"schedule.*(?:borrowing|debt|loan|fixed\s*asset)", re.IGNORECASE), "notes_to_accounts"),
    ]

    def _classify_blocks(self, blocks: List[Dict], schema: List[Dict]) -> List[DocumentSection]:
        """Match each block to a section label."""
        sections: List[DocumentSection] = []

        for blk in blocks:
            text_lower = blk["text"].lower()

            best_label = "unclassified"
            best_score = 0

            for schema_entry in schema:
                score = sum(1 for kw in schema_entry["keywords"] if kw in text_lower)
                if score > best_score:
                    best_score = score
                    best_label = schema_entry["label"]

            # Confidence: 1 keyword = 0.5, 2 = 0.75, 3+ = 0.95
            confidence = min(0.5 + (best_score - 1) * 0.25, 0.95) if best_score > 0 else 0.15

            # Fallback: try header-based patterns if keyword match gave "unclassified"
            if best_label == "unclassified":
                header_text = blk["text"][:300]  # check first 300 chars for headers
                for pat, label in self._HEADER_FALLBACKS:
                    if pat.search(header_text):
                        best_label = label
                        confidence = 0.55
                        break

            sections.append(DocumentSection(
                label=best_label,
                raw_text=blk["text"],
                page_hint=None,
                confidence=confidence,
                entities={},
                financial_figures=[],
                flags=[],
            ))

        return sections

    # ─── FIGURE EXTRACTION ────────────────────────────────────────────────────

    def _extract_figures(self, text: str) -> List[Dict]:
        """Extract financial figures from section text."""
        figures = []
        seen = set()

        for compiled_re, fig_type in self._figure_compiled:
            for match in compiled_re.finditer(text):
                gd = match.groupdict()
                label_raw = gd.get("label", "").strip().lower()
                value_raw = gd.get("value", "").replace(",", "").strip()

                if not label_raw or not value_raw:
                    continue

                # Normalise label
                norm_label = self._normalise_label(label_raw)
                cache_key = f"{norm_label}:{value_raw}"
                if cache_key in seen:
                    continue
                seen.add(cache_key)

                try:
                    value = float(value_raw)
                except ValueError:
                    continue

                unit = gd.get("unit", "").strip() if gd.get("unit") else ""

                # Convert to absolute rupees
                multiplier = 1
                if unit.lower() in ("cr", "cr.", "crore", "crores"):
                    multiplier = 10_000_000
                elif unit.lower() in ("l", "l.", "lakh", "lakhs"):
                    multiplier = 100_000
                elif unit.lower() == "k":
                    multiplier = 1_000

                figures.append({
                    "label": norm_label,
                    "canonical_label": self._canonical_label(norm_label),
                    "raw_value": value,
                    "unit": unit,
                    "absolute_value": value * multiplier,
                    "type": fig_type,
                    "context": text[max(0, match.start() - 60): match.end() + 60].strip(),
                })

        return figures

    def _extract_table_figures(self, tables: List[Dict]) -> List[Dict]:
        """Parse financial figures from structured tables."""
        figures = []

        for table in tables:
            if not table or "rows" not in table:
                continue
            headers = table.get("headers", [])
            for row in table.get("rows", []):
                # First column is usually the label
                if not row:
                    continue
                cols = list(row.values())
                label_raw = str(cols[0]).strip() if cols else ""
                if not label_raw or len(label_raw) < 3:
                    continue

                norm_label = self._normalise_label(label_raw)
                canon = self._canonical_label(norm_label)

                for i, col_val in enumerate(cols[1:], start=1):
                    clean_val = re.sub(r"[^\d.]", "", str(col_val))
                    if not clean_val:
                        continue
                    try:
                        value = float(clean_val)
                    except ValueError:
                        continue

                    header = headers[i] if i < len(headers) else f"col_{i}"
                    figures.append({
                        "label": norm_label,
                        "canonical_label": canon,
                        "raw_value": value,
                        "unit": "",
                        "absolute_value": value,
                        "type": "table",
                        "period": header,
                        "context": f"Table row: {label_raw}",
                    })

        return figures

    # Mapping from PDFParser financial_data keys → SegmentedDocument canonical labels
    _PARSER_TO_CANON: Dict[str, str] = {
        # Annual report keys
        "revenue":             "revenue",
        "ebitda":              "ebitda",
        "pat":                 "pat",
        "total_debt":          "total_debt",
        "equity":              "net_worth",
        "current_assets":      "current_assets",
        "current_liabilities": "current_liab",
        # GST keys
        "gstr1_turnover":      "gst_turnover",
        "itc_claimed":         "itc",
        # ITR keys
        "gross_total_income":  "revenue",
        "taxable_income":      "revenue",
    }

    def _extract_parser_financial_data(self, parsed_doc: "ParsedDocument") -> List[Dict]:
        """
        Convert PDFParser's structured financial_data into the all_financial_figures
        format so the FeatureEngine and verification engines can use it.
        Values from PDFParser are already in absolute rupees (Cr/Lakh multiplied).
        We mark them type='currency' and unit='_parsed' (truthy) so the
        FeatureEngine's unit-filter accepts them.
        """
        figures: List[Dict] = []
        fd = getattr(parsed_doc, "financial_data", None)
        if not isinstance(fd, dict):
            return figures

        for key, val in fd.items():
            if val is None or not isinstance(val, (int, float)) or val <= 0:
                continue
            canon = self._PARSER_TO_CANON.get(key)
            if not canon:
                continue
            figures.append({
                "label":           key,
                "canonical_label": canon,
                "raw_value":       val,
                "unit":            "_parsed",   # truthy → passes unit filter; already absolute
                "absolute_value":  val,
                "type":            "currency",
                "context":         f"PDFParser structured extraction: {key}",
            })

        if figures:
            logger.debug(f"[Segmenter] Parser financial figures: {[f['label'] for f in figures]}")
        return figures

    def _normalise_label(self, raw: str) -> str:
        """Clean and normalise a label string."""
        cleaned = re.sub(r"\s+", " ", raw).strip().lower()
        cleaned = re.sub(r"[^\w\s/&()-]", "", cleaned)
        return cleaned

    def _canonical_label(self, norm: str) -> str:
        """Map a label to a canonical key or return 'other'."""
        for canon, aliases in self.KEY_LABELS.items():
            for alias in aliases:
                if alias in norm:
                    return canon
        return "other"

    # ─── ENTITY EXTRACTION ────────────────────────────────────────────────────

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities using regex patterns.
        spaCy NER is applied at agent level for deeper extraction.
        """
        entities: Dict[str, List[str]] = {}

        patterns_map = {
            "gstin":        r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b",
            "pan":          r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b",
            "cin":          r"\b[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\b",
            "din":          r"\bDIN[\s:]*([0-9]{8})\b",
            "ifsc":         r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
            "person_name":  r"\b(?:Mr\.|Ms\.|Dr\.|Shri|Smt\.|CA|CS)\s+([A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\b",
            "date":         r"\b(\d{1,2}[-/\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/\s]\d{2,4}|\d{1,2}/\d{1,2}/\d{2,4})\b",
            "company_name": r"\b([A-Z][A-Za-z\s&.()]{5,60}(?:Limited|Ltd\.?|Pvt\.|LLP|Private Limited|Pvt\. Ltd\.))\b",
            "bank_name":    r"\b((?:State Bank|SBI|HDFC|ICICI|Axis|Kotak|Bank of Baroda|Bank of India|Punjab National|Canara|Union Bank|IndusInd)[A-Za-z\s]*Bank(?:\s+of\s+[A-Za-z]+)?)\b",
        }

        for entity_type, pattern in patterns_map.items():
            matches = re.findall(pattern, text)
            if matches:
                # Flatten if groups
                flat = [m if isinstance(m, str) else m for m in matches]
                unique = list(dict.fromkeys(flat))[:10]
                entities[entity_type] = unique

        return entities

    # ─── RED FLAG DETECTION ───────────────────────────────────────────────────

    def _detect_flags(self, text: str) -> List[str]:
        """Scan text for red-flag patterns."""
        flags = []
        for compiled_re, flag_label in self._red_flag_compiled:
            if compiled_re.search(text):
                flags.append(flag_label)
        return flags

    def _extract_audit_remarks(self, text: str) -> List[Dict[str, str]]:
        """
        Return structured audit remark objects from auditor's report / directors' report text.
        Each remark includes: type, severity, and up to 200 chars of context.
        De-duped by remark type so the same qualification isn't listed N times.
        """
        remarks: List[Dict[str, str]] = []
        seen_types: set = set()
        for pattern, remark_type, severity in self._AUDIT_REMARK_PATTERNS:
            if remark_type in seen_types:
                continue
            m = pattern.search(text)
            if m:
                start = max(0, m.start() - 80)
                end   = min(len(text), m.end() + 120)
                ctx   = re.sub(r"\s+", " ", text[start:end]).strip()
                remarks.append({
                    "type":     remark_type,
                    "severity": severity,
                    "context":  ctx,
                })
                seen_types.add(remark_type)
        return remarks

    # ─── ENTITY MERGING ───────────────────────────────────────────────────────

    def _merge_entities(self, sections: List[DocumentSection]) -> Dict[str, List[str]]:
        merged: Dict[str, List[str]] = {}
        for sec in sections:
            for etype, vals in sec.entities.items():
                merged.setdefault(etype, [])
                for v in vals:
                    if v not in merged[etype]:
                        merged[etype].append(v)
        return merged

    # ─── SUMMARY BUILDER ──────────────────────────────────────────────────────

    def _build_summary(
        self,
        sections: List[DocumentSection],
        all_figs: List[Dict],
        all_flags: List[str],
        parsed_doc: ParsedDocument,
    ) -> Dict[str, Any]:
        """Build a high-level summary of segmentation results."""
        # Group figures by canonical label
        canonical_map: Dict[str, List[float]] = {}
        for fig in all_figs:
            canon = fig["canonical_label"]
            if canon != "other":
                canonical_map.setdefault(canon, []).append(fig["absolute_value"])

        # Best estimate = median of all found values for each canonical label
        key_figures: Dict[str, Optional[float]] = {}
        for canon, vals in canonical_map.items():
            if vals:
                sorted_vals = sorted(vals)
                mid = len(sorted_vals) // 2
                key_figures[canon] = sorted_vals[mid]

        # Flag severity
        severity = "LOW"
        if any("LEGAL" in f or "CREDIT" in f or "AUDIT" in f for f in all_flags):
            severity = "MEDIUM"
        if any(kw in " ".join(all_flags) for kw in
               ["Wilful", "Insolvency", "Fraud", "NPA", "Going concern"]):
            severity = "HIGH"

        return {
            "doc_type": parsed_doc.doc_type,
            "source_file": parsed_doc.file_name,
            "total_sections": len(sections),
            "sections_found": [s.label for s in sections if s.label != "unclassified"],
            "total_figures_extracted": len(all_figs),
            "key_financial_figures": key_figures,
            "red_flags": all_flags,
            "flag_severity": severity,
            "extraction_confidence": parsed_doc.extraction_confidence,
            "page_count": parsed_doc.page_count,
        }
