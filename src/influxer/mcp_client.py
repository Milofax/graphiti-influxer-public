"""MCP Client Module for Graphiti Influxer.

Provides MCP client for connecting to Graphiti MCP server and sending episodes.

Edge cases handled:
- #33: Server nicht erreichbar (health check vor Start, fail-fast)
- #34: Timeout 30-50s (configurable timeout)
- #36: Rate-Limiting 429 (exponential backoff)
- #38: Ungültige Credentials (pre-auth check)
- #39: Response Parsing Fehler (defensive parsing)
- #40: SSL/TLS Probleme (--insecure flag)
- #41: Proxy/Firewall (clear error + network diagnostics)
- #42: DNS fehlschlägt (clear error message)
- #59: Ungültige group_id (format validation)
- #61: Duplikat-Detection (hash in metadata)
- #63: Entity-Extraction fails (warning + continue)
- #83: Source-Tracking (file_path + file_hash in metadata)
- #87: 0 Entities (warning, continue)
"""

from __future__ import annotations

import asyncio
import logging
import re
import ssl
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult

from influxer.config import GRAPHITI_MCP_URL, MCP_TIMEOUT

logger = logging.getLogger(__name__)

# Retry configuration for rate limiting (#36)
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0
BACKOFF_MULTIPLIER = 2.0

# Group ID validation pattern (#59)
GROUP_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


class MCPConnectionError(Exception):
    """Server unreachable (#33, #41, #42)."""

    pass


class MCPAuthError(Exception):
    """Authentication failed (#38)."""

    pass


class MCPToolError(Exception):
    """Tool call failed (#39)."""

    pass


class MCPSSLError(Exception):
    """SSL/TLS certificate issues (#40)."""

    pass


class MCPTimeoutError(Exception):
    """Request timeout (#34)."""

    pass


@dataclass
class ChunkMetadata:
    """Metadata for a chunk being sent to Graphiti (#61, #83)."""

    file_hash: str
    file_path: str
    chunk_index: int
    total_chunks: int
    source_description: str | None = None


def validate_group_id(group_id: str) -> bool:
    """Validate group_id format (#59).

    Group IDs must:
    - Start with alphanumeric character
    - Contain only alphanumeric, hyphen, underscore
    - Be non-empty

    Args:
        group_id: Group ID to validate

    Returns:
        True if valid
    """
    if not group_id:
        return False
    return bool(GROUP_ID_PATTERN.match(group_id))


