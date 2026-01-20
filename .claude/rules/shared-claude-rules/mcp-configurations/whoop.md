#PITH:1.2
#MCP:whoop|stand:2026-01

!einsatz:Gesundheits+Fitness-Daten|Recovery,Strain,Sleep,Workouts
!aktivierung:discover_tools_by_words("whoop",enable=true)

## tools_daten
whoop-get-user-profile|whoop-get-user-body-measurements
whoop-get-recovery-collection|whoop-get-recovery-for-cycle
whoop-get-cycle-collection|whoop-get-cycle-by-id
whoop-get-sleep-collection|whoop-get-sleep-by-id|whoop-get-sleep-for-cycle
whoop-get-workout-collection|whoop-get-workout-by-id

## tools_auth
whoop-get-authorization-url|whoop-exchange-code-for-token
whoop-refresh-token|whoop-set-access-token|whoop-revoke-user-access

## kernkonzept_cycle
WHOOP=Physiological Cycles,NICHT Kalendertage
Cycle beginnt mit Aufwachen|endet mit nächstem Schlaf
aktueller Cycle hat kein end-Datum

## score_state
SCORED:vollständig ausgewertet|PENDING_SCORE:wird ausgewertet|UNSCORABLE:fehlende Daten
⚠️Nur SCORED Daten haben vollständige Werte

## recovery(0-100%)
recovery_score:Hauptindikator|resting_heart_rate:Ruhepuls(bpm)
hrv_rmssd_milli:HRV(ms)|spo2_percentage:Blutsauerstoff(WHOOP 4.0)
skin_temp_celsius:Hauttemperatur(WHOOP 4.0)

## sleep
nap:true=Mittagsschlaf|sleep_performance_percentage:Schlaf vs Bedarf
sleep_consistency_percentage|sleep_efficiency_percentage
stage_summary:Schlafphasen in Millisekunden(light,slow_wave,rem,awake)
sleep_needed:baseline+debt+strain+nap

## cycle(strain)
strain:Tages-Strain(0-21)|kilojoule:verbrannte Energie
average_heart_rate|max_heart_rate

## workout
sport_name|strain|distance_meter|altitude_gain_meter
zone_durations:zone_zero bis zone_five_milli
sport_ids:0=Running,1=Cycling,44=Yoga,45=Weightlifting,63=Walking,96=HIIT

## workflow
aktuelle_recovery:get-cycle-collection(limit:1)→get-recovery-for-cycle(cycle_id)
schlaf_woche:get-sleep-collection(start:7d zurück,end:heute)→Durchschnitte berechnen
training_analyse:get-workout-collection(30 Tage)→nach sport gruppieren→strain summieren

## wichtig
zeitstempel:UTC,timezone_offset für lokal|millisekunden:Schlafzeiten/3600000=Stunden
recovery braucht cycle_id|pagination:next_token für weitere Seiten

## rate_limit
100 Requests/Minute
