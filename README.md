# Graphiti Influxer

Ingest large documents (PDFs, EPUBs, videos) into [Graphiti Knowledge Graph](https://github.com/getzep/graphiti).

## Problem

Claude's context window can't handle large documents. Graphiti needs content in digestible chunks.

## Solution

A tool that:
- Extracts text from PDFs, EPUBs, videos (speech-to-text)
- Chunks content intelligently (semantic boundaries)
- Feeds chunks to Graphiti step-by-step
- Tracks progress and handles failures

## Status

Planning phase - PRD in progress.

## License

MIT
