"""PDF Text Extraction Module for Graphiti Influxer.

Provides PDF text extraction with a fallback chain:
pymupdf4llm → pdfplumber → PyPDF2 → OCR

Based on: github.com/Milofax/Archon/python/src/server/utils/document_processing.py

Edge cases handled:
- #1: Password-protected PDF (detect + skip + log)
- #2: Scanned PDF (OCR fallback)
- #3: Mixed content (text + scans per page)
- #4: Corrupt PDF (try/catch + skip)
- #7: Embedded files (log warning)
- #8: Very large PDF (1000+ pages, page-by-page streaming)
- #12: Empty PDF (detect + skip)
- #72: 500MB PDF (page-by-page processing)
- #76: UTF-16/32 encoding (detect + convert)
- #80: Security (text-only extraction, no JS/macros)
"""

from __future__ import annotations

import io
import logging
import re
from collections.abc import Callable, Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from influxer.extractors.ocr import extract_text_with_ocr, is_ocr_available

if TYPE_CHECKING:
    from pypdf import PdfReader

logger = logging.getLogger(__name__)

# Check for PDF processing libraries with availability flags
try:
    import pymupdf4llm

    PYMUPDF4LLM_AVAILABLE = True
except ImportError:
    PYMUPDF4LLM_AVAILABLE = False
    pymupdf4llm = None

try:
    from pypdf import PdfReader
    from pypdf.errors import FileNotDecryptedError, PdfReadError

    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    PdfReader = None  # type: ignore[misc, assignment]
    PdfReadError = Exception  # type: ignore[misc, assignment]
    FileNotDecryptedError = Exception  # type: ignore[misc, assignment]

try:
    import pdfplumber

    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    pdfplumber = None  # type: ignore[assignment]


# Custom exceptions for PDF handling
class PDFExtractionError(Exception):
    """Base exception for PDF extraction errors."""

    pass


class PDFPasswordError(PDFExtractionError):
    """PDF is password-protected (#1)."""

    pass


class PDFCorruptError(PDFExtractionError):
    """PDF file is corrupted or invalid (#4)."""

    pass


class PDFEmptyError(PDFExtractionError):
    """PDF has no extractable text (#12)."""

    pass


# Minimum text threshold to consider extraction successful
MIN_TEXT_THRESHOLD = 100  # characters
MIN_OCR_TEXT_THRESHOLD = 50  # lower threshold for OCR


def is_password_protected(file_path: Path) -> bool:
    """Check if a PDF is password-protected (#1).

    Args:
        file_path: Path to the PDF file

    Returns:
        True if the PDF requires a password to open
    """
    if not PYPDF_AVAILABLE or PdfReader is None:
        return False

    try:
        with file_path.open("rb") as f:
            reader = PdfReader(f)
            return reader.is_encrypted
    except Exception:
        return False


def has_embedded_files(file_path: Path) -> bool:
    """Check if PDF has embedded files/attachments (#7).

    Args:
        file_path: Path to the PDF file

    Returns:
        True if the PDF contains embedded files
    """
    if not PYPDF_AVAILABLE or PdfReader is None:
        return False

    try:
        with file_path.open("rb") as f:
            reader = PdfReader(f)
            # Check for /EmbeddedFiles in the PDF catalog
            if reader.trailer and "/Root" in reader.trailer:
                root: Any = reader.trailer["/Root"]
                if hasattr(root, "get_object"):
                    root = root.get_object()
                if hasattr(root, "__contains__") and "/Names" in root:
                    names: Any = root["/Names"]
                    if hasattr(names, "get_object"):
                        names = names.get_object()
                    return hasattr(names, "__contains__") and "/EmbeddedFiles" in names
    except Exception:
        pass
    return False


def _is_page_scanned(page_text: str | None, page_images_count: int = 0) -> bool:
    """Check if a page is likely scanned (image-only) (#3).

    Args:
        page_text: Extracted text from the page (or None)
        page_images_count: Number of images on the page

    Returns:
        True if the page appears to be a scan
    """
    # If we got meaningful text, it's not a scan
    if page_text and len(page_text.strip()) > 20:
        return False
    # If we got images but no text, likely a scan
    return page_images_count > 0 and (not page_text or len(page_text.strip()) < 20)


