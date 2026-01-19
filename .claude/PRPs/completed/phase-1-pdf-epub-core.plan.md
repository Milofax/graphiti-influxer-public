# Feature: Phase 1 - PDF + EPUB Core

## Summary

Implementierung des Kern-Moduls von Graphiti Influxer: Ein CLI-Tool das PDF und EPUB Dateien in semantische Chunks aufteilt und via MCP-Protokoll an den Graphiti MCP-Server sendet. Nutzt bewährte PDF-Extraktion aus dem Archon-Fork (pymupdf4llm → pdfplumber → PyPDF2 → OCR) und ebooklib für EPUBs.

## User Story

Als Power-User mit Graphiti-Setup und grosser Dokumenten-Bibliothek
will ich eine PDF oder EPUB Datei in Graphiti laden
damit Claude (und andere Tools via MCP) später darauf zugreifen und Fragen beantworten kann.

## Problem Statement

Claude's Context-Window ist begrenzt. Wertvolles Wissen in grossen Dokumenten ist für Claude unzugänglich. Der User braucht ein Tool das Dokumente automatisch chunked und in Graphiti einpflegt.

## Solution Statement

Ein Python CLI-Tool (`influxer`) das:
1. Text aus PDFs extrahiert (inkl. OCR für gescannte Dokumente)
2. Text aus EPUBs extrahiert
3. Text in semantische Chunks aufteilt
4. Chunks via MCP-Protokoll (`add_memory`) an Graphiti sendet
5. Lokalen State in SQLite speichert (für Resume-Capability)
6. Progress mit Rich anzeigt

## Metadata

| Field            | Value                                             |
| ---------------- | ------------------------------------------------- |
| Type             | NEW_CAPABILITY                                    |
| Complexity       | HIGH                                              |
| Systems Affected | CLI, MCP Client, PDF Extractor, EPUB Extractor, Chunker, State DB |
| Dependencies     | mcp>=1.25.0, pymupdf4llm>=0.2.9, pytesseract>=0.3.10, pdf2image>=1.17, ebooklib, langchain-text-splitters, typer, rich, tomli-w, beautifulsoup4, chardet |
| Estimated Tasks  | 13                                                |

---

## UX Design

### Before State

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                              BEFORE STATE                                      ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   ┌─────────────┐                                                             ║
║   │  200-page   │                                                             ║
║   │    PDF      │ ──────► Claude Context Window ──────► ❌ OVERFLOW           ║
║   │  (5MB)      │         (max ~50 pages)                                     ║
║   └─────────────┘                                                             ║
║                                                                               ║
║   USER_FLOW: User versucht PDF in Claude zu laden → Context Limit erreicht    ║
║   PAIN_POINT: Keine Möglichkeit grosse Dokumente zu verarbeiten               ║
║   DATA_FLOW: PDF → Claude (direkt) → FAIL                                     ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### After State

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                               AFTER STATE                                      ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   ║
║   │  200-page   │    │  Influxer   │    │   Graphiti  │    │   Claude    │   ║
║   │    PDF      │───►│   CLI       │───►│ MCP Server  │───►│  via MCP    │   ║
║   │  (5MB)      │    │             │    │             │    │             │   ║
║   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘   ║
║         │                  │                  │                  │            ║
║         │            ┌─────┴─────┐      ┌─────┴─────┐      ┌─────┴─────┐     ║
║         │            │ Extract   │      │ Store in  │      │ Search &  │     ║
║         │            │ + Chunk   │      │ Knowledge │      │ Answer    │     ║
║         │            │ + Send    │      │ Graph     │      │ Questions │     ║
║         │            └───────────┘      └───────────┘      └───────────┘     ║
║                                                                               ║
║   USER_FLOW: influxer ingest doc.pdf --group-id main → Progress → Done       ║
║   VALUE_ADD: Grosse Dokumente werden Teil von Claude's Wissensbasis          ║
║   DATA_FLOW: PDF → Extract → Chunk → MCP add_memory → Graphiti → Claude      ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Interaction Changes

| Location | Before | After | User Impact |
|----------|--------|-------|-------------|
| Terminal | Kein Tool | `influxer ingest file.pdf` | Kann Dokumente in Graphiti laden |
| Graphiti | Leer | Enthält Episoden | Claude hat Zugriff auf Wissen |
| Claude | Kennt Dokument nicht | Kann Fragen beantworten | AI-Sparringpartner für Bibliothek |

---

## Mandatory Reading

**CRITICAL: Implementation agent MUST read these files before starting any task:**

| Priority | File | Why Read This |
|----------|------|---------------|
| P0 | `https://github.com/Milofax/Archon/blob/main/python/src/server/utils/document_processing.py` | PDF extraction pattern to MIRROR (copy-paste, not dependency) |
| P0 | `https://github.com/Milofax/Archon/blob/main/python/src/server/utils/ocr_processing.py` | OCR implementation to MIRROR (copy-paste, not dependency) |
| P1 | `https://github.com/Milofax/graphiti/blob/main/mcp_server/src/graphiti_mcp_server.py` | MCP Server tools (add_memory, get_episodes) |

**Archon Code Strategy**: Copy-paste the relevant functions, not import as dependency. Archon is a separate project with different dependencies. We extract only the PDF/OCR logic and adapt it for Influxer.

**External Documentation:**

