"""Extractors package for Graphiti Influxer.

Provides unified text extraction from PDF and EPUB documents.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from influxer.extractors.epub import (
    EPUBCorruptError,
    EPUBDRMError,
    EPUBExtractionError,
    extract_text_from_epub,
    extract_text_from_epub_async,
)
from influxer.extractors.ocr import (
    extract_text_with_ocr,
    extract_text_with_ocr_async,
    is_ocr_available,
)
from influxer.extractors.pdf import (
    PDFCorruptError,
    PDFEmptyError,
    PDFExtractionError,
    PDFPasswordError,
    extract_text_from_pdf,
    extract_text_from_pdf_async,
)

__all__ = [
    # PDF
    "extract_text_from_pdf",
    "extract_text_from_pdf_async",
    "PDFExtractionError",
    "PDFPasswordError",
    "PDFCorruptError",
    "PDFEmptyError",
    # EPUB
    "extract_text_from_epub",
    "extract_text_from_epub_async",
    "EPUBExtractionError",
    "EPUBDRMError",
    "EPUBCorruptError",
    # OCR
    "extract_text_with_ocr",
    "extract_text_with_ocr_async",
    "is_ocr_available",
    # Unified
    "extract_text",
    "extract_text_async",
    "ExtractionError",
]


class ExtractionError(Exception):
    """Base exception for all extraction errors."""

    pass


# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".epub"}


def extract_text(file_path: Path) -> str:
    """Extract text from a file based on its extension.

    Automatically detects file type and uses the appropriate extractor.

    Args:
        file_path: Path to the file to extract text from

    Returns:
        Extracted text content

    Raises:
        ValueError: If file extension is not supported
        ExtractionError: If extraction fails
        PDFExtractionError: For PDF-specific errors
        EPUBExtractionError: For EPUB-specific errors
    """
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")

    extension = file_path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: {extension}. "
            f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    try:
        if extension == ".pdf":
            return extract_text_from_pdf(file_path)
        elif extension == ".epub":
            return extract_text_from_epub(file_path)
        else:
            raise ValueError(f"Unsupported file format: {extension}")
    except (PDFExtractionError, EPUBExtractionError):
        # Re-raise specific exceptions
        raise
    except Exception as e:
        raise ExtractionError(f"Failed to extract text from {file_path.name}: {e}") from e


async def extract_text_async(
    file_path: Path,
    progress_callback: Callable[[int, int, str], Any] | None = None,
) -> str:
    """Extract text from a file with async progress tracking.

    Args:
        file_path: Path to the file to extract text from
        progress_callback: Optional callback(items_done, total_items, status)

    Returns:
        Extracted text content

    Raises:
        Same exceptions as extract_text
    """
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")

    extension = file_path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format: {extension}. "
            f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    try:
        if extension == ".pdf":
            return await extract_text_from_pdf_async(file_path, progress_callback)
        elif extension == ".epub":
            return await extract_text_from_epub_async(file_path, progress_callback)
        else:
            raise ValueError(f"Unsupported file format: {extension}")
    except (PDFExtractionError, EPUBExtractionError):
        raise
    except Exception as e:
        raise ExtractionError(f"Failed to extract text from {file_path.name}: {e}") from e


def get_supported_extensions() -> set[str]:
    """Get set of supported file extensions.

    Returns:
        Set of supported extensions (e.g., {".pdf", ".epub"})
    """
    return SUPPORTED_EXTENSIONS.copy()


def is_supported(file_path: Path) -> bool:
    """Check if a file is supported for extraction.

    Args:
        file_path: Path to the file

    Returns:
        True if the file format is supported
    """
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS
