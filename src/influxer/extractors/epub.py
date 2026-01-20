"""EPUB Text Extraction Module for Graphiti Influxer.

Provides EPUB text extraction with chapter structure preservation.

Edge cases handled:
- #13: DRM-protected EPUB (detect + skip + log)
- #14: Kaputtes ZIP (try/catch + skip)
- #16: Eingebettetes Audio/Video (log info)
- #17: Komplexes CSS (text-only extraction via BeautifulSoup)
- #18: JavaScript (security skip)
- #20: EPUB2 vs EPUB3 (ebooklib supports both)
- #21: Fehlendes TOC (content-order fallback)
- #22: Non-UTF8 Encoding (detect + convert via chardet)
- #76: UTF-16/32 encoding (detect + convert)
- #80: Security (text-only extraction, no JS)
"""

from __future__ import annotations

import logging
import warnings
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import chardet
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from ebooklib import epub

# Suppress XMLParsedAsHTMLWarning - we use lxml-html intentionally for XHTML
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

logger = logging.getLogger(__name__)


# Custom exceptions for EPUB handling
class EPUBExtractionError(Exception):
    """Base exception for EPUB extraction errors."""

    pass


class EPUBDRMError(EPUBExtractionError):
    """EPUB is DRM-protected (#13)."""

    pass


class EPUBCorruptError(EPUBExtractionError):
    """EPUB file is corrupted or invalid ZIP (#14)."""

    pass


# DRM indicator files/signatures
DRM_INDICATORS = [
    "META-INF/encryption.xml",  # Adobe DRM
    "META-INF/rights.xml",  # Adobe DRM
    "rights.xml",  # Generic DRM
]


def is_drm_protected(file_path: Path) -> bool:
    """Check if an EPUB is DRM-protected (#13).

    Args:
        file_path: Path to the EPUB file

    Returns:
        True if the EPUB appears to have DRM protection
    """
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            for indicator in DRM_INDICATORS:
                if indicator in zf.namelist():
                    return True

            # Also check for encrypted content in META-INF/encryption.xml
            if "META-INF/encryption.xml" in zf.namelist():
                encryption_data = zf.read("META-INF/encryption.xml")
                # If encryption.xml exists and has content, likely DRM
                if b"<EncryptedData" in encryption_data:
                    return True

    except zipfile.BadZipFile:
        # Can't check, will fail later with EPUBCorruptError
        pass
    except Exception as e:
        logger.warning(f"Could not check EPUB for DRM: {e}")

    return False


def get_epub_version(book: epub.EpubBook) -> str:
    """Get EPUB version (EPUB2 or EPUB3) (#20).

    Args:
        book: ebooklib EpubBook object

    Returns:
        Version string ("2.0", "3.0", or "unknown")
    """
    try:
        # Check the OPF version attribute
        version = book.get_metadata("OPF", "version")
        if version:
            return version[0][0] if version[0] else "unknown"

        # Fallback: check for EPUB3-specific features
        for item in book.get_items():
            if item.media_type == "application/xhtml+xml":
                content = item.get_content()
                if b'epub:type' in content or b'xmlns:epub' in content:
                    return "3.0"

        return "2.0"  # Default to EPUB2
    except Exception:
        return "unknown"


def _decode_content(content: bytes) -> str:
    """Decode byte content to string, handling various encodings (#22, #76).

    Args:
        content: Raw bytes to decode

    Returns:
        Decoded string
    """
    # Try UTF-8 first (most common)
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        pass

    # Use chardet to detect encoding
    detection = chardet.detect(content)
    encoding = detection.get("encoding", "utf-8")
    confidence = detection.get("confidence", 0)

    if encoding and confidence > 0.5:
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            pass

    # Try common encodings
    for enc in ["latin-1", "cp1252", "utf-16", "utf-32"]:
        try:
            return content.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

    # Last resort: decode with replacement
    return content.decode("utf-8", errors="replace")


