# Wrapper for auto-starting live_bot at Windows logon (Round 75, 2026-09-23).
#
# Not run automatically by anything yet -- registering the scheduled task that
# calls this is a separate, deliberate step (see register_manual_startup_task.ps1
# in this same directory). This script only prepares logging and launches
# main.py; it does not itself decide anything about trading.
#
# main.py has no file-logging of its own (logging.basicConfig logs to
# console only) -- when launched unattended at boot with no console open,
# that output would otherwise just be lost. This wrapper redirects it to a
# dated file under live_bot/logs/ instead.

$ErrorActionPreference = "Stop"
Set-Location "data\beginner-quant-research"

$logDir = "live_bot\logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}
$logFile = Join-Path $logDir ("manual_live_{0}.log" -f (Get-Date -Format "yyyy-MM-dd_HHmmss"))

# .env (BOT_MODE=live, the real account, Round 75 sizing) is read by main.py
# itself via load_dotenv() -- nothing live-specific needs to be passed here.
python -m live_bot.main *>&1 | Tee-Object -FilePath $logFile
