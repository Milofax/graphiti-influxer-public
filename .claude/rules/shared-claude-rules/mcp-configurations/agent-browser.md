#PITH:1.2
#CLI:agent-browser|stand:2026-01

!!snapshot_first:IMMER snapshot VOR jeder Interaktion
  |verstoß:Ohne Snapshot→Refs unbekannt→click/fill schlägt fehl→Debug-Zeit
  |workflow:open(url)→snapshot→refs lesen(@e1,@e2...)→click/fill mit Ref
  |warnsignal:click/fill ohne vorheriges snapshot=STOP→erst snapshot

!!refs_bevorzugen:Refs(@e1,@e2) IMMER vor anderen Selektoren
  |grund:Refs sind deterministisch+session-gebunden→stabilste Interaktion
  |priorität:@e1(Ref)>CSS>[role=button]>text()
  |fallback:Wenn kein Ref→CSS mit data-testid→role→text

!installation:npm install -g agent-browser && agent-browser install
!hilfe:agent-browser --help→zeigt alle verfügbaren Befehle
!einsatz:Browser-Automatisierung für AI-Agenten|Deterministische Element-Interaktion via Refs
!nicht_zuständig:Headless-Tests|CI/CD-Pipelines(→Playwright)|Performance-Testing

## commands
open:url[--session name]→Browser öffnen+navigieren
click:ref|selector[--session]→Element anklicken
fill:ref|selector --text "value"[--session]→Text eingeben
select:ref|selector --value "option"[--session]→Dropdown auswählen
hover:ref|selector[--session]→über Element hovern
scroll:[--direction up|down][--session]→Seite scrollen
type:--text "value"[--session]→Tastatureingabe(ohne Element)
press:--key Enter|Tab|...[--session]→Taste drücken
screenshot:[--session]→Screenshot erstellen
snapshot:[--session]→Seite analysieren+Refs generieren(WICHTIG!)
wait:--seconds N[--session]→warten
close:[--session]→Browser schließen

## refs
@e1,@e2,...:Automatisch generierte Element-Referenzen nach snapshot
!vorteil:Eindeutig+deterministisch|Kein komplexer Selektor nötig|Session-gebunden
!lebensdauer:Gültig bis nächster snapshot|Nach Navigation→neuer snapshot nötig
beispiel:snapshot zeigt @e1="Submit Button"→click @e1

## session_management
!persistenz:--session name→Browser-Session benennen+wiederverwenden
!workflow:open --session myapp→...interaktionen...→close --session myapp
!vorteil:Login-State erhalten|Mehrere Tabs/Fenster|Parallele Sessions
!default:Ohne --session→temporäre Session(schließt automatisch)

## workflow
login:open(url)→snapshot→fill(@email)→fill(@password)→click(@submit)→snapshot(verify)
navigation:open(url)→snapshot→click(@link)→wait→snapshot(neue Refs)
formular:snapshot→fill(@field1)→fill(@field2)→select(@dropdown)→click(@submit)
scraping:open→snapshot→Refs für Daten-Elemente→extract

## selektoren(Fallback wenn kein Ref)
1:@e1,@e2(Refs von snapshot)→stabilste+bevorzugt
2:CSS([data-testid='submit'])→wenn kein Ref
3:role([role=button][name='Submit'])→accessibility
4:text(text()='Submit')→user-sichtbar|fragil

## einschränkungen
keine_headless_option|CAPTCHAs nicht lösbar|2FA braucht manuelle Intervention
iframes:Extra snapshot im iframe-Kontext nötig

## fehler
element_not_found→snapshot wiederholen|Refs prüfen|CSS-Fallback
stale_ref→Nach Navigation/Änderung→neuer snapshot nötig
session_not_found→--session Name prüfen|Session existiert?
timeout→wait --seconds erhöhen|Seite langsam?

## tipps
IMMER snapshot vor Interaktion|Refs in Variablen speichern
--session für komplexe Workflows|screenshot bei Fehlern für Debugging
Nach jeder Navigation neuer snapshot
