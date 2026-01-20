# Graphiti Influxer

[![CI](https://github.com/Milofax/graphiti-influxer-public/actions/workflows/ci.yml/badge.svg)](https://github.com/Milofax/graphiti-influxer-public/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Ingest large documents (PDFs, EPUBs) into [Graphiti Knowledge Graph](https://github.com/getzep/graphiti) via MCP.

## Problem

Claude's context window can't handle large documents. Your valuable knowledge in books, papers, and documents remains inaccessible to AI assistants. Traditional RAG solutions deliver "text deserts" without semantic connections.

## Solution

Graphiti Influxer is a web interface that:
- **Extracts** text and metadata from PDFs and EPUBs
- **Chunks** content intelligently at semantic boundaries
- **Validates** metadata with external API lookups (OpenLibrary, CrossRef)
- **Ingests** chunks into Graphiti via MCP protocol
- **Tracks** progress and handles failures gracefully

## Status

**Phase 1: In Progress** - Web Interface MVP

## Features

- Drag-and-drop file upload (PDF, EPUB)
- Automatic metadata extraction (title, author, year)
- Card-based review interface with inline editing
- Metadata lookup via OpenLibrary, CrossRef, ISBN.de
- Semantic chunking (paragraph boundaries, 500-3000 chars)
- Real-time ingestion progress
- Resume capability for interrupted ingestions

## Requirements

- Python 3.12+
- [Graphiti MCP Server](https://github.com/getzep/graphiti) running and accessible
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

### Using uv (recommended)

```bash
# Clone the repository
git clone https://github.com/Milofax/graphiti-influxer-public.git
cd graphiti-influxer-public

# Install dependencies
uv sync

# Run the application
uv run influxer --help
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/Milofax/graphiti-influxer-public.git
cd graphiti-influxer-public

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install package
pip install -e .

# Run the application
influxer --help
```

## Usage

```bash
# Check MCP server connection
influxer status

# Ingest a PDF document
influxer ingest document.pdf --group-id main

# Ingest with custom metadata
influxer ingest book.epub --group-id main --title "Custom Title" --author "Author Name"
```

## Configuration

Configure via environment variables or `.env` file:

```bash
# MCP Server connection
GRAPHITI_MCP_URL=http://localhost:8000
GRAPHITI_MCP_TIMEOUT=30

# Ingestion settings
INFLUXER_CHUNK_SIZE=2000
INFLUXER_RATE_LIMIT=1.0  # requests per second
```

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run linter
uv run ruff check src tests

# Run type checker
uv run mypy src

# Run tests
uv run pytest tests -v

# Format code
uv run ruff format src tests
```

## Architecture

```
Browser (React + TypeScript)
         │
    HTTP/REST
         │
         ▼
┌─────────────────────────────────────┐
│     Influxer Docker Container       │
│  FastAPI │ Extractor │ MCP Client   │
│          │ (pymupdf) │ (SSE)        │
│  ────────┴───────────┴──────────    │
│  SQLite (State: Hash → UUIDs)       │
└─────────────────────────────────────┘
                   │
              MCP Protocol
                   │
                   ▼
         Graphiti MCP Server
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.

## License

[MIT](LICENSE)
