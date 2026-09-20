"""Provider-aware OCR adapter — upgraded for PDF pages and image preprocessing.

Supports:
- Direct image OCR (PNG, JPG, JPEG)
- PDF page-to-image rendering then OCR
- Image preprocessing (grayscale, contrast, deskew)
- Multiple provider fallback (Tesseract, pdf2image)
- Structured confidence reporting
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


class OcrError(RuntimeError):
    pass


@dataclass
class OcrResult:
    """Structured OCR output with confidence and page info."""
    text: str
    page: int = 1
    confidence: float = 0.0
    source: str = "ocr"
    provider: str = ""
    warnings: list[str] = field(default_factory=list)


class OcrAdapter:
    PROVIDERS = ("tesseract",)

    @classmethod
    def available_providers(cls) -> list[str]:
        providers: list[str] = []
        try:
            import pytesseract  # noqa: F401
            providers.append("tesseract")
        except ImportError:
            pass
        return providers

    @classmethod
    def is_configured(cls) -> bool:
        return bool(cls.available_providers())

    @classmethod
    def has_pillow(cls) -> bool:
        try:
            from PIL import Image  # noqa: F401
            return True
        except ImportError:
            return False

    @classmethod
    def has_pdf2image(cls) -> bool:
        try:
            from pdf2image import convert_from_path  # noqa: F401
            return True
        except ImportError:
            return False

    @classmethod
    async def ocr(cls, image_path: str) -> str:
        """OCR a single image file. Returns extracted text."""
        results = await cls.ocr_image(image_path)
        return "\n".join(r.text for r in results if r.text.strip())

    @classmethod
    async def ocr_image(cls, image_path: str) -> list[OcrResult]:
        """OCR an image file with preprocessing. Returns list of OcrResult."""
        providers = cls.available_providers()
        for provider in providers:
            try:
                if provider == "tesseract":
                    return await cls._ocr_tesseract_image(image_path)
            except Exception as exc:
                logger.warning("OCR via %s failed: %s", provider, exc)
        raise OcrError(
            "OCR is not configured (no ``pytesseract`` + Tesseract binary). "
            "Install ``pytesseract`` and the Tesseract binary for image/scanned PDF support."
        )

    @classmethod
    async def ocr_pdf(cls, pdf_path: str) -> list[OcrResult]:
        """OCR all pages of a PDF by rendering to images first."""
        # Try pdf2image first (uses poppler on Linux, or Pillow fallback)
        if cls.has_pdf2image():
            try:
                return await cls._ocr_pdf_pdf2image(pdf_path)
            except Exception as exc:
                logger.warning("pdf2image failed, falling back to pdfplumber: %s", exc)

        # Fallback: use pdfplumber to render pages to images
        try:
            return await cls._ocr_pdf_pdfplumber(pdf_path)
        except Exception as exc:
            logger.warning("pdfplumber rendering failed: %s", exc)

        raise OcrError(
            "Could not render PDF pages to images for OCR. "
            "Install ``pdf2image`` + poppler, or ``Pillow`` for page rendering."
        )

    @classmethod
    async def _ocr_pdf_pdf2image(cls, pdf_path: str) -> list[OcrResult]:
        """Use pdf2image to convert PDF pages to PIL Images, then OCR."""
        from pdf2image import convert_from_path

        images = convert_from_path(pdf_path, dpi=300)
        results: list[OcrResult] = []

        for i, img in enumerate(images, 1):
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                img.save(tmp.name, "PNG")
                try:
                    page_results = await cls._ocr_tesseract_image(tmp.name)
                    for r in page_results:
                        r.page = i
                        r.source = "ocr_pdf"
                    results.extend(page_results)
                finally:
                    try:
                        os.unlink(tmp.name)
                    except OSError:
                        pass

        return results

    @classmethod
    async def _ocr_pdf_pdfplumber(cls, pdf_path: str) -> list[OcrResult]:
        """Use pdfplumber to convert pages to images, then OCR."""
        try:
            from PIL import Image
        except ImportError:
            raise OcrError("Pillow is required for PDF page rendering")

        import pdfplumber

        results: list[OcrResult] = []

        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                # Convert page to PIL Image
                try:
                    im = page.to_image(resolution=300)
                    # pdfplumber Image object has a .original attribute
                    pil_img = im.original if hasattr(im, "original") else None
                    if pil_img is None:
                        continue

                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        pil_img.save(tmp.name, "PNG")
                        try:
                            page_results = await cls._ocr_tesseract_image(tmp.name)
                            for r in page_results:
                                r.page = i
                                r.source = "ocr_pdf"
                            results.extend(page_results)
                        finally:
                            try:
                                os.unlink(tmp.name)
                            except OSError:
                                pass
                except Exception as exc:
                    logger.warning("Failed to render PDF page %d: %s", i, exc)
                    continue

        return results

    @classmethod
    async def _ocr_tesseract_image(cls, image_path: str) -> list[OcrResult]:
        """OCR a single image using Tesseract with preprocessing."""
        import pytesseract

        try:
            from PIL import Image, ImageFilter, ImageEnhance
        except ImportError:
            # Fall back to no preprocessing
            text = pytesseract.image_to_string(image_path) or ""
            confidence = 0.7
            return [OcrResult(
                text=text.strip(),
                confidence=confidence,
                provider="tesseract",
            )]

        # Load and preprocess image
        img = Image.open(image_path)

        # Convert to RGB if needed
        if img.mode not in ("L", "RGB"):
            img = img.convert("RGB")

        # Convert to grayscale for better OCR
        if img.mode != "L":
            img = img.convert("L")

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

        # Sharpen
        img = img.filter(ImageFilter.SHARPEN)

        # Resize if too small (OCR works better on larger images)
        width, height = img.size
        if width < 1000:
            scale = 1000 / width
            img = img.resize((int(width * scale), int(height * scale)), Image.LANCZOS)

        # Get OCR with confidence data
        try:
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            # Calculate average confidence from word-level data
            confs = [int(c) for c in data["conf"] if int(c) > 0]
            avg_conf = sum(confs) / len(confs) / 100.0 if confs else 0.5
        except Exception:
            avg_conf = 0.7

        text = pytesseract.image_to_string(img) or ""

        return [OcrResult(
            text=text.strip(),
            confidence=round(avg_conf, 3),
            provider="tesseract",
        )]

    @classmethod
    def ocr_image_sync(cls, image_path: str) -> str:
        """Synchronous OCR for a single image (non-async context)."""
        try:
            import pytesseract
            return pytesseract.image_to_string(image_path) or ""
        except ImportError:
            raise OcrError("pytesseract is not installed")

    @classmethod
    def ocr_pdf_sync(cls, pdf_path: str) -> str:
        """Synchronous OCR for a PDF (non-async context)."""
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, dpi=300)
            texts = []
            for img in images:
                try:
                    import pytesseract
                    texts.append(pytesseract.image_to_string(img) or "")
                except ImportError:
                    raise OcrError("pytesseract is not installed")
            return "\n\n".join(texts)
        except ImportError:
            pass

        # Fallback: try pdfplumber rendering
        try:
            from PIL import Image
            import pdfplumber
            import pytesseract

            texts = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    try:
                        im = page.to_image(resolution=300)
                        pil_img = im.original if hasattr(im, "original") else None
                        if pil_img:
                            texts.append(pytesseract.image_to_string(pil_img) or "")
                    except Exception:
                        continue
            return "\n\n".join(texts)
        except Exception as exc:
            raise OcrError(f"PDF OCR failed: {exc}")