| Source | Section | Why Needed |
|--------|---------|------------|
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | Client Session | How to connect to MCP server |
| [pypdf docs](https://pypdf.readthedocs.io/) | Text extraction | Basic PDF handling |
| [ebooklib docs](https://ebooklib.readthedocs.io/) | Reading EPUBs | EPUB text extraction |
| [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/) | RecursiveCharacterTextSplitter | Semantic chunking |
| [Typer docs](https://typer.tiangolo.com/) | CLI creation | CLI framework |
| [Rich docs](https://rich.readthedocs.io/) | Progress bars | Progress display |

---

## Patterns to Mirror

**PDF_EXTRACTION_CHAIN (from Archon):**

```python
# SOURCE: Milofax/Archon:python/src/server/utils/document_processing.py
# COPY THIS PATTERN - Fallback chain with OCR:

def extract_text_from_pdf(file_content: bytes) -> str:
    # Primary: pymupdf4llm (best quality - proper word separation and Markdown)
    if PYMUPDF4LLM_AVAILABLE:
        try:
            markdown_text = pymupdf4llm.to_markdown(tmp_path)
            if markdown_text and len(markdown_text.strip()) > 100:
                return markdown_text
        except Exception as e:
            pass  # fallback

    # Fallback 1: pdfplumber
    if PDFPLUMBER_AVAILABLE:
        # ... extract with pdfplumber

    # Fallback 2: PyPDF2
    if PYPDF2_AVAILABLE:
        # ... extract with PyPDF2

    # Final fallback: OCR for image-based/scanned PDFs
    if is_ocr_available():
        ocr_text = extract_text_with_ocr(file_content)
        if ocr_text:
            return ocr_text
```

**OCR_PATTERN (from Archon):**

```python
# SOURCE: Milofax/Archon:python/src/server/utils/ocr_processing.py
# COPY THIS PATTERN - Multi-language OCR:

def extract_text_with_ocr(
    file_content: bytes,
    language: str = "eng",  # or "eng+deu" for multi-language
    dpi: int = 300,
) -> str | None:
    images = convert_from_bytes(file_content, dpi=dpi)
    text_content = []
    for page_num, image in enumerate(images, start=1):
        page_text = pytesseract.image_to_string(image, lang=language)
        if page_text and page_text.strip():
            text_content.append(f"--- Page {page_num} ---\n{page_text.strip()}")
    return "\n\n".join(text_content)
```

**MCP_CLIENT_PATTERN:**

```python
# SOURCE: MCP Python SDK README
# COPY THIS PATTERN - Connect to MCP server:

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def connect_to_graphiti(server_url: str):
    async with streamablehttp_client(server_url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # Call add_memory tool
            result = await session.call_tool("add_memory", {
                "content": chunk_text,
                "group_id": group_id,
            })
```

**CHUNKING_PATTERN:**

```python
# SOURCE: LangChain docs
# COPY THIS PATTERN - Semantic chunking:

from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,      # Target chunk size in chars
    chunk_overlap=200,    # Overlap for context continuity
    separators=["\n\n", "\n", ". ", " ", ""],  # Paragraph > Sentence > Word
)
chunks = text_splitter.split_text(document_text)
```

**CLI_PATTERN:**

```python
# SOURCE: Typer docs
# COPY THIS PATTERN - CLI with subcommands:

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(help="Graphiti Influxer - Ingest documents into Graphiti")

@app.command()
def ingest(
    path: Path = typer.Argument(..., help="File or directory to ingest"),
    group_id: str = typer.Option("main", "--group-id", "-g", help="Graphiti group ID"),
    chunk_size: int = typer.Option(2000, "--chunk-size", help="Chunk size in characters"),
):
    """Ingest a PDF or EPUB file into Graphiti."""
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        # ... process file
```

---

## Files to Change

| File                             | Action | Justification                            |
| -------------------------------- | ------ | ---------------------------------------- |
| `pyproject.toml`                 | CREATE | Project config, dependencies             |
| `src/influxer/__init__.py`       | CREATE | Package init                             |
| `src/influxer/cli.py`            | CREATE | Typer CLI entry point                    |
| `src/influxer/mcp_client.py`     | CREATE | MCP client for Graphiti connection       |
| `src/influxer/extractors/__init__.py` | CREATE | Extractors package                  |
| `src/influxer/extractors/pdf.py` | CREATE | PDF text extraction (from Archon)        |
| `src/influxer/extractors/epub.py`| CREATE | EPUB text extraction                     |
| `src/influxer/extractors/ocr.py` | CREATE | OCR processing (from Archon)             |
| `src/influxer/chunker.py`        | CREATE | Semantic text chunking                   |
| `src/influxer/state.py`          | CREATE | SQLite state management                  |
| `src/influxer/progress.py`       | CREATE | Rich progress display                    |
| `src/influxer/config.py`         | CREATE | Configuration (MCP URL, defaults)        |
| `src/influxer/deps.py`           | CREATE | System dependency checks (Tesseract, Poppler) |

| `tests/fixtures/`                | CREATE | Test fixtures directory                  |

---

## Test Fixtures

**Required for validation - create BEFORE running smoke tests:**

| Fixture | Source | Purpose |
|---------|--------|---------|
| `tests/fixtures/sample.pdf` | Create simple 2-page PDF with text | Basic PDF extraction test |
| `tests/fixtures/sample.epub` | Create simple EPUB with 2 chapters | Basic EPUB extraction test |
| `tests/fixtures/scanned.pdf` | PDF with image-only pages (scan) | OCR fallback test |

**How to create fixtures:**
- `sample.pdf`: Use Python `reportlab` or export from any text editor
- `sample.epub`: Use `ebooklib` to create programmatically, or download public domain EPUB
- `scanned.pdf`: Scan a page or convert image to PDF

**Alternative**: Download public domain test files:
- PDF: https://www.w3.org/WAI/WCAG21/Techniques/pdf/img/table-word.pdf
- EPUB: https://www.gutenberg.org/ebooks/11 (Alice in Wonderland)

---

## NOT Building (Scope Limits)

Explicit exclusions to prevent scope creep:

- **Batch-Verarbeitung (Ordner)** - Phase 2
- **Resume bei Abbruch** - Phase 2 (State-Tracking wird gebaut, Resume-Logic später)
- **Partial Ingestion Recovery** - Phase 2 (wenn 50/100 Chunks gesendet und Abbruch: `get_episodes` Abgleich in Phase 2)
- **Interaktiver Wizard-Modus** - Phase 2
- **Autonomer Modus (--yes --quiet)** - Phase 2
- **Verify-Command** - Phase 2
- **Markdown Support** - Phase 3
- **Web Crawling** - Phase 5
- **Web UI** - Won't build

---

## Edge Cases (Phase 1)

**59 Cases aus [edge-cases.md](../edge-cases.md)** - MÜSSEN in Phase 1 behandelt werden.

### PDF-Extraktion (8 Cases)

| # | Case | Mitigation | Implementiert in |
|---|------|------------|------------------|
| 1 | Passwortgeschützte PDF | Detect + Skip + Log (`PDFPasswordError`) | Task 5 |
| 2 | Gescannte PDF (nur Bilder) | OCR-Fallback (Tesseract) | Task 4, 5 |
| 3 | Gemischter Content (Text + Scans) | Seiten-Check + OCR für leere Seiten | Task 5 |
| 4 | Korrupte PDF | Try/Catch + Skip + Log (`PDFCorruptError`) | Task 5 |
| 7 | Eingebettete Dateien | Log Warning "Attachments ignoriert" | Task 5 |
| 8 | Sehr große PDF (1000+ Seiten) | Page-by-Page Streaming | Task 5 |
| 12 | Leere PDF | Skip + Log (`PDFEmptyError`) | Task 5 |

### EPUB-Extraktion (8 Cases)

| # | Case | Mitigation | Implementiert in |
|---|------|------------|------------------|
| 13 | DRM-geschütztes EPUB | Detect + Skip + Log | Task 6 |
| 14 | Kaputtes ZIP | Try/Catch + Skip | Task 6 |
| 16 | Eingebettetes Audio/Video | Log Info "Media ignoriert" | Task 6 |
| 17 | Komplexes CSS | Text-Only Extraktion (BeautifulSoup) | Task 6 |
| 18 | JavaScript | Security Skip | Task 6 |
| 20 | EPUB2 vs EPUB3 | ebooklib unterstützt beide, testen | Task 6 |
| 21 | Fehlendes TOC | Content-Order als Fallback | Task 6 |
| 22 | Non-UTF8 Encoding | Detect + Convert (chardet) | Task 6 |

### Chunking (4 Cases)

| # | Case | Mitigation | Implementiert in |
|---|------|------------|------------------|
| 23 | Fließtext ohne Absätze | Sentence-Splitter Fallback | Task 8 |
| 24 | Sehr kurzes Dokument | Minimum-Size Check (< 100 chars = warning) | Task 8 |
| 29 | Chunk > MCP-Limit | Pre-Verify Size, Split wenn nötig | Task 8 |
| 30 | Overlap-Duplikate | Dokumentieren: Graphiti dedupliziert | Task 8 |

### MCP/Netzwerk (9 Cases)

| # | Case | Mitigation | Implementiert in |
|---|------|------------|------------------|
| 33 | Server nicht erreichbar | Health-Check vor Start (Fail-Fast) | Task 10, 12 |
| 34 | Timeout 30-50s | Async + Progress + Configurable Timeout | Task 10 |
| 36 | Rate-Limiting (429) | Exponential Backoff (1s, 2s, 4s) | Task 10 |
| 38 | Ungültige Credentials | Pre-Auth-Check | Task 10 |
| 39 | Response Parsing Fehler | Defensive Parsing, MCPToolError | Task 10 |
| 40 | SSL/TLS Probleme | `--insecure` Flag für Self-Signed | Task 10, 12 |
| 41 | Proxy/Firewall | Clear Error + Network-Diagnostics | Task 10 |
| 42 | DNS fehlschlägt | Clear Error Message | Task 10 |

### State/SQLite (4 Cases)

| # | Case | Mitigation | Implementiert in |
|---|------|------------|------------------|
| 44 | Kill während DB-Write | SQLite Transactions | Task 9 |
| 47 | Disk voll | Pre-Check + Clear Error | Task 9 |
| 48 | Parallele Instanzen | File-Locking (sqlite3 handled) | Task 9 |
| 50 | Network-Drive | Dokumentieren: Local empfohlen | Docs |

### File System (2 Cases)

| # | Case | Mitigation | Implementiert in |
|---|------|------------|------------------|
| 52 | Keine Leserechte | Skip + Log (PermissionError) | Task 12 |
| 55 | Sonderzeichen | pathlib handled | Task 12 |

### Graphiti (5 Cases)

| # | Case | Mitigation | Implementiert in |
|---|------|------------|------------------|
| 59 | Ungültige group_id | Validate Format (alphanumeric + hyphen) | Task 10, 12 |
| 60 | group_id existiert nicht | Graphiti erstellt auto, dokumentieren | Docs |
| 61 | Duplikat-Detection | Hash in Metadata (file_hash, chunk_index) | Task 10 |
| 63 | Entity-Extraction fails | Warning + trotzdem speichern | Task 10 |
| 87 | 0 Entities | Warning, continue | Task 10 |

### OCR (6 Cases)

| # | Case | Mitigation | Implementiert in |
|---|------|------------|------------------|
| 65 | Tesseract nicht installiert | deps.py Check + Install Instructions | Task 3 |
| 66 | Falsche Sprache | --language Option + Sprach-Check | Task 3, 12 |
| 67 | Handschrift | Confidence Warning (< 60%) | Task 4 |
| 68 | Niedriger DPI | Warning wenn < 150 DPI | Task 4 |
| 69 | OCR Timeout | Timeout pro Seite (60s) + Skip | Task 4 |
| 70 | Multi-Language | eng+deu+spa Config | Task 2, 4 |

### Memory/Performance (3 Cases)

| # | Case | Mitigation | Implementiert in |
|---|------|------------|------------------|
| 72 | 500MB PDF | Page-by-Page Processing | Task 5 |
| 73 | HDD vs SSD | Progress zeigt ETA | Task 11 |
| 75 | File-Handles | Context Managers (with statements) | All Tasks |

### Encoding (1 Case)

| # | Case | Mitigation | Implementiert in |
|---|------|------------|------------------|
| 76 | UTF-16/32 | Detect + Convert | Task 5, 6 |

### Security (4 Cases)

| # | Case | Mitigation | Implementiert in |
|---|------|------------|------------------|
| 80 | Malware | Keine Ausführung, nur Text | Task 5, 6 |
| 81 | Urheberrecht | User-Verantwortung (Terms) | Docs |
| 82 | DSGVO | Privacy-Warning | Docs |
| 83 | Source-Tracking | file_path + file_hash in Metadata | Task 10 |

### CLI/UX (4 Cases)

| # | Case | Mitigation | Implementiert in |
|---|------|------------|------------------|
| 88 | Ctrl+C | Signal-Handler + Cleanup | Task 12 |
| 89 | No Color Support | Rich auto-detects | Task 11 |
| 90 | Piped Output | Rich handles | Task 11 |
| 91 | Falscher Pfad | Frühzeitige Validierung | Task 12 |

---

## Step-by-Step Tasks

Execute in order. Each task is atomic and independently verifiable.

### Task 0: VERIFY Test Fixtures (Already Created)

- **ACTION**: Verify test fixtures exist (required for smoke tests)
- **STATUS**: ✓ FIXTURES ALREADY EXIST in `tests/fixtures/`
- **FILES**:
  | File | Size | Purpose |
  |------|------|---------|
  | `tests/fixtures/sample.pdf` | 3.1KB | Text-based PDF (1215 chars extractable) |
  | `tests/fixtures/scanned.pdf` | 126KB | Image-only PDF (requires OCR, contains real Umlaute: Ö, Ü, ä, ö, ß) |
  | `tests/fixtures/sample.epub` | 3.4KB | EPUB with 2 chapters and TOC |
- **VALIDATE ONLY** - Skip creation, just verify:
  ```bash
  ls -la tests/fixtures/
  # Expected: sample.pdf, scanned.pdf, sample.epub
  ```
- **IF MISSING** - Recreate with:
  ```bash
  # Ensure fixtures directory exists
  mkdir -p tests/fixtures

  # Create sample.pdf (text-based) using reportlab
  uvx --with reportlab python -c "
  from reportlab.lib.pagesizes import A4
  from reportlab.pdfgen import canvas
  from reportlab.lib.units import cm
  c = canvas.Canvas('tests/fixtures/sample.pdf', pagesize=A4)
  c.setFont('Helvetica-Bold', 24)
  c.drawString(2*cm, 26*cm, 'Test Document Page 1')
  c.setFont('Helvetica', 12)
  c.drawString(2*cm, 24*cm, 'This is sample text for PDF extraction testing.')
  c.showPage()
  c.drawString(2*cm, 26*cm, 'Test Document Page 2')
  c.drawString(2*cm, 24*cm, 'Second page with additional content.')
  c.save()
  "

  # Create scanned.pdf (image-only, requires OCR) using PIL + reportlab
  uvx --with reportlab --with pillow python -c "
  from reportlab.lib.pagesizes import A4
  from reportlab.pdfgen import canvas
  from reportlab.lib.utils import ImageReader
  from PIL import Image, ImageDraw, ImageFont
  from io import BytesIO
  img = Image.new('RGB', (2480, 3508), 'white')
  draw = ImageDraw.Draw(img)
  font = ImageFont.load_default()
  draw.text((150, 200), 'OCR Test - This text is an image', fill='black', font=font)
  draw.text((150, 300), 'PDF extraction should return empty', fill='black', font=font)
  buf = BytesIO()
  img.save(buf, format='PNG')
  buf.seek(0)
  c = canvas.Canvas('tests/fixtures/scanned.pdf', pagesize=A4)
  c.drawImage(ImageReader(buf), 0, 0, width=A4[0], height=A4[1])
  c.save()
  "

  # Create sample.epub (2 chapters) using ebooklib
  uvx --with ebooklib --with lxml python -c "
  from ebooklib import epub
  book = epub.EpubBook()
  book.set_identifier('test-001')
  book.set_title('Test EPUB')
  book.set_language('en')
  c1 = epub.EpubHtml(title='Chapter 1', file_name='ch1.xhtml')
  c1.content = '<h1>Chapter 1</h1><p>First chapter content for testing.</p>'
  c2 = epub.EpubHtml(title='Chapter 2', file_name='ch2.xhtml')
  c2.content = '<h1>Chapter 2</h1><p>Second chapter with more text.</p>'
  book.add_item(c1)
  book.add_item(c2)
  book.toc = [epub.Link('ch1.xhtml', 'Chapter 1', 'c1'), epub.Link('ch2.xhtml', 'Chapter 2', 'c2')]
  book.add_item(epub.EpubNcx())
  book.add_item(epub.EpubNav())
  book.spine = ['nav', c1, c2]
  epub.write_epub('tests/fixtures/sample.epub', book, {})
  "
  ```
- **VALIDATE**:
  ```bash
  # Verify fixtures exist
  ls -la tests/fixtures/

  # Verify sample.pdf has extractable text
  uvx --with pdfplumber python -c "
  import pdfplumber
  with pdfplumber.open('tests/fixtures/sample.pdf') as pdf:
      text = ''.join(p.extract_text() or '' for p in pdf.pages)
      assert len(text) > 100, 'sample.pdf should have text'
      print(f'sample.pdf: {len(text)} chars ✓')
  "

  # Verify scanned.pdf has NO extractable text (image-only)
  uvx --with pdfplumber python -c "
  import pdfplumber
  with pdfplumber.open('tests/fixtures/scanned.pdf') as pdf:
      text = ''.join(p.extract_text() or '' for p in pdf.pages)
      assert len(text) < 10, 'scanned.pdf should be image-only'
      print(f'scanned.pdf: {len(text)} chars (OCR required) ✓')
  "

  # Verify sample.epub structure
  uvx --with ebooklib python -c "
  from ebooklib import epub
  book = epub.read_epub('tests/fixtures/sample.epub')
  chapters = [i for i in book.get_items() if i.get_type() == 9]
  assert len(chapters) >= 2, 'sample.epub should have 2+ chapters'
  print(f'sample.epub: {len(chapters)} chapters ✓')
  "
  ```
- **GOTCHA**: These fixtures are committed to git - they're test data, not generated artifacts

### Task 1: CREATE `pyproject.toml`

- **ACTION**: Create project configuration with all dependencies
- **IMPLEMENT**:
  - Project name: `graphiti-influxer`
  - Python >= 3.12
  - Dependencies: mcp, pymupdf4llm, pytesseract, pdf2image, pypdf2, pdfplumber, ebooklib, langchain-text-splitters, typer, rich, tomli-w, beautifulsoup4, chardet
  - Entry point: `influxer = "influxer.cli:app"`
- **MIRROR**: Standard Python pyproject.toml structure
- **GOTCHA**: Use `mcp>=1.25.0` (latest stable, streamable HTTP support)
- **VALIDATE**: `uv sync` succeeds

### Task 2: CREATE `src/influxer/config.py`

- **ACTION**: Create configuration module with environment variable support
- **IMPLEMENT**:
  - `GRAPHITI_MCP_URL` from env `INFLUXER_MCP_URL` or default
    - **Default**: `https://graphiti.marakanda.biz/mcp` (Traefik HTTPS, intern + extern)
    - **MUST be configurable**: Jeder User hat andere Graphiti-Instanz
    - Config priority: CLI flag > env var > config file > default
  - `DEFAULT_GROUP_ID` = "main" (env: `INFLUXER_GROUP_ID`)
  - `DEFAULT_CHUNK_SIZE` = 2000 (env: `INFLUXER_CHUNK_SIZE`)
  - `DEFAULT_CHUNK_OVERLAP` = 200
  - `OCR_LANGUAGE` = "eng+deu+spa" (env: `INFLUXER_OCR_LANGUAGE`)
  - `OCR_DPI` = 300
  - `STATE_DB_PATH` = `~/.influxer/state.db` (env: `INFLUXER_STATE_DB`)
  - `CONFIG_FILE_PATH` = `~/.influxer/config.toml`
  - Helper: `get_config() -> dict` - Returns all config values with env overrides
  - Helper: `save_config(config: dict)` - Writes config to TOML file
  - Helper: `load_config() -> dict` - Loads from TOML, merges with env vars
  - **First-Run Setup**: If no config file exists, prompt user for MCP URL (or use `influxer init`)
- **IMPORTS**: `os`, `pathlib`, `tomllib` (Python 3.11+), `tomli_w` (for writing)
- **GOTCHA**: tomllib is read-only in stdlib, need `tomli_w` for writing
- **GOTCHA**: Use `os.getenv()` with sensible defaults
- **VALIDATE**: `INFLUXER_MCP_URL=http://test python -c "from influxer.config import GRAPHITI_MCP_URL; print(GRAPHITI_MCP_URL)"`

### Task 3: CREATE `src/influxer/deps.py`

- **ACTION**: Create system dependency validation module
- **IMPLEMENT**:
  - `PLATFORM` detection (mac/linux/windows)
  - `check_tesseract() -> tuple[bool, str | None]` - Check if installed, return version
  - `check_poppler() -> tuple[bool, str | None]` - Check if installed (needed for pdf2image)
  - `get_tesseract_languages() -> list[str]` - List installed OCR languages
  - `check_language_available(lang: str) -> bool` - Check specific language
  - `get_install_instructions(dependency: str) -> str` - Platform-specific install commands
  - `validate_dependencies(require_ocr: bool = False) -> list[str]` - Returns list of missing deps
  - `print_dependency_status(console: Console)` - Pretty-print status table
- **INSTALL_INSTRUCTIONS**:
  ```python
  INSTALL_COMMANDS = {
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
  ```
- **IMPORTS**: `shutil`, `subprocess`, `platform`, `rich.console`, `rich.table`
- **GOTCHA**: Use `shutil.which()` for cross-platform executable detection
- **VALIDATE**: `python -c "from influxer.deps import check_tesseract; print(check_tesseract())"`

### Task 4: CREATE `src/influxer/extractors/ocr.py`

- **ACTION**: Create OCR processing module (copy from Archon)
- **EDGE CASES**: #2, #67, #68, #69, #70
- **IMPLEMENT**:
  - `is_ocr_available()` - Check dependencies
  - `get_supported_languages()` - List installed Tesseract languages
  - `extract_text_with_ocr(file_content, language, dpi)` - Sync OCR
  - `extract_text_with_ocr_async(file_content, progress_callback, language, dpi)` - Async with progress
  - `get_ocr_confidence(image) -> float` - Returns confidence score (#67)
  - `check_image_dpi(image) -> int` - Warn if < 150 DPI (#68)
  - Timeout: 60s pro Seite, Skip bei Timeout (#69)
- **MIRROR**: `https://github.com/Milofax/Archon/blob/main/python/src/server/utils/ocr_processing.py`
- **IMPORTS**: `pytesseract`, `pdf2image.convert_from_bytes`, `PIL.Image`
- **GOTCHA**: Requires system deps: `brew install tesseract poppler` (Mac)
- **VALIDATE**: `python -c "from influxer.extractors.ocr import is_ocr_available; print(is_ocr_available())"`

### Task 5: CREATE `src/influxer/extractors/pdf.py`

- **ACTION**: Create PDF extraction module (copy from Archon)
- **EDGE CASES**: #1, #2, #3, #4, #7, #8, #12, #72, #76, #80
- **IMPLEMENT**:
  - `extract_text_from_pdf(file_path: Path) -> str` - Sync extraction
  - `extract_text_from_pdf_async(file_path, progress_callback) -> str` - Async with progress
  - `is_password_protected(file_path) -> bool` - Check before extraction (#1)
  - `has_embedded_files(file_path) -> bool` - Log warning if true (#7)
  - `extract_page_by_page(file_path) -> Generator[str]` - For large PDFs (#8, #72)
  - `is_page_scanned(page) -> bool` - Check if page needs OCR (#3)
  - Fallback chain: pymupdf4llm → pdfplumber → PyPDF2 → OCR
- **ERROR HANDLING**:
  - `PDFExtractionError` - Base exception for PDF errors
  - `PDFCorruptError` - File is corrupted or not a valid PDF (#4)
  - `PDFEmptyError` - PDF has no extractable text (#12)
  - `PDFPasswordError` - PDF is password-protected (#1)
  - Each fallback logs warning before trying next method
  - Final fallback (OCR) failure → raise with helpful message
- **SECURITY**: Text-only extraction, keine JavaScript/Macros ausführen (#80)
- **MIRROR**: `https://github.com/Milofax/Archon/blob/main/python/src/server/utils/document_processing.py`
- **IMPORTS**: `pymupdf4llm`, `pdfplumber`, `PyPDF2`, `.ocr`, `chardet`
- **GOTCHA**: pymupdf4llm needs file path, not bytes - use tempfile
- **VALIDATE**: Extract text from test PDFs (normal, scanned, password-protected, empty)

### Task 6: CREATE `src/influxer/extractors/epub.py`

- **ACTION**: Create EPUB extraction module
- **EDGE CASES**: #13, #14, #16, #17, #18, #20, #21, #22, #76, #80
- **IMPLEMENT**:
  - `extract_text_from_epub(file_path: Path) -> str`
  - `is_drm_protected(file_path) -> bool` - Check for DRM (#13)
  - `get_epub_version(book) -> str` - EPUB2 vs EPUB3 (#20)
  - Use `ebooklib.epub.read_epub()`
  - Extract text from all `ITEM_DOCUMENT` items
  - Parse HTML content with BeautifulSoup (strips CSS #17, JS #18)
  - Preserve chapter structure with markers
  - Fallback to content order if no TOC (#21)
  - Log info for audio/video items (#16)
- **ERROR HANDLING**:
  - `EPUBExtractionError` - Base exception
  - `EPUBDRMError` - DRM protected, cannot extract (#13)
  - `EPUBCorruptError` - Invalid ZIP or structure (#14)
  - Encoding detection with chardet (#22, #76)
- **SECURITY**: Text-only extraction, no JS execution (#80)
- **MIRROR**: ebooklib docs pattern
- **IMPORTS**: `ebooklib`, `ebooklib.epub`, `bs4.BeautifulSoup`, `chardet`, `zipfile`
- **GOTCHA**: EPUB content is HTML, needs cleaning; some EPUBs have invalid XML
- **VALIDATE**: Extract text from test EPUBs (EPUB2, EPUB3, with/without TOC)

### Task 7: CREATE `src/influxer/extractors/__init__.py`

- **ACTION**: Create extractors package with unified interface
- **IMPLEMENT**:
  - `extract_text(file_path: Path) -> str` - Auto-detect format and extract
  - Support: `.pdf`, `.epub`
  - Raise `ValueError` for unsupported formats
- **VALIDATE**: `from influxer.extractors import extract_text`

### Task 8: CREATE `src/influxer/chunker.py`

- **ACTION**: Create semantic chunking module
- **EDGE CASES**: #23, #24, #29, #30
- **IMPLEMENT**:
  - `chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]`
  - `validate_chunk_size(chunk: str, max_size: int) -> bool` - Pre-verify (#29)
  - `get_chunk_metadata(chunk: str, index: int, total: int) -> dict`
  - Use `RecursiveCharacterTextSplitter` from langchain
  - Separators: `["\n\n", "\n", ". ", " ", ""]` - handles Fließtext (#23)
  - Minimum text length check: < 100 chars = warning (#24)
  - Return list of chunk strings
- **OVERLAP STRATEGY** (#30):
  - Default overlap: 200 chars
  - Graphiti dedupliziert basierend auf Entity-Matching
  - chunk_index in Metadata für Reihenfolge
- **MIRROR**: LangChain RecursiveCharacterTextSplitter pattern
- **IMPORTS**: `langchain_text_splitters.RecursiveCharacterTextSplitter`
- **GOTCHA**: chunk_size is characters, not tokens; MCP may have size limit
- **VALIDATE**: Chunk texts of various lengths, verify no chunk exceeds max_size

### Task 9: CREATE `src/influxer/state.py`

- **ACTION**: Create SQLite state management
- **EDGE CASES**: #44, #47, #48, #50, #75
- **IMPLEMENT**:
  - `StateDB` class with context manager
  - `init_db()` - Create tables if not exist
  - `get_file_hash(file_path: Path) -> str` - SHA256 of file
  - `is_file_ingested(file_hash: str) -> bool`
  - `record_ingestion(file_hash: str, file_path: str, group_id: str, chunk_count: int, episode_uuids: list[str])`
  - `get_ingestion_status(file_hash: str) -> dict | None`
  - `check_disk_space(path: Path, min_mb: int = 10) -> bool` - Pre-check (#47)
  - Table: `ingestions (file_hash, file_path, group_id, chunk_count, episode_uuids, created_at, status)`
- **TRANSACTIONS** (#44):
  - All writes in `with conn: conn.execute(...)` block
  - Atomic: entweder alles oder nichts
- **LOCKING** (#48):
  - SQLite handles concurrent access
  - `timeout=30` in connection für busy-wait
- **IMPORTS**: `sqlite3`, `hashlib`, `pathlib`, `json`, `shutil`
- **GOTCHA**: Store episode_uuids as JSON string; Network drives may cause issues (#50)
- **VALIDATE**: Insert and retrieve test record; test concurrent access

### Task 10: CREATE `src/influxer/mcp_client.py`

- **ACTION**: Create MCP client for Graphiti
- **EDGE CASES**: #33, #34, #36, #38, #39, #40, #41, #42, #59, #61, #63, #83, #87
- **IMPLEMENT**:
  - `GraphitiClient` class
  - `async connect(server_url: str, insecure: bool = False)` - Establish MCP connection
  - `async add_memory(content: str, group_id: str, metadata: dict) -> str` - Send episode with metadata (#61, #83)
  - `async get_episodes(group_id: str) -> list` - Get episodes for verification
  - `async get_status() -> dict` - Health check
  - `async is_connected() -> bool` - Quick connectivity test (#33)
  - `validate_group_id(group_id: str) -> bool` - Format check (#59)
- **METADATA** (#61, #83):
  - `file_hash` - SHA256 of source file
  - `file_path` - Original file path (provenance)
  - `chunk_index` - Position in document
  - `total_chunks` - Total chunks from this file
- **ERROR HANDLING**:
  - `MCPConnectionError` - Server unreachable (#33, #41, #42)
  - `MCPAuthError` - Authentication failed (#38)
  - `MCPToolError` - Tool call failed (#39)
  - `MCPSSLError` - Certificate issues (#40)
  - Retry logic: 3 attempts with exponential backoff (1s, 2s, 4s) (#36)
  - Timeout: 30s for connection, 60s for tool calls (#34)
  - Log warning if entity extraction returns 0 (#63, #87)
- **MIRROR**: MCP Python SDK ClientSession pattern
- **IMPORTS**: `mcp.ClientSession`, `mcp.client.streamable_http.streamablehttp_client`, `ssl`
- **GOTCHA**: Use `streamablehttp_client` not `sse_client`; `--insecure` für self-signed certs
- **VALIDATE**: Connect to Graphiti MCP, call `get_status`, send test episode

### Task 11: CREATE `src/influxer/progress.py`

- **ACTION**: Create Rich progress display
- **EDGE CASES**: #73, #89, #90
- **IMPLEMENT**:
  - `create_progress()` - Factory for Rich Progress
  - `IngestionProgress` class with:
    - `start_file(filename, total_chunks)`
    - `update_chunk(current_chunk)`
    - `complete_file()`
    - `show_summary(files_processed, chunks_sent, errors)`
    - `show_eta()` - Estimated time remaining (#73)
- **TERMINAL HANDLING**:
  - Rich auto-detects color support (#89)
  - Rich handles piped output gracefully (#90)
  - Force no-color with `NO_COLOR=1` env var
- **MIRROR**: Rich Progress docs
- **IMPORTS**: `rich.progress`, `rich.console`, `rich.table`
- **VALIDATE**: Visual inspection of progress output; test with `| cat`

### Task 12: CREATE `src/influxer/cli.py`

- **ACTION**: Create Typer CLI
- **EDGE CASES**: #33, #40, #52, #55, #65, #66, #88, #91
- **IMPLEMENT**:
  - `app = typer.Typer()`
  - `ingest` command:
    - `path: Path` argument (file to ingest)
    - `--group-id` / `-g` option (default: "main")
    - `--chunk-size` option (default: 2000)
    - `--mcp-url` option (default from config)
    - `--language` option for OCR (default: "eng+deu+spa")
    - `--insecure` flag for self-signed SSL certs (#40)
  - `check-deps` command:
    - Shows status of all system dependencies (#65)
    - Shows installed OCR languages (#66)
    - Pretty table with ✓/✗ status
  - `init` command:
    - Creates `~/.influxer/` directory
    - Prompts for MCP URL (with default)
    - Tests connection
    - Saves to `~/.influxer/config.toml`
  - `smoke-test` command:
    - Tests MCP server connectivity (#33)
    - Tests PDF extraction with sample file
    - Tests EPUB extraction with sample file
    - Shows summary: "Ready to ingest" or lists failures
  - **Path Validation** (#91):
    - Check file exists before any processing
    - Check read permissions (#52)
    - pathlib handles special characters (#55)
  - **Signal Handling** (#88):
    - Register SIGINT/SIGTERM handlers
    - Graceful shutdown: finish current chunk, save state, exit cleanly
    - Message: "Interrupted. Progress saved. Run again to resume."
  - Flow: Validate Path → Check Deps → Connect MCP → Extract → Chunk → Send → Update State
  - **Fail-Fast on MCP**: Test connection BEFORE processing file.
- **ERROR HANDLING**:
  - MCP unreachable → "Cannot connect to Graphiti MCP at {url}. Is the server running?"
  - PDF extraction failed → Show which fallback methods were tried
  - SQLite write error → "Cannot write to state DB at {path}. Check permissions."
  - File not found → "File not found: {path}"
  - Permission denied → "Cannot read file: {path}. Check permissions."
  - All errors: Rich formatted with suggestions for next steps
- **MIRROR**: Typer docs pattern
- **IMPORTS**: `typer`, `signal`, `influxer.deps`, all influxer modules
- **GOTCHA**: Use `asyncio.run()` for async MCP calls; signal handlers need special handling in async
- **VALIDATE**: `influxer --help` shows usage, `influxer check-deps` shows status, Ctrl+C test

### Task 13: CREATE `src/influxer/__init__.py` and test end-to-end

- **ACTION**: Create package init and verify full flow
- **IMPLEMENT**:
  - Export version: `__version__ = "0.1.0"`
  - Export main components
- **VALIDATE**:
  - `influxer ingest test.pdf --group-id test` succeeds
  - Chunks appear in Graphiti (via `get_episodes`)
  - State DB records ingestion

---

## Testing Strategy

### Unit Tests to Write (Phase 4)

| Test File | Test Cases | Validates |
|-----------|------------|-----------|
| `tests/test_extractors.py` | PDF extraction, EPUB extraction, OCR fallback | Text extraction |
| `tests/test_chunker.py` | Chunk sizes, overlap, edge cases | Chunking logic |
| `tests/test_state.py` | DB operations, hash calculation | State management |
| `tests/test_mcp_client.py` | Connection, add_memory, error handling | MCP integration |

### Edge Cases Checklist

- [ ] Empty PDF (no text, no images)
- [ ] Scanned PDF (image-only, needs OCR)
- [ ] PDF with complex layout (tables, columns)
- [ ] Large PDF (1000+ pages)
- [ ] EPUB with nested chapters
- [ ] EPUB with images only
- [ ] Non-UTF8 text encoding
- [ ] MCP server unavailable
- [ ] Network timeout during ingestion

---

## Validation Commands

### Level 1: STATIC_ANALYSIS

```bash
uv run ruff check src/
uv run mypy src/
```

**EXPECT**: Exit 0, no errors

### Level 2: MANUAL_SMOKE_TEST

```bash
# Test PDF extraction
uv run python -c "
from pathlib import Path
from influxer.extractors import extract_text
text = extract_text(Path('test.pdf'))
print(f'Extracted {len(text)} chars')
"

# Test CLI
uv run influxer --help
uv run influxer ingest test.pdf --group-id test
```

**EXPECT**: Text extracted, CLI works

### Level 3: INTEGRATION_TEST

```bash
# Verify chunks in Graphiti
uv run python -c "
import asyncio
from influxer.mcp_client import GraphitiClient

async def check():
    client = GraphitiClient()
    await client.connect('https://graphiti.marakanda.biz/mcp')
    episodes = await client.get_episodes('test')
    print(f'Found {len(episodes)} episodes')

asyncio.run(check())
"
```

**EXPECT**: Episodes found in Graphiti

---

## Acceptance Criteria

- [ ] `influxer ingest file.pdf --group-id main` processes a PDF successfully
- [ ] `influxer ingest file.epub --group-id main` processes an EPUB successfully
- [ ] Scanned/image PDFs are processed via OCR fallback
- [ ] German and English text is correctly extracted
- [ ] Chunks are sent to Graphiti via MCP `add_memory`
- [ ] Progress is displayed during ingestion
- [ ] State is recorded in SQLite for future resume
- [ ] 200-page PDF is fully ingested (Success Metric from PRD)

---

## Completion Checklist

- [ ] All tasks completed in dependency order
- [ ] Each task validated immediately after completion
- [ ] Level 1: Static analysis passes
- [ ] Level 2: Manual smoke test passes
- [ ] Level 3: Integration test passes
- [ ] All acceptance criteria met

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| MCP connection issues | MEDIUM | HIGH | Graceful error handling, retry logic |
| OCR quality on complex scans | MEDIUM | MEDIUM | Configurable DPI, language selection |
| Large PDF memory usage | MEDIUM | MEDIUM | Streaming extraction where possible |
| Graphiti rate limiting | LOW | MEDIUM | Configurable delay between chunks |
| Tesseract not installed | LOW | HIGH | Clear error message with install instructions |

---

## System Dependencies (Cross-Platform)

Before running Influxer, install system dependencies. Use `influxer check-deps` to verify installation.

### macOS (Homebrew)
```bash
brew install tesseract tesseract-lang poppler
```

### Ubuntu/Debian
```bash
sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu tesseract-ocr-spa poppler-utils
```

### Windows (Chocolatey)
```bash
choco install tesseract poppler
```

### Windows (Manual)
1. Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
2. Poppler: https://github.com/oschwartz10612/poppler-windows/releases
3. Add both to PATH

---

## Notes

**Design Decisions:**

1. **MCP over REST**: User explicitly wants abstraction from Graphiti internals. MCP is the stable interface.

2. **pymupdf4llm as primary**: Better Markdown output and word separation than pdfplumber/PyPDF2. Version 0.2.9 adds optional OCR support (`ocr=True` parameter) which could simplify the fallback chain.

3. **OCR as final fallback**: Only triggered when text extraction fails. Configurable language.

4. **SQLite for state**: Simple, local, no additional dependencies. Query-capable for future resume logic.

5. **langchain-text-splitters**: Battle-tested semantic chunking. No need to reinvent.

6. **Reuse Archon code**: PDF/OCR extraction is already production-ready in User's Archon fork.

**Future Considerations:**

- Phase 2 will add batch processing and resume logic using the state DB
- Consider adding `--dry-run` flag to preview chunks without sending
- Consider adding `--verify` flag to check if chunks arrived in Graphiti
