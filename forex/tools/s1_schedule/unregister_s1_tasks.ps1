# Removes every task of the S1 live schedule (folder \S1Live\).  powershell -ExecutionPolicy Bypass -File unregister_s1_tasks.ps1
Get-ScheduledTask -TaskPath "\S1Live\" -ErrorAction SilentlyContinue | ForEach-Object { Unregister-ScheduledTask -TaskName $_.TaskName -TaskPath $_.TaskPath -Confirm:$false; Write-Host "removed $($_.TaskName)" }
