# Graphiti Influxer

## Problem Statement

Claude's Context-Window ist begrenzt. Wertvolles Wissen in grossen Dokumenten (PDFs, EPUBs, Markdown-Dateien) ist fuer Claude unzugaenglich. RAG-Server liefern nur "Textwuesten" ohne semantische Verknuepfungen. Der User hat eine grosse Bibliothek an Wissen, kann aber nicht mit einem AI-Sparringpartner darueber diskutieren, der alles "gelesen" hat.

## Evidence

- User hat eine grosse Bibliothek an EPUBs, PDFs, Textdateien die nicht in Graphiti sind
- Aktuell: Nach 2-3 Seiten faellt Claude um wegen Context-Limit
- GitHub Issue #356 in Graphiti zeigt: Andere haben das gleiche Problem ("Long Ingestion process")
- Kein existierendes Tool fuer Bulk-Document-Ingestion in Graphiti

## Proposed Solution

Ein **Web Interface** (Docker Container) das grosse Dokumente in semantische Chunks aufteilt und ueber den **Graphiti MCP-Server** in den Knowledge Graph einpflegt. Upload → Metadaten-Preview → Edit → Batch-Review → Ingest.

**Warum Web Interface statt CLI?**
- Metadaten-Validierung mit interaktiven Prompts ist in CLI umständlich
- Batch-Review (10+ Dateien mit fehlenden Feldern) braucht Übersicht
- Web-Suche für fehlende Metadaten (OpenLibrary, CrossRef) integrierbar
- Card-basiertes Layout ideal für "Review vor Ingestion"-Workflow
- Single Page App: Kein Page-Reload, alles auf einem Screen

**Warum MCP statt REST?**
- MCP-Server ist die stabile, gepflegte Schnittstelle
- Abstraktion: Interne Graphiti-Aenderungen sind transparent
- Kein Fork-Wartungsproblem: Nutzt bestehende Infrastruktur
- Bereits deployed und funktional auf User's Ubuntu VM

## Key Hypothesis

Wir glauben dass **Influxer** das Problem **"Wissen in grossen Dokumenten ist fuer Claude unzugaenglich"** fuer **Power-User die Graphiti nutzen** loest.
Wir wissen dass wir richtig liegen wenn **ein 200-Seiten-PDF fehlerfrei in Episoden aufgeteilt und in Graphiti abrufbar ist**.

## What We're NOT Building

- Kein direkter Datenbank-Zugriff - nur MCP-Server (Architekturprinzip: Abstraktion)
- Keine Replikation von Graphiti-Logik (Entity Extraction, Embedding, Deduplication)
- Kein eigener LLM/Embedding-Service - nutzt Graphiti's Infrastruktur
- Keine Aenderungen am Graphiti-Fork noetig
- Keine CLI in v1 (Web first) - CLI kann später als headless-mode ergänzt werden

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| 200-Seiten PDF erfolgreich ingesten | 100% Chunks in Graphiti | `get_episodes` zeigt alle UUIDs |
| Bibliothek-Batch (10+ Dateien) | Batch-Upload + Review + Ingest in einem Flow | Web UI zeigt alle Cards, Ingest läuft durch |
| Metadaten-Validation | 100% der Pflichtfelder ausgefüllt vor Ingest | UI blockiert Ingest bei fehlenden Feldern |
| Web-Suche für Metadaten | Fehlende ISBN/Autor via OpenLibrary ergänzen | "Search" Button findet korrekte Metadaten |
| Resume nach Abbruch | Fortsetzung ohne Duplikate | `get_episodes` Abgleich + lokaler State |

## Open Questions

- [x] Wie erkennt Influxer bereits ingestete Dateien? → Hash + UUID in lokaler SQLite DB, Abgleich mit `get_episodes`
- [x] Optimale Chunk-Groesse fuer Graphiti Episoden? → **Semantisches Chunking** (Paragraph-Gruppen, 500-3000 Zeichen). Nicht seitenbasiert, da Seiten keine logischen Einheiten sind.
- [x] Rate-Limiting: Wie viele Episoden/Minute vertraegt der MCP-Server? → **Start mit 1 req/s**, bei Bedarf anpassbar via Config
- [x] MCP-Client Library: mcp-python-sdk oder eigene SSE-Implementation? → **mcp-python-sdk** (offizielle Library)
- [x] **Entity-Types**: → **Vereinfacht nach Pflichtfeldern**: Gleiche Pflichtfelder = gleicher Typ. Buch und Roman haben identische Pflichtfelder (Autor+Titel+Jahr) → beide als "Buch" behandeln. RFC und Artikel haben unterschiedliche → bleiben getrennt.
- [x] **Pflichtfelder pro Type**: → Aus graphiti.md Regeln (Buch: Autor+Titel+Jahr, RFC: Nummer+Jahr, Artikel: Autor+Titel+Quelle+Jahr)
- [x] **Default-Mapping**: → Alle Bücher (auch Romane, Sachbücher) → "Buch". Typ-Erkennung basiert auf Metadaten (DOI → Artikel, RFC in Titel → RFC)
- [x] **ISBN-Extraktion**: Aus Impressum-Seite scannen? → **Deferred to P2** (aufwändig, Regex-basiert, nicht MVP-kritisch)

---

## Users & Context

**Primary User**
- **Who**: Power-User mit Graphiti-Setup, grosse Dokumenten-Bibliothek
- **Current behavior**: Kann grosse Dokumente nicht nutzen, liest manuell, kein AI-Sparringpartner
- **Trigger**: Findet wertvolles PDF/EPUB, will Wissen in "Digital Twin" laden
- **Success state**: Dokument in Graphiti, Claude kann darauf zugreifen und Fragen beantworten

**Job to Be Done**
Wenn ich ein wichtiges Buch/Dokument habe, will ich es in Graphiti laden, damit Claude (und andere Tools via MCP) spaeter darauf zugreifen kann.

**Non-Users**
- User ohne Graphiti-Setup (brauchen erst Graphiti)
- User die nur kleine Dokumente haben (Claude Context reicht)
- User die RAG-Loesungen bevorzugen

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | **Web Interface** | Single Page App für Upload → Review → Ingest Flow |
| Must | **Drag-and-Drop Upload** | Mit Click-Fallback, Multiple Files |
| Must | PDF Text-Extraktion | Haupt-Use-Case: Bibliothek einpflegen |
| Must | EPUB Text-Extraktion | Haupt-Use-Case: Bibliothek einpflegen |
| Must | **Metadaten-Extraktion** | Autor, Titel, Jahr aus PDF/EPUB extrahieren |
| Must | **Entity-Type-Bestimmung** | Vereinfacht: Buch, Artikel, RFC (gleiche Pflichtfelder = gleicher Typ) |
| Must | **Pflichtfeld-Validation** | Buch: Autor+Titel+Jahr, RFC: Nummer+Jahr, Artikel: Autor+Titel+Quelle+Jahr |
| Must | **Card-basiertes Metadaten-Review** | Inline-editierbar, visuelle Hervorhebung fehlender Felder |
| Must | **Source-Type Classification** | Dropdown: Non-Fiction, Academic, Opinion, Fiction, Unknown (Trust-Level) |
| Must | **Web-Suche für Metadaten** | Nach Typ: ISBN→OpenLibrary, DOI→CrossRef, DE-ISBN→ISBN.de |
| Must | Semantisches Chunking | Nicht mitten im Satz/Paragraph abschneiden |
| Must | MCP-Client Integration | Nutzt `add_memory` Tool des MCP-Servers |
| Must | Group-ID Auswahl | Projekt-spezifische vs. allgemeine Doku |
| Must | Progress-Anzeige | Echtzeit-Feedback während Verarbeitung |
| Must | Resume bei Abbruch | `get_episodes` Abgleich + lokaler State |
| Must | **Docker Deployment** | Container auf User's Infrastruktur |
| Should | Markdown Support | Phase 2 |
| Should | CLI Headless-Mode | Für Automatisierung/Scripts |
| Could | Web Crawling | Phase 3 |
| Could | Video/Audio (Speech-to-Text) | Nice-to-have, externe API nötig |
| Won't | Direkte Datenbank-Operationen | Architekturprinzip: Abstraktion |
| Won't | REST-API Änderungen | MCP ist die stabile Schnittstelle |

### MVP Scope

Phase 1: Web Interface für PDF + EPUB Upload mit Metadaten-Review und Ingestion in Graphiti.

### User Flow

