"""OCR Processing Module for Graphiti Influxer.

Provides OCR (Optical Character Recognition) capabilities for extracting
text from image-based PDFs and scanned documents.

Based on: github.com/Milofax/Archon/python/src/server/utils/ocr_processing.py

Edge cases handled:
- #2: Scanned PDF (image-only, needs OCR)
- #67: Handschrift (low confidence warning)
- #68: Niedriger DPI (warning wenn < 150 DPI)
- #69: OCR Timeout (60s pro Seite + Skip)
- #70: Multi-Language (eng+deu+spa Config)
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from influxer.config import OCR_DPI, OCR_LANGUAGE

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger(__name__)

# Check for OCR dependencies
try:
    from pdf2image import convert_from_bytes, convert_from_path

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    convert_from_bytes = None  # type: ignore[assignment]
    convert_from_path = None  # type: ignore[assignment]

try:
    import pytesseract

    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    pytesseract = None


# Constants
DEFAULT_PAGE_TIMEOUT = 60  # seconds per page (#69)
LOW_CONFIDENCE_THRESHOLD = 60  # percentage (#67)
MIN_RECOMMENDED_DPI = 150  # (#68)


def is_ocr_available() -> bool:
    """Check if OCR processing is available.

    Returns:
        True if both pdf2image and pytesseract are installed
    """
    return PDF2IMAGE_AVAILABLE and PYTESSERACT_AVAILABLE


def get_supported_languages() -> list[str]:
    """Get list of installed Tesseract languages.

    Returns:
        List of language codes available for OCR
    """
    if not PYTESSERACT_AVAILABLE or pytesseract is None:
        return []

    try:
        languages = pytesseract.get_languages()
        # Filter out 'osd' (orientation and script detection)
        return [lang for lang in languages if lang != "osd"]
    except Exception as e:
        logger.warning(f"Could not get Tesseract languages: {e}")
        return ["eng"]  # Default fallback


def check_language_installed(language: str) -> bool:
    """Check if a specific language or language combo is installed.

    Args:
        language: Tesseract language code (e.g., "eng", "eng+deu+spa")

    Returns:
        True if all specified languages are available
    """
    available = get_supported_languages()
    if not available:
        return False

    # Handle combined languages like "eng+deu+spa"
    requested = language.split("+")
    return all(lang in available for lang in requested)


def get_ocr_confidence(image: Image.Image, language: str = "eng") -> float:
    """Get OCR confidence score for an image.

    Edge case #67: Handschrift detection - warn if confidence < 60%

    Args:
        image: PIL Image to analyze
        language: Tesseract language code

    Returns:
        Average confidence score (0-100)
    """
    if not PYTESSERACT_AVAILABLE or pytesseract is None:
        return 0.0

    try:
        # Get detailed OCR data including confidence scores
        data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)

        confidences = [
            int(conf)
            for conf in data.get("conf", [])
            if conf != "-1" and str(conf).isdigit() and int(conf) > 0
        ]

        if not confidences:
            return 0.0

        return sum(confidences) / len(confidences)
    except Exception as e:
        logger.warning(f"Could not calculate OCR confidence: {e}")
        return 0.0


def check_image_dpi(image: Image.Image) -> int | None:
    """Check image DPI and warn if too low.

    Edge case #68: Warning wenn < 150 DPI

    Args:
        image: PIL Image to check

    Returns:
        DPI value if available, None if unknown
    """
    try:
        dpi_info = image.info.get("dpi")
        if dpi_info:
            # dpi can be (x_dpi, y_dpi) or a single value
            if isinstance(dpi_info, tuple):
                return min(int(dpi_info[0]), int(dpi_info[1]))
            return int(dpi_info)
    except Exception:
        pass
    return None


def _ocr_single_page(
    image: Image.Image,
    language: str,
    page_num: int,
    total_pages: int,
) -> tuple[int, str | None, float]:
    """OCR a single page with timeout handling.

    Args:
        image: PIL Image of the page
        language: Tesseract language code
        page_num: Current page number (1-indexed)
        total_pages: Total number of pages

    Returns:
        Tuple of (page_num, extracted_text or None, confidence)
    """
    if pytesseract is None:
        return (page_num, None, 0.0)

    try:
        # Get confidence first
        confidence = get_ocr_confidence(image, language)

        # Check DPI (#68)
        dpi = check_image_dpi(image)
        if dpi is not None and dpi < MIN_RECOMMENDED_DPI:
            logger.warning(f"Page {page_num}: Low DPI ({dpi}) may affect OCR quality")

        # Warn about low confidence (#67)
        if confidence < LOW_CONFIDENCE_THRESHOLD:
            logger.warning(
                f"Page {page_num}: Low OCR confidence ({confidence:.1f}%) - "
                "may be handwriting or poor quality scan"
            )

        # Extract text
        page_text = pytesseract.image_to_string(image, lang=language)

        if page_text and page_text.strip():
            # Add page marker for multi-page documents
            if total_pages > 1:
                return (page_num, f"--- Page {page_num} ---\n{page_text.strip()}", confidence)
            return (page_num, page_text.strip(), confidence)

        logger.debug(f"No text found on page {page_num}")
        return (page_num, None, confidence)

    except Exception as e:
        logger.warning(f"OCR failed on page {page_num}: {e}")
        return (page_num, None, 0.0)


def extract_text_with_ocr(
    file_content: bytes,
    language: str | None = None,
    dpi: int | None = None,
    page_timeout: int = DEFAULT_PAGE_TIMEOUT,
) -> str | None:
    """Extract text from a PDF using OCR (Tesseract).

    This function converts each PDF page to an image and runs OCR on it.
    Use this for scanned documents or image-based PDFs.

    Edge cases handled:
    - #2: Scanned PDF support
    - #67: Low confidence warning for handwriting
    - #68: Low DPI warning
    - #69: Per-page timeout
    - #70: Multi-language support

    Args:
        file_content: Raw PDF bytes
        language: Tesseract language code (default from config: "eng+deu+spa")
        dpi: Resolution for PDF to image conversion (default from config: 300)
        page_timeout: Timeout in seconds per page (default: 60)

    Returns:
        Extracted text content, or None if OCR fails

    Raises:
        RuntimeError: If OCR dependencies are not installed
    """
    if not PDF2IMAGE_AVAILABLE or convert_from_bytes is None:
        raise RuntimeError(
            "pdf2image not installed. Install with: pip install pdf2image\n"
            "Also requires poppler: brew install poppler (macOS) or apt install poppler-utils (Linux)"
        )

    if not PYTESSERACT_AVAILABLE or pytesseract is None:
        raise RuntimeError(
            "pytesseract not installed. Install with: pip install pytesseract\n"
            "Also requires tesseract: brew install tesseract (macOS) or apt install tesseract-ocr (Linux)"
        )

    # Use defaults from config if not provided
    if language is None:
        language = OCR_LANGUAGE
    if dpi is None:
        dpi = OCR_DPI

    try:
        logger.info(f"Starting OCR extraction (language={language}, dpi={dpi})")

        # Convert PDF pages to images
        images = convert_from_bytes(file_content, dpi=dpi)

        if not images:
            logger.warning("No pages found in PDF for OCR")
            return None

        total_pages = len(images)
        logger.info(f"Converting {total_pages} pages with OCR...")

        # Extract text from each page with timeout (#69)
        text_content: list[str] = []
        total_confidence = 0.0
        processed_pages = 0

        for page_num, image in enumerate(images, start=1):
            try:
                # Use ThreadPoolExecutor for timeout support (#69)
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        _ocr_single_page, image, language, page_num, total_pages
                    )
                    try:
                        _, page_text, confidence = future.result(timeout=page_timeout)
                        if page_text:
                            text_content.append(page_text)
                            total_confidence += confidence
                            processed_pages += 1
                            logger.debug(
                                f"OCR extracted {len(page_text)} chars from page {page_num}"
                            )
                    except concurrent.futures.TimeoutError:
                        logger.warning(
                            f"OCR timeout on page {page_num} (>{page_timeout}s) - skipping"
                        )
                        continue

            except Exception as e:
                logger.warning(f"OCR failed on page {page_num}: {e}")
                continue

        if not text_content:
            logger.warning("OCR extracted no text from any page")
            return None

        # Log average confidence
        if processed_pages > 0:
            avg_confidence = total_confidence / processed_pages
            logger.info(
                f"OCR completed: {sum(len(t) for t in text_content)} chars "
                f"from {total_pages} pages (avg confidence: {avg_confidence:.1f}%)"
            )

        return "\n\n".join(text_content)

    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return None


async def extract_text_with_ocr_async(
    file_content: bytes,
    progress_callback: Callable[[int, int, str], Any] | None = None,
    language: str | None = None,
    dpi: int | None = None,
    page_timeout: int = DEFAULT_PAGE_TIMEOUT,
) -> str | None:
    """Extract text from a PDF using OCR with async progress tracking.

    Args:
        file_content: Raw PDF bytes
        progress_callback: Optional callback(pages_done, total_pages, status)
        language: Tesseract language code
        dpi: Resolution for PDF to image conversion
        page_timeout: Timeout in seconds per page

    Returns:
        Extracted text content, or None if OCR fails
    """
    if not PDF2IMAGE_AVAILABLE or convert_from_bytes is None:
        raise RuntimeError("pdf2image not installed")
    if not PYTESSERACT_AVAILABLE:
        raise RuntimeError("pytesseract not installed")

    # Use defaults from config if not provided
    if language is None:
        language = OCR_LANGUAGE
    if dpi is None:
        dpi = OCR_DPI

    try:
        if progress_callback:
            await asyncio.to_thread(progress_callback, 0, 0, "Converting PDF to images...")

        # Convert PDF pages to images (CPU-bound, run in thread)
        images = await asyncio.to_thread(convert_from_bytes, file_content, dpi)

        if not images:
            return None

        total_pages = len(images)
        if progress_callback:
            await asyncio.to_thread(progress_callback, 0, total_pages, "Starting OCR...")

        text_content: list[str] = []
        loop = asyncio.get_event_loop()

        for page_num, image in enumerate(images, start=1):
            if progress_callback:
                await asyncio.to_thread(
                    progress_callback, page_num - 1, total_pages, f"OCR page {page_num}/{total_pages}"
                )

            try:
                # Run OCR in thread pool with timeout
                _, page_text, _ = await asyncio.wait_for(
                    loop.run_in_executor(
                        None, _ocr_single_page, image, language, page_num, total_pages
                    ),
                    timeout=page_timeout,
                )

                if page_text:
                    text_content.append(page_text)

            except TimeoutError:
                logger.warning(f"OCR timeout on page {page_num}")
                continue
            except Exception as e:
                logger.warning(f"OCR failed on page {page_num}: {e}")
                continue

        if progress_callback:
            await asyncio.to_thread(progress_callback, total_pages, total_pages, "OCR complete")

        if not text_content:
            return None

        return "\n\n".join(text_content)

    except Exception as e:
        logger.error(f"Async OCR extraction failed: {e}")
        return None
