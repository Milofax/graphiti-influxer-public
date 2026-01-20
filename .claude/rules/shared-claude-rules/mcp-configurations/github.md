#PITH:1.2
#MCP:github|stand:2026-01

## entscheidung
!priorität:`gh` CLI bevorzugen→weniger Overhead,direkt,schneller
!fallback:GitHub MCP→wenn gh nicht verfügbar
gh_verfügbar?→JA→gh CLI nutzen|NEIN→MCP aktivieren
!ausnahme_mcp:mehrere API-Calls batchen|gh nicht installiert/authentifiziert

## mcp_fallback
!einsatz:GitHub API|Repos,Issues,PRs,Branches,Files,Code Search
!aktivierung:discover_tools_by_words("github",enable=true)

## tools_repos
search_repositories:query→Repos suchen
create_repository:→neues Repo
get_file_contents:owner+repo+path→Datei lesen
create_or_update_file:→Datei erstellen/aktualisieren
push_files:→mehrere Dateien in einem Commit
fork_repository|create_branch|list_commits

## tools_issues
list_issues|get_issue|create_issue|update_issue|add_issue_comment|search_issues

## tools_prs
list_pull_requests|get_pull_request|create_pull_request|merge_pull_request
get_pull_request_files|get_pull_request_status|get_pull_request_comments
get_pull_request_reviews|create_pull_request_review|update_pull_request_branch

## tools_andere
search_code:query→Code durchsuchen|search_users

## toolsets(optional aktivieren)
default:repos,issues,pull_requests
optional:code_security,actions,discussions,gists,notifications,projects
alle:--toolsets=all

## search_syntax
language:python|user:username|repo:owner/name|is:open|is:closed
label:bug|created:>2024-01-01

## workflow
repo_lesen:search_repositories(query)→get_file_contents(README.md)
issue_erstellen:create_issue(owner,repo,title,body,labels)→update_issue(assignees)
pr_workflow:create_branch→push_files→create_pull_request→get_pull_request_status→merge_pull_request

## pagination
per_page:max 100|page:Seitennummer

## rate_limits
authenticated:5000/Stunde|search:30/Minute
bei_überschreitung:403 Forbidden+X-RateLimit-Reset Header

## fehler
404→Repo/File nicht vorhanden oder keine Berechtigung|422→ungültige Parameter
409→Merge-Konflikt oder Branch existiert|403→Rate Limit oder fehlende Permissions
