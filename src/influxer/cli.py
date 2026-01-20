"""CLI Module for Graphiti Influxer.

Provides the command-line interface using Typer.

Edge cases handled:
- #33: Server nicht erreichbar (fail-fast with health check)
- #40: SSL/TLS Probleme (--insecure flag)
- #52: Keine Leserechte (skip + log)
- #55: Sonderzeichen (pathlib handles)
- #65: Tesseract nicht installiert (check-deps command)
- #66: Falsche Sprache (--language option)
- #88: Ctrl+C (signal handler + cleanup)
- #91: Falscher Pfad (early validation)
"""

from __future__ import annotations

import asyncio
import signal
from pathlib import Path
from typing import Annotated

import typer

from influxer import __version__
from influxer.chunker import chunk_text
from influxer.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CONFIG_FILE_PATH,
    GRAPHITI_MCP_URL,
    OCR_LANGUAGE,
    ensure_config_dir,
    get_config,
    save_config,
)
from influxer.deps import (
    check_language_available,
    print_dependency_status,
    validate_dependencies,
)
from influxer.extractors import (
    EPUBDRMError,
    EPUBExtractionError,
    PDFEmptyError,
    PDFExtractionError,
    PDFPasswordError,
    extract_text,
    get_supported_extensions,
    is_supported,
)
from influxer.mcp_client import (
    ChunkMetadata,
    GraphitiClient,
    MCPAuthError,
    MCPConnectionError,
    MCPSSLError,
    MCPTimeoutError,
    MCPToolError,
    validate_group_id,
)
from influxer.progress import (
    IngestionProgress,
    create_console,
    show_error,
    show_success,
    show_warning,
)
from influxer.state import StateDB, get_file_hash

# Create Typer app
app = typer.Typer(
    name="influxer",
    help="Graphiti Influxer - Ingest documents into Graphiti via MCP",
    add_completion=False,
)

# Global console
console = create_console()

# Shutdown flag for signal handling (#88)
_shutdown_requested = False


def _signal_handler(_signum: int, _frame: object) -> None:
    """Handle shutdown signals (#88)."""
    global _shutdown_requested
    _shutdown_requested = True
    console.print("\n[yellow]Interrupt received. Finishing current operation...[/yellow]")


# Register signal handlers
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"Graphiti Influxer v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", "-v", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """Graphiti Influxer - Ingest documents into Graphiti via MCP."""
    pass


@app.command()
def ingest(
    path: Annotated[
        Path,
        typer.Argument(help="File to ingest (PDF or EPUB)"),
    ],
    group_id: Annotated[
        str,
        typer.Option("--group-id", "-g", help="Graphiti group ID"),
    ] = "main",
    chunk_size: Annotated[
        int,
        typer.Option("--chunk-size", help="Chunk size in characters"),
    ] = CHUNK_SIZE,
    chunk_overlap: Annotated[
        int,
        typer.Option("--chunk-overlap", help="Overlap between chunks"),
    ] = CHUNK_OVERLAP,
    mcp_url: Annotated[
        str | None,
        typer.Option("--mcp-url", help="MCP server URL"),
    ] = None,
    language: Annotated[
        str,
        typer.Option("--language", "-l", help="OCR language (e.g., eng, deu, eng+deu)"),
    ] = OCR_LANGUAGE,
    insecure: Annotated[
        bool,
        typer.Option("--insecure", help="Skip SSL certificate verification"),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="MCP request timeout in seconds"),
    ] = 60,
) -> None:
    """Ingest a PDF or EPUB file into Graphiti.

    Examples:
        influxer ingest document.pdf
        influxer ingest book.epub --group-id my-project
        influxer ingest scan.pdf --language deu
    """
    global _shutdown_requested
    _shutdown_requested = False

    # Validate path exists (#91)
    if not path.exists():
        show_error(console, f"File not found: {path}")
        raise typer.Exit(1)

    # Check read permissions (#52)
    if not path.is_file():
        show_error(console, f"Not a file: {path}")
        raise typer.Exit(1)

    try:
        # Test read access
        with path.open("rb") as f:
            f.read(1)
    except PermissionError as e:
        show_error(console, f"Permission denied: {path}")
        raise typer.Exit(1) from e

    # Check supported format
    if not is_supported(path):
        supported = ", ".join(get_supported_extensions())
        show_error(console, f"Unsupported file format: {path.suffix}")
        console.print(f"Supported formats: {supported}")
        raise typer.Exit(1)

    # Validate group_id (#59)
    if not validate_group_id(group_id):
        show_error(
            console,
            f"Invalid group_id: '{group_id}'. "
            "Must start with alphanumeric and contain only alphanumeric, hyphen, underscore.",
        )
        raise typer.Exit(1)

    # Check OCR language if needed (#66)
    if path.suffix.lower() == ".pdf" and not check_language_available(language):
        show_warning(
            console,
            f"OCR language '{language}' may not be installed. "
            "Run 'influxer check-deps' to verify.",
        )

    # Run async ingestion
    try:
        asyncio.run(
            _ingest_file(
                path=path,
                group_id=group_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                mcp_url=mcp_url or GRAPHITI_MCP_URL,
                _language=language,
                insecure=insecure,
                timeout=timeout,
            )
        )
    except KeyboardInterrupt as e:
        console.print("\n[yellow]Interrupted. Progress saved.[/yellow]")
        raise typer.Exit(130) from e


