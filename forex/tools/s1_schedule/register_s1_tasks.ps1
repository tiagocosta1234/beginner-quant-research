# Registers the S1 live schedule as Windows scheduled tasks in the folder \S1Live\ (current user, only while logged on; expiry 2026-11-22).
# Run:    powershell -ExecutionPolicy Bypass -File register_s1_tasks.ps1        Remove: powershell -ExecutionPolicy Bypass -File unregister_s1_tasks.ps1
# Nothing here trades or arms anything; the tasks only show reminders and run the read-only morning brief.
$ErrorActionPreference = "Stop"
$root = "D:\finance\beginner-quant-research\mt5\tools\s1_schedule"; $ps = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"; $folder = "\S1Live\"
$first = "2026-10-23"; $end = "2026-11-22T23:59:59"; $user = "$env:USERDOMAIN\$env:USERNAME"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$wk = @("Monday", "Tuesday", "Wednesday", "Thursday", "Friday"); $bed = @("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday")
function Reg($name, $trigger, $args_, $desc) {
    $a = New-ScheduledTaskAction -Execute $ps -Argument $args_
    Register-ScheduledTask -TaskName $name -TaskPath $folder -Action $a -Trigger $trigger -Principal $principal -Settings $settings -Description $desc -Force | Out-Null
    Write-Host "registered $folder$name"
}
function AlarmArgs($title, $text, $beep) { return "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$root\s1_alarm.ps1`" -Title `"$title`" -Text `"$text`" -Beep $beep" }
function Weekly($days, $time, $from) { $t = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $days -At $time; $t.StartBoundary = "${from}T${time}:00"; $t.EndBoundary = $end; return $t }
function Once($when) {                                                    # a weekly trigger limited to that one date: its next-run time is computed correctly across the 25 Oct clock change (a plain Once trigger showed a bogus next run)
    $d = [datetime]::ParseExact($when, "yyyy-MM-dd HH:mm", $null); $t = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $d.DayOfWeek -At $d.ToString("HH:mm")
    $t.StartBoundary = $d.ToString("yyyy-MM-ddTHH:mm:00"); $t.EndBoundary = $d.ToString("yyyy-MM-ddT23:59:59"); return $t
}
Reg "S1-0650-wake" (Weekly $wk "06:50" $first) (AlarmArgs "S1 LIVE DAY - wake up" "06:50. London window is 08:00-08:15. Be at the desk by 07:30. One trade at most, the size card opens by itself at 07:35 and 07:56, log the Notion row BEFORE entering." 40) "S1 live schedule"
Reg "S1-0720-up" (Weekly $wk "07:20" $first) (AlarmArgs "S1 - get up now" "07:20. Up and at the desk. The morning brief opens at 07:35." 40) "S1 live schedule"
Reg "S1-0735-brief" (Weekly $wk "07:35" $first) "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$root\morning_brief.ps1`"" "S1 morning brief (read-only)"
Reg "S1-0755-chart" (Weekly $wk "07:55" $first) (AlarmArgs "S1 - window opens at 08:00" "07:55. At the chart. Algo Trading OFF, no position open. Setup candle, then the lots from the size card (it opens at 07:56), then the Notion row, then the order with SL and TP attached." 25) "S1 live schedule"
Reg "S1-0756-card" (Weekly $wk "07:56" $first) "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$root\size_card.ps1`"" "S1 size card (read-only)"
Reg "S1-0816-closed" (Weekly $wk "08:16" $first) (AlarmArgs "S1 - window closed" "08:16. The London window is over. No trade today = add the No trade row in Notion now. If a trade is open, check that SL and TP are attached." 20) "S1 live schedule"
Reg "S1-1705-dayover" (Weekly $wk "17:05" $first) "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$root\eod_report.ps1`"" "S1 day report (read-only): account, today's trades, live record, chance to still pass"
Reg "S1-Fri-1730-review" (Weekly @("Friday") "17:30" $first) (AlarmArgs "S1 - weekly review" "Friday review: R this week, balance against the 92,000 floor, rule compliance, Notion rows complete. Ask Claude to update CLAUDE.md and decide commits." 20) "S1 live schedule"
Reg "S1-2315-bed" (Weekly $bed "23:15" "2026-10-22") (AlarmArgs "S1 - bedtime" "23:15. Wrap up. Bed by 23:30: the London window is at 08:00 and you are up at 06:50." 20) "S1 bedtime reminder"
function Daily($time, $from) { $t = New-ScheduledTaskTrigger -Daily -At $time; $t.StartBoundary = "${from}T${time}:00"; $t.EndBoundary = $end; return $t }
Reg "S1-cal-1000" (Daily "10:00" "2026-10-24") "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$root\s1_calendar.ps1`" -Time 10:00" "S1 dated reminders at 10:00 (batch 2 slots 24 and 31 Oct, schedule end 22 Nov)"
Reg "S1-cal-1710" (Daily "17:10" "2026-10-23") "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$root\s1_calendar.ps1`" -Time 17:10" "S1 dated reminders at 17:10 (10 trade review 5 Nov)"
Write-Host "done"
