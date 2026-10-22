param([string]$Time)
# Dated reminders of the S1 live schedule. A daily task runs this at 10:00 and at 17:10; it fires the alarm only when today's date and the given time are in the list
# (one-off scheduled tasks showed a broken next-run time across the 25 Oct clock change, daily tasks do not).
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$items = @(
    @{ d = "2026-10-24"; t = "10:00"; title = "Batch 2 slot"; text = "Saturday 24 Oct 10:00: optional slot for blind batch 2 (5-6 hours, FX Replay, calendar order, no peeking). Read the FX Replay Trades page within a week of playing." },
    @{ d = "2026-10-31"; t = "10:00"; title = "Batch 2 backup slot"; text = "Saturday 31 Oct 10:00: backup slot for blind batch 2, and the last day to read the FX Replay Trades page if you played on 24 Oct." },
    @{ d = "2026-11-22"; t = "10:00"; title = "S1 schedule ends today"; text = "22 Nov: the 30 day schedule expires. Re-plan the next block with Claude (30 Nov is day 27, 22 Dec is day 43)." },
    @{ d = "2026-11-05"; t = "17:10"; title = "S1 - 10 trade review"; text = "10th business day. Review the live trades so far: mean R, fills against the plan (0.30 USD), rule compliance. Pause if the mean is 0 or below, or 4 of the first 6 lost. Tell Claude." }
)
$today = Get-Date -Format "yyyy-MM-dd"
foreach ($i in $items) { if ($i.d -eq $today -and $i.t -eq $Time) { & "$root\s1_alarm.ps1" -Title $i.title -Text $i.text -Beep 15 } }
