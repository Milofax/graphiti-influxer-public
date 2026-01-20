# Feature: Phase 1 - Web Interface MVP

## Summary

Web Interface (FastAPI Backend + React Frontend) für Upload → Metadaten-Review → Ingestion Flow. Baut auf dem existierenden CLI-Backend auf (Extractors, Chunker, MCP-Client, State-DB). Ermöglicht Drag-and-Drop Upload, Card-basiertes Metadaten-Review mit Inline-Editing, Web-Suche für fehlende Metadaten (OpenLibrary, CrossRef, ISBN.de, Google Books), und Echtzeit-Progress während Ingestion.

## User Story

As a Power-User mit Graphiti-Setup und grosser Dokumenten-Bibliothek
I want to Dokumente über ein Web Interface hochladen, Metadaten reviewen/editieren, und in Graphiti ingestieren
So that ich grössere Mengen an Dokumenten effizient verarbeiten kann ohne CLI-Kenntnisse.

## Problem Statement

Das CLI-Tool ist funktional, aber für Batch-Workflows mit vielen Dateien unpraktisch. Metadaten-Review und -Korrektur sind im Terminal umständlich. Der User braucht eine visuelle Oberfläche mit Card-Layout für "Upload → Review → Ingest" Flow.

## Solution Statement

Ein Web Interface das:
1. FastAPI Backend mit REST-Endpoints für Upload, Metadaten, Ingestion
2. React + TypeScript + Vite Frontend mit modernem UX
3. SSE (Server-Sent Events) für Echtzeit-Progress
4. Wiederverwendung des existierenden Backend-Codes (Extractors, Chunker, MCP-Client, State-DB)
5. Web-Suche für fehlende Metadaten via strukturierte APIs

## Metadata

| Field            | Value                                             |
| ---------------- | ------------------------------------------------- |
| Type             | NEW_CAPABILITY                                    |
| Complexity       | HIGH                                              |
| Systems Affected | FastAPI Backend, React Frontend, API-Integration, Docker |
| Dependencies     | fastapi>=0.115.0, uvicorn>=0.34.0, python-multipart>=0.0.20, sse-starlette>=2.2.0, react, vite, typescript, tailwindcss, tanstack-query, react-dropzone |
| Estimated Tasks  | 22                                                |

---

## UX Design

### Before State

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                              BEFORE STATE                                      ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║   ┌─────────────┐                                                             ║
║   │  Terminal   │ ──────► influxer ingest file.pdf ──────► Single file only   ║
║   │  (CLI)      │         --group-id main                                     ║
║   └─────────────┘                                                             ║
║                                                                               ║
║   USER_FLOW: Datei für Datei via CLI-Befehle verarbeiten                      ║
║   PAIN_POINT: Keine Übersicht, kein Batch, keine Metadaten-Korrektur          ║
║   DATA_FLOW: Terminal → CLI → Extractor → Chunker → MCP                       ║
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
║   │   Browser   │    │  Web UI     │    │  FastAPI    │    │   Graphiti  │   ║
║   │             │───►│  (React)    │───►│  Backend    │───►│ MCP Server  │   ║
║   │             │    │             │    │             │    │             │   ║
║   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘   ║
║         │                  │                  │                  │            ║
║         │            ┌─────┴─────┐      ┌─────┴─────┐      ┌─────┴─────┐     ║
║         │            │ Drag&Drop │      │ Extraktor │      │ Knowledge │     ║
║         │            │ + Review  │      │ + Chunker │      │   Graph   │     ║
║         │            │ + Search  │      │ + MCP     │      │           │     ║
║         │            └───────────┘      └───────────┘      └───────────┘     ║
║                                                                               ║
║   USER_FLOW: Upload → Review Cards → Edit Metadata → Search → Ingest All     ║
║   VALUE_ADD: Batch-Upload, Visual Review, Web-Suche für fehlende Daten       ║
║   DATA_FLOW: Browser → React → FastAPI → Extractor → Chunker → MCP → Graphiti║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

### Interaction Changes

| Location | Before | After | User Impact |
|----------|--------|-------|-------------|
| Upload | CLI single file | Drag-and-Drop, Multiple Files | Batch-Upload möglich |
| Metadaten | Keine Korrektur | Card-Layout, Inline-Edit | Fehlende Daten ergänzen |
| Search | N/A | OpenLibrary, CrossRef, ISBN.de | Auto-Fill von ISBN/DOI |
| Progress | Terminal-Spinner | Visual Progress-Bar, SSE | Echtzeit-Feedback |
| Review | N/A | Pflichtfeld-Validation | Ingestion nur wenn komplett |

---

## Mandatory Reading

**CRITICAL: Implementation agent MUST read these files before starting any task:**

| Priority | File | Lines | Why Read This |
|----------|------|-------|---------------|
| P0 | `src/influxer/mcp_client.py` | all | MCP integration patterns, ChunkMetadata |
| P0 | `src/influxer/extractors/__init__.py` | all | Extractor API: `extract_text()` |
| P0 | `src/influxer/chunker.py` | all | Chunking API: `chunk_text()`, `estimate_chunk_count()` |
| P0 | `src/influxer/state.py` | all | State-DB API: `StateDB`, `get_file_hash()` |
| P1 | `src/influxer/config.py` | all | Configuration patterns |
| P1 | `src/influxer/progress.py` | all | Progress patterns for SSE adaptation |
| P2 | `src/influxer/deps.py` | all | Dependency checking for health endpoint |
| P2 | `src/influxer/extractors/pdf.py` | 1-100 | PDF metadata extraction patterns |
| P2 | `src/influxer/extractors/epub.py` | 1-100 | EPUB metadata extraction patterns |

**External Documentation:**