```
1. UPLOAD
   - User öffnet Web Interface im Browser
   - Drag-and-Drop oder Click für Datei-Auswahl
   - Mehrere Dateien gleichzeitig möglich

2. PROCESSING
   - Automatische Text-Extraktion (PDF/EPUB)
   - Metadaten-Extraktion (Titel, Autor, Jahr)
   - Entity-Type-Erkennung (Buch/Artikel/RFC/Roman)
   - Progress-Bar während Verarbeitung

3. REVIEW (Card-Layout)
   - Jede Datei als Card mit:
     - Cover-Thumbnail (falls verfügbar)
     - Extrahierte Metadaten (inline-editierbar)
     - Entity-Type Dropdown
     - **Source-Type Dropdown** (required, Trust-Level):
       - Non-Fiction / Reference
       - Academic (peer-reviewed)
       - Journalism / News
       - Opinion / Autobiography / Memoir
       - Fiction
       - Unknown
     - ⚠️ Warning for "Opinion/Fiction": "This source is classified as opinion/fiction"
     - Status-Indikator (grün=komplett, rot=Pflichtfelder fehlen)
   - "Search" Button für fehlende Metadaten (OpenLibrary)

4. BATCH ACTIONS
   - Group-ID Auswahl (main, projekt-x, etc.)
   - "Ingest All" Button (nur wenn alle Pflichtfelder erfüllt)
   - "Ingest Selected" für Teilmenge

5. INGESTION
   - Chunking der Texte
   - Senden via MCP add_memory
   - Echtzeit-Progress pro Datei
   - UUID-Tracking für Resume

6. SUMMARY
   - X Dateien, Y Chunks erfolgreich
   - Fehler-Liste falls vorhanden
   - "Clear & Start New" Button
```

### Web Interface Layout (Single Page)

```
┌────────────────────────────────────────────────────────────────┐
│  GRAPHITI INFLUXER                          [Group: main ▼]    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                                                          │  │
│  │         📁 Drop files here or click to upload            │  │
│  │              PDF, EPUB supported                         │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  ─────────────────── QUEUED FILES ───────────────────────────  │
│                                                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ 📕              │  │ 📘              │  │ 📙              │ │
│  │ Deep Work       │  │ Clean Code      │  │ RFC 2616        │ │
│  │ ─────────────── │  │ ─────────────── │  │ ─────────────── │ │
│  │ Autor: Cal N... │  │ Autor: [????]   │  │ Nummer: 2616    │ │
│  │ Jahr:  2016     │  │ Jahr:  [????]   │  │ Jahr:  1999     │ │
│  │ Type:  Buch  ▼  │  │ Type:  Buch  ▼  │  │ Type:  RFC   ▼  │ │
│  │ Trust: Sachb.▼  │  │ Trust: [????]▼  │  │ Trust: Wiss. ▼  │ │
│  │ ─────────────── │  │ ─────────────── │  │ ─────────────── │ │
│  │ ✓ Ready        │  │ ⚠ Missing fields │  │ ✓ Ready        │ │
│  │ [🔍 Search]     │  │ [🔍 Search]     │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                │
│  ───────────────────────────────────────────────────────────── │
│  [□ Select All]                [Ingest Selected] [Ingest All]  │
│                                                                │
│  ─────────────────── PROGRESS ──────────────────────────────── │
│  ████████████░░░░░░░░  3/10 files | 47/120 chunks              │
│  Current: Deep Work.pdf - Sending chunk 12/31                  │
│  MCP: ✓ Connected | Rate: 2.3 eps/min                          │
└────────────────────────────────────────────────────────────────┘
```

### API Routes (FastAPI Backend)

```
POST   /api/upload          - Datei-Upload (multipart/form-data)
GET    /api/files           - Liste aller geladenen Dateien
GET    /api/files/{id}      - Details einer Datei
PATCH  /api/files/{id}      - Metadaten editieren
DELETE /api/files/{id}      - Datei aus Queue entfernen

POST   /api/search-metadata - OpenLibrary/CrossRef Suche
POST   /api/ingest          - Ingestion starten (file IDs)
GET    /api/ingest/status   - Ingestion-Progress (SSE)

GET    /api/health          - Backend Health Check
GET    /api/mcp/status      - Graphiti MCP Status
```

---

## Technical Approach

**Feasibility**: HOCH