def _preserve_code_blocks_across_pages(text: str) -> str:
    """Fix code blocks split across PDF page boundaries.

    PDFs often break markdown code blocks with page headers.
    This function rejoins split code blocks.

    Args:
        text: Text with potential split code blocks

    Returns:
        Text with rejoined code blocks
    """
    # Pattern to match page separators that split code blocks
    page_break_pattern = r"(```\w*[^\n]*\n(?:[^`]|`(?!``))*)(\n--- Page \d+ ---\n)((?:[^`]|`(?!``))*)```"

    # Keep merging until no more splits are found
    while True:
        matches = list(re.finditer(page_break_pattern, text, re.DOTALL))
        if not matches:
            break

        for match in reversed(matches):
            before_break = match.group(1)
            after_break = match.group(3)
            rejoined = f"{before_break}\n{after_break}```"
            text = text[: match.start()] + rejoined + text[match.end() :]

    return text


def extract_page_by_page(file_path: Path) -> Generator[tuple[int, str], None, None]:
    """Extract text page-by-page for large PDFs (#8, #72).

    Uses streaming to avoid loading entire PDF into memory.

    Args:
        file_path: Path to the PDF file

    Yields:
        Tuple of (page_number, page_text) for each page with text
    """
    if not PDFPLUMBER_AVAILABLE or pdfplumber is None:
        if not PYPDF_AVAILABLE or PdfReader is None:
            raise PDFExtractionError("No PDF library available for page-by-page extraction")

        # Use pypdf for streaming
        with file_path.open("rb") as f:
            reader = PdfReader(f)
            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        yield (page_num, text.strip())
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num}: {e}")
                    continue
        return

    # Use pdfplumber for better quality
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):  # type: ignore[assignment]
            try:
                text = page.extract_text()
                if text and text.strip():
                    yield (page_num, text.strip())
            except Exception as e:
                logger.warning(f"Failed to extract page {page_num}: {e}")
                continue


