#PITH:1.2
#MCP:macos-automator|stand:2026-01

!einsatz:macOS Automatisierung|AppleScript+JXA ausführen|200+ vorgefertigte Scripts
!aktivierung:discover_tools_by_words("macos automator",enable=true)

## tools
execute_script:script ausführen(AppleScript oder JXA)
get_scripting_tips:Knowledge Base durchsuchen(200+ Scripts)

## execute_script_quellen(mutually exclusive)
script_content:Inline Script-Code
script_path:absoluter Pfad zu Script-Datei
kb_script_id:ID eines vorgefertigten Scripts

## execute_script_params
language:"applescript"|"jxa"|timeout_seconds:30(default)
input_data:{key:value}→Parameter für kb_script

## get_scripting_tips_params
list_categories:true→alle Kategorien|category:z.B."safari"
search_term:Suche in Kategorie|limit:Ergebnisse begrenzen

## kategorien
finder|safari|chrome|mail|calendar|terminal|system|music|...

## häufige_kb_scripts
safari_get_front_tab_url|safari_get_all_tabs_urls|safari_open_url
finder_create_new_folder_desktop|finder_create_folder_at_path
systemsettings_toggle_dark_mode_ui|music_playback_controls
terminal_app_run_command_new_tab

## workflow
browser:get_scripting_tips(category:"safari")→execute_script(kb_script_id)
dateien:execute_script(script_content:"tell application \"Finder\"...")
system:execute_script(kb_script_id:"systemsettings_toggle_dark_mode_ui")

## applescript_basics
tell_block:tell application "App" ... end tell
variablen:set myVar to "value"
dialoge:display dialog "Text"|display notification "Text"

## jxa_basics
const app = Application('Finder');app.desktop.files()

## permissions_required
Automation:System Settings>Privacy>Automation
Accessibility:System Settings>Privacy>Accessibility(für UI-Scripting)

## fehler
not_authorized→System Settings>Privacy|app_not_found→exakten App-Namen
syntax_error→Script Editor testen|timeout→timeout_seconds erhöhen
