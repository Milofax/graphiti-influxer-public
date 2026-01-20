#PITH:1.2
#TOOL:1password|stand:2026-01

!zuständig:SSH-Keys|Secrets|API-Keys|Credentials
!nie_manuell:SSH-Keys NIEMALS in ~/.ssh/ kopieren|NIEMALS aus 1Password exportieren|NIEMALS op read für Keys

## ssh_agent
!prinzip:1Password SSH Agent liefert Keys automatisch|Kein manuelles Handling
config:~/.ssh/config→IdentityAgent "~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"
keys_prüfen:ssh-add -l→zeigt alle verfügbaren Keys
verbinden:ssh user@host→1Password bietet passenden Key an(automatisch)

## workflow_ssh
richtig:ssh mathi@192.168.1.12→1Password Agent→Key automatisch
falsch:op read→~/.ssh/→ssh -i ~/.ssh/key→VERBOTEN
bei_key_fehlt:In 1Password prüfen ob Key existiert+für SSH Agent aktiviert

## cli(op)
prüfen:op --version|op whoami
vaults:op vault list
items:op item list|op item list --categories "SSH Key"
suchen:op item get "Name" --format json
secrets:op read "op://vault/item/field"→für API-Keys,Tokens(NICHT für SSH)

## aktivierung_ssh_agent
1password_app:Settings→Developer→Use the SSH Agent→aktivieren
key_freigeben:Item öffnen→Configure for SSH Agent→aktivieren

## anti_pattern
!verboten:op read für SSH private keys→IMMER Agent nutzen
!verboten:Keys nach ~/.ssh/ kopieren→1Password Agent macht das obsolet
!verboten:-i flag mit lokaler Key-Datei wenn 1Password Agent aktiv

## fehler
key_nicht_angeboten:Key in 1Password für SSH Agent aktivieren
permission_denied:ssh-add -l prüfen→Key vorhanden?→1Password entsperrt?
agent_socket_fehlt:1Password App öffnen→Developer Settings prüfen
too_many_auth_failures:~/.ssh/config prüfen→Host-Einträge fehlen
  |ursache:Agent bietet ALLE Keys→Server bricht ab
  |lösung:Host-Eintrag mit HostName+Port+User
  |NICHT:IdentitiesOnly yes(blockiert Agent-Keys)

## ssh_config_beispiel
```
Host ubuntu-vm 192.168.1.10
    HostName 192.168.1.10
    Port 2222
    User dockeradmin
```
