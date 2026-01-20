#PITH:1.2
#MCP:morgen|stand:2026-01

!einsatz:Kalender-Management+Terminplanung|Morgen vereint mehrere Kalender-Accounts
!aktivierung:discover_tools_by_words("morgen",enable=true)

## tools
morgen_list_calendars:→alle Kalender auflisten
morgen_list_events:account_id+calendar_ids+start+end→Events mit Datums-Filter
morgen_create_event:account_id+calendar_id+title+start+duration→neuen Termin
morgen_update_event:event_id+account_id+calendar_id+änderungen→Termin aktualisieren
morgen_delete_event:event_id+account_id+calendar_id→Termin löschen
morgen_update_calendar_metadata:calendar_id+account_id+override_name?+override_color?→Anzeige ändern

## ⚠️datetime_format
RICHTIG:2026-01-20T10:00:00(LocalDateTime,KEIN Z-Suffix)
FALSCH:2026-01-20T10:00:00Z
timezone:separat als Parameter(Europe/Berlin,America/New_York,etc.)

## create_event_params
account_id+calendar_id+title+start+duration(required)
duration:ISO 8601(PT1H,PT30M,PT2H30M)
optional:time_zone|is_all_day|description|location|participants:[emails]|free_busy_status|privacy

## update_event_wichtig
bei_zeitänderung:start+duration+time_zone+is_all_day ALLE angeben
wiederkehrend:series_update_mode:"single"|"future"|"all"

## workflow
tagesübersicht:list_calendars→list_events(start:00:00,end:23:59)
meeting_planen:list_calendars→list_events(freie Slots)→create_event
verschieben:list_events(event_id finden)→update_event(neues start+duration+time_zone+is_all_day)

## fehler
invalid_datetime→LocalDateTime OHNE Z|calendar_not_found→list_calendars für IDs
event_not_found→list_events zur Verifizierung
