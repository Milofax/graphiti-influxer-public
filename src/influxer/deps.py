"""System dependency validation module.

Checks for required system dependencies like Tesseract and Poppler.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

# Platform detection
PLATFORM = platform.system().lower()
if PLATFORM == "darwin":
    PLATFORM = "mac"
elif PLATFORM == "windows":
    PLATFORM = "windows"
else:
    PLATFORM = "linux"

# Install commands for each platform
INSTALL_COMMANDS: dict[str, dict[str, str]] = {
    "tesseract": {
        "mac": "brew install tesseract tesseract-lang",
        "linux": "sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu tesseract-ocr-spa",
        "windows": "choco install tesseract",
    },
    "poppler": {
        "mac": "brew install poppler",
        "linux": "sudo apt install poppler-utils",
        "windows": "choco install poppler",
    },
}


def check_tesseract() -> tuple[bool, str | None]:
    """Check if Tesseract is installed.

    Returns:
        Tuple of (is_installed, version_string or None)
    """
    tesseract_path = shutil.which("tesseract")
    if not tesseract_path:
        return False, None

    try:
        result = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Tesseract version output is on first line
        version_line = result.stdout.split("\n")[0] if result.stdout else result.stderr.split("\n")[0]
        # Extract version number (e.g., "tesseract 5.3.3" -> "5.3.3")
        version = version_line.replace("tesseract", "").strip()
        return True, version
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return True, None  # Installed but couldn't get version


def check_poppler() -> tuple[bool, str | None]:
    """Check if Poppler is installed (needed for pdf2image).

    Returns:
        Tuple of (is_installed, version_string or None)
    """
    # Check for pdftoppm which is part of poppler-utils
    pdftoppm_path = shutil.which("pdftoppm")
    if not pdftoppm_path:
        return False, None

    try:
        result = subprocess.run(
            ["pdftoppm", "-v"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # pdftoppm outputs version to stderr
        version_line = result.stderr.strip() if result.stderr else result.stdout.strip()
        # Extract version (e.g., "pdftoppm version 24.02.0" -> "24.02.0")
        if "version" in version_line.lower():
            version = version_line.split("version")[-1].strip()
        else:
            version = version_line
        return True, version
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return True, None  # Installed but couldn't get version


def get_tesseract_languages() -> list[str]:
    """Get list of installed Tesseract language packs.

    Returns:
        List of language codes (e.g., ["eng", "deu", "spa"])
    """
    if not check_tesseract()[0]:
        return []

    try:
        result = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Output format:
        # List of available languages (N):
        # eng
        # deu
        # ...
        lines = result.stdout.strip().split("\n")
        # Skip the first line (header) and return language codes
        languages = [line.strip() for line in lines[1:] if line.strip() and not line.startswith("List")]
        return languages
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return []


def check_language_available(lang: str) -> bool:
    """Check if a specific OCR language is installed.

    Args:
        lang: Language code (e.g., "eng", "deu") or combined (e.g., "eng+deu")

    Returns:
        True if all specified languages are available
    """
    available = get_tesseract_languages()
    if not available:
        return False

    # Handle combined languages like "eng+deu+spa"
    requested = lang.split("+")
    return all(language in available for language in requested)


def get_install_instructions(dependency: str) -> str:
    """Get platform-specific install instructions for a dependency.

    Args:
        dependency: Name of dependency ("tesseract" or "poppler")

    Returns:
        Install command string for the current platform
    """
    if dependency not in INSTALL_COMMANDS:
        return f"Unknown dependency: {dependency}"

    cmd = INSTALL_COMMANDS[dependency].get(PLATFORM, "")
    if not cmd:
        return f"No install instructions available for {dependency} on {PLATFORM}"
    return cmd


def validate_dependencies(require_ocr: bool = False) -> list[str]:
    """Validate system dependencies and return list of missing ones.

    Args:
        require_ocr: If True, require OCR dependencies (Tesseract + Poppler)

    Returns:
        List of missing dependency names (empty if all present)
    """
    missing: list[str] = []

    if require_ocr:
        if not check_tesseract()[0]:
            missing.append("tesseract")
        if not check_poppler()[0]:
            missing.append("poppler")

    return missing


def print_dependency_status(console: Console) -> None:
    """Print a pretty table showing status of all dependencies.

    Args:
        console: Rich Console instance for output
    """
    from rich.table import Table

    table = Table(title="System Dependencies")
    table.add_column("Dependency", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Version", style="yellow")
    table.add_column("Install Command", style="dim")

    # Check Tesseract
    tess_installed, tess_version = check_tesseract()
    tess_status = "[green]✓ Installed[/green]" if tess_installed else "[red]✗ Missing[/red]"
    tess_install = "" if tess_installed else get_install_instructions("tesseract")
    table.add_row("Tesseract", tess_status, tess_version or "-", tess_install)

    # Check Poppler
    pop_installed, pop_version = check_poppler()
    pop_status = "[green]✓ Installed[/green]" if pop_installed else "[red]✗ Missing[/red]"
    pop_install = "" if pop_installed else get_install_instructions("poppler")
    table.add_row("Poppler", pop_status, pop_version or "-", pop_install)

    console.print(table)

    # Show installed OCR languages
    if tess_installed:
        langs = get_tesseract_languages()
        if langs:
            console.print(f"\n[cyan]Installed OCR languages:[/cyan] {', '.join(langs)}")
        else:
            console.print("\n[yellow]Warning: Could not list installed OCR languages[/yellow]")
