"""Semantic Text Chunking Module for Graphiti Influxer.

Provides text chunking using LangChain's RecursiveCharacterTextSplitter.

Edge cases handled:
- #23: Fließtext ohne Absätze (sentence splitter fallback)
- #24: Sehr kurzes Dokument (minimum size warning)
- #29: Chunk > MCP-Limit (pre-verify size, split if needed)
- #30: Overlap-Duplikate (documented: Graphiti deduplicates)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from langchain_text_splitters import RecursiveCharacterTextSplitter

from influxer.config import CHUNK_OVERLAP, CHUNK_SIZE

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# MCP size limit (conservative estimate)
MCP_MAX_CONTENT_SIZE = 100_000  # characters

# Minimum text threshold for warning (#24)
MIN_TEXT_LENGTH = 100


@dataclass
class ChunkMetadata:
    """Metadata for a text chunk."""

    chunk_index: int
    total_chunks: int
    char_count: int
    start_offset: int
    end_offset: int


def validate_chunk_size(chunk: str, max_size: int = MCP_MAX_CONTENT_SIZE) -> bool:
    """Validate that a chunk doesn't exceed the MCP size limit (#29).

    Args:
        chunk: Text chunk to validate
        max_size: Maximum allowed size in characters

    Returns:
        True if chunk is within size limit
    """
    return len(chunk) <= max_size


def get_chunk_metadata(
    chunk: str,
    index: int,
    total: int,
    start_offset: int = 0,
) -> ChunkMetadata:
    """Get metadata for a text chunk.

    Args:
        chunk: The text chunk
        index: Zero-based index of this chunk
        total: Total number of chunks
        start_offset: Character offset in original document

    Returns:
        ChunkMetadata instance
    """
    return ChunkMetadata(
        chunk_index=index,
        total_chunks=total,
        char_count=len(chunk),
        start_offset=start_offset,
        end_offset=start_offset + len(chunk),
    )


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    max_chunk_size: int = MCP_MAX_CONTENT_SIZE,
) -> list[str]:
    """Split text into semantic chunks.

    Uses RecursiveCharacterTextSplitter with separators that preserve
    document structure (paragraphs > sentences > words).

    Edge cases handled:
    - #23: Fließtext - sentence separator fallback
    - #24: Short text - warning logged
    - #29: Large chunks - split further if exceeds max
    - #30: Overlap - Graphiti handles deduplication

    Args:
        text: Text to split into chunks
        chunk_size: Target chunk size in characters (default from config)
        chunk_overlap: Overlap between chunks (default from config)
        max_chunk_size: Maximum allowed chunk size (MCP limit)

    Returns:
        List of text chunks
    """
    if chunk_size is None:
        chunk_size = CHUNK_SIZE
    if chunk_overlap is None:
        chunk_overlap = CHUNK_OVERLAP

    # Handle empty or very short text (#24)
    if not text or not text.strip():
        logger.warning("Empty text provided for chunking")
        return []

    text = text.strip()

    if len(text) < MIN_TEXT_LENGTH:
        logger.warning(
            f"Very short text ({len(text)} chars < {MIN_TEXT_LENGTH}). "
            "May not provide meaningful context in Graphiti."
        )

    # Create splitter with paragraph > sentence > word separators (#23)
    # This handles fließtext (continuous text without paragraphs)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n\n",  # Paragraph breaks (primary)
            "\n",  # Line breaks
            ". ",  # Sentence endings
            "! ",  # Exclamation
            "? ",  # Questions
            "; ",  # Semicolons
            ", ",  # Commas
            " ",  # Words
            "",  # Characters (last resort)
        ],
        length_function=len,
        is_separator_regex=False,
    )

    # Split the text
    chunks = splitter.split_text(text)

    if not chunks:
        logger.warning("Text splitting produced no chunks")
        return []

    # Validate and potentially re-split oversized chunks (#29)
    validated_chunks: list[str] = []

    for i, chunk in enumerate(chunks):
        if validate_chunk_size(chunk, max_chunk_size):
            validated_chunks.append(chunk)
        else:
            # Chunk exceeds MCP limit - split it further
            logger.warning(
                f"Chunk {i + 1} exceeds max size ({len(chunk)} > {max_chunk_size}). "
                "Splitting further..."
            )

            # Use a smaller chunk size for oversized chunks
            sub_splitter = RecursiveCharacterTextSplitter(
                chunk_size=max_chunk_size // 2,
                chunk_overlap=chunk_overlap,
                separators=["\n", ". ", " ", ""],
                length_function=len,
            )
            sub_chunks = sub_splitter.split_text(chunk)
            validated_chunks.extend(sub_chunks)

    logger.info(
        f"Chunked {len(text)} chars into {len(validated_chunks)} chunks "
        f"(size={chunk_size}, overlap={chunk_overlap})"
    )

    return validated_chunks


def chunk_text_with_metadata(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[tuple[str, ChunkMetadata]]:
    """Split text into chunks with metadata.

    Args:
        text: Text to split
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks

    Returns:
        List of (chunk_text, metadata) tuples
    """
    chunks = chunk_text(text, chunk_size, chunk_overlap)

    if not chunks:
        return []

    result: list[tuple[str, ChunkMetadata]] = []
    offset = 0

    for i, chunk in enumerate(chunks):
        # Find actual position in original text
        # Note: This is approximate due to overlap
        pos = text.find(chunk[:50], offset) if len(chunk) >= 50 else text.find(chunk, offset)
        if pos == -1:
            pos = offset

        metadata = get_chunk_metadata(
            chunk=chunk,
            index=i,
            total=len(chunks),
            start_offset=pos,
        )

        result.append((chunk, metadata))
        offset = pos + len(chunk) - (chunk_overlap or CHUNK_OVERLAP)

    return result


def estimate_chunk_count(
    text_length: int,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> int:
    """Estimate the number of chunks for a given text length.

    Useful for progress estimation before actual chunking.

    Args:
        text_length: Length of text in characters
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks

    Returns:
        Estimated number of chunks
    """
    if chunk_size is None:
        chunk_size = CHUNK_SIZE
    if chunk_overlap is None:
        chunk_overlap = CHUNK_OVERLAP

    if text_length <= 0:
        return 0

    if text_length <= chunk_size:
        return 1

    # Effective chunk size (accounting for overlap)
    effective_size = chunk_size - chunk_overlap

    if effective_size <= 0:
        return 1

    return max(1, (text_length - chunk_overlap) // effective_size + 1)