**Architecture**

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
│               (React + TypeScript + Vite)               │
└─────────────────────────────────────────────────────────┘
                              │
                         HTTP/REST
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                 Influxer Docker Container               │
│                    (dieses Projekt)                     │
├─────────────────────────────────────────────────────────┤
│  FastAPI      │  Extractor    │  Chunker    │ MCP Client│
│  (Web API)    │  (pymupdf,    │  (semantic) │ (SSE)     │
│               │   ebooklib)   │             │           │
│  ─────────────┴───────────────┴─────────────┴───────────│
│  SQLite (State: File-Hash → UUIDs, Session-Queue)       │
└─────────────────────────────────────────────────────────┘
                                                    │
                                              MCP Protocol
                                              (add_memory,
                                               get_episodes)
                                                    │
                                                    ▼
┌─────────────────────────────────────────────────────────┐
│              Graphiti MCP-Server                        │
│              (bereits deployed auf Ubuntu VM)           │
│              Stabile Schnittstelle - keine Aenderungen  │
└─────────────────────────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     FalkorDB      CLIProxyAPI      Ollama
     (Graph)       (LLM)           (Embeddings)
     [intern]      [intern]        [intern]
```

**Vorteile dieser Architektur:**
- Web UI ermöglicht bessere UX für Metadaten-Review
- Docker Container: Einfaches Deployment auf User's Infrastruktur
- FastAPI: Schnell, async, OpenAPI-Spec automatisch
- React + Vite: Complex state management, modern tooling, mature ecosystem
- Influxer bleibt unabhängig von Graphiti-Interna
- MCP-Server Upgrades sind transparent

**Key Technical Decisions**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python | Gute MCP-Libraries, PDF/EPUB Support |
| Backend | FastAPI | Async, schnell, OpenAPI-Spec automatisch |
| Frontend | React + TypeScript + Vite | Complex state management, mature ecosystem (react-dropzone, TanStack Query) |
| PDF Parser | pymupdf (fitz) | Schnell, Metadaten-Extraktion |
| EPUB Parser | ebooklib | Standard für EPUB in Python |
| Chunking | Custom semantic | Paragraph/Section boundaries |
| MCP Client | mcp-python-sdk | Offizielle MCP Library |
| State/Resume | SQLite | Tracking: Datei-Hash → UUID Mapping |
| Deployment | Docker | Portabel, konfigurierbar via ENV |
| Metadata Search | OpenLibrary API | Kostenlos, ISBN/Titel-Suche |

**MCP Tools die Influxer nutzt:**

| MCP Tool | Zweck |
|----------|-------|
| `add_memory` | Episode (Chunk) senden |
| `get_episodes` | Pruefen ob Episoden angekommen sind |
| `get_status` | MCP-Server Health Check |

**Technical Risks**

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| MCP-Server Rate-Limiting | MITTEL | Configurable delay, backoff, get_status Check |
| Grosse PDFs (1000+ Seiten) | MITTEL | Streaming, Memory-Management |
| Chunk-Qualitaet | MITTEL | Testen mit verschiedenen Docs |
| SSE Connection Drops | NIEDRIG | Reconnect-Logic, Resume-Funktion |

---

## Edge Cases

**134 dokumentierte Edge Cases** in separater Master-Liste: [edge-cases.md](../edge-cases.md)

| Phase | Cases | Beschreibung |
|-------|-------|--------------|
| P1 | 90 | Web Interface MVP (PDF/EPUB, Metadaten, Web UI, API-Suche) |
| P2 | 20 | Batch & Polish, API-Keys, weitere APIs |
| P3 | 2 | Markdown Support |
| P4 | 4 | Testing & Docs |
| P5 | 5 | CLI Headless-Mode |
| P? | 13 | Future / Low Priority |

**WICHTIG**: Bei jeder Phasen-Planung (`/prp-plan`) MUSS `edge-cases.md` konsultiert werden, um die relevanten Cases in den Plan aufzunehmen.

---

## Implementation Phases

| # | Phase | Description | Status | Parallel | Depends | PRP Plan |
|---|-------|-------------|--------|----------|---------|----------|
| 1 | Web Interface MVP | FastAPI + React, PDF/EPUB, Metadaten-Suche (4 APIs) | **in-progress** | - | - | [phase-1-web-interface-mvp.plan.md](../plans/phase-1-web-interface-mvp.plan.md) |
| 2 | Batch & Polish | Batch-Presets, History, Concurrent Edit, weitere APIs | pending | - | 1 | - |
| 3 | Markdown Support | Markdown/Text-Dateien unterstützen | pending | with 4 | 2 | - |
| 4 | Testing & Docs | Umfassende Tests, Dokumentation | pending | with 3 | 2 | - |
| 5 | CLI Headless-Mode | Kommandozeilen-Interface für Automatisierung | pending | - | 4 | - |

### Phase Details

**Phase 1: Web Interface MVP**
- **Goal**: Funktionierendes Web Interface für Upload → Review → Ingest Flow
- **Scope**:
  - **Backend (FastAPI)**:
    - File Upload Endpoint (multipart/form-data)
    - PDF Text/Metadaten-Extraktion (pymupdf)
    - EPUB Text/Metadaten-Extraktion (ebooklib)
    - Entity-Type-System (vereinfacht: Buch, Artikel, RFC - nach Pflichtfeldern)
    - Pflichtfeld-Validation (Buch: Autor+Titel+Jahr, RFC: Nummer+Jahr, Artikel: Autor+Titel+Quelle+Jahr)
    - Semantisches Chunking (Paragraph-Gruppen, 500-3000 Zeichen)
    - MCP-Client für Graphiti (add_memory, get_episodes)
    - SQLite State (Session-Queue, Datei-Hash → UUIDs)
    - SSE Endpoint für Ingestion-Progress
    - Rate-Limiting: 1 req/s (konfigurierbar)
  - **Frontend (React + TypeScript + Vite)**:
    - Drag-and-Drop Upload Zone
    - Card-Layout für Datei-Queue
    - Inline-editierbare Metadaten-Felder
    - Entity-Type Dropdown
    - **Source-Type Dropdown** (required: Non-Fiction, Academic, Opinion, Fiction, Unknown)
    - Warning when "Opinion/Fiction" selected
    - Pflichtfeld-Validierung (visuelle Hervorhebung)
    - Group-ID Selector
    - Ingest Button + Progress-Anzeige
  - **Docker**:
    - Dockerfile für Container-Deployment
    - ENV-Konfiguration (MCP-URL, Ports)
- **Metadaten-Suche** (nach Dokumenttyp):
    - **ISBN erkannt** → OpenLibrary (Fallback: Google Books)
    - **DOI erkannt** → CrossRef
    - **Deutsche ISBN (978-3-...)** → ISBN.de
    - **Nur Titel** → OpenLibrary Titel-Suche
    - Auto-Fill bei Suchergebnis
- **Success signal**: PDF hochladen → Metadaten editieren/suchen → Ingest → `get_episodes` zeigt alle Chunks
- **Edge Cases (90 total)**:
  - #1-#12 (PDF), #13-#22 (EPUB), #23-#32 (Chunking)
  - #33-#42 (MCP/Netzwerk), #44-#50 (State)
  - #52, #55, #58 (File System)
  - #59-#63 (Graphiti-spezifisch)
  - #65-#70 (OCR), #72-#73, #75-#76 (Memory/Performance/Encoding)
  - #80-#83 (Security/Provenance), #87 (Verification)
  - #97-#108 (Metadaten/Entity-Types)
  - #109-#117, #119-#120 (Web Interface)
  - #121-#134 (Metadaten-Suche APIs)

**Phase 2: Batch & Polish**
- **Goal**: Verfeinerungen für Batch-Workflows und erweiterte APIs
- **Scope**:
  - **API-Key-Konfiguration** für höhere Limits (Google Books, weitere)
  - Weitere Metadaten-APIs (WorldCat, etc.)
  - Batch-Presets (alle als "Buch", alle gleiche group_id)
  - History: Zuletzt verwendete group_ids
  - Concurrent Edit Locking (#118)
- **Success signal**: 20+ Dateien effizient in einem Flow verarbeitet

**Phase 3: Markdown Support**
- **Goal**: Markdown/Text-Dateien unterstützen
- **Scope**:
  - Markdown Parser
  - Chunk-Strategie für Markdown (Headings als Boundaries)
  - Integration in Web UI
- **Success signal**: Grosse Markdown-Datei erfolgreich ingestet

**Phase 4: Testing & Docs**
- **Goal**: Stabile, dokumentierte Software
- **Scope**:
  - Unit Tests für Extractor, Chunker, MCP-Client
  - Integration Tests gegen MCP-Server
  - API Tests für FastAPI Endpoints
  - README, Usage Docs
- **Success signal**: CI grün, README vollständig

**Phase 5: CLI Headless-Mode**
- **Goal**: Kommandozeilen-Interface für Automatisierung/Scripts
- **Scope**:
  - `influxer ingest <file> --group-id main` Command
  - Batch-Verarbeitung (Ordner rekursiv)
  - JSON-Output für Scripting
  - Resume-Funktion
- **Success signal**: 100+ Dateien Batch läuft durch ohne UI

### Parallelism Notes

Phase 3 (Markdown) und Phase 4 (Testing) koennen parallel laufen da sie unterschiedliche Domaenen bearbeiten.

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| **UI Language** | **English first** | German first | Industry standard; i18n can be added later; broader contributor base |
| **Interface** | **Web UI** | CLI-only | Metadaten-Review/Edit besser in UI; Batch-Review braucht Übersicht |
| Backend | FastAPI | Flask, Django | Async, schnell, automatische OpenAPI-Spec |
| Frontend | React + TypeScript + Vite | HTMX + Alpine.js | Complex client-side state (file queue, inline editing, selection) requires React's state management |
| Deployment | Docker | Native Python | Portabel, isoliert, einfaches Deployment auf User's Infra |
| API Interface | MCP-Server | REST-API, Direct DB | Abstraktion: Graphiti-Interna sind transparent, kein Fork-Problem |
| State Storage | SQLite | JSON, Redis | Einfach, lokal, robust, Query-fähig |
| Chunking Strategy | Semantic (Paragraph) | Fixed-size, Sentence | Graphiti braucht sinnvolle Einheiten |
| Verification | get_episodes | Nur HTTP Status | Echte Bestätigung dass Episode gespeichert |
| Metadata Search | OpenLibrary + CrossRef + ISBN.de | Firecrawl, WorldCat | Strukturierte APIs liefern direkt JSON; Firecrawl braucht AI für Extraktion |
| Entity-Types | Vereinfacht (Buch, Artikel, RFC) | Document/Work Hierarchie | Gleiche Pflichtfelder = gleicher Typ. Buch=Roman (beide Autor+Titel+Jahr) |
| Chunking | Semantisch (500-3000 Zeichen) | Seitenbasiert, Fixed-size | Seiten sind keine logischen Einheiten; Paragraph-Gruppen sind semantisch sinnvoll |
| Rate-Limiting | 1 req/s Start | Aggressiver (5 req/s) | Konservativ starten, bei Bedarf erhöhen |
| Source-Type | Pflicht-Dropdown | Automatische Klassifikation | Manuelle Klassifikation ist zuverlässiger; User trifft bewusste Entscheidung |

---

## Research Summary

**Market Context**
- LlamaIndex/LangChain haben Document Loaders, aber fuer RAG (Vektor-DBs), nicht Knowledge Graphs
- Kein existierendes Tool fuer Graphiti Bulk-Ingestion
- GitHub Issue #356 zeigt Bedarf

**Technical Context**
- Graphiti serialisiert Episoden pro group_id (sequenziell fuer temporale Integritaet)
- MCP-Server ist die stabile, gepflegte Schnittstelle
- User hat FalkorDB (nicht Neo4j), Fork mit Bugfixes
- Architektur: Ubuntu VM (FalkorDB, Graphiti MCP), Mac Mini (Ollama), Mac Studio (Claude Code)

**Graphiti Group-ID Konzept**
- group_id = isolierter Namespace
- `main` fuer allgemeines Wissen
- projekt-spezifische IDs fuer projekt-bezogene Doku
- Wenn Dokument fuer mehrere Projekte relevant → `main`

**MCP-Server Tools (bereits verfuegbar)**
- `add_memory`: Episode hinzufuegen (text/json/message)
- `get_episodes`: Episoden abrufen (fuer Verification)
- `search_memory_facts`: Fakten suchen
- `search_nodes`: Entities suchen
- `get_status`: Server-Status pruefen

---

*Generated: 2026-01-19*
*Updated: 2026-01-19 - MAJOR PIVOT: CLI → Web Interface. Architektur: FastAPI + HTMX + Docker*
*Updated: 2026-01-19 - Open Questions resolved (Chunking, Rate-Limiting, Entity-Types vereinfacht)*
*Updated: 2026-01-19 - Source-Type Classification (Trust-Level) added, UI language set to English*
*Updated: 2026-01-19 - Frontend changed from HTMX+Alpine.js to React+TypeScript+Vite (UX analysis)*
*Status: PHASE 1 IN PROGRESS - All questions resolved, plan created, ready for implementation*