def _extract_text_from_html(html_content: str, strip_scripts: bool = True) -> str:
    """Extract clean text from HTML content (#17, #18, #80).

    Args:
        html_content: Raw HTML string
        strip_scripts: If True, remove all script tags (security #18, #80)

    Returns:
        Clean text without HTML tags
    """
    soup = BeautifulSoup(html_content, "lxml")

    # Remove script and style elements (#18, #80 security)
    if strip_scripts:
        for script in soup(["script", "style", "noscript"]):
            script.decompose()

    # Get text with proper spacing
    text = soup.get_text(separator="\n", strip=True)

    # Clean up multiple newlines
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def _get_chapter_title(item: epub.EpubItem) -> str | None:
    """Try to extract chapter title from EPUB item.

    Args:
        item: ebooklib EpubItem

    Returns:
        Chapter title if found, None otherwise
    """
    try:
        content = _decode_content(item.get_content())
        soup = BeautifulSoup(content, "lxml")

        # Try common heading tags
        for tag in ["h1", "h2", "h3", "title"]:
            heading = soup.find(tag)
            if heading:
                text = heading.get_text(strip=True)
                if text and len(text) < 200:  # Reasonable title length
                    return text

        return None
    except Exception:
        return None


def extract_text_from_epub(file_path: Path) -> str:
    """Extract text from EPUB with chapter structure preservation.

    Edge cases handled: #13-#14, #16-#22, #76, #80

    Args:
        file_path: Path to the EPUB file

    Returns:
        Extracted text content with chapter markers

    Raises:
        EPUBDRMError: If EPUB is DRM-protected
        EPUBCorruptError: If EPUB is corrupted
        EPUBExtractionError: For other extraction failures
    """
    # Check for DRM (#13)
    if is_drm_protected(file_path):
        raise EPUBDRMError(
            f"EPUB is DRM-protected: {file_path.name}. "
            "Cannot extract text from DRM-protected files."
        )

    # Validate ZIP structure (#14)
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            # Check for required EPUB files
            if "META-INF/container.xml" not in zf.namelist():
                raise EPUBCorruptError(
                    f"Invalid EPUB structure: {file_path.name}. "
                    "Missing META-INF/container.xml"
                )
    except zipfile.BadZipFile as e:
        raise EPUBCorruptError(f"Corrupt EPUB file (invalid ZIP): {file_path.name}") from e

    try:
        book = epub.read_epub(str(file_path), options={"ignore_ncx": False})
    except Exception as e:
        raise EPUBCorruptError(f"Cannot read EPUB: {e}") from e

    # Log EPUB version (#20)
    version = get_epub_version(book)
    logger.info(f"Processing EPUB {version}: {file_path.name}")

    # Track media items for logging (#16)
    media_items: list[str] = []

    # Collect document items
    text_content: list[str] = []
    chapter_num = 0

    # Try to use spine order (TOC order) first (#21)
    spine_items: list[epub.EpubItem] = []

    try:
        # Get items in reading order from spine
        for item_id, _ in book.spine:
            item = book.get_item_with_id(item_id)
            if item:
                spine_items.append(item)
    except Exception:
        # Fallback to content order if spine fails (#21)
        logger.warning("Could not read EPUB spine, using content order")

    # If spine is empty, use all document items
    if not spine_items:
        spine_items = list(book.get_items_of_type(epub.ITEM_DOCUMENT))

    for item in spine_items:
        try:
            # Skip navigation documents
            if isinstance(item, epub.EpubNav):
                continue

            media_type = item.media_type

            # Log audio/video items (#16)
            if media_type and media_type.startswith(("audio/", "video/")):
                media_items.append(f"{item.get_name()} ({media_type})")
                continue

            # Only process HTML/XHTML documents
            if media_type not in ("application/xhtml+xml", "text/html"):
                continue

            content = item.get_content()
            if not content:
                continue

            # Decode content (#22, #76)
            html_content = _decode_content(content)

            # Extract clean text (#17, #18, #80)
            text = _extract_text_from_html(html_content)

            if text and len(text.strip()) > 10:
                chapter_num += 1

                # Try to get chapter title
                title = _get_chapter_title(item) or f"Chapter {chapter_num}"

                text_content.append(f"## {title}\n\n{text}")

        except Exception as e:
            logger.warning(f"Failed to extract content from {item.get_name()}: {e}")
            continue

    # Log media items (#16)
    if media_items:
        logger.info(f"Ignored {len(media_items)} media items: {', '.join(media_items[:5])}")
        if len(media_items) > 5:
            logger.info(f"... and {len(media_items) - 5} more")

    if not text_content:
        raise EPUBExtractionError(f"No text content found in EPUB: {file_path.name}")

    # Add book metadata header
    title = book.get_metadata("DC", "title")
    author = book.get_metadata("DC", "creator")

    header_parts: list[str] = []
    if title:
        header_parts.append(f"# {title[0][0]}")
    if author:
        header_parts.append(f"*By {author[0][0]}*")

    header = "\n".join(header_parts) + "\n\n---\n\n" if header_parts else ""

    combined_text = header + "\n\n".join(text_content)
    logger.info(f"EPUB extracted: {len(combined_text)} chars from {chapter_num} chapters")

    return combined_text


