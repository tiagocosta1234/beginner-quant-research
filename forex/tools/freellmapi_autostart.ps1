# SessionStart hook: start the local FreeLLMAPI router (data\tools\freellmapi)
# if nothing is listening on its API port yet. Runs detached, so it keeps running
# after the Claude Code session ends. Log: data\scratch\freellmapi_dev.log
$ErrorActionPreference = 'SilentlyContinue'

if (Get-NetTCPConnection -LocalPort 3001 -State Listen) {
    Write-Output 'freellmapi: already running on 3001'
    exit 0
}

$dir = 'data\tools\freellmapi'
$log = 'data\scratch\freellmapi_dev.log'
Start-Process -FilePath 'cmd.exe' `
    -ArgumentList '/c', "npm run dev > `"$log`" 2>&1" `
    -WorkingDirectory $dir -WindowStyle Hidden
Write-Output "freellmapi: started (log $log)"
exit 0