async def _ingest_file(
    path: Path,
    group_id: str,
    chunk_size: int,
    chunk_overlap: int,
    mcp_url: str,
    _language: str,  # Reserved for future OCR language config
    insecure: bool,
    timeout: int,
) -> None:
    """Async implementation of file ingestion."""
    global _shutdown_requested

    # Initialize state database
    state_db = StateDB()

    # Calculate file hash
    file_hash = get_file_hash(path)

    # Check if already ingested
    if state_db.is_file_ingested(file_hash, group_id):
        show_warning(
            console,
            f"File already ingested to group '{group_id}'. "
            "Use a different group_id or delete the previous ingestion.",
        )
        status = state_db.get_ingestion_status(file_hash, group_id)
        if status:
            console.print(f"  Chunks: {status['chunks_sent']}")
            console.print(f"  Date: {status['completed_at']}")
        return

    # Create MCP client and test connection (#33)
    client = GraphitiClient(server_url=mcp_url, timeout=timeout, insecure=insecure)

    try:
        console.print(f"[dim]Connecting to {mcp_url}...[/dim]")
        await client.connect()
    except MCPConnectionError as e:
        show_error(console, str(e))
        console.print("\n[dim]Troubleshooting:[/dim]")
        console.print("  • Is the Graphiti MCP server running?")
        console.print("  • Check the URL is correct")
        console.print("  • Check network connectivity")
        raise typer.Exit(1) from None
    except MCPSSLError as e:
        show_error(console, str(e))
        console.print("\n[dim]Try:[/dim] influxer ingest --insecure ...")
        raise typer.Exit(1) from None
    except MCPAuthError as e:
        show_error(console, str(e))
        raise typer.Exit(1) from None

    show_success(console, "Connected to Graphiti MCP")

    # Extract text
    console.print(f"\n[cyan]Extracting text from {path.name}...[/cyan]")

    try:
        text = extract_text(path)
        console.print(f"  Extracted {len(text):,} characters")
    except PDFPasswordError as e:
        show_error(console, str(e))
        raise typer.Exit(1) from None
    except PDFEmptyError as e:
        show_error(console, str(e))
        raise typer.Exit(1) from None
    except PDFExtractionError as e:
        show_error(console, f"PDF extraction failed: {e}")
        raise typer.Exit(1) from None
    except EPUBDRMError as e:
        show_error(console, str(e))
        raise typer.Exit(1) from None
    except EPUBExtractionError as e:
        show_error(console, f"EPUB extraction failed: {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        show_error(console, f"Extraction failed: {e}")
        raise typer.Exit(1) from None

    # Chunk text
    console.print(f"\n[cyan]Chunking text (size={chunk_size}, overlap={chunk_overlap})...[/cyan]")
    chunks = chunk_text(text, chunk_size, chunk_overlap)
    console.print(f"  Created {len(chunks)} chunks")

    if not chunks:
        show_warning(console, "No chunks created. File may be too short.")
        return

    # Start ingestion tracking
    ingestion_id = state_db.start_ingestion(file_hash, path, group_id, len(chunks))

    # Send chunks to Graphiti
    console.print(f"\n[cyan]Sending to Graphiti (group: {group_id})...[/cyan]")

    episode_uuids: list[str] = []
    errors: list[str] = []

    with IngestionProgress(console) as progress:
        progress.start_file(path.name, len(chunks))

        for i, chunk in enumerate(chunks):
            # Check for shutdown (#88)
            if _shutdown_requested:
                console.print("\n[yellow]Shutdown requested. Saving progress...[/yellow]")
                break

            try:
                metadata = ChunkMetadata(
                    file_hash=file_hash,
                    file_path=str(path),
                    chunk_index=i,
                    total_chunks=len(chunks),
                    source_description=f"Ingested from {path.name}",
                )

                episode_uuid = await client.add_memory(
                    content=chunk,
                    group_id=group_id,
                    metadata=metadata,
                )

                if episode_uuid:
                    episode_uuids.append(episode_uuid)

                progress.update_chunk(i + 1)
                state_db.update_progress(ingestion_id, i + 1, episode_uuid)

            except MCPTimeoutError as e:
                error_msg = f"Chunk {i + 1}: Timeout - {e}"
                errors.append(error_msg)
                progress.add_error(error_msg)
                show_warning(console, error_msg)
                continue

            except MCPToolError as e:
                error_msg = f"Chunk {i + 1}: {e}"
                errors.append(error_msg)
                progress.add_error(error_msg)
                show_warning(console, error_msg)
                continue

            except Exception as e:
                error_msg = f"Chunk {i + 1}: Unexpected error - {e}"
                errors.append(error_msg)
                progress.add_error(error_msg)
                show_warning(console, error_msg)
                continue

        # Complete if not interrupted
        if not _shutdown_requested:
            progress.complete_file()

        # Show summary
        chunks_sent = len(chunks) - len(errors)
        progress.show_summary(
            files_processed=1,
            chunks_sent=chunks_sent,
            errors=len(errors),
        )

    # Finalize state
    if _shutdown_requested or errors:
        state_db.fail_ingestion(
            ingestion_id,
            f"Interrupted or errors: {len(errors)} failures",
        )
        if _shutdown_requested:
            console.print("[yellow]Progress saved. Run again to resume.[/yellow]")
    else:
        state_db.complete_ingestion(ingestion_id)
        show_success(console, f"Ingestion complete! {len(chunks)} chunks sent to '{group_id}'")

    await client.close()
    state_db.close()


@app.command("check-deps")
def check_deps() -> None:
    """Check system dependencies (Tesseract, Poppler).

    Shows status of OCR dependencies and available languages.
    """
    console.print("[cyan]Checking system dependencies...[/cyan]\n")
    print_dependency_status(console)

    # Check for critical missing deps
    missing = validate_dependencies(require_ocr=True)
    if missing:
        console.print(f"\n[yellow]Missing for OCR support: {', '.join(missing)}[/yellow]")
        console.print("OCR will not work until these are installed.")
    else:
        console.print("\n[green]✓ All dependencies installed[/green]")


@app.command()
def init(
    mcp_url: Annotated[
        str | None,
        typer.Option("--mcp-url", help="MCP server URL"),
    ] = None,
    test_connection: Annotated[
        bool,
        typer.Option("--test/--no-test", help="Test connection after init"),
    ] = True,
) -> None:
    """Initialize Influxer configuration.

    Creates ~/.influxer/ directory and config file.
    """
    console.print("[cyan]Initializing Influxer...[/cyan]\n")

    # Ensure config directory exists
    config_dir = ensure_config_dir()
    console.print(f"  Config directory: {config_dir}")

    # Get MCP URL
    if mcp_url is None:
        mcp_url = typer.prompt(
            "Graphiti MCP URL",
            default=GRAPHITI_MCP_URL,
        )

    # Save config
    config = get_config()
    config["mcp_url"] = mcp_url
    save_config(config)
    console.print(f"  Config saved to: {CONFIG_FILE_PATH}")

    # Test connection if requested
    if test_connection:
        console.print("\n[cyan]Testing connection...[/cyan]")

        async def _test() -> bool:
            client = GraphitiClient(server_url=mcp_url)
            try:
                await client.connect()
                await client.close()
                return True
            except Exception as e:
                show_error(console, str(e))
                return False

        if asyncio.run(_test()):
            show_success(console, "Connection successful!")
        else:
            show_warning(console, "Connection failed. Check URL and try again.")

    console.print("\n[green]✓ Initialization complete[/green]")
    console.print("\nRun: influxer ingest <file.pdf> --group-id <group>")


@app.command("smoke-test")
def smoke_test(
    mcp_url: Annotated[
        str | None,
        typer.Option("--mcp-url", help="MCP server URL"),
    ] = None,
    insecure: Annotated[
        bool,
        typer.Option("--insecure", help="Skip SSL certificate verification"),
    ] = False,
) -> None:
    """Run smoke tests to verify setup.

    Tests:
    - MCP server connectivity
    - PDF extraction with sample file
    - EPUB extraction with sample file
    """
    url = mcp_url or GRAPHITI_MCP_URL
    console.print("[cyan]Running smoke tests...[/cyan]\n")

    results: list[tuple[str, bool, str]] = []

    # Test 1: MCP connectivity
    console.print("1. Testing MCP connectivity...")

    async def _test_mcp() -> tuple[bool, str]:
        client = GraphitiClient(server_url=url, insecure=insecure)
        try:
            await client.connect()
            await client.get_status()  # Verify status endpoint works
            await client.close()
            return True, f"Connected to {url}"
        except Exception as e:
            return False, str(e)

    success, msg = asyncio.run(_test_mcp())
    results.append(("MCP Connection", success, msg))
    if success:
        show_success(console, msg)
    else:
        show_error(console, msg)

    # Test 2: PDF extraction
    console.print("\n2. Testing PDF extraction...")
    sample_pdf = Path("tests/fixtures/sample.pdf")
    if sample_pdf.exists():
        try:
            text = extract_text(sample_pdf)
            results.append(("PDF Extraction", True, f"Extracted {len(text)} chars"))
            show_success(console, f"Extracted {len(text)} chars from sample.pdf")
        except Exception as e:
            results.append(("PDF Extraction", False, str(e)))
            show_error(console, str(e))
    else:
        results.append(("PDF Extraction", False, "Sample file not found"))
        show_warning(console, "tests/fixtures/sample.pdf not found")

    # Test 3: EPUB extraction
    console.print("\n3. Testing EPUB extraction...")
    sample_epub = Path("tests/fixtures/sample.epub")
    if sample_epub.exists():
        try:
            text = extract_text(sample_epub)
            results.append(("EPUB Extraction", True, f"Extracted {len(text)} chars"))
            show_success(console, f"Extracted {len(text)} chars from sample.epub")
        except Exception as e:
            results.append(("EPUB Extraction", False, str(e)))
            show_error(console, str(e))
    else:
        results.append(("EPUB Extraction", False, "Sample file not found"))
        show_warning(console, "tests/fixtures/sample.epub not found")

    # Summary
    console.print("\n[cyan]Summary:[/cyan]")
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for name, success, msg in results:
        status = "[green]PASS[/green]" if success else "[red]FAIL[/red]"
        console.print(f"  {status} {name}: {msg}")

    console.print(f"\n{passed}/{total} tests passed")

    if passed == total:
        console.print("\n[green]✓ Ready to ingest documents![/green]")
    else:
        console.print("\n[yellow]Some tests failed. Check the errors above.[/yellow]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