async def extract_text_from_epub_async(
    file_path: Path,
    progress_callback: Callable[[int, int, str], Any] | None = None,
) -> str:
    """Extract text from EPUB with async progress tracking.

    Args:
        file_path: Path to the EPUB file
        progress_callback: Optional callback(items_done, total_items, status)

    Returns:
        Extracted text content

    Raises:
        Same exceptions as extract_text_from_epub
    """
    import asyncio

    if progress_callback:
        await asyncio.to_thread(progress_callback, 0, 0, "Checking EPUB...")

    # Validation
    if is_drm_protected(file_path):
        raise EPUBDRMError(f"EPUB is DRM-protected: {file_path.name}")

    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            if "META-INF/container.xml" not in zf.namelist():
                raise EPUBCorruptError(f"Invalid EPUB: {file_path.name}")
    except zipfile.BadZipFile as e:
        raise EPUBCorruptError(f"Corrupt EPUB: {file_path.name}") from e

    if progress_callback:
        await asyncio.to_thread(progress_callback, 0, 0, "Loading EPUB...")

    book = await asyncio.to_thread(epub.read_epub, str(file_path), {"ignore_ncx": False})

    # Get items in spine order
    spine_items: list[epub.EpubItem] = []
    try:
        for item_id, _ in book.spine:
            item = book.get_item_with_id(item_id)
            if item:
                spine_items.append(item)
    except Exception:
        spine_items = list(book.get_items_of_type(epub.ITEM_DOCUMENT))

    if not spine_items:
        spine_items = list(book.get_items_of_type(epub.ITEM_DOCUMENT))

    total_items = len(spine_items)
    if progress_callback:
        await asyncio.to_thread(
            progress_callback, 0, total_items, f"Extracting {total_items} chapters..."
        )

    text_content: list[str] = []
    chapter_num = 0

    for idx, item in enumerate(spine_items, start=1):
        try:
            if isinstance(item, epub.EpubNav):
                continue

            media_type = item.media_type
            if media_type not in ("application/xhtml+xml", "text/html"):
                continue

            content = item.get_content()
            if not content:
                continue

            html_content = _decode_content(content)
            text = _extract_text_from_html(html_content)

            if text and len(text.strip()) > 10:
                chapter_num += 1
                title = _get_chapter_title(item) or f"Chapter {chapter_num}"
                text_content.append(f"## {title}\n\n{text}")

            if progress_callback:
                await asyncio.to_thread(
                    progress_callback, idx, total_items, f"Chapter {idx}/{total_items}"
                )

        except Exception as e:
            logger.warning(f"Failed to extract: {e}")
            continue

    if not text_content:
        raise EPUBExtractionError(f"No text in EPUB: {file_path.name}")

    # Add header
    title = book.get_metadata("DC", "title")
    author = book.get_metadata("DC", "creator")

    header_parts: list[str] = []
    if title:
        header_parts.append(f"# {title[0][0]}")
    if author:
        header_parts.append(f"*By {author[0][0]}*")

    header = "\n".join(header_parts) + "\n\n---\n\n" if header_parts else ""

    if progress_callback:
        await asyncio.to_thread(progress_callback, total_items, total_items, "Complete")

    return header + "\n\n".join(text_content)