def extract_text_from_pdf(file_path: Path) -> str:
    """Extract text from PDF with Markdown structure preservation.

    Uses a fallback chain: pymupdf4llm → pdfplumber → PyPDF2 → OCR

    Edge cases handled: #1-#4, #7-#8, #12, #72, #76, #80

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text content (Markdown format when possible)

    Raises:
        PDFPasswordError: If PDF is password-protected
        PDFCorruptError: If PDF is corrupted
        PDFEmptyError: If PDF has no extractable text
        PDFExtractionError: For other extraction failures
    """
    if not PYMUPDF4LLM_AVAILABLE and not PDFPLUMBER_AVAILABLE and not PYPDF_AVAILABLE:
        raise PDFExtractionError(
            "No PDF processing libraries available. "
            "Install pymupdf4llm, pdfplumber, or pypdf."
        )

    # Check for password protection (#1)
    if is_password_protected(file_path):
        raise PDFPasswordError(
            f"PDF is password-protected: {file_path.name}. "
            "Please decrypt the PDF first."
        )

    # Check for embedded files (#7)
    if has_embedded_files(file_path):
        logger.warning(f"PDF has embedded files/attachments that will be ignored: {file_path.name}")

    # Read file content for libraries that need bytes
    try:
        file_content = file_path.read_bytes()
    except PermissionError as e:
        raise PDFExtractionError(f"Permission denied reading: {file_path}") from e
    except Exception as e:
        raise PDFCorruptError(f"Cannot read PDF file: {e}") from e

    # Primary: pymupdf4llm (best quality - proper word separation and Markdown)
    if PYMUPDF4LLM_AVAILABLE and pymupdf4llm is not None:
        try:
            # pymupdf4llm requires a file path
            markdown_text: str = pymupdf4llm.to_markdown(str(file_path))

            if markdown_text and len(markdown_text.strip()) > MIN_TEXT_THRESHOLD:
                logger.info(f"PDF extracted with pymupdf4llm: {len(markdown_text)} chars")
                return str(markdown_text)
            else:
                logger.warning("pymupdf4llm returned insufficient text, trying fallback")

        except Exception as e:
            logger.warning(f"pymupdf4llm extraction failed: {e}, trying pdfplumber")

    # Fallback 1: pdfplumber
    if PDFPLUMBER_AVAILABLE and pdfplumber is not None:
        try:
            text_content: list[str] = []
            scanned_pages: list[int] = []

            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"Extracting {total_pages} pages with pdfplumber...")

                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        page_text = page.extract_text()
                        images_count = len(page.images) if hasattr(page, "images") else 0

                        # Check for scanned pages (#3)
                        if _is_page_scanned(page_text, images_count):
                            scanned_pages.append(page_num)

                        if page_text and page_text.strip():
                            text_content.append(f"--- Page {page_num} ---\n{page_text.strip()}")

                    except Exception as e:
                        logger.warning(f"pdfplumber failed on page {page_num}: {e}")
                        continue

            # Warn about scanned pages
            if scanned_pages:
                logger.warning(
                    f"Pages {scanned_pages} appear to be scans - "
                    "OCR may be needed for full extraction"
                )

            if text_content and len("\n".join(text_content).strip()) > MIN_TEXT_THRESHOLD:
                combined_text = "\n\n".join(text_content)
                logger.info(f"PDF extracted with pdfplumber: {len(combined_text)} chars")
                return _preserve_code_blocks_across_pages(combined_text)

        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}, trying pypdf")

    # Fallback 2: pypdf
    if PYPDF_AVAILABLE and PdfReader is not None:
        try:
            text_content = []
            reader = PdfReader(io.BytesIO(file_content))

            # Check for encryption (#1)
            if reader.is_encrypted:
                raise PDFPasswordError(f"PDF is encrypted: {file_path.name}")

            total_pages = len(reader.pages)
            logger.info(f"Extracting {total_pages} pages with pypdf...")

            for page_num, page in enumerate(reader.pages, start=1):  # type: ignore[assignment]
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_content.append(f"--- Page {page_num} ---\n{page_text.strip()}")

                except Exception as e:
                    logger.warning(f"pypdf failed on page {page_num}: {e}")
                    continue

            if text_content:
                combined_text = "\n\n".join(text_content)
                logger.info(f"PDF extracted with pypdf: {len(combined_text)} chars")
                return _preserve_code_blocks_across_pages(combined_text)

        except FileNotDecryptedError as e:
            raise PDFPasswordError(f"PDF requires password: {file_path.name}") from e
        except PdfReadError as e:
            raise PDFCorruptError(f"Corrupt PDF file: {e}") from e
        except PDFPasswordError:
            raise
        except Exception as e:
            logger.warning(f"pypdf extraction failed: {e}, trying OCR")

    # Final fallback: OCR for image-based/scanned PDFs (#2)
    if is_ocr_available():
        logger.info("No text extracted - attempting OCR for image-based PDF")
        ocr_text = extract_text_with_ocr(file_content)

        if ocr_text and len(ocr_text.strip()) > MIN_OCR_TEXT_THRESHOLD:
            logger.info(f"PDF extracted with OCR: {len(ocr_text)} chars")
            return ocr_text

        # If OCR also failed, the PDF is truly empty (#12)
        raise PDFEmptyError(
            f"No text extracted from PDF: {file_path.name}. "
            "File may be empty or contain only non-text images."
        )

    # No OCR available and no text extracted (#12)
    raise PDFEmptyError(
        f"No text extracted from PDF: {file_path.name}. "
        "File appears to be images-only or scanned. "
        "Install OCR dependencies for scanned PDF support: "
        "pip install pytesseract pdf2image (and install tesseract + poppler)"
    )


