#PITH:1.2
#MCP:vscode|stand:2026-01

!einsatz:VS Code Fernsteuerung|Datei-Navigation,Code-Editing,Terminal-Befehle
!voraussetzung:VS Code 1.99+ muss laufen+MCP Server aktiv
!aktivierung:discover_tools_by_words("vscode",enable=true)

## tools
vscode__open_file:path→Datei öffnen
vscode__get_active_editor:→aktiven Editor/Datei abrufen
vscode__get_selection:→aktuelle Textauswahl
vscode__replace_selection:→Auswahl ersetzen
vscode__insert_text:text+position(line,column)→Text einfügen
vscode__run_command:command→VS Code Command ausführen
vscode__get_diagnostics:uri→Fehler/Warnungen abrufen
vscode__run_terminal_command:command→Terminal-Befehl
vscode__get_workspace_folders:→Workspace-Ordner
vscode__search_files:pattern→Dateien suchen

## wichtige_commands
workbench.action.files.save|workbench.action.files.saveAll
editor.action.formatDocument|editor.action.commentLine|editor.action.rename
workbench.action.quickOpen|workbench.action.gotoLine|editor.action.revealDefinition
workbench.action.terminal.new|workbench.action.terminal.focus
workbench.action.closeActiveEditor|workbench.action.reloadWindow

## diagnostics_severity
1=Error|2=Warning|3=Information|4=Hint

## workflow
datei_editieren:open_file(path)→get_active_editor→insert_text(text,position)
fehler_beheben:get_diagnostics(uri)→open_file→replace_selection(fix)
format+save:run_command("editor.action.formatDocument")→run_command("workbench.action.files.save")
build:run_terminal_command("npm run build")→run_terminal_command("npm test")
dateien_finden:search_files("**/*.test.ts")→open_file(erste)

## editor_state
active_editor:fokussierter Tab|selection:markierter Text
cursor_position:Zeile/Spalte|visible_range:sichtbarer Bereich

## einschränkungen
VS Code muss offen sein|nur lokale Instanz(kein Remote)
einige Commands erfordern User-Bestätigung

## fehler
connection_refused→VS Code öffnen|file_not_found→absoluten Pfad
command_not_found→Command-ID prüfen|no_active_editor→erst Datei öffnen
