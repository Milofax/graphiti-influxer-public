#PITH:1.2
#MCP:firecrawl|stand:2026-01

!!websuche:Firecrawl IMMER vor WebSearch/WebFetch
  |verstoß:Credits verschwendet→User zahlt $19/Mo→3-Strikes→Session kompromittiert
  |trigger:"such"|"recherchier"|"find"|"web"→sofort discover_tools_by_words("firecrawl",enable=true)
  |warnsignal:WebSearch/WebFetch-Gedanke=STOP→Firecrawl erst aktivieren+nutzen
  |ausnahme:NUR wenn Firecrawl keine Credits mehr hat

!zuständig:Web-Recherche,Scraping|Web-Suche,News,Artikel,beliebige Webseiten|Strukturierte Datenextraktion|JS-rendered Seiten
!nicht_zuständig:Bekannte Library/Framework-Docs|Private/interne Dokumentation
!aktivierung:discover_tools_by_words("firecrawl",enable=true)

## tools
firecrawl_scrape:url→einzelne Seite(schnellstes Tool)
firecrawl_search:query→Web-Suche mit Extraktion
firecrawl_map:url+limit?+search?→URLs entdecken(ohne Content laden)
firecrawl_crawl:url+limit+maxDiscoveryDepth+includePaths?+excludePaths?→multi-page(⚠️Token-Limit)
firecrawl_extract:urls+prompt+schema→strukturierte Daten
firecrawl_check_crawl_status:job_id→async Status
⚠️firecrawl_agent:NICHT NUTZEN(Timeout)

## dokument_parsing(automatisch)
PDF:.pdf(1 Credit/Seite,OCR für Scans)
Excel:.xlsx,.xls→HTML-Tabellen
Word:.docx,.doc,.odt,.rtf

## scrape_params
url(required)|formats:["markdown"]|onlyMainContent:true|maxAge:172800000(Cache,500% schneller)
waitFor:ms für JS|mobile:boolean

## map_params
url(required)|limit:max URLs|search:keyword filter in URLs

## crawl_params
url(required)|limit:max Seiten|maxDiscoveryDepth:Tiefe
includePaths:["/docs/*"]|excludePaths:["/blog/*"]

## search_params
query(required)|limit|scrapeOptions:{formats,onlyMainContent}
!!sources:OBJEKT-ARRAY,NICHT String-Array
  |FALSCH:sources:["web"]→ValidationError
  |RICHTIG:sources:[{"type":"web"}]
  |optionen:{"type":"web"}|{"type":"news"}|{"type":"images"}

## extract_params
urls:[array]|prompt:"Extract X"|schema:{type:"object",properties:{name:{type:"string"},price:{type:"number"}},required:["name"]}

## actions(für dynamische Seiten)
actions:[{type:"write",text:"email"},{type:"press",key:"Tab"},{type:"write",text:"pw"},{type:"click",selector:"button[type='submit']"},{type:"wait",milliseconds:2000}]
typen:click|write|press|scroll|wait|screenshot

## search_operators
""=exakte Phrase|-=ausschließen|site:=nur Domain|inurl:|intitle:|related:

## workflow
docs_scrapen:map(url)→relevante URLs filtern→scrape(jede URL)
produkt_recherche:search(query)→extract(top URLs,schema)
news:search("site:domain.com topic",sources:[{"type":"news"}])

## performance
maxAge nutzen(Cache)|onlyMainContent:true|map vor crawl|limits setzen

## credits
scrape:1/Seite|crawl:1/Seite|map:1/Seite|search:2/10 Ergebnisse
hobby:$19/Mo,3000 Credits,5 concurrent

## fehler
timeout→waitFor erhöhen|leer→waitFor oder actions|token_overflow→limit+onlyMainContent