| Source | Section | Why Needed |
|--------|---------|------------|
| [FastAPI](https://fastapi.tiangolo.com/) | File Upload, Background Tasks | Multipart upload, async processing |
| [SSE-Starlette](https://github.com/sysid/sse-starlette) | EventSourceResponse | Real-time progress |
| [React + Vite](https://vitejs.dev/guide/) | Project Setup | Frontend build |
| [TanStack Query](https://tanstack.com/query/latest) | Mutations, SSE | Data fetching, optimistic updates |
| [react-dropzone](https://react-dropzone.js.org/) | Drop Zone | File upload UI |
| [OpenLibrary API](https://openlibrary.org/developers/api) | Books API | ISBN/Title search |
| [CrossRef API](https://api.crossref.org/) | Works | DOI lookup |

---

## Patterns to Mirror

**EXISTING_MCP_CLIENT:**

```python
# SOURCE: src/influxer/mcp_client.py:115-200
# REUSE THIS - Don't reimplement:

@dataclass
class ChunkMetadata:
    file_hash: str
    file_path: str
    chunk_index: int
    total_chunks: int
    source_description: str | None = None

class GraphitiClient:
    async def connect(self) -> None
    async def add_memory(self, content: str, group_id: str, metadata: ChunkMetadata) -> str | None
    async def get_episodes(self, group_id: str, max_episodes: int = 100) -> list[dict]
    async def get_status(self) -> dict[str, Any]
```

**EXISTING_EXTRACTOR:**

```python
# SOURCE: src/influxer/extractors/__init__.py:50-80
# REUSE THIS - extract text + detect format:

from influxer.extractors import extract_text, detect_format
from influxer.extractors.pdf import extract_metadata_from_pdf
from influxer.extractors.epub import extract_metadata_from_epub

text = extract_text(file_path)  # Returns full text
file_format = detect_format(file_path)  # "pdf" | "epub" | None
```

**EXISTING_CHUNKER:**

```python
# SOURCE: src/influxer/chunker.py:90-150
# REUSE THIS - chunk text:

from influxer.chunker import chunk_text, estimate_chunk_count

chunks = chunk_text(text, chunk_size=2000, chunk_overlap=200)
estimated = estimate_chunk_count(len(text), chunk_size=2000, chunk_overlap=200)
```

**EXISTING_STATE_DB:**

```python
# SOURCE: src/influxer/state.py:200-350
# REUSE THIS - file tracking:

from influxer.state import StateDB, get_file_hash

db = StateDB()
file_hash = get_file_hash(file_path)
is_done = db.is_file_ingested(file_hash, group_id)
ingestion_id = db.start_ingestion(file_hash, file_path, group_id, chunk_count)
db.update_progress(ingestion_id, chunks_sent, episode_uuid)
db.complete_ingestion(ingestion_id)
```

**FASTAPI_FILE_UPLOAD:**

```python
# PATTERN: FastAPI multipart file upload
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Graphiti Influxer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    # Save to temp, extract metadata, return preview
    pass
```

**SSE_PATTERN:**

```python
# PATTERN: Server-Sent Events for progress
from sse_starlette.sse import EventSourceResponse
import asyncio

async def progress_generator(file_id: str):
    while True:
        progress = get_progress(file_id)
        yield {"event": "progress", "data": json.dumps(progress)}
        if progress["status"] == "completed":
            break
        await asyncio.sleep(0.5)

@app.get("/api/ingest/{file_id}/progress")
async def stream_progress(file_id: str):
    return EventSourceResponse(progress_generator(file_id))
```

**REACT_DROPZONE:**

```typescript
// PATTERN: react-dropzone with TypeScript
import { useDropzone } from 'react-dropzone';

interface FileWithPreview extends File {
  preview: string;
}

function UploadZone() {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'application/epub+zip': ['.epub'],
    },
    onDrop: (acceptedFiles) => {
      // Handle files
    },
  });

  return (
    <div {...getRootProps()} className={isDragActive ? 'border-blue-500' : ''}>
      <input {...getInputProps()} />
      {/* UI */}
    </div>
  );
}
```

**TANSTACK_MUTATION:**

```typescript
// PATTERN: TanStack Query mutation with optimistic update
import { useMutation, useQueryClient } from '@tanstack/react-query';

const updateMetadata = useMutation({
  mutationFn: (data: { fileId: string; metadata: Metadata }) =>
    fetch(`/api/files/${data.fileId}`, {
      method: 'PATCH',
      body: JSON.stringify(data.metadata),
    }),
  onMutate: async (newData) => {
    // Optimistic update
    queryClient.setQueryData(['file', newData.fileId], old => ({
      ...old,
      ...newData.metadata,
    }));
  },
});
```

---

## Files to Change

### Backend (FastAPI)

| File                             | Action | Justification                            |
| -------------------------------- | ------ | ---------------------------------------- |
| `src/influxer/api/__init__.py`   | CREATE | API package init                         |
| `src/influxer/api/main.py`       | CREATE | FastAPI app, CORS, lifespan              |
| `src/influxer/api/routes/upload.py` | CREATE | File upload endpoint                  |
| `src/influxer/api/routes/files.py` | CREATE | File CRUD (list, get, patch, delete)  |
| `src/influxer/api/routes/search.py` | CREATE | Metadata search (OpenLibrary, CrossRef) |
| `src/influxer/api/routes/ingest.py` | CREATE | Ingestion endpoint + SSE progress     |
| `src/influxer/api/routes/health.py` | CREATE | Health check, MCP status              |
| `src/influxer/api/models.py`     | CREATE | Pydantic models for API                  |
| `src/influxer/api/services/metadata_search.py` | CREATE | OpenLibrary, CrossRef, ISBN.de, Google Books |
| `src/influxer/api/services/file_processor.py` | CREATE | Background processing orchestration  |
| `src/influxer/extractors/metadata.py` | CREATE | Unified metadata extraction from PDF/EPUB |
| `pyproject.toml`                 | UPDATE | Add FastAPI dependencies                 |

### Frontend (React)

| File                             | Action | Justification                            |
| -------------------------------- | ------ | ---------------------------------------- |
| `frontend/package.json`          | CREATE | Frontend dependencies                    |
| `frontend/vite.config.ts`        | CREATE | Vite configuration                       |
| `frontend/tsconfig.json`         | CREATE | TypeScript configuration                 |
| `frontend/tailwind.config.js`    | CREATE | Tailwind CSS configuration               |
| `frontend/index.html`            | CREATE | HTML entry point                         |
| `frontend/src/main.tsx`          | CREATE | React entry point                        |
| `frontend/src/App.tsx`           | CREATE | Main app component                       |
| `frontend/src/components/UploadZone.tsx` | CREATE | Drag-and-drop upload              |
| `frontend/src/components/FileCard.tsx` | CREATE | File card with metadata editing      |
| `frontend/src/components/MetadataForm.tsx` | CREATE | Inline metadata form              |
| `frontend/src/components/SearchButton.tsx` | CREATE | Metadata search trigger           |
| `frontend/src/components/ProgressBar.tsx` | CREATE | Ingestion progress display        |
| `frontend/src/components/GroupIdSelector.tsx` | CREATE | Group ID dropdown/input        |
| `frontend/src/api/client.ts`     | CREATE | API client with TanStack Query           |
| `frontend/src/types/index.ts`    | CREATE | TypeScript types                         |
| `frontend/src/hooks/useSSE.ts`   | CREATE | SSE hook for progress                    |

### Docker

| File                             | Action | Justification                            |
| -------------------------------- | ------ | ---------------------------------------- |
| `Dockerfile`                     | CREATE | Multi-stage build (backend + frontend)   |
| `docker-compose.yml`             | CREATE | Development compose                      |
| `.dockerignore`                  | CREATE | Ignore unnecessary files                 |

---

## NOT Building (Scope Limits)

Explicit exclusions to prevent scope creep:

- **Batch-Presets** - Phase 2 (alle als "Buch", alle gleiche group_id)
- **History/Recent group_ids** - Phase 2
- **Concurrent Edit Locking** - Phase 2 (#118)
- **API-Key-Konfiguration** für höhere Limits - Phase 2
- **Markdown Support** - Phase 3
- **CLI Headless-Mode** - Phase 5
- **User Authentication** - Won't build (single-user tool)
- **Database Migration** - Won't build (SQLite schema is stable)

---

## Edge Cases (Phase 1 - 90 total)

**Reference: [edge-cases.md](../edge-cases.md)**

### Web Interface Specific (#109-#120)

| # | Case | Mitigation | Task |
|---|------|------------|------|
| 109 | File Upload > 100MB | Server-side limit (200MB) + Frontend check + Clear Error | Task 3, 9 |
| 110 | Upload-Abbruch (Tab closed) | Cleanup bei Session-Timeout (1h) | Task 3 |
| 111 | Concurrent Uploads (10+ files) | Queue-System + Max 5 concurrent | Task 3 |
| 112 | SSE Connection Drop | Polling-Fallback + Reconnect | Task 5, 19 |
| 113 | Session Timeout | SQLite persistence + Warning | Task 3 |
| 114 | Browser ohne JavaScript | Clear Error "JavaScript required" | Task 9 |
| 115 | Mobile Browser (Touch) | Click-Fallback (File-Input) | Task 9 |
| 116 | CORS-Probleme | CORS-Config in FastAPI | Task 2 |
| 117 | Slow Network | Progress-Feedback + Retry | Task 5, 19 |
| 119 | Ingest bei unvollständigen Feldern | Frontend + Backend Validation | Task 5, 14 |
| 120 | Group-ID neue eingeben | Validation + Autocomplete | Task 17 |

### Metadaten-Suche (#121-#134)

| # | Case | Mitigation | Task |
|---|------|------------|------|
| 121 | ISBN ungültiges Format | ISBN-Validation (10/13-stellig) | Task 6 |
| 122 | DOI ungültiges Format | DOI-Validation (10.xxxx/...) | Task 6 |
| 123 | Weder ISBN noch DOI | Titel-Suche anbieten | Task 6, 15 |
| 124 | OpenLibrary: Kein Ergebnis | Google Books Fallback | Task 6 |
| 125 | OpenLibrary: Mehrere Ergebnisse | Liste anzeigen, User wählt | Task 6, 15 |
| 126 | OpenLibrary Rate-Limiting | Backoff + Clear Error | Task 6 |
| 127 | Google Books Limit (100/Tag) | Clear Error + Hinweis | Task 6 |
| 128 | CrossRef: DOI nicht gefunden | Clear Error + manuell | Task 6 |
| 129 | CrossRef Rate-Limiting | Backoff + Clear Error | Task 6 |
| 130 | ISBN.de: Kein Ergebnis | OpenLibrary Fallback | Task 6 |
| 131 | ISBN.de: API-Änderung | Defensive Parsing | Task 6 |
| 132 | API nicht erreichbar | Timeout + Clear Error | Task 6 |
| 133 | Suche während anderer Suche | Debounce + Cancel | Task 15 |
| 134 | Auto-Fill überschreibt User | Bestätigung vor Überschreiben | Task 15 |

### Metadaten/Entity-Types (#97-#108)

| # | Case | Mitigation | Task |
|---|------|------------|------|
| 97 | Metadaten komplett leer | UI zeigt "Missing" + User-Prompt | Task 11, 14 |
| 98 | Metadaten unvollständig | Pflichtfeld-Highlighting | Task 11, 14 |
| 99 | Metadaten falsch/veraltet | User kann überschreiben | Task 4, 14 |
| 100 | Jahr ≠ Publikationsjahr | Warning wenn Jahr > heute oder < 1800 | Task 7, 14 |
| 101 | ISBN nicht in Metadaten | Optional: Search Button | Task 15 |
| 102 | Entity-Type unklar | Default + Dropdown Override | Task 4, 12 |
| 103 | Pflichtfelder nicht ermittelbar | User-Prompt + Skip-Validation | Task 5, 14 |
| 106 | Titel aus Content extrahieren | H1 > metadata.title | Task 7 |
| 107 | EPUB identifier keine ISBN | ISBN-Pattern prüfen | Task 7 |
| 108 | Multi-Author | Comma-separated | Task 7, 14 |

### Inherited from CLI (#1-#96 relevant subset)

Alle PDF/EPUB/OCR/MCP Edge Cases werden vom existierenden Backend gehandled.
Siehe [phase-1-pdf-epub-core.plan.md](../completed/phase-1-pdf-epub-core.plan.md) für Details.

---

## Step-by-Step Tasks

Execute in order. Each task is atomic and independently verifiable.

### BACKEND TASKS

### Task 1: UPDATE `pyproject.toml` - Add FastAPI dependencies

- **ACTION**: Add web framework dependencies
- **IMPLEMENT**:
  ```toml
  dependencies = [
      # ... existing deps ...
      "fastapi>=0.115.0",
      "uvicorn[standard]>=0.34.0",
      "python-multipart>=0.0.20",
      "sse-starlette>=2.2.0",
      "aiofiles>=24.1.0",
  ]

  [project.scripts]
  influxer = "influxer.cli:app"
  influxer-api = "influxer.api.main:run"
  ```
- **GOTCHA**: `python-multipart` is required for file uploads in FastAPI
- **VALIDATE**: `uv sync && uv run python -c "import fastapi; print(fastapi.__version__)"`

### Task 2: CREATE `src/influxer/api/main.py` - FastAPI app setup

- **ACTION**: Create main FastAPI application
- **EDGE CASES**: #116 (CORS)
- **IMPLEMENT**:
  - FastAPI app with metadata (title, version, description)
  - CORS middleware for localhost:5173 (Vite) + configurable origins
  - Lifespan context manager for startup/shutdown
  - Include all routers (upload, files, search, ingest, health)
  - Global exception handlers for custom errors
  - `run()` function for uvicorn entry point
- **IMPORTS**: `fastapi`, `uvicorn`, `contextlib.asynccontextmanager`
- **MIRROR**: FastAPI docs pattern
- **GOTCHA**: Use `@asynccontextmanager` for lifespan, not deprecated `on_event`
- **VALIDATE**: `uv run influxer-api --help` shows uvicorn options

### Task 3: CREATE `src/influxer/api/routes/upload.py` - File upload endpoint

- **ACTION**: Create file upload with metadata extraction
- **EDGE CASES**: #109, #110, #111, #113
- **IMPLEMENT**:
  - `POST /api/upload` - Accept multipart file upload
  - Save to temp directory with UUID filename
  - Extract text using `influxer.extractors.extract_text()`
  - Extract metadata using new `extract_metadata()` function
  - Determine entity_type based on metadata
  - Calculate file_hash
  - Check if already ingested via StateDB
  - Store in session (SQLite table: `upload_session`)
  - Return file preview with metadata
  - Max file size: 200MB (#109)
  - Concurrent upload limit: 5 (#111)
  - Session timeout cleanup: 1 hour (#110, #113)
- **RESPONSE_MODEL**:
  ```python
  class UploadResponse(BaseModel):
      file_id: str  # UUID
      filename: str
      file_size: int
      file_hash: str
      format: str  # "pdf" | "epub"
      text_length: int
      estimated_chunks: int
      metadata: FileMetadata
      already_ingested: bool
      entity_type: str  # "book" | "article" | "rfc"
      validation: ValidationResult
  ```
- **IMPORTS**: `fastapi.UploadFile`, `influxer.extractors`, `influxer.state`, `influxer.chunker.estimate_chunk_count`
- **GOTCHA**: Use `aiofiles` for async file operations; temp files need cleanup
- **VALIDATE**: `curl -X POST -F "file=@test.pdf" http://localhost:8000/api/upload`

### Task 4: CREATE `src/influxer/api/routes/files.py` - File CRUD endpoints

- **ACTION**: Create endpoints for file management
- **EDGE CASES**: #99, #102
- **IMPLEMENT**:
  - `GET /api/files` - List all files in current session
  - `GET /api/files/{file_id}` - Get single file details
  - `PATCH /api/files/{file_id}` - Update metadata (inline edit)
  - `DELETE /api/files/{file_id}` - Remove from session (cleanup temp)
  - Update `upload_session` table for all operations
  - Return validation status after each update
- **PATCH_MODEL**:
  ```python
  class MetadataUpdate(BaseModel):
      title: str | None = None
      author: str | None = None
      year: int | None = None
      isbn: str | None = None
      doi: str | None = None
      entity_type: str | None = None
      source_type: str | None = None  # Non-Fiction, Academic, etc.
      # ... other fields
  ```
- **VALIDATE**: `curl http://localhost:8000/api/files`

### Task 5: CREATE `src/influxer/api/routes/ingest.py` - Ingestion endpoint + SSE

- **ACTION**: Create ingestion endpoint with real-time progress
- **EDGE CASES**: #112, #117, #119, #103
- **IMPLEMENT**:
  - `POST /api/ingest` - Start ingestion for selected files
    - Validate all files have required fields (#119)
    - Return 400 if validation fails with details
    - Start background task for ingestion
    - Return ingestion_id for progress tracking
  - `GET /api/ingest/{ingestion_id}/progress` - SSE progress stream
    - Yield progress events every 500ms
    - Include: file_id, chunk_index, total_chunks, status, error
    - Close stream when completed
  - `POST /api/ingest/{ingestion_id}/cancel` - Cancel ingestion
  - Use existing `GraphitiClient`, `chunk_text()`, `StateDB`
- **SSE_EVENTS**:
  ```python
  {"event": "start", "data": {"file_id": "...", "total_chunks": 50}}
  {"event": "progress", "data": {"file_id": "...", "chunk": 10, "total": 50}}
  {"event": "chunk_done", "data": {"file_id": "...", "chunk": 10, "uuid": "..."}}
  {"event": "file_done", "data": {"file_id": "...", "chunks_sent": 50}}
  {"event": "error", "data": {"file_id": "...", "error": "..."}}
  {"event": "complete", "data": {"files_processed": 3, "total_chunks": 150}}
  ```
- **IMPORTS**: `sse_starlette.sse.EventSourceResponse`, `influxer.mcp_client`, `influxer.chunker`, `influxer.state`
- **GOTCHA**: SSE requires `text/event-stream` content type; use generator pattern
- **VALIDATE**: `curl -N http://localhost:8000/api/ingest/123/progress`

### Task 6: CREATE `src/influxer/api/services/metadata_search.py` - External API search

- **ACTION**: Create metadata search service for OpenLibrary, CrossRef, ISBN.de, Google Books
- **EDGE CASES**: #121-#134
- **IMPLEMENT**:
  - `class MetadataSearchService`:
    - `async search_by_isbn(isbn: str) -> list[SearchResult]`
      - Validate ISBN format (10 or 13 digits) (#121)
      - If DE ISBN (978-3-...) → ISBN.de first, then OpenLibrary (#130)
      - Otherwise → OpenLibrary first, then Google Books (#124)
    - `async search_by_doi(doi: str) -> SearchResult | None`
      - Validate DOI format (10.xxxx/...) (#122)
      - CrossRef API lookup (#128)
    - `async search_by_title(title: str, author: str | None) -> list[SearchResult]`
      - OpenLibrary search API (#123)
      - Return multiple results for user selection (#125)
    - `async _call_openlibrary(query: str) -> list[dict]`
    - `async _call_crossref(doi: str) -> dict | None`
    - `async _call_isbn_de(isbn: str) -> dict | None` (scrape or API)
    - `async _call_google_books(query: str) -> list[dict]`
  - Rate limiting with exponential backoff (#126, #127, #129)
  - Timeout handling (#132)
- **RESPONSE_MODEL**:
  ```python
  class SearchResult(BaseModel):
      source: str  # "openlibrary" | "crossref" | "isbn_de" | "google_books"
      title: str
      author: str | None
      year: int | None
      isbn: str | None
      doi: str | None
      publisher: str | None
      confidence: float  # 0.0-1.0
  ```
- **IMPORTS**: `httpx`, `asyncio`, `re` (for validation)
- **GOTCHA**: ISBN.de may require scraping; Google Books has 100/day limit without API key
- **VALIDATE**: Unit test with known ISBNs/DOIs

### Task 7: CREATE `src/influxer/extractors/metadata.py` - Unified metadata extraction

- **ACTION**: Create unified metadata extraction from PDF/EPUB
- **EDGE CASES**: #97, #98, #100, #106, #107, #108
- **IMPLEMENT**:
  - `extract_metadata(file_path: Path) -> FileMetadata`
    - Detect format, delegate to PDF/EPUB extractor
    - Normalize and clean metadata
    - Handle multi-author (#108)
    - Validate year (#100): warn if > current_year or < 1800
    - Fallback to content-based extraction (#106): H1 as title
    - Validate EPUB identifier as ISBN (#107)
  - `class FileMetadata(BaseModel)`:
    - title, author, year, isbn, doi
    - publisher, language, subject
    - creation_date (PDF creation, not publication)
    - raw_metadata (original dict for debugging)
- **PDF_METADATA** (from pymupdf):
  - `metadata.title`, `metadata.author`, `metadata.creationDate`
- **EPUB_METADATA** (from ebooklib):
  - `DC.title`, `DC.creator`, `DC.date`, `DC.identifier`
- **IMPORTS**: `pymupdf`, `ebooklib`, `influxer.extractors.pdf`, `influxer.extractors.epub`
- **GOTCHA**: PDF creationDate is often PDF creation, not book publication date
- **VALIDATE**: Extract metadata from sample.pdf and sample.epub

### Task 8: CREATE `src/influxer/api/routes/search.py` - Search endpoint

- **ACTION**: Create metadata search endpoint
- **IMPLEMENT**:
  - `POST /api/search-metadata` - Search for metadata
    - Input: isbn | doi | title+author
    - Route to appropriate search method
    - Return list of results for user selection
  - `POST /api/files/{file_id}/apply-search-result` - Apply selected result
    - Update file metadata with search result
    - Return updated file with validation
- **REQUEST_MODEL**:
  ```python
  class SearchRequest(BaseModel):
      isbn: str | None = None
      doi: str | None = None
      title: str | None = None
      author: str | None = None
  ```
- **VALIDATE**: `curl -X POST -d '{"isbn":"978-0-06-112008-4"}' http://localhost:8000/api/search-metadata`

### Task 9: CREATE `src/influxer/api/routes/health.py` - Health endpoints

- **ACTION**: Create health and status endpoints
- **EDGE CASES**: #114
- **IMPLEMENT**:
  - `GET /api/health` - Basic health check
  - `GET /api/mcp/status` - MCP server status (uses `GraphitiClient.get_status()`)
  - `GET /api/dependencies` - System dependencies (uses `deps.validate_dependencies()`)
  - `GET /api/config` - Current configuration (non-sensitive)
- **VALIDATE**: `curl http://localhost:8000/api/health`

### Task 10: CREATE `src/influxer/api/models.py` - Pydantic models

- **ACTION**: Create all Pydantic models for API
- **IMPLEMENT**:
  - `FileMetadata` - Extracted metadata
  - `ValidationResult` - Validation status with missing fields
  - `UploadResponse` - Upload endpoint response
  - `FileResponse` - File details response
  - `MetadataUpdate` - PATCH request body
  - `SearchRequest` / `SearchResult` - Search API
  - `IngestRequest` / `IngestResponse` - Ingestion API
  - `ProgressEvent` - SSE event model
  - `HealthResponse` / `MCPStatusResponse` - Health API
  - Entity types enum: `book`, `article`, `rfc`
  - Source types enum: `non_fiction`, `academic`, `journalism`, `opinion`, `fiction`, `unknown`
- **GOTCHA**: Use `from __future__ import annotations` for forward refs
- **VALIDATE**: `uv run python -c "from influxer.api.models import *"`

### Task 11: CREATE `src/influxer/api/__init__.py` - Package init

- **ACTION**: Create API package init
- **IMPLEMENT**: Export main app and version
- **VALIDATE**: `from influxer.api import app`

---

### FRONTEND TASKS

### Task 12: SETUP Frontend project structure

- **ACTION**: Initialize React + TypeScript + Vite project
- **IMPLEMENT**:
  ```bash
  cd /Volumes/DATEN/Coding/graphiti-influxer
  npm create vite@latest frontend -- --template react-ts
  cd frontend
  npm install
  npm install -D tailwindcss postcss autoprefixer
  npx tailwindcss init -p
  npm install @tanstack/react-query react-dropzone lucide-react
  ```
- **FILES**:
  - `frontend/package.json` - Dependencies
  - `frontend/vite.config.ts` - Proxy to backend
  - `frontend/tsconfig.json` - TypeScript config
  - `frontend/tailwind.config.js` - Tailwind config
  - `frontend/src/index.css` - Tailwind imports
- **VITE_CONFIG** (proxy):
  ```typescript
  export default defineConfig({
    server: {
      proxy: {
        '/api': 'http://localhost:8000',
      },
    },
  });
  ```
- **VALIDATE**: `cd frontend && npm run dev` opens localhost:5173

### Task 13: CREATE `frontend/src/types/index.ts` - TypeScript types

- **ACTION**: Create TypeScript types matching backend models
- **IMPLEMENT**:
  ```typescript
  export interface FileMetadata {
    title: string | null;
    author: string | null;
    year: number | null;
    isbn: string | null;
    doi: string | null;
    publisher: string | null;
    language: string | null;
  }

  export type EntityType = 'book' | 'article' | 'rfc';
  export type SourceType = 'non_fiction' | 'academic' | 'journalism' | 'opinion' | 'fiction' | 'unknown';

  export interface FileItem {
    file_id: string;
    filename: string;
    file_size: number;
    format: 'pdf' | 'epub';
    text_length: number;
    estimated_chunks: number;
    metadata: FileMetadata;
    entity_type: EntityType;
    source_type: SourceType | null;
    validation: ValidationResult;
    already_ingested: boolean;
  }

  export interface ValidationResult {
    is_valid: boolean;
    missing_fields: string[];
    warnings: string[];
  }

  export interface SearchResult {
    source: string;
    title: string;
    author: string | null;
    year: number | null;
    isbn: string | null;
    doi: string | null;
    confidence: number;
  }

  export interface ProgressEvent {
    event: string;
    file_id?: string;
    chunk?: number;
    total?: number;
    error?: string;
  }
  ```
- **VALIDATE**: TypeScript compiles without errors

### Task 14: CREATE `frontend/src/api/client.ts` - API client

- **ACTION**: Create API client with TanStack Query
- **IMPLEMENT**:
  - `uploadFile(file: File): Promise<FileItem>`
  - `getFiles(): Promise<FileItem[]>`
  - `updateFileMetadata(fileId: string, metadata: Partial<FileMetadata>): Promise<FileItem>`
  - `deleteFile(fileId: string): Promise<void>`
  - `searchMetadata(query: SearchRequest): Promise<SearchResult[]>`
  - `applySearchResult(fileId: string, result: SearchResult): Promise<FileItem>`
  - `startIngestion(fileIds: string[], groupId: string): Promise<{ ingestion_id: string }>`
  - `getHealth(): Promise<HealthResponse>`
  - Query hooks: `useFiles()`, `useHealth()`, etc.
  - Mutation hooks: `useUploadFile()`, `useUpdateMetadata()`, `useStartIngestion()`
- **ERROR_HANDLING**: Show toast on error, retry on network failure
- **VALIDATE**: API calls work in browser DevTools

### Task 15: CREATE `frontend/src/components/UploadZone.tsx` - Drag-and-drop upload

- **ACTION**: Create upload zone component
- **EDGE CASES**: #109, #115, #134
- **IMPLEMENT**:
  - react-dropzone integration
  - Accept: PDF, EPUB only
  - Max size: 200MB (#109)
  - Visual feedback: drag active, upload progress
  - Click fallback for mobile (#115)
  - Multiple file support
  - On drop → call `uploadFile()` for each file
  - Show upload progress per file
- **UI**:
  ```
  ┌──────────────────────────────────────────────────────────┐
  │                                                          │
  │         📁 Drop files here or click to upload            │
  │              PDF, EPUB supported (max 200MB)             │
  │                                                          │
  └──────────────────────────────────────────────────────────┘
  ```
- **VALIDATE**: Drag PDF onto zone, see it in file list

### Task 16: CREATE `frontend/src/components/FileCard.tsx` - File card with metadata

- **ACTION**: Create file card component with inline editing
- **EDGE CASES**: #97, #98, #102, #133, #134
- **IMPLEMENT**:
  - Display: filename, format icon, size, estimated chunks
  - Metadata fields: title, author, year (inline editable)
  - Entity-Type dropdown (book, article, rfc)
  - Source-Type dropdown (required) with warning for opinion/fiction
  - Validation status indicator (green ✓ / red ⚠)
  - Missing field highlighting
  - Search button (triggers search modal)
  - Delete button
  - Checkbox for selection
  - Optimistic UI updates (#134)
- **UI**:
  ```
  ┌─────────────────┐
  │ 📕              │
  │ Deep Work       │
  │ ─────────────── │
  │ Autor: Cal N... │  ← Click to edit
  │ Jahr:  2016     │  ← Click to edit
  │ Type:  Buch  ▼  │  ← Dropdown
  │ Trust: Sachb.▼  │  ← Required dropdown
  │ ─────────────── │
  │ ✓ Ready        │  ← Validation status
  │ [🔍 Search]     │  ← Search button
  └─────────────────┘
  ```
- **VALIDATE**: Edit metadata, see validation update

### Task 17: CREATE `frontend/src/components/GroupIdSelector.tsx` - Group ID selector

- **ACTION**: Create group ID input with validation
- **EDGE CASES**: #59, #120
- **IMPLEMENT**:
  - Text input with validation (alphanumeric + hyphen)
  - Default: "main"
  - Autocomplete from known group_ids (future: from API)
  - Show validation error for invalid format
- **VALIDATE**: Type invalid group_id, see error

### Task 18: CREATE `frontend/src/components/SearchModal.tsx` - Metadata search

- **ACTION**: Create search modal for metadata lookup
- **EDGE CASES**: #123, #125, #133, #134
- **IMPLEMENT**:
  - Triggered by Search button on FileCard
  - Pre-fill with existing ISBN/DOI/title
  - Search button → show loading → show results
  - Display multiple results as cards (#125)
  - User clicks result → confirm → apply (#134)
  - Debounce input for title search (#133)
- **VALIDATE**: Search ISBN, see results, apply to file

### Task 19: CREATE `frontend/src/hooks/useSSE.ts` - SSE hook for progress

- **ACTION**: Create hook for Server-Sent Events
- **EDGE CASES**: #112, #117
- **IMPLEMENT**:
  - `useIngestionProgress(ingestionId: string | null)`
  - Connect to SSE endpoint when ingestionId is set
  - Parse events, update state
  - Auto-reconnect on connection drop (#112)
  - Cleanup on unmount
  - Return: `{ events, isConnected, error }`
- **VALIDATE**: Start ingestion, see progress updates

### Task 20: CREATE `frontend/src/components/ProgressBar.tsx` - Ingestion progress

- **ACTION**: Create progress display component
- **IMPLEMENT**:
  - Show overall progress: files processed / total
  - Show current file progress: chunks sent / total
  - Show rate: chunks/minute
  - Show errors if any
  - "Cancel" button
- **UI**:
  ```
  ─────────────────── PROGRESS ────────────────────────────
  ████████████░░░░░░░░  3/10 files | 47/120 chunks
  Current: Deep Work.pdf - Sending chunk 12/31
  MCP: ✓ Connected | Rate: 2.3 eps/min
  [Cancel]
  ```
- **VALIDATE**: Start ingestion, see progress bar update

### Task 21: CREATE `frontend/src/App.tsx` - Main app component

- **ACTION**: Create main app with full layout
- **IMPLEMENT**:
  - Header with title and Group-ID selector
  - UploadZone
  - File cards grid
  - Batch action buttons: "Select All", "Ingest Selected", "Ingest All"
  - "Ingest All" disabled if any validation fails
  - Progress section (visible during ingestion)
  - Summary section (after ingestion)
  - TanStack QueryClientProvider
- **LAYOUT** (matches PRD wireframe):
  ```
  ┌────────────────────────────────────────────────────────────────┐
  │  GRAPHITI INFLUXER                          [Group: main ▼]    │
  ├────────────────────────────────────────────────────────────────┤
  │  [UploadZone]                                                  │
  │  ─────────────────── QUEUED FILES ───────────────────────────  │
  │  [FileCard] [FileCard] [FileCard] ...                          │
  │  ───────────────────────────────────────────────────────────── │
  │  [□ Select All]                [Ingest Selected] [Ingest All]  │
  │  ─────────────────── PROGRESS ──────────────────────────────── │
  │  [ProgressBar]                                                 │
  └────────────────────────────────────────────────────────────────┘
  ```
- **VALIDATE**: Full flow: upload → edit → search → ingest

---

### DOCKER TASKS

### Task 22: CREATE Docker configuration

- **ACTION**: Create Dockerfile and docker-compose.yml
- **IMPLEMENT**:
  - **Dockerfile**: Multi-stage build
    - Stage 1: Build frontend (node:20-alpine)
    - Stage 2: Python runtime (python:3.12-slim)
    - Copy frontend dist to Python static files
    - Install system deps (tesseract, poppler)
    - Install Python deps with uv
    - Serve frontend via FastAPI StaticFiles
  - **docker-compose.yml**: Development compose
    - Service: influxer (build from Dockerfile)
    - Ports: 8000:8000
    - Volumes: ./data:/app/data (for SQLite persistence)
    - Environment: INFLUXER_MCP_URL
  - **.dockerignore**: Exclude .venv, node_modules, __pycache__, .git
- **DOCKERFILE**:
  ```dockerfile
  # Stage 1: Build frontend
  FROM node:20-alpine AS frontend-build
  WORKDIR /app/frontend
  COPY frontend/package*.json ./
  RUN npm ci
  COPY frontend/ ./
  RUN npm run build

  # Stage 2: Python runtime
  FROM python:3.12-slim

  # Install system dependencies
  RUN apt-get update && apt-get install -y \
      tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu tesseract-ocr-spa \
      poppler-utils \
      && rm -rf /var/lib/apt/lists/*

  # Install uv
  COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

  WORKDIR /app
  COPY pyproject.toml uv.lock ./
  RUN uv sync --frozen

  COPY src/ ./src/
  COPY --from=frontend-build /app/frontend/dist ./static/

  EXPOSE 8000
  CMD ["uv", "run", "uvicorn", "influxer.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```
- **VALIDATE**: `docker build -t influxer . && docker run -p 8000:8000 influxer`

---

## Testing Strategy

### Unit Tests to Write

| Test File | Test Cases | Validates |
|-----------|------------|-----------|
| `tests/test_api_upload.py` | Upload PDF/EPUB, file too large, invalid format | Upload endpoint |
| `tests/test_api_files.py` | CRUD operations, metadata update | Files endpoint |
| `tests/test_api_search.py` | ISBN search, DOI search, title search | Search endpoint |
| `tests/test_api_ingest.py` | Start ingestion, progress events, cancel | Ingest endpoint |
| `tests/test_metadata_search.py` | OpenLibrary, CrossRef, ISBN.de, rate limiting | Search service |
| `tests/test_metadata_extraction.py` | PDF/EPUB metadata, edge cases | Metadata extractor |

### Edge Cases Checklist

- [ ] Upload > 200MB file → 413 error
- [ ] Upload non-PDF/EPUB → 415 error
- [ ] Update metadata with invalid year (< 1800, > current) → warning
- [ ] Search non-existent ISBN → empty results
- [ ] Ingest with missing required fields → 400 error
- [ ] SSE connection drop → reconnect
- [ ] Cancel mid-ingestion → graceful stop
- [ ] Invalid group_id format → validation error

---

## Validation Commands

### Level 1: STATIC_ANALYSIS

```bash
uv run ruff check src/
uv run mypy src/
cd frontend && npm run lint && npm run type-check
```

**EXPECT**: Exit 0, no errors

### Level 2: UNIT_TESTS

```bash
uv run pytest tests/test_api_*.py -v
uv run pytest tests/test_metadata_*.py -v
cd frontend && npm test
```

**EXPECT**: All tests pass

### Level 3: INTEGRATION_TEST

```bash
# Start backend
uv run influxer-api &

# Test endpoints
curl http://localhost:8000/api/health
curl -X POST -F "file=@tests/fixtures/sample.pdf" http://localhost:8000/api/upload
curl http://localhost:8000/api/files

# Start frontend
cd frontend && npm run dev &

# Open browser to http://localhost:5173
# Manual test: Upload → Edit → Search → Ingest
```

**EXPECT**: Full flow works

### Level 4: DOCKER_VALIDATION

```bash
docker build -t influxer .
docker run -p 8000:8000 -e INFLUXER_MCP_URL=https://graphiti.marakanda.biz/mcp influxer

# Test in browser: http://localhost:8000
```

**EXPECT**: Container runs, UI accessible

### Level 5: E2E_TEST

```bash
# With MCP server running:
# 1. Upload sample.pdf
# 2. Edit metadata
# 3. Search ISBN
# 4. Ingest
# 5. Verify in Graphiti: get_episodes shows chunks
```

**EXPECT**: Chunks appear in Graphiti

---

## Acceptance Criteria

- [ ] Drag-and-drop upload works for PDF and EPUB
- [ ] Metadata is extracted and displayed in cards
- [ ] Inline metadata editing works with optimistic UI
- [ ] Entity-Type and Source-Type dropdowns work
- [ ] Validation highlights missing required fields
- [ ] "Ingest All" is disabled when validation fails
- [ ] Metadata search works for ISBN, DOI, and title
- [ ] Search results can be applied to files
- [ ] Ingestion shows real-time progress via SSE
- [ ] Chunks appear in Graphiti after ingestion
- [ ] Docker container runs successfully
- [ ] 200-page PDF is fully ingested (Success Metric from PRD)

---

## Completion Checklist

- [ ] All 22 tasks completed in order
- [ ] Each task validated immediately after completion
- [ ] Level 1: Static analysis passes
- [ ] Level 2: Unit tests pass
- [ ] Level 3: Integration test passes
- [ ] Level 4: Docker validation passes
- [ ] Level 5: E2E test passes
- [ ] All acceptance criteria met

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SSE connection instability | MEDIUM | MEDIUM | Polling fallback, auto-reconnect |
| Large file uploads (>100MB) | MEDIUM | LOW | Chunked upload, clear error messages |
| Metadata API rate limiting | MEDIUM | LOW | Exponential backoff, clear errors |
| ISBN.de API changes | MEDIUM | LOW | Defensive parsing, fallback to OpenLibrary |
| CORS issues in development | LOW | LOW | Proper CORS config, Vite proxy |
| React state complexity | MEDIUM | MEDIUM | TanStack Query for server state |

---

## Notes

**Design Decisions:**

1. **FastAPI over Flask**: Async-first, automatic OpenAPI docs, better type hints
2. **React over HTMX**: Complex client-side state (file queue, inline editing, search modal) benefits from React's component model
3. **TanStack Query**: Handles caching, optimistic updates, background refetching
4. **SSE over WebSocket**: Simpler for unidirectional progress updates
5. **Tailwind CSS**: Rapid UI development, consistent styling
6. **Multi-stage Docker**: Smaller image, frontend pre-built

**Architecture Notes:**

- Backend reuses ALL existing CLI logic (extractors, chunker, MCP client, state DB)
- Only new code: API routes, Pydantic models, metadata search service
- Frontend is pure UI layer, all logic in backend
- Session state in SQLite (not memory) for persistence

**Future Considerations:**

- Phase 2: Batch presets, history, concurrent edit locking
- Phase 3: Markdown support
- Phase 5: CLI headless mode using same backend
