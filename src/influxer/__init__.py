"""Graphiti Influxer - Ingest documents into Graphiti via MCP.

A CLI tool that extracts text from PDF and EPUB files, chunks it semantically,
and sends it to Graphiti via the MCP protocol.
"""

__version__ = "0.1.0"

from influxer.chunker import chunk_text
from influxer.config import get_config, load_config
from influxer.extractors import extract_text, is_supported
from influxer.mcp_client import GraphitiClient
from influxer.state import StateDB, get_file_hash

__all__ = [
    "__version__",
    "chunk_text",
    "extract_text",
    "get_config",
    "get_file_hash",
    "GraphitiClient",
    "is_supported",
    "load_config",
    "StateDB",
]
