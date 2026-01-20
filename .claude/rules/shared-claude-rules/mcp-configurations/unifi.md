#PITH:1.2
#MCP:unifi|stand:2026-01

!einsatz:UniFi Network Controller|Firewall,Traffic,Ports,QoS,VPN,WLANs,Geräte,Clients,Stats
!wichtig:State-ändernde Tools erfordern confirm=true
!aktivierung:discover_tools_by_words("unifi",enable=true)

## tools_firewall
list_firewall_policies|get_firewall_policy_details|toggle_firewall_policy
create_firewall_policy|update_firewall_policy|list_firewall_zones|list_ip_groups

## tools_traffic
list_traffic_routes|get_traffic_route_details|toggle_traffic_route|create_traffic_route

## tools_ports
list_port_forwards|get_port_forward|toggle_port_forward|create_port_forward

## tools_qos
list_qos_rules|get_qos_rule_details|toggle_qos_rule_enabled|create_qos_rule

## tools_networks
list_networks|get_network_details|create_network(⚠️disabled by default)
list_wlans|get_wlan_details|create_wlan(⚠️disabled by default)

## tools_vpn
list_vpn_clients|get_vpn_client_details|update_vpn_client_state|list_vpn_servers

## tools_devices
list_devices|get_device_details|rename_device
reboot_device(⚠️disabled)|adopt_device(⚠️disabled)|upgrade_device(⚠️disabled)

## tools_clients
list_clients|get_client_details|list_blocked_clients|rename_client|force_reconnect_client
block_client(⚠️disabled)|unblock_client|authorize_guest(⚠️disabled)

## tools_stats
get_network_stats|get_client_stats|get_device_stats|get_top_clients
get_dpi_stats|get_alerts|get_system_info|get_network_health

## tools_meta
unifi_tool_index:alle Tools+Schemas|unifi_async_start|unifi_async_status

## lazy_loading
default:nur 3 Meta-Tools registriert(~200 Tokens,96% Ersparnis)
eager:UNIFI_TOOL_REGISTRATION_MODE=eager

## permissions(env vars)
UNIFI_PERMISSIONS_NETWORKS_CREATE=true|UNIFI_PERMISSIONS_DEVICES_UPDATE=true
UNIFI_PERMISSIONS_CLIENTS_UPDATE=true

## confirm_required
ALLE state-ändernden Ops:{"confirm":true}

## workflow
übersicht:get_system_info→get_network_health→list_devices→list_clients
traffic:get_top_clients(limit:10)→get_dpi_stats→get_client_stats(mac)
firewall:list_firewall_zones→list_ip_groups→create_simple_firewall_policy(confirm:true)
port_forward:create_simple_port_forward(name,ports,ip,protocol,confirm:true)

## async_ops
lange Ops:unifi_async_start(tool,arguments)→jobId→unifi_async_status(jobId)

## controller_erkennung
auto:UniFi OS(/proxy/network/api)|Standalone(/api)
override:UNIFI_CONTROLLER_TYPE=proxy|direct

## fehler
404→falscher Controller-Typ|permission_denied→ENV setzen|confirm_required→confirm:true
