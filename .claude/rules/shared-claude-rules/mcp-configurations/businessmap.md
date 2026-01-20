#PITH:1.2
#MCP:businessmap|stand:2026-01

!einsatz:Enterprise Kanban|Workspaces,Boards,Cards,Subtasks,Parent-Child,Custom Fields
!aktivierung:discover_tools_by_words("businessmap",enable=true)

## tools_workspace(3)
list_workspaces|get_workspace|create_workspace

## tools_board(8)
list_boards|search_board|get_current_board_structure|create_board
get_columns|get_lanes|get_lane|create_lane

## tools_card_basic(7)
list_cards|get_card|get_card_size|create_card|move_card|update_card|set_card_size

## tools_card_details
get_card_comments|get_card_comment|get_card_custom_fields|get_card_types
get_card_outcomes|get_card_history|get_card_linked_cards

## tools_card_subtasks(3)
get_card_subtasks|get_card_subtask|create_card_subtask

## tools_card_hierarchy(6)
get_card_parents|get_card_parent|add_card_parent|remove_card_parent
get_card_parent_graph|get_card_children

## tools_andere
get_custom_field|get_workflow_cycle_time_columns|get_workflow_effective_cycle_time_columns
list_users|get_user|get_current_user|health_check|get_api_info

## board_struktur
Workspace→Board→Workflow→Columns(Backlog,In Progress,Done)+Lanes(Priority)→Cards→Subtasks

## parent_child_hierarchie
Initiatives→Epics→Stories→Tasks
get_card_parent_graph:komplette Hierarchie|get_card_children:Unter-Karten

## workflow
übersicht:list_workspaces→list_boards(workspace_id)→get_current_board_structure(board_id)
card_erstellen:get_current_board_structure(IDs)→get_card_types→create_card(board,column,lane,title,type)
card_bewegen:list_cards(filter)→get_current_board_structure(Ziel-Column)→move_card
subtasks:get_card_subtasks→create_card_subtask(card_id,description,assignee)
hierarchie:create_card(Epic)→create_card(Stories)→add_card_parent(story→epic)

## card_filter(list_cards)
card_ids|column_id|lane_id|type_id|assignee_ids|owner_ids
created_from/to|done_from/to|custom_fields|is_blocked|tags

## env_vars
BUSINESSMAP_API_TOKEN(required)|BUSINESSMAP_API_URL(required)
BUSINESSMAP_READ_ONLY_MODE:true→nur Lesen|BUSINESSMAP_DEFAULT_WORKSPACE_ID

## read_only_modus
create_*,update_*,move_card→blockiert|Lese-Ops→erlaubt

## fehler
401→Token prüfen|404→IDs via list_* verifizieren|403→Admin-Rechte
read_only→BUSINESSMAP_READ_ONLY_MODE=false
