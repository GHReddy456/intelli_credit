"""
PDF Parser - Multi-format document ingestion
Handles scanned PDFs, native PDFs, tables, and forms
"""
import os
import io
import re
import json
import pdfplumber
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from loguru import logger

# Optional heavy deps — import lazily so a missing binary doesn't crash startup
try:
    import fitz as _fitz
    # Verify this is actually PyMuPDF (not the unrelated 'fitz' stub package)
    if not hasattr(_fitz, 'open'):
        raise ImportError("Wrong fitz package installed. Run: pip uninstall fitz -y && pip install PyMuPDF")
    PYMUPDF_OK = True
except Exception as _e:
    logger.warning(f"[PDFParser] PyMuPDF unavailable ({_e}) — using pdfplumber only")
    _fitz = None
    PYMUPDF_OK = False

try:
    import pytesseract as _pytesseract
    TESSERACT_OK = True
except ImportError:
    _pytesseract = None
    TESSERACT_OK = False

try:
    import cv2 as _cv2
    import numpy as _np
    from PIL import Image as _Image
    CV2_OK = True
except ImportError:
    _cv2 = _np = _Image = None
    CV2_OK = False

try:
    import camelot
except ImportError:
    camelot = None

# Module-level constant — imported by ocr_engine.py
DOC_TYPE_KEYWORDS = {
    "annual_report":  ["annual report", "directors report", "auditors report", "standalone", "consolidated"],
    "gst":            ["gstr", "gstin", "input tax credit", "itc", "outward supply", "inward supply", "gst return"],
    "bank_statement": ["account statement", "opening balance", "closing balance", "debit", "credit", "ifsc"],
    "itr":            ["income tax return", "itr", "assessment year", "pan", "total income", "tax liability"],
    "legal":          ["writ petition", "honble court", "plaintiff", "defendant", "order", "decree", "drt", "nclt"],
    "sanction_letter":["sanction", "credit limit", "rate of interest", "repayment", "security", "disbursement"],
}


@dataclass
class ParsedDocument:
    file_name: str
    doc_type: str  # annual_report, gst, bank_statement, legal, itr, sanction_letter
    text_content: str
    tables: List[Dict]
    metadata: Dict[str, Any]
    page_count: int
    extraction_confidence: float
    raw_pages: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    financial_data: Dict = field(default_factory=dict)


