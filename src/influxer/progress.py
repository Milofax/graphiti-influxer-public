"""Rich Progress Display Module for Graphiti Influxer.

Provides progress tracking and display using Rich.

Edge cases handled:
- #73: HDD vs SSD (ETA display)
- #89: No Color Support (Rich auto-detects)
- #90: Piped Output (Rich handles gracefully)
"""

from __future__ import annotations

import time
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table


def create_console(force_terminal: bool | None = None) -> Console:
    """Create a Rich console with proper terminal detection (#89, #90).

    Args:
        force_terminal: Override terminal detection

    Returns:
        Configured Console instance
    """
    return Console(force_terminal=force_terminal)


def create_progress(console: Console | None = None) -> Progress:
    """Create a Rich Progress instance for file processing.

    Args:
        console: Optional console to use

    Returns:
        Configured Progress instance
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),  # ETA (#73)
        console=console,
        transient=False,
    )


class IngestionProgress:
    """Progress tracker for document ingestion.

    Provides methods to track extraction, chunking, and sending progress.
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the progress tracker.

        Args:
            console: Optional console to use
        """
        self.console = console or create_console()
        self._progress: Progress | None = None
        self._task_id: TaskID | None = None
        self._file_task_id: TaskID | None = None
        self._start_time: float | None = None
        self._chunks_sent = 0
        self._total_chunks = 0
        self._errors: list[str] = []

    def __enter__(self) -> IngestionProgress:
        """Context manager entry."""
        self._progress = create_progress(self.console)
        self._progress.start()
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: Any,
    ) -> None:
        """Context manager exit."""
        if self._progress:
            self._progress.stop()
            self._progress = None

    def start_file(self, filename: str, total_chunks: int) -> None:
        """Start tracking a file.

        Args:
            filename: Name of the file being processed
            total_chunks: Total number of chunks to send
        """
        if not self._progress:
            return

        self._start_time = time.time()
        self._total_chunks = total_chunks
        self._chunks_sent = 0

        # Remove old task if exists
        if self._file_task_id is not None:
            self._progress.remove_task(self._file_task_id)

        self._file_task_id = self._progress.add_task(
            f"[cyan]Processing {filename}",
            total=total_chunks,
        )

    def update_extraction(self, status: str) -> None:
        """Update extraction status.

        Args:
            status: Status message
        """
        if self._progress and self._file_task_id is not None:
            self._progress.update(
                self._file_task_id,
                description=f"[yellow]{status}",
            )

    def update_chunk(self, current_chunk: int, status: str | None = None) -> None:
        """Update chunk progress.

        Args:
            current_chunk: Current chunk number (1-indexed)
            status: Optional status message
        """
        if not self._progress or self._file_task_id is None:
            return

        self._chunks_sent = current_chunk

        description = f"[cyan]Sending chunk {current_chunk}/{self._total_chunks}"
        if status:
            description = f"[cyan]{status}"

        self._progress.update(
            self._file_task_id,
            completed=current_chunk,
            description=description,
        )

    def complete_file(self) -> None:
        """Mark file as complete."""
        if self._progress and self._file_task_id is not None:
            self._progress.update(
                self._file_task_id,
                completed=self._total_chunks,
                description="[green]✓ Complete",
            )

    def add_error(self, error: str) -> None:
        """Record an error.

        Args:
            error: Error message
        """
        self._errors.append(error)

    def show_summary(
        self,
        files_processed: int,
        chunks_sent: int,
        errors: int | None = None,
    ) -> None:
        """Show final summary.

        Args:
            files_processed: Number of files processed
            chunks_sent: Total chunks sent
            errors: Number of errors (or uses recorded errors)
        """
        if errors is None:
            errors = len(self._errors)

        elapsed = time.time() - self._start_time if self._start_time else 0

        # Create summary table
        table = Table(title="Ingestion Summary", show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Files processed", str(files_processed))
        table.add_row("Chunks sent", str(chunks_sent))
        table.add_row("Errors", f"[red]{errors}[/red]" if errors > 0 else "0")
        table.add_row("Time elapsed", f"{elapsed:.1f}s")

        if elapsed > 0 and chunks_sent > 0:
            rate = chunks_sent / elapsed
            table.add_row("Rate", f"{rate:.1f} chunks/sec")

        self.console.print()
        self.console.print(table)

        # Show errors if any
        if self._errors:
            self.console.print()
            self.console.print("[red]Errors:[/red]")
            for error in self._errors[-5:]:  # Show last 5 errors
                self.console.print(f"  • {error}")
            if len(self._errors) > 5:
                self.console.print(f"  ... and {len(self._errors) - 5} more")

    def show_eta(self) -> str | None:
        """Calculate and return ETA string (#73).

        Returns:
            ETA string or None if cannot calculate
        """
        if not self._start_time or self._chunks_sent == 0:
            return None

        elapsed = time.time() - self._start_time
        rate = self._chunks_sent / elapsed
        remaining = self._total_chunks - self._chunks_sent

        if rate > 0:
            eta_seconds = remaining / rate
            if eta_seconds < 60:
                return f"{eta_seconds:.0f}s"
            elif eta_seconds < 3600:
                return f"{eta_seconds / 60:.1f}m"
            else:
                return f"{eta_seconds / 3600:.1f}h"

        return None


def show_status_panel(
    console: Console,
    title: str,
    message: str,
    style: str = "green",
) -> None:
    """Show a status panel.

    Args:
        console: Console to print to
        title: Panel title
        message: Panel message
        style: Border style color
    """
    panel = Panel(message, title=title, border_style=style)
    console.print(panel)


def show_error(console: Console, message: str) -> None:
    """Show an error message.

    Args:
        console: Console to print to
        message: Error message
    """
    console.print(f"[red]Error:[/red] {message}")


def show_warning(console: Console, message: str) -> None:
    """Show a warning message.

    Args:
        console: Console to print to
        message: Warning message
    """
    console.print(f"[yellow]Warning:[/yellow] {message}")


def show_success(console: Console, message: str) -> None:
    """Show a success message.

    Args:
        console: Console to print to
        message: Success message
    """
    console.print(f"[green]✓[/green] {message}")
