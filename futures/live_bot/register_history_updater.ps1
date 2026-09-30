# Registers a Windows scheduled task that runs live_bot/update_history.py once a day,
# after the US close, so the two history caches (the bracket bot's POC filter and the
# Combined bot's meta-model inputs) stay continuous whether or not a bot is running.
#
# The updater is read-only against the broker (login + bar history; no orders, no
# account or position calls). It never starts a bot or places a trade.
#
# 22:30 local = 17:30 ET most of the year (18:30 ET in the week between the EU and US
# clock changes) -- always after 16:05 ET, when the day's last bar is final.
# If the PC is off or asleep at 22:30, it runs as soon as the PC is next on.
#
# Run it in PowerShell (no admin needed for a task that runs as you):
#   powershell -ExecutionPolicy Bypass -File "live_bot\register_history_updater.ps1"
#
# Check it:        Get-ScheduledTask -TaskName "live_bot-history-updater"
# Run it now:      Start-ScheduledTask -TaskName "live_bot-history-updater"
# Its log:         live_bot\logs\update_history.log (exit code in live_bot\state\history_updater.json)
# Turn it off:     Unregister-ScheduledTask -TaskName "live_bot-history-updater" -Confirm:$false

$ErrorActionPreference = "Stop"

$taskName = "live_bot-history-updater"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

# pythonw: same interpreter as `python`, but no console window pops up at 22:30.
$python = (Get-Command python).Source
$pythonw = Join-Path (Split-Path $python) "pythonw.exe"
if (-not (Test-Path $pythonw)) { $pythonw = $python }

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "-m live_bot.update_history" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At "22:30"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 10)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Tops up live_bot's daily and session history caches from the broker's 1-minute bars (read-only). 2026-09-30." `
    -Force

Write-Host "Registered '$taskName': daily at 22:30, runs at next start if missed."
Write-Host "Run it now with: Start-ScheduledTask -TaskName '$taskName'"