class PDFParser:
    """
    Advanced PDF parser with OCR fallback for scanned Indian documents.
    Specifically tuned for:
    - Annual Reports (MCA/ROC filings)
    - GST Returns (GSTR-1, GSTR-3B, GSTR-2A)
    - Bank Statements (Indian banks - SBI, HDFC, ICICI, Axis etc.)
    - ITR documents
    - Legal notices and court orders
    - Sanction letters from banks
    """

    def __init__(self, tesseract_path: Optional[str] = None):
        if TESSERACT_OK:
            import pytesseract
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            elif os.name == "nt":  # Windows
                pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

        # Indian-specific patterns
        self.patterns = {
            "gstin": r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b",
            "pan": r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b",
            "cin": r"\b[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\b",
            "din": r"\bDIN[:\s]*[0-9]{8}\b",
            "amount_inr": r"₹\s*[\d,]+\.?\d*\s*(?:Cr|L|Lakh|Crore|K|lakhs|crores)?",
            "amount_words": r"(?:Rs\.?|INR)\s*[\d,]+\.?\d*",
            "date_indian": r"\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b",
            "ifsc": r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
            "account_num": r"\b\d{9,18}\b",
        }

        self.doc_type_keywords = DOC_TYPE_KEYWORDS

    def parse(self, file_path: str) -> ParsedDocument:
        """Main entry point - detect doc type and parse accordingly."""
        path = Path(file_path)
        logger.info(f"Parsing document: {path.name}")

        # Try native PDF extraction first
        text, tables, page_count, confidence = self._try_native_extraction(file_path)

        # Fallback to OCR if text quality is poor
        if confidence < 0.4:
            logger.warning(f"Low confidence ({confidence:.2f}), fallback to OCR")
            text, _, _, confidence = self._ocr_extraction(file_path)

        # Detect document type
        doc_type = self._detect_doc_type(text, path.name)
        logger.info(f"Detected doc type: {doc_type} (confidence: {confidence:.2f})")

        # Extract metadata
        metadata = self._extract_metadata(text, doc_type)

        # Extract financial data based on doc type
        financial_data = self._extract_financial_data(text, tables, doc_type)

        return ParsedDocument(
            file_name=path.name,
            doc_type=doc_type,
            text_content=text,
            tables=tables,
            metadata=metadata,
            page_count=page_count,
            extraction_confidence=confidence,
            financial_data=financial_data,
        )

    def _try_native_extraction(self, file_path: str) -> Tuple[str, List[Dict], int, float]:
        """Extract text from native (non-scanned) PDFs."""
        full_text = []
        tables = []
        page_count = 0

        # --- pdfplumber (always available) ---
        try:
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    t = page.extract_text() or ""
                    full_text.append(t)
                    extracted_tables = page.extract_tables() or []
                    for table in extracted_tables:
                        if table and len(table) > 1:
                            tables.append(self._clean_table(table))
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")

        # --- PyMuPDF (optional, better text layout) ---
        if PYMUPDF_OK and not any(full_text):
            try:
                doc = _fitz.open(file_path)
                page_count = len(doc)
                full_text = [page.get_text("text") for page in doc]
                doc.close()
            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed: {e}")

        combined_text = "\n".join(full_text)
        confidence = self._estimate_text_quality(combined_text)
        return combined_text, tables, page_count, confidence

    def _ocr_extraction(self, file_path: str) -> Tuple[str, List[Dict], int, float]:
        """OCR-based extraction for scanned documents. Skipped gracefully if deps missing."""
        if not TESSERACT_OK:
            logger.warning("[PDFParser] Tesseract not available — skipping OCR")
            return "", [], 0, 0.0
        if not CV2_OK:
            logger.warning("[PDFParser] OpenCV not available — skipping OCR")
            return "", [], 0, 0.0

        pages_text = []
        try:
            # Prefer PyMuPDF for page→image (no poppler required)
            if PYMUPDF_OK:
                import io as _io
                from PIL import Image as _PIL_Image
                doc = _fitz.open(file_path)
                for i, page in enumerate(doc):
                    mat = _fitz.Matrix(2.0, 2.0)  # 2x zoom ≈ 144 dpi
                    pix = page.get_pixmap(matrix=mat, colorspace=_fitz.csGRAY)
                    img = _PIL_Image.open(_io.BytesIO(pix.tobytes("png")))
                    img_array = _np.array(img) if CV2_OK else img
                    text = _pytesseract.image_to_string(img_array, config="--oem 3 --psm 6 -l eng")
                    pages_text.append(text)
                    logger.debug(f"OCR page {i+1}/{len(doc)}")
                doc.close()
            else:
                from pdf2image import convert_from_path
                images = convert_from_path(file_path, dpi=300, fmt="PNG")
                for i, image in enumerate(images):
                    img_array = _np.array(image) if CV2_OK else image
                    text = _pytesseract.image_to_string(img_array, config="--oem 3 --psm 6 -l eng")
                    pages_text.append(text)
                    logger.debug(f"OCR page {i+1}/{len(images)}")
            combined = "\n".join(pages_text)
            confidence = self._estimate_text_quality(combined) * 0.85
            return combined, [], len(pages_text), confidence
        except Exception as e:
            logger.warning(f"OCR extraction failed (non-fatal): {e}")
            return "", [], 0, 0.0

    def _preprocess_for_ocr(self, img_array) -> "_Image.Image":
        """Enhance scanned image quality for OCR."""
        if not CV2_OK:
            return img_array
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = _cv2.cvtColor(img_array, _cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        denoised = _cv2.fastNlMeansDenoising(gray, h=10)
        thresh = _cv2.adaptiveThreshold(
            denoised, 255, _cv2.ADAPTIVE_THRESH_GAUSSIAN_C, _cv2.THRESH_BINARY, 11, 2
        )
        # Deskew
        coords = _np.column_stack(_np.where(thresh > 0))
        if len(coords) > 0:
            angle = _cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = 90 + angle
            if abs(angle) > 0.5:
                (h, w) = thresh.shape
                M = _cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
                thresh = _cv2.warpAffine(thresh, M, (w, h), flags=_cv2.INTER_CUBIC)
        return _Image.fromarray(thresh)

    def _detect_doc_type(self, text: str, filename: str) -> str:
        """Detect document type from content and filename."""
        text_lower = text.lower()
        filename_lower = filename.lower()

        scores = {}
        for doc_type, keywords in self.doc_type_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower or kw in filename_lower)
            scores[doc_type] = score

        if max(scores.values()) == 0:
            return "unknown"

        return max(scores, key=scores.get)

    def _extract_metadata(self, text: str, doc_type: str) -> Dict:
        """Extract key identifiers from text."""
        metadata = {}

        for pattern_name, pattern in self.patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                metadata[pattern_name] = list(set(matches))[:5]  # Top 5 unique

        # Indian financial year detection
        fy_pattern = r"(?:FY|F\.Y\.|Financial Year)[:\s]*(\d{4}[-–]\d{2,4})"
        fy_matches = re.findall(fy_pattern, text, re.IGNORECASE)
        if fy_matches:
            metadata["financial_years"] = list(set(fy_matches))

        # Company name extraction (first line or title)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            metadata["probable_company_name"] = lines[0][:100]

        return metadata

    def _extract_financial_data(self, text: str, tables: List[Dict], doc_type: str) -> Dict:
        """Extract structured financial data based on document type."""
        financial_data = {}

        if doc_type == "gst":
            financial_data = self._extract_gst_data(text, tables)
        elif doc_type == "bank_statement":
            financial_data = self._extract_bank_data(text, tables)
        elif doc_type == "annual_report":
            financial_data = self._extract_annual_report_data(text, tables)
        elif doc_type == "itr":
            financial_data = self._extract_itr_data(text, tables)

        return financial_data

    def _extract_gst_data(self, text: str, tables: List[Dict]) -> Dict:
        """Extract GST-specific data for GSTR analysis."""
        data = {
            "gstr1_turnover": None,
            "gstr3b_tax_paid": None,
            "itc_claimed": None,
            "itc_available": None,
            "outward_supplies": [],
            "inward_supplies": [],
            "gst_discrepancy_flag": False,
        }

        # Extract turnover figures
        turnover_pattern = r"(?:taxable value|outward supplies|total turnover)[:\s]*(?:Rs\.?|₹|INR)?\s*([\d,]+)"
        matches = re.findall(turnover_pattern, text, re.IGNORECASE)
        if matches:
            data["gstr1_turnover"] = self._parse_amount(matches[0])

        # ITC patterns
        itc_pattern = r"(?:input tax credit|ITC)[:\s]*(?:Rs\.?|₹|INR)?\s*([\d,]+)"
        itc_matches = re.findall(itc_pattern, text, re.IGNORECASE)
        if itc_matches:
            data["itc_claimed"] = self._parse_amount(itc_matches[0])

        return data

    def _extract_bank_data(self, text: str, tables: List[Dict]) -> Dict:
        """Extract bank statement data for analysis."""
        data = {
            "opening_balance": None,
            "closing_balance": None,
            "total_credits": 0,
            "total_debits": 0,
            "large_transactions": [],
            "cash_transactions": [],
            "emi_patterns": [],
            "abb": None,  # Average Bank Balance
        }

        # Extract balances
        ob_pattern = r"(?:opening balance)[:\s]*(?:Rs\.?|₹|INR)?\s*([\d,]+\.?\d*)"
        cb_pattern = r"(?:closing balance)[:\s]*(?:Rs\.?|₹|INR)?\s*([\d,]+\.?\d*)"

        ob_match = re.search(ob_pattern, text, re.IGNORECASE)
        cb_match = re.search(cb_pattern, text, re.IGNORECASE)

        if ob_match:
            data["opening_balance"] = self._parse_amount(ob_match.group(1))
        if cb_match:
            data["closing_balance"] = self._parse_amount(cb_match.group(1))

        # Parse transaction tables
        for table in tables:
            if self._is_transaction_table(table):
                transactions = self._parse_transactions(table)
                for txn in transactions:
                    if txn.get("amount", 0) > 1000000:  # > 10 lakh
                        data["large_transactions"].append(txn)
                    if "cash" in str(txn.get("narration", "")).lower():
                        data["cash_transactions"].append(txn)

        return data

    def _extract_annual_report_data(self, text: str, tables: List[Dict]) -> Dict:
        """Extract key financial data from annual reports."""
        data = {
            "revenue": {},
            "ebitda": {},
            "pat": {},
            "total_debt": {},
            "net_worth": {},
            "audit_qualifications": [],
            "contingent_liabilities": {},
            "related_party_transactions": [],
            "directors": [],
        }

        # Revenue patterns (Indian format: "Rs. X Crores" or "₹ X Cr.")
        rev_pattern = r"(?:revenue from operations|net revenue|total revenue)[^\n]*?(?:Rs\.?|₹|INR)?\s*([\d,]+\.?\d*)\s*(?:Cr|Crore|L|Lakh)?"
        rev_matches = re.findall(rev_pattern, text, re.IGNORECASE)
        if rev_matches:
            data["revenue"]["extracted"] = [self._parse_amount(m) for m in rev_matches[:3]]

        # Audit qualification check
        qual_keywords = ["emphasis of matter", "qualified opinion", "adverse opinion", "unable to obtain"]
        for kw in qual_keywords:
            if kw.lower() in text.lower():
                # Extract surrounding context
                idx = text.lower().find(kw.lower())
                context = text[max(0, idx-100):idx+300]
                data["audit_qualifications"].append({"keyword": kw, "context": context[:200]})

        # Directors extraction
        dir_pattern = r"(?:Mr\.|Ms\.|Dr\.|Shri|Smt\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})"
        directors = re.findall(dir_pattern, text)
        data["directors"] = list(set(directors))[:20]

        return data

    def _extract_itr_data(self, text: str, tables: List[Dict]) -> Dict:
        """Extract Income Tax Return data."""
        data = {
            "assessment_year": None,
            "gross_total_income": None,
            "taxable_income": None,
            "tax_paid": None,
            "tds_claimed": None,
            "return_type": None,
        }

        ay_pattern = r"Assessment Year[:\s]*(\d{4}[-–]\d{2,4})"
        ay_match = re.search(ay_pattern, text, re.IGNORECASE)
        if ay_match:
            data["assessment_year"] = ay_match.group(1)

        income_pattern = r"(?:gross total income|total income)[:\s]*(?:Rs\.?|₹)?\s*([\d,]+)"
        income_match = re.search(income_pattern, text, re.IGNORECASE)
        if income_match:
            data["gross_total_income"] = self._parse_amount(income_match.group(1))

        return data

    def _clean_table(self, raw_table: List[List]) -> Dict:
        """Clean and structure extracted tables."""
        if not raw_table:
            return {}

        # Use first row as headers
        headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(raw_table[0])]
        rows = []
        for row in raw_table[1:]:
            if row and any(cell for cell in row):
                row_dict = {headers[i]: str(cell).strip() if cell is not None else "" for i, cell in enumerate(row)}
                rows.append(row_dict)

        return {"headers": headers, "rows": rows}

    def _is_transaction_table(self, table: Dict) -> bool:
        """Check if table is a bank transaction table."""
        if not table or "headers" not in table:
            return False
        headers_lower = [h.lower() for h in table.get("headers", [])]
        tx_indicators = ["debit", "credit", "balance", "narration", "description", "date"]
        return sum(1 for ind in tx_indicators if any(ind in h for h in headers_lower)) >= 3

    def _parse_transactions(self, table: Dict) -> List[Dict]:
        """Parse transaction records from bank statement table."""
        transactions = []
        for row in table.get("rows", []):
            txn = {}
            for key, val in row.items():
                key_lower = key.lower()
                if "date" in key_lower:
                    txn["date"] = val
                elif "debit" in key_lower:
                    txn["debit"] = self._parse_amount(val)
                elif "credit" in key_lower:
                    txn["credit"] = self._parse_amount(val)
                elif "balance" in key_lower:
                    txn["balance"] = self._parse_amount(val)
                elif any(x in key_lower for x in ["narration", "description", "particulars", "remarks"]):
                    txn["narration"] = val

            if txn.get("debit") or txn.get("credit"):
                txn["amount"] = txn.get("debit") or txn.get("credit")
                transactions.append(txn)

        return transactions

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse Indian currency amounts."""
        if not amount_str:
            return None
        try:
            clean = re.sub(r"[^\d.]", "", str(amount_str))
            if clean:
                val = float(clean)
                # If amount looks like it's in lakhs/crores notation
                if "cr" in str(amount_str).lower():
                    val *= 10000000  # Convert crores to rupees
                elif "l" in str(amount_str).lower() or "lakh" in str(amount_str).lower():
                    val *= 100000
                return val
        except (ValueError, AttributeError):
            pass
        return None

    def _estimate_text_quality(self, text: str) -> float:
        """Estimate OCR/extraction quality (0-1)."""
        if not text or len(text) < 100:
            return 0.0

        # Check for readable content
        words = text.split()
        if len(words) < 50:
            return 0.1

        # Check alpha ratio
        alpha_chars = sum(1 for c in text if c.isalpha())
        total_chars = max(len(text), 1)
        alpha_ratio = alpha_chars / total_chars

        # Check for common OCR errors
        garbage_patterns = len(re.findall(r"[^\x00-\x7F]{3,}", text))
        garbage_ratio = garbage_patterns / max(len(words), 1)

        quality = alpha_ratio * 0.7 + (1 - min(garbage_ratio, 1)) * 0.3
        return min(max(quality, 0.0), 1.0)
