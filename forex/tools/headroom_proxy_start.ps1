# Start the Headroom compression proxy on 127.0.0.1:6767 if nothing listens there yet.
# Used by the SessionStart hook (.claude/settings.local.json) and the per-user logon entry
# (HKCU\...\Run\HeadroomProxy6767). Runs detached; logs in D:\finance\scratch.
# The Headroom persistent install (headroom install apply) needs admin on this PC, hence this script.
$ErrorActionPreference = 'SilentlyContinue'

if (Get-NetTCPConnection -LocalPort 6767 -State Listen) {
    Write-Output 'headroom: proxy already running on 6767'
    exit 0
}

$exe = 'C:\Users\author\AppData\Local\Headroom\headroom\runtime\venv\Scripts\headroom.exe'
Start-Process -FilePath $exe -ArgumentList 'proxy', '--port', '6767', '--no-telemetry' `
    -WindowStyle Hidden `
    -RedirectStandardOutput 'D:\finance\scratch\headroom_proxy.out.log' `
    -RedirectStandardError 'D:\finance\scratch\headroom_proxy.err.log'

# Wait up to 45 s so a session started right after this sees a live proxy.
for ($i = 0; $i -lt 45; $i++) {
    if (Get-NetTCPConnection -LocalPort 6767 -State Listen) {
        Write-Output "headroom: proxy started on 6767 (${i}s)"
        exit 0
    }
    Start-Sleep -Seconds 1
}
Write-Output 'headroom: proxy did not come up in 45 s, see D:\finance\scratch\headroom_proxy.err.log'
exit 0
