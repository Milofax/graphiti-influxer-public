#PITH:1.2
#MCP:xert|stand:2026-01

!einsatz:Radtraining-Analyse|Fitness Signature,Training Load,Workouts,Aktivitäten
!aktivierung:discover_tools_by_words("xert",enable=true)

## tools
xert-get-training-info:→Fitness Signature+Training Status+XSS+WOTD
xert-list-workouts:→alle gespeicherten Workouts
xert-get-workout:id→Workout-Details mit Intervallen
xert-download-workout:id+format(zwo|erg)→Export für Zwift/Trainer
xert-list-activities:from+to(Unix ms)→Aktivitäten im Zeitraum
xert-get-activity:id→Aktivität mit XSS+MPA-Daten
xert-upload-fit:→FIT-Datei hochladen

## fitness_signature
TP:Threshold Power(~FTP,Watt)|HIE:High Intensity Energy(anaerobe Kapazität,kJ)|PP:Peak Power(Watt)
LTP:Lower Threshold Power(~75% TP)

## training_status
Fresh(3-5 Stars):bereit für hartes Training
Tired(2 Stars):moderate Ermüdung
Very Tired(0-1 Stars):Erholung nötig

## training_load
High/Low Intensity Load:Optimal|Maintenance|Overreaching|Detraining

## XSS(Xert Strain Score)
wie TSS,aber basierend auf Fitness Signature|Focus XSS:nach Leistungsbereichen

## focus(athlete_type)
Sprint(<30s)|Pursuiter(30s-2min)|Breakaway(2-4min)|Climber(4-8min)
GC Specialist(8-20min)|Rouleur(20min-1h)|Endurance(>1h)

## MPA(Maximum Power Available)
startet bei PP|fällt bei Belastung>TP|erholt bei<TP
Breakthrough:MPA erreicht tatsächliche Leistung→Signature Update

## workflow
fitness_status:get-training-info→TP,HIE,PP,Status,WOTD
woche_analysieren:list-activities(7 Tage)→XSS summieren,Breakthroughs prüfen
workout_export:list-workouts→download-workout(id,format:"zwo")

## params
timestamps:Unix Millisekunden(from,to)
format:get-training-info optional für WOTD("zwo"|"erg")

## api_limits
KEIN Zugriff:Training Advisor,Workout-Planung,Forecast AI,Smart Workout Auswahl

## auth_setup
pfad:~/dotfiles/vendor/xert-mcp
setup:`cd ~/dotfiles/vendor/xert-mcp && npm run setup-auth`
interaktiv:fragt Email+Passwort→speichert Tokens in .env

## fehler:"No refresh token available"
ursache:mcp-funnel lädt .env NICHT automatisch
fix:env-Variablen manuell in ~/.mcp-funnel.json eintragen:
```json
"xert": {
  "command": "node",
  "args": ["/Users/mathias/dotfiles/vendor/xert-mcp/dist/server.js"],
  "env": {
    "XERT_ACCESS_TOKEN": "<aus .env>",
    "XERT_REFRESH_TOKEN": "<aus .env>"
  }
}
```
danach:Claude Code neu starten(`/exit`→neu starten)
