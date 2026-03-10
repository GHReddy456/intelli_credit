"""
OCR Engine — pytesseract-based extraction for scanned Indian documents.
Returns the same ParsedDocument interface as PDFParser.
"""
import re
from pathlib import Path
from typing import List, Tuple
from loguru import logger

try:
    import numpy as np
    NUMPY_OK = True
except ImportError:
    np = None
    NUMPY_OK = False

from ingestion.pdf_parser import ParsedDocument, DOC_TYPE_KEYWORDS


class OCREngine:
    """
    Converts scanned/image-based PDFs to text via pytesseract.
    Pre-processing pipeline: grayscale → denoise → deskew → threshold.
    Falls back gracefully if dependencies are missing.
    """

    def __init__(self):
        self._tesseract_ok = self._check_tesseract()
        self._pdf2image_ok = self._check_pdf2image()

    # ── Public API ─────────────────────────────────────────────────────────
    def parse(self, file_path: str) -> ParsedDocument:
        fp = Path(file_path)
        logger.info(f"[OCREngine] Processing: {fp.name}")

        if not self._tesseract_ok or not self._pdf2image_ok:
            logger.warning("[OCREngine] Dependencies missing — returning empty doc")
            return self._empty(fp)

        try:
            pages_text = self._ocr_pdf(str(fp))
            full_text  = "\n".join(pages_text)
            confidence = self._quality(full_text) * 0.85   # OCR slight penalty
            doc_type   = self._detect_type(full_text, fp.name)
            return ParsedDocument(
                file_name=fp.name,
                doc_type=doc_type,
                text_content=full_text,
                tables=[],
                metadata={},
                page_count=len(pages_text),
                extraction_confidence=confidence,
                raw_pages=pages_text,
            )
        except Exception as e:
            logger.error(f"[OCREngine] Failed: {e}")
            return self._empty(fp)

    # ── OCR Pipeline ───────────────────────────────────────────────────────
    def _ocr_pdf(self, file_path: str) -> List[str]:
        from pdf2image import convert_from_path
        import pytesseract

        images = convert_from_path(file_path, dpi=300, fmt="PNG")
        pages  = []
        for i, img in enumerate(images):
            processed = self._preprocess(img)
            # Indian PDFs: English + Devanagari fallback
            cfg  = "--oem 3 --psm 6 -l eng"
            text = pytesseract.image_to_string(processed, config=cfg)
            pages.append(text)
            logger.debug(f"[OCREngine] OCR'd page {i+1}/{len(images)}")
        return pages

    def _preprocess(self, img):
        """Enhance image quality before OCR."""
        import cv2
        from PIL import Image

        arr = np.array(img)
        if arr.ndim == 3:
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        else:
            gray = arr

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=10)

        # Adaptive threshold
        thresh = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Deskew
        thresh = self._deskew(thresh)
        return Image.fromarray(thresh)

    def _deskew(self, img_array: np.ndarray) -> np.ndarray:
        import cv2
        coords = np.column_stack(np.where(img_array > 0))
        if len(coords) < 10:
            return img_array
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) > 0.5:
            h, w = img_array.shape
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            img_array = cv2.warpAffine(img_array, M, (w, h), flags=cv2.INTER_CUBIC)
        return img_array

    # ── Helpers ────────────────────────────────────────────────────────────
    def _quality(self, text: str) -> float:
        if not text or len(text) < 100:
            return 0.0
        alpha = sum(c.isalpha() for c in text) / max(len(text), 1)
        return round(min(max(alpha * 1.2, 0.0), 1.0), 3)

    def _detect_type(self, text: str, name: str) -> str:
        tl = (text + name).lower()
        scores = {t: sum(kw in tl for kw in kws) for t, kws in DOC_TYPE_KEYWORDS.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "unknown"

    def _empty(self, fp: Path) -> ParsedDocument:
        return ParsedDocument(
            file_name=fp.name,
            doc_type="unknown", text_content="",
            tables=[], metadata={},
            page_count=0, extraction_confidence=0.0,
        )

    def _check_tesseract(self) -> bool:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            logger.warning("[OCREngine] pytesseract/Tesseract not available")
            return False

    def _check_pdf2image(self) -> bool:
        try:
            import pdf2image   # noqa
            return True
        except ImportError:
            logger.warning("[OCREngine] pdf2image not available")
            return False
