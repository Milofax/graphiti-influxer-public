# PITH Format Referenz

PITH ist ein kompaktes Notationsformat für Regeln und strukturierte Daten.

## Header

```
#PITH:1.2
#SYM:→=then,|=or,∧=and,∨=any,!=imp,:=kv,·=pending,►=doing,~=parked,✓=done,§=archiv
#RULE:1line=1block,nospace,.md=pith-aware
```

## Symbole

| Symbol | Bedeutung | Beispiel |
|--------|-----------|----------|
| `→` | then/führt zu | `fehler→stopp` |
| `|` | or/oder | `option_a|option_b` |
| `∧` | and/und | `bedingung_a∧bedingung_b` |
| `∨` | any/beliebig | `tool∨script∨manual` |
| `!` | important/Prinzip | `!prinzip:Wissen VOR Handeln` |
| `!!` | kritisch/MUSS | `!!regel:IMMER X vor Y\|verstoß:Konsequenz` |
| `:` | key:value | `name:wert` |
| `·` | pending | `·todo_item` |
| `►` | doing/in progress | `►aktueller_task` |
| `~` | parked/geparkt | `~später_machen` |
| `✓` | done/erledigt | `✓abgeschlossen` |
| `§` | archiv | `§nicht_mehr_relevant` |
| `💡` | Hinweis (Graphiti/Tool) | `💡 Was weißt du schon?` |
| `❤️` | Präferenz (optional) | `❤️ Version empfohlen` |
| `⚠️` | Warnung (Sicherheit) | `⚠️ Credentials erkannt!` |

## Struktur-Regeln

- **1 Zeile = 1 Block** - Keine mehrzeiligen Blöcke
- **Kein Leerraum** - Kompakt schreiben
- **Einrückung mit |** - Sub-Regeln einrücken

## Beispiele

### Einfache Regel
```
!wissen_erst:Wissen sichern VOR handeln|Unwissen aussprechen VOR raten
```

### Kritische Regel (MUSS befolgt werden)
```
!!tool_priority:Firecrawl IMMER vor WebSearch
  |verstoß:Credits verschwendet→User zahlt→3-Strikes
  |trigger:"such"|"recherchier"→Tool aktivieren
  |warnsignal:WebSearch-Gedanke=STOP→erst prüfen
```

### Regel mit Bedingungen
```
bei_fehler:Nach Fehler→transparenz→Stufe→handeln
  |stufen:trivial→Fix+weiter|logik→STOPP|pattern→3_strikes
  |warnsignal:"nur"|"schnell"=Stufe↑
```

### Todo-Liste
```
►doing:Aktueller Task
·pending:Nächster Task
✓done:Erledigter Task
~parked:Später machen
```

### Entscheidungen
```
[2025-01-12]|entscheidung:API-Design
  was:REST statt GraphQL
  warum:Team-Erfahrung,einfacher zu debuggen
  risiko:Mehr Endpoints nötig
```

## Wann Pith nutzen

**Gut für:**
- Kompakte Regeln
- Todo-Listen
- Entscheidungs-Logs
- State-Dateien

**Nicht gut für:**
- Lange Dokumentation
- Code-Beispiele
- Erklärende Texte

## Dateien

**WICHTIG:** Immer `.md` Endung verwenden!

- Claude Code lädt NUR `.md` Dateien als Regeln
- `.pith` Dateien werden IGNORIERT und nicht gelesen
- Pith-Syntax wird IN `.md` Dateien verwendet
- Pith-Header (`#PITH:1.2`) am Anfang = Datei enthält Pith-Notation