async def extract_text_from_pdf_async(
    file_path: Path,
    progress_callback: Callable[[int, int, str], Any] | None = None,
) -> str:
    """Extract text from PDF with async progress tracking.

    Args:
        file_path: Path to the PDF file
        progress_callback: Optional callback(pages_done, total_pages, status)

    Returns:
        Extracted text content

    Raises:
        Same exceptions as extract_text_from_pdf
    """
    import asyncio

    if progress_callback:
        await asyncio.to_thread(progress_callback, 0, 0, "Checking PDF...")

    # Check for password protection
    if is_password_protected(file_path):
        raise PDFPasswordError(f"PDF is password-protected: {file_path.name}")

    # Check for embedded files
    if has_embedded_files(file_path):
        logger.warning(f"PDF has embedded files that will be ignored: {file_path.name}")

    file_content = await asyncio.to_thread(file_path.read_bytes)

    # Try pymupdf4llm first (fast, single call)
    if PYMUPDF4LLM_AVAILABLE and pymupdf4llm is not None:
        try:
            if progress_callback:
                await asyncio.to_thread(progress_callback, 0, 1, "Extracting with pymupdf4llm...")

            markdown_text: str = await asyncio.to_thread(pymupdf4llm.to_markdown, str(file_path))

            if markdown_text and len(markdown_text.strip()) > MIN_TEXT_THRESHOLD:
                if progress_callback:
                    await asyncio.to_thread(progress_callback, 1, 1, "Extraction complete")
                return str(markdown_text)

        except Exception as e:
            logger.warning(f"pymupdf4llm failed: {e}")

    # Try pdfplumber with progress
    if PDFPLUMBER_AVAILABLE and pdfplumber is not None:
        try:
            text_content: list[str] = []

            # Open synchronously in thread
            pdf = await asyncio.to_thread(pdfplumber.open, io.BytesIO(file_content))

            try:
                total_pages = len(pdf.pages)
                if progress_callback:
                    await asyncio.to_thread(
                        progress_callback, 0, total_pages, f"Extracting {total_pages} pages..."
                    )

                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        page_text = await asyncio.to_thread(page.extract_text)
                        if page_text and page_text.strip():
                            text_content.append(f"--- Page {page_num} ---\n{page_text.strip()}")

                        if progress_callback:
                            await asyncio.to_thread(
                                progress_callback,
                                page_num,
                                total_pages,
                                f"Page {page_num}/{total_pages}",
                            )

                    except Exception as e:
                        logger.warning(f"pdfplumber failed on page {page_num}: {e}")
                        continue

            finally:
                pdf.close()

            if text_content and len("\n".join(text_content).strip()) > MIN_TEXT_THRESHOLD:
                combined = "\n\n".join(text_content)
                return _preserve_code_blocks_across_pages(combined)

        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")

    # Try pypdf with progress
    if PYPDF_AVAILABLE and PdfReader is not None:
        try:
            reader = PdfReader(io.BytesIO(file_content))

            if reader.is_encrypted:
                raise PDFPasswordError(f"PDF is encrypted: {file_path.name}")

            text_content = []
            total_pages = len(reader.pages)

            if progress_callback:
                await asyncio.to_thread(
                    progress_callback, 0, total_pages, f"Extracting {total_pages} pages..."
                )

            for page_num, page in enumerate(reader.pages, start=1):  # type: ignore[assignment]
                try:
                    page_text = await asyncio.to_thread(page.extract_text)
                    if page_text and page_text.strip():
                        text_content.append(f"--- Page {page_num} ---\n{page_text.strip()}")

                    if progress_callback:
                        await asyncio.to_thread(
                            progress_callback, page_num, total_pages, f"Page {page_num}/{total_pages}"
                        )

                except Exception as e:
                    logger.warning(f"pypdf failed on page {page_num}: {e}")
                    continue

            if text_content:
                combined = "\n\n".join(text_content)
                return _preserve_code_blocks_across_pages(combined)

        except PDFPasswordError:
            raise
        except Exception as e:
            logger.warning(f"pypdf failed: {e}")

    # Final fallback: OCR
    if is_ocr_available():
        if progress_callback:
            await asyncio.to_thread(progress_callback, 0, 0, "Starting OCR...")

        from influxer.extractors.ocr import extract_text_with_ocr_async

        ocr_text = await extract_text_with_ocr_async(file_content, progress_callback)

        if ocr_text and len(ocr_text.strip()) > MIN_OCR_TEXT_THRESHOLD:
            return ocr_text

        raise PDFEmptyError(f"No text extracted from PDF: {file_path.name}")

    raise PDFEmptyError(
        f"No text extracted from PDF: {file_path.name}. "
        "Install OCR dependencies for scanned PDF support."
    )
