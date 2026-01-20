#PITH:1.2
#MCP:context7|stand:2026-01

!!erst:Bei GitHub-Repos/Libraries→IMMER ZUERST Context7 versuchen
  |workflow:resolve-library-id(repo-name)→gefunden?→query-docs nutzen
  |verstoß:Direkt andere Tools nutzen ohne Context7 zu prüfen→Potentiell veraltete/unvollständige Infos
  |trigger:GitHub-URL|Library-Name|Framework|"docs"|"documentation"|"how to use"
  |warnsignal:Recherche-Gedanke ohne resolve-library-id=STOP→erst Context7 prüfen

!zuständig:Öffentliche Library/Framework-Dokumentation|GitHub-Repos+Projekte|61k+ Libraries indexiert|API-Docs,Code-Beispiele,Best Practices
!nicht_zuständig:Private/interne Docs|Beliebige Webseiten|News,Artikel|Allgemeine Web-Suche
!aktivierung:discover_tools_by_words("context7",enable=true)

## tools
resolve-library-id:libraryName→Library-ID("/owner/repo"|"/websites/domain")
query-docs:context7CompatibleLibraryID+topic?(optional)+tokens?(optional)→Docs

## library-ids(häufig)
/vercel/next.js|/vercel/ai|/anthropics/claude-code|/websites/ui_shadcn
/prisma/docs|/langchain-ai/langgraph|/better-auth/better-auth
insgesamt:61.920+ Libraries indexiert

## workflow
unbekannt:resolve-library-id(name)→query-docs(id,topic)
bekannt:query-docs direkt mit ID
mehrere:query-docs für jede Library separat

## params
query-docs:context7CompatibleLibraryID(required)|topic(filter)|tokens(max)
resolve-library-id:libraryName(string)

## tipps
topic-filter→reduziert Tokens|token-budget setzen|library-id cachen
ideal:Aktuelle APIs,Code-Beispiele,Best Practices,Migration
nicht-ideal:Allgemeine Konzepte,historische Versionen,private Docs

## fehler
nicht_gefunden→resolve-library-id nutzen|leer→breiteren Begriff
token_überschritten→tokens Parameter reduzieren
