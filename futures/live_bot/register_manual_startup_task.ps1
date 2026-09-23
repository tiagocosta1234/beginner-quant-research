# Registers the trader's live $250K bot to start automatically at Windows logon.
#
# YOU run this yourself -- Claude prepared it but won't register it, same
# reason it won't launch main.py directly: this makes the bot start trading
# real money with zero human action from this point forward on every boot,
# which is the exact line "I don't execute trades myself" is meant to hold,
# just recurring instead of one-time.
#
# Run this in an elevated (Run as Administrator) PowerShell window:
#   powershell -ExecutionPolicy Bypass -File "live_bot\register_manual_startup_task.ps1"
#
# To check it later:      Get-ScheduledTask -TaskName "the trader-250K-LiveBot"
# To turn it off:         Unregister-ScheduledTask -TaskName "the trader-250K-LiveBot" -Confirm:$false
# To run it right now (without waiting for a reboot): Start-ScheduledTask -TaskName "the trader-250K-LiveBot"

$ErrorActionPreference = "Stop"

$taskName = "the trader-250K-LiveBot"
$scriptPath = "live_bot\start_manual_live.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

# At logon for this user specifically (not "at startup"/SYSTEM), so it runs in
# your normal user context -- correct PATH, correct access to your own .env.
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Restart up to 3 times, 5 minutes apart, if the process dies -- the plan
# flagged "it has silently stopped before" as a real, observed failure mode.
# Does NOT restart it after a governor hard-breach exit (DAILY_LOSS_LIMIT /
# TRAILING_DRAWDOWN / BALANCE_RECONCILIATION_MISMATCH) within the same logon
# session in a way that bypasses that breach -- main.py still requires a human
# to review and manually restart after those, this only recovers from crashes,
# not from a risk governor deciding to stop on purpose.
$settings = New-ScheduledTaskSettingsSet `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable -DontStopOnIdleEnd -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Starts live_bot (the trader, real $250K Freedom Test account) at logon. Round 75, 2026-09-23." `
    -Force

Write-Host "Registered '$taskName'. It will start automatically at your next logon."
Write-Host "To start it right now instead of waiting: Start-ScheduledTask -TaskName '$taskName'"