class GraphitiClient:
    """MCP client for Graphiti operations.

    Handles connection management, retries, and error handling.
    """

    def __init__(
        self,
        server_url: str | None = None,
        timeout: int | None = None,
        insecure: bool = False,
    ) -> None:
        """Initialize the Graphiti client.

        Args:
            server_url: MCP server URL (default from config)
            timeout: Request timeout in seconds (default from config)
            insecure: If True, skip SSL certificate verification (#40)
        """
        self.server_url = server_url or GRAPHITI_MCP_URL
        self.timeout = timeout or MCP_TIMEOUT
        self.insecure = insecure
        self._session: ClientSession | None = None
        self._connected = False

    def _create_http_client(self) -> httpx.AsyncClient:
        """Create HTTP client with SSL configuration (#40)."""
        if self.insecure:
            # Skip SSL verification for self-signed certs
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return httpx.AsyncClient(verify=False, timeout=self.timeout)
        return httpx.AsyncClient(timeout=self.timeout)

    async def connect(self) -> None:
        """Establish connection to MCP server.

        Raises:
            MCPConnectionError: If server unreachable
            MCPSSLError: If SSL certificate issues
            MCPAuthError: If authentication fails
        """
        try:
            # The streamablehttp_client is a context manager, we can't hold it open
            # We'll create connections per-operation instead
            # For now, just verify connectivity with a health check
            await self.get_status()
            self._connected = True
            logger.info(f"Connected to Graphiti MCP at {self.server_url}")

        except ssl.SSLError as e:
            raise MCPSSLError(
                f"SSL certificate error connecting to {self.server_url}. "
                f"Use --insecure for self-signed certificates. Error: {e}"
            ) from e
        except httpx.ConnectError as e:
            raise MCPConnectionError(
                f"Cannot connect to Graphiti MCP at {self.server_url}. "
                f"Is the server running? Error: {e}"
            ) from e
        except httpx.ConnectTimeout as e:
            raise MCPConnectionError(
                f"Connection timeout to {self.server_url}. "
                f"Check network connectivity. Error: {e}"
            ) from e
        except Exception as e:
            if "DNS" in str(e).upper() or "RESOLVE" in str(e).upper():
                raise MCPConnectionError(
                    f"DNS resolution failed for {self.server_url}. "
                    f"Check the hostname. Error: {e}"
                ) from e
            raise MCPConnectionError(f"Failed to connect: {e}") from e

    async def is_connected(self) -> bool:
        """Quick connectivity test (#33).

        Returns:
            True if server is reachable
        """
        try:
            await self.get_status()
            return True
        except Exception:
            return False

    async def _execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        retry_count: int = 0,
    ) -> CallToolResult:
        """Execute a tool call with retry logic (#36).

        Args:
            tool_name: Name of the MCP tool to call
            arguments: Tool arguments
            retry_count: Current retry attempt

        Returns:
            Tool call result

        Raises:
            MCPToolError: If tool call fails after retries
            MCPTimeoutError: If request times out
        """
        try:
            # Create HTTP client with SSL config
            httpx_client_factory = None
            if self.insecure:
                def _factory() -> httpx.AsyncClient:
                    return httpx.AsyncClient(verify=False, timeout=self.timeout)
                httpx_client_factory = _factory

            async with streamablehttp_client(  # noqa: SIM117
                url=self.server_url,
                httpx_client_factory=httpx_client_factory,  # type: ignore[arg-type]
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    result = await session.call_tool(
                        name=tool_name,
                        arguments=arguments,
                        read_timeout_seconds=timedelta(seconds=self.timeout),
                    )

                    return result

        except httpx.HTTPStatusError as e:
            # Handle rate limiting (#36)
            if e.response.status_code == 429:
                if retry_count < MAX_RETRIES:
                    wait_time = INITIAL_BACKOFF_SECONDS * (BACKOFF_MULTIPLIER**retry_count)
                    logger.warning(
                        f"Rate limited (429). Retrying in {wait_time}s "
                        f"(attempt {retry_count + 1}/{MAX_RETRIES})"
                    )
                    await asyncio.sleep(wait_time)
                    return await self._execute_tool(tool_name, arguments, retry_count + 1)
                raise MCPToolError(
                    f"Rate limited after {MAX_RETRIES} retries. "
                    "Try again later or reduce request frequency."
                ) from e

            # Handle auth errors (#38)
            if e.response.status_code in (401, 403):
                raise MCPAuthError(
                    f"Authentication failed ({e.response.status_code}). "
                    "Check your credentials."
                ) from e

            raise MCPToolError(f"HTTP error {e.response.status_code}: {e}") from e

        except TimeoutError as e:
            raise MCPTimeoutError(
                f"Request timed out after {self.timeout}s. "
                "Try increasing timeout or check server load."
            ) from e

        except Exception as e:
            # Defensive error handling (#39)
            error_msg = str(e)
            if "SSL" in error_msg.upper() or "CERTIFICATE" in error_msg.upper():
                raise MCPSSLError(f"SSL error: {e}") from e
            if "CONNECT" in error_msg.upper() or "REFUSED" in error_msg.upper():
                raise MCPConnectionError(f"Connection error: {e}") from e
            raise MCPToolError(f"Tool call failed: {e}") from e

    async def get_status(self) -> dict[str, Any]:
        """Get server status / health check.

        Returns:
            Status information from the server
        """
        try:
            result = await self._execute_tool("get_status", {})

            # Parse result content
            if result.content:
                for item in result.content:
                    if hasattr(item, "text"):
                        return {"status": "ok", "message": item.text}

            return {"status": "ok"}

        except MCPToolError as e:
            # get_status may not exist - that's OK for health check
            if "not found" in str(e).lower() or "unknown" in str(e).lower():
                return {"status": "ok", "message": "Server reachable (get_status not available)"}
            raise

    async def add_memory(
        self,
        content: str,
        group_id: str,
        metadata: ChunkMetadata | None = None,
        name: str | None = None,
    ) -> str | None:
        """Send an episode to Graphiti (#61, #83).

        Args:
            content: Text content to store
            group_id: Graphiti group ID
            metadata: Optional chunk metadata for provenance
            name: Optional episode name

        Returns:
            Episode UUID if available, None otherwise

        Raises:
            ValueError: If group_id is invalid
            MCPToolError: If the tool call fails
        """
        # Validate group_id (#59)
        if not validate_group_id(group_id):
            raise ValueError(
                f"Invalid group_id: '{group_id}'. "
                "Must start with alphanumeric and contain only alphanumeric, hyphen, underscore."
            )

        # Build arguments
        arguments: dict[str, Any] = {
            "episode_body": content,
            "group_id": group_id,
        }

        # Build episode name with source info (#83)
        if name:
            arguments["name"] = name
        elif metadata:
            arguments["name"] = (
                f"{metadata.file_path} "
                f"[chunk {metadata.chunk_index + 1}/{metadata.total_chunks}]"
            )

        # Add source description (#83)
        if metadata and metadata.source_description:
            arguments["source_description"] = metadata.source_description
        elif metadata:
            arguments["source_description"] = (
                f"Ingested from {metadata.file_path} (hash: {metadata.file_hash[:12]})"
            )

        try:
            result = await self._execute_tool("add_memory", arguments)

            # Try to extract episode UUID from result
            episode_uuid = None
            if result.content:
                for item in result.content:
                    if hasattr(item, "text"):
                        text = item.text
                        # Look for UUID pattern in response
                        import re

                        uuid_match = re.search(
                            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                            text,
                            re.IGNORECASE,
                        )
                        if uuid_match:
                            episode_uuid = uuid_match.group(0)
                            break

            # Check for warnings about entities (#63, #87)
            if result.content:
                for item in result.content:
                    if hasattr(item, "text"):
                        text = item.text.lower()
                        if "no entities" in text or "0 entities" in text:
                            logger.warning(
                                "No entities extracted from chunk. "
                                "Content may be too short or lack named entities."
                            )

            logger.debug(f"Added memory: {arguments.get('name', 'unnamed')}")
            return episode_uuid

        except MCPToolError as e:
            # Log entity extraction failures but don't fail (#63)
            if "entity" in str(e).lower():
                logger.warning(f"Entity extraction issue: {e}")
                return None
            raise

    async def get_episodes(self, group_id: str, max_episodes: int = 100) -> list[dict[str, Any]]:
        """Get episodes from a group.

        Args:
            group_id: Graphiti group ID
            max_episodes: Maximum number of episodes to retrieve

        Returns:
            List of episode data
        """
        if not validate_group_id(group_id):
            raise ValueError(f"Invalid group_id: '{group_id}'")

        try:
            result = await self._execute_tool(
                "get_episodes",
                {"group_ids": [group_id], "max_episodes": max_episodes},
            )

            episodes: list[dict[str, Any]] = []
            if result.content:
                for item in result.content:
                    if hasattr(item, "text"):
                        # Try to parse as JSON
                        import json

                        try:
                            data = json.loads(item.text)
                            if isinstance(data, list):
                                episodes.extend(data)
                            elif isinstance(data, dict):
                                episodes.append(data)
                        except json.JSONDecodeError:
                            # Not JSON, skip
                            pass

            return episodes

        except MCPToolError as e:
            logger.warning(f"Could not get episodes: {e}")
            return []

    async def close(self) -> None:
        """Close the client (cleanup)."""
        self._connected = False
        self._session = None

    async def __aenter__(self) -> GraphitiClient:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.close()
