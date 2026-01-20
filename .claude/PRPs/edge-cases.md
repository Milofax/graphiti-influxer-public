# Edge Cases - Graphiti Influxer

**Master-Liste aller bekannten Edge Cases mit Phase-Zuordnung.**

Dieses Dokument wird bei jeder Phasen-Planung konsultiert. Cases werden nach Implementation als `[x]` markiert.

---

## Legende

| Symbol | Bedeutung |
|--------|-----------|
| `[ ]` | Offen |
| `[x]` | Implementiert |
| `[~]` | Teilweise / Workaround |
| `[-]` | Bewusst nicht implementiert (Won't Fix) |

| Phase | Beschreibung |
|-------|--------------|
| **P1** | Phase 1: Web Interface MVP (FastAPI + HTMX, PDF/EPUB, Metadaten-Review) |
| **P2** | Phase 2: Metadaten-Suche (OpenLibrary, CrossRef) |
| **P3** | Phase 3: Markdown Support |
| **P4** | Phase 4: Testing & Docs |
| **P5** | Phase 5: CLI Headless-Mode |
| **P?** | Unassigned / Future |

---

## 1. PDF-Extraktion

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 1 | [ ] | Passwortgeschützte PDF | Extraktion schlägt fehl | Detect + Skip + Log | **P1** |
| 2 | [ ] | Gescannte PDF (nur Bilder) | Kein Text extrahierbar | OCR-Fallback (Tesseract) | **P1** |
| 3 | [ ] | PDF mit gemischtem Content (Text + Scans) | Teilweise leer | Seiten-Check + OCR für leere | **P1** |
| 4 | [ ] | Korrupte PDF | Parser-Crash | Try/Catch + Skip + Log | **P1** |
| 5 | [ ] | PDF mit Formularen | Formularfelder ignoriert | Formular-Extraktion optional | P2 |
| 6 | [ ] | PDF mit Annotationen/Kommentaren | Annotationen verloren | Annotation-Extraktion optional | P2 |
| 7 | [ ] | PDF mit eingebetteten Dateien | Attachments ignoriert | Log Warning | **P1** |
| 8 | [ ] | Sehr große PDF (1000+ Seiten) | Memory Overflow | Streaming/Page-by-Page | **P1** |
| 9 | [ ] | PDF mit komplexen Tabellen | Tabellen-Struktur zerstört | pdfplumber für Tabellen | P2 |
| 10 | [ ] | PDF mit Multi-Column Layout | Spalten vermischt | Layout-Detection (pymupdf4llm) | P2 |
| 11 | [ ] | PDF mit Wasserzeichen | Wasserzeichen im Text | Filter-Option | P? |
| 12 | [ ] | Leere PDF (0 Seiten oder nur Whitespace) | Leere Episode | Skip + Log | **P1** |

---

## 2. EPUB-Extraktion

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 13 | [ ] | DRM-geschütztes EPUB | Extraktion blockiert | Detect + Skip + Log | **P1** |
| 14 | [ ] | EPUB mit kaputtem ZIP | Parser-Crash | Try/Catch + Skip | **P1** |
| 15 | [ ] | EPUB ohne Text (nur Bilder) | Kein Content | OCR oder Skip | P2 |
| 16 | [ ] | EPUB mit eingebettetem Audio/Video | Media ignoriert | Log Info | **P1** |
| 17 | [ ] | EPUB mit komplexem CSS | Formatierung verloren | Text-Only Extraktion | **P1** |
| 18 | [ ] | EPUB mit JavaScript | JS ignoriert | Sicherheits-Skip | **P1** |
| 19 | [ ] | EPUB mit MathML/SVG | Formeln/Grafiken verloren | Fallback-Text "[Formel]" | P2 |
| 20 | [ ] | EPUB3 vs EPUB2 Format-Unterschiede | Parser-Inkompatibilität | Beide Formate testen | **P1** |
| 21 | [ ] | EPUB mit fehlendem TOC | Navigation unmöglich | Kapitel aus Content-Order | **P1** |
| 22 | [ ] | EPUB mit nicht-UTF8 Encoding | Encoding-Fehler | Detect + Convert | **P1** |

---

## 3. Chunking/Semantik

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 23 | [ ] | Dokument ohne Absätze (Fließtext) | Schlechte Chunk-Grenzen | Sentence-Splitter Fallback | **P1** |
| 24 | [ ] | Sehr kurzes Dokument (< 1 Chunk) | Overhead für Mini-Chunk | Minimum-Size Check + Warning | **P1** |
| 25 | [ ] | Dokument mit Code-Blöcken | Code zerrissen | Code-Block-Detection (```) | P2 |
| 26 | [ ] | Dokument mit Fußnoten | Fußnoten getrennt vom Text | Fußnoten-Merge | P? |
| 27 | [ ] | Dokument mit Inhaltsverzeichnis | TOC als eigene Chunks | TOC-Detection + Skip | P2 |
| 28 | [ ] | Dokument mit Index/Glossar | Sinnlose Chunks | Backend-Matter Detection | P? |
| 29 | [ ] | Chunk-Size > MCP-Limit | Request rejected | Pre-Split + Verify Size | **P1** |
| 30 | [ ] | Überlappende Chunks (Kontext) | Duplikate in Graphiti | Overlap-Strategie dokumentieren | **P1** |
| 31 | [ ] | Sprach-Wechsel im Dokument | Gemischte Sprachen pro Chunk | Language-Detection | P? |
| 32 | [ ] | Listen/Aufzählungen | Listen zerrissen | List-Boundary-Detection | P2 |

---

## 4. MCP/Netzwerk

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 33 | [ ] | MCP-Server nicht erreichbar | Alle Requests fehlschlagen | Health-Check vor Start (Fail-Fast) | **P1** |
| 34 | [ ] | MCP-Server Timeout (30-50s pro Episode) | Langsame Verarbeitung | Async + Progress + Configurable Timeout | **P1** |
| 35 | [ ] | MCP Connection Drop mid-batch | Teilweise Verarbeitung | Resume-Logik | P2 |
| 36 | [ ] | MCP Rate-Limiting | 429 Errors | Exponential Backoff | **P1** |
| 37 | [ ] | MCP Server Restart während Batch | Connection Lost | Reconnect + Resume | P2 |
| 38 | [ ] | Ungültige MCP-Credentials | Auth-Fehler | Pre-Auth-Check | **P1** |
| 39 | [ ] | MCP-Response Parsing Fehler | Unerwartetes Format | Defensive Parsing | **P1** |
| 40 | [ ] | SSL/TLS Zertifikat-Probleme | Connection refused | --insecure Flag für Self-Signed | **P1** |
| 41 | [ ] | Proxy/Firewall blockiert | Network unreachable | Network-Diagnostics + Clear Error | **P1** |
| 42 | [ ] | DNS-Auflösung fehlschlägt | Host unknown | Clear Error Message | **P1** |

---

## 5. State/Resume

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 43 | [ ] | SQLite DB korrupt | State verloren | Backup + Rebuild Command | P2 |
| 44 | [ ] | Prozess-Kill während DB-Write | Inkonsistenter State | SQLite Transactions | **P1** |
| 45 | [ ] | Datei geändert nach Teil-Ingestion | Hash-Mismatch | Re-Ingest oder Skip (User-Choice) | P2 |
| 46 | [ ] | Datei gelöscht nach Teil-Ingestion | Orphan-State | Cleanup-Command | P2 |
| 47 | [ ] | Disk voll während State-Write | Write-Failure | Pre-Check + Clear Error | **P1** |
| 48 | [ ] | Parallele Influxer-Instanzen | DB-Lock-Conflicts | File-Locking | **P1** |
| 49 | [ ] | Resume nach Schema-Migration | Inkompatible DB | Migration-Scripts | P2 |
| 50 | [ ] | State-DB auf Network-Drive | Latenz/Locks | Dokumentieren: Local empfohlen | **P1** |

---

## 6. File System

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 51 | [ ] | Symlinks im Ordner | Loops oder Missing | --follow-symlinks Option | P2 |
| 52 | [ ] | Keine Leserechte für Datei | Permission Denied | Skip + Log | **P1** |
| 53 | [ ] | Datei während Verarbeitung geändert | Inkonsistenter Content | Read-Once (kein Lock nötig) | P2 |
| 54 | [ ] | Sehr lange Dateinamen | OS-Limits | OS handled, Log Warning | P? |
| 55 | [ ] | Sonderzeichen in Dateinamen | Encoding-Probleme | pathlib handled | **P1** |
| 56 | [ ] | Versteckte Dateien (.dotfiles) | Unerwartet übersprungen | --include-hidden Option | P2 |
| 57 | [ ] | Case-Sensitivity (macOS vs Linux) | Duplikate | Normalize-Paths | P2 |
| 58 | [ ] | Netzwerk-Laufwerke (SMB/NFS) | Latenz, Locks | Dokumentieren: Local empfohlen | **P1** |

---

## 7. Graphiti-spezifisch

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 59 | [ ] | Ungültige group_id | Rejection | Validate Format vor Start | **P1** |
| 60 | [ ] | group_id existiert nicht | Neue Gruppe oder Fehler? | Graphiti erstellt auto, dokumentieren | **P1** |
| 61 | [ ] | Duplikat-Detection in Graphiti | Doppelte Episoden | Hash-in-Metadata (file_hash, chunk_index) | **P1** |
| 62 | [ ] | Episode-Limit pro group_id | Quota erreicht | Pre-Check oder Warning | P? |
| 63 | [ ] | Graphiti Entity-Extraction fehlschlägt | Episode ohne Entities | Warning + trotzdem speichern | **P1** |
| 64 | [ ] | Graphiti-Version Inkompatibilität | API-Änderungen | Version-Check via get_status | P2 |

---

## 8. OCR-spezifisch

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 65 | [ ] | Tesseract nicht installiert | OCR nicht verfügbar | deps.py Check + Install Instructions | **P1** |
| 66 | [ ] | Falsche OCR-Sprache | Schlechte Erkennung | --language Option | **P1** |
| 67 | [ ] | Handschriftliche Dokumente | OCR-Qualität sehr schlecht | Confidence-Threshold + Warning | **P1** |
| 68 | [ ] | Niedriger DPI/Scan-Qualität | Unleserlich | DPI-Check (< 150 = Warning) | **P1** |
| 69 | [ ] | OCR-Timeout bei großen Bildern | Hängt | Timeout pro Seite + Skip | **P1** |
| 70 | [ ] | Multi-Language OCR | Sprach-Mix pro Seite | Multi-Lang Config (eng+deu+spa) | **P1** |

---

## 9. Memory/Performance

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 71 | [ ] | 10.000+ Dateien im Batch | Memory-Erschöpfung | Generator/Streaming | P2 |
| 72 | [ ] | Einzelne 500MB PDF | RAM-Spike | Page-by-Page Processing | **P1** |
| 73 | [ ] | Langsame HDD vs SSD | I/O-Bottleneck | Progress zeigt ETA | **P1** |
| 74 | [ ] | CPU 100% bei OCR | System unresponsive | --max-workers Option | P? |
| 75 | [ ] | Zu viele offene File-Handles | OS-Limit erreicht | Context Managers (with statements) | **P1** |

---

## 10. Encoding/Unicode

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 76 | [ ] | UTF-16/UTF-32 statt UTF-8 | Encoding-Fehler | Detect + Convert | **P1** |
| 77 | [ ] | Mixed Encodings in einem Dokument | Mojibake | Per-Section Detection | P? |
| 78 | [ ] | Right-to-Left Sprachen (Arabisch, Hebräisch) | Reihenfolge falsch | BiDi-Support | P? |
| 79 | [ ] | CJK-Zeichen (Chinesisch, Japanisch, Koreanisch) | Chunking-Probleme | CJK-aware Splitter | P2 |

---

## 11. Security/Provenance

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 80 | [ ] | Malware in PDF/EPUB | Sicherheitsrisiko | Keine Ausführung, nur Text-Extraktion | **P1** |
| 81 | [ ] | Urheberrechtlich geschützte Inhalte | Rechtliche Probleme | User-Verantwortung (Terms/Docs) | **P1** |
| 82 | [ ] | Persönliche Daten in Dokumenten | DSGVO | Privacy-Warning in Docs | **P1** |
| 83 | [ ] | Source-Tracking (woher kam Dokument) | Provenance verloren | file_path + file_hash in Episode Metadata | **P1** |

---

## 12. Verification/Quality

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 84 | [ ] | get_episodes liefert weniger als gesendet | Silent Failures | Count-Verify (verify command) | P2 |
| 85 | [ ] | Episode-Content in Graphiti ≠ Sent Content | Corruption | Hash-Verify (Stichprobe) | P2 |
| 86 | [ ] | Graphiti-Search findet ingested Content nicht | Indexing-Delay | Wait + Retry in verify | P2 |
| 87 | [ ] | Entity-Extraction ergibt 0 Entities | Content zu generisch | Warning + trotzdem OK | **P1** |

---

## 13. CLI/UX (Phase 5)

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 88 | [ ] | Ctrl+C während Verarbeitung | Unkontrollierter Abbruch | Signal-Handler + Cleanup | **P5** |
| 89 | [ ] | Terminal ohne Farb-Support | Progress-Bar kaputt | Rich auto-detects | **P5** |
| 90 | [ ] | Piped Output (nicht interaktiv) | Progress-Spam | Rich handles --no-color | **P5** |
| 91 | [ ] | Falscher Pfad-Argument | FileNotFound | Frühzeitige Validierung | **P5** |
| 92 | [ ] | --yes ohne --quiet | Unerwartete Prompts trotzdem | Konsistenz prüfen | **P5** |

---

## 14. Text-Struktur

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 93 | [ ] | Header/Footer auf jeder Seite | Repetitiver Content | Header/Footer-Detection | P2 |
| 94 | [ ] | Seitenzahlen im Text | Noise | Page-Number-Strip (Regex) | P2 |
| 95 | [ ] | Bibliographie/Referenzen | Wenig Kontext pro Chunk | Reference-Section-Detection | P? |
| 96 | [ ] | Bildunterschriften ohne Bilder | Kontext fehlt | Caption-Marker + Skip-Option | P? |

---

## 15. Metadaten/Entity-Types

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 97 | [ ] | Metadaten komplett leer ("untitled", "anonymous") | Pflichtfelder fehlen | User-Prompt für fehlende Felder | **P1** |
| 98 | [ ] | Metadaten unvollständig (nur Titel, kein Autor) | Unvollständige source_description | User-Prompt für fehlende Pflichtfelder | **P1** |
| 99 | [ ] | Metadaten falsch/veraltet (Konvertierungsartefakte) | Falsches Wissen in Graphiti | User kann überschreiben (--title, --author) | **P1** |
| 100 | [ ] | Jahr in Metadaten ≠ Publikationsjahr | CreationDate = PDF-Erstellung, nicht Buch-Jahr | User-Prompt wenn Jahr > heute oder < 1800 | **P1** |
| 101 | [ ] | ISBN nicht in Metadaten | Pflichtfeld für Buch fehlt | Optional: Impressum-Scan oder User-Prompt | **P1** |
| 102 | [ ] | Entity-Type unklar (Buch vs. Artikel vs. RFC) | Falscher Type → falsche Pflichtfelder | Default + --type Override | **P1** |
| 103 | [ ] | Pflichtfelder nicht ermittelbar | Ingestion blockiert | User-Prompt ODER --skip-validation | **P1** |
| 104 | [ ] | Batch: Verschiedene Entity-Types im Ordner | Jede Datei braucht eigene Metadaten | Pre-Scan + Batch-Review vor Ingestion | P2 |
| 105 | [ ] | Metadaten in falschen Feldern (Autor im Subject) | Felder nicht erkannt | Heuristik + User-Korrektur | P? |
| 106 | [ ] | Titel aus Content extrahieren (H1 > metadata.title) | metadata.title = "untitled" | Content-Scan als Fallback | **P1** |
| 107 | [ ] | EPUB: DC:identifier ist keine ISBN | ISBN-Validation schlägt fehl | ISBN-Pattern prüfen, sonst ignorieren | **P1** |
| 108 | [ ] | Multi-Author Dokument | Nur ein Autor-Feld | Comma-separated oder Array | **P1** |

---

## 16. Web Interface

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 109 | [ ] | File Upload > Browser-Limit (oft 100MB) | Upload schlägt fehl | Server-side Limit + Frontend-Check + Clear Error | **P1** |
| 110 | [ ] | Upload-Abbruch (Browser Tab geschlossen) | Orphan-Dateien | Cleanup bei Session-Timeout | **P1** |
| 111 | [ ] | Concurrent Uploads (10+ Dateien gleichzeitig) | Server-Überlastung | Queue-System + Max-Concurrent-Limit | **P1** |
| 112 | [ ] | SSE Connection Drop während Ingestion | Progress-Updates verloren | Reconnect-Logik + Polling-Fallback | **P1** |
| 113 | [ ] | Session Timeout während Batch-Review | Daten verloren | Session-Persistence (SQLite) + Warnung | **P1** |
| 114 | [ ] | Browser ohne JavaScript | HTMX funktioniert nicht | Graceful Degradation oder Clear Error | **P1** |
| 115 | [ ] | Mobile Browser (Touch-only) | Drag-and-Drop funktioniert nicht | Click-Fallback (File-Input) | **P1** |
| 116 | [ ] | CORS-Probleme (wenn Frontend ≠ Backend Host) | API-Calls blockiert | CORS-Config in FastAPI | **P1** |
| 117 | [ ] | Slow Network (Dial-up-ähnlich) | Timeouts, schlechte UX | Progress-Feedback + Retry-Option | **P1** |
| 118 | [ ] | Card-Edit: Concurrent Edit (Race Condition) | Daten überschrieben | Optimistic UI + Last-Write-Wins oder Locking | P2 |
| 119 | [ ] | Ingest-Button bei unvollständigen Pflichtfeldern | Ungültige Daten in Graphiti | Frontend-Validation + Backend-Validation | **P1** |
| 120 | [ ] | Group-ID Selector: Neue group_id eingeben | User-Tippfehler | Validation + Autocomplete von bekannten IDs | **P1** |

---

## 17. Metadaten-Suche (nach Dokumenttyp: ISBN→OpenLibrary, DOI→CrossRef, DE-ISBN→ISBN.de)

| # | Status | Case | Risiko | Mitigation | Phase |
|---|--------|------|--------|------------|-------|
| 121 | [ ] | ISBN erkannt aber ungültiges Format | Suche schlägt fehl | ISBN-Validation (10/13-stellig, Prüfziffer) | **P1** |
| 122 | [ ] | DOI erkannt aber ungültiges Format | Suche schlägt fehl | DOI-Validation (10.xxxx/...) | **P1** |
| 123 | [ ] | Weder ISBN noch DOI erkannt | Keine automatische API-Wahl | Titel-Suche anbieten + User wählt API | **P1** |
| 124 | [ ] | OpenLibrary: Kein Ergebnis | Buch nicht gefunden | Fallback zu Google Books anbieten | **P1** |
| 125 | [ ] | OpenLibrary: Mehrere Ergebnisse | Falsches Buch gewählt | Liste anzeigen, User wählt | **P1** |
| 126 | [ ] | OpenLibrary: Rate-Limiting | 429 Error | Backoff + Clear Error | **P1** |
| 127 | [ ] | Google Books: Rate-Limiting (100/Tag ohne Key) | Limit erreicht | Clear Error + Hinweis auf API-Key (P2) | **P1** |
| 128 | [ ] | CrossRef: DOI nicht gefunden | Paper nicht in CrossRef | Clear Error + manuell | **P1** |
| 129 | [ ] | CrossRef: Rate-Limiting | 429 Error | Backoff + Clear Error | **P1** |
| 130 | [ ] | ISBN.de: Kein Ergebnis | Deutsches Buch nicht gefunden | Fallback zu OpenLibrary | **P1** |
| 131 | [ ] | ISBN.de: API/Struktur-Änderung | Scraping bricht | Defensive Parsing + Clear Error | **P1** |
| 132 | [ ] | API nicht erreichbar (Netzwerk) | Search funktioniert nicht | Timeout + Clear Error | **P1** |
| 133 | [ ] | Suche während anderer Suche läuft | Race Condition | Debounce + Cancel vorheriger | **P1** |
| 134 | [ ] | Auto-Fill überschreibt User-Eingabe | Daten verloren | Bestätigung vor Überschreiben | **P1** |

---

## Zusammenfassung nach Phase

| Phase | Anzahl Cases | Beschreibung |
|-------|--------------|--------------|
| **P1** | 90 | Web Interface MVP (PDF/EPUB, Metadaten, Web UI, API-Suche) |
| **P2** | 20 | Batch & Polish, API-Keys, weitere APIs |
| **P3** | 2 | Markdown Support |
| **P4** | 4 | Testing & Docs |
| **P5** | 5 | CLI Headless-Mode |
| **P?** | 13 | Future / Low Priority |
| **Total** | **134** | |

---

## Änderungshistorie

| Datum | Änderung |
|-------|----------|
| 2026-01-19 | Initial: 96 Cases aus Review-Session |
| 2026-01-19 | +12 Cases: Sektion 15 "Metadaten/Entity-Types" (#97-#108) |
| 2026-01-19 | **PIVOT CLI→Web**: Phasen-Struktur angepasst, CLI-Cases (#88-92) → P5 |
| 2026-01-19 | +12 Cases: Sektion 16 "Web Interface" (#109-#120) |
| 2026-01-19 | +14 Cases: Sektion 17 "Metadaten-Suche" (#121-#134), typ-basierte API-Wahl statt Wasserfall |

---

*Dieses Dokument wird bei jeder `/prp-plan` Ausführung konsultiert.*
