param([string]$Title = "S1 live", [string]$Text = "", [int]$Beep = 20)
# Loud reminder for the S1 live schedule: repeating system sound for about $Beep rounds plus a topmost message box that stays until OK is pressed. Sends nothing, places nothing.
Add-Type -AssemblyName System.Windows.Forms
$job = Start-Job -ScriptBlock { param($n) for ($i = 0; $i -lt $n; $i++) { [System.Media.SystemSounds]::Exclamation.Play(); Start-Sleep -Milliseconds 800; try { [console]::Beep(1000, 250) } catch {}; Start-Sleep -Milliseconds 500 } } -ArgumentList $Beep
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true; $owner.ShowInTaskbar = $false; $owner.WindowState = 'Minimized'; $owner.Show()
[void][System.Windows.Forms.MessageBox]::Show($owner, $Text, $Title, [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
$owner.Close()
Stop-Job $job -ErrorAction SilentlyContinue; Remove-Job $job -Force -ErrorAction SilentlyContinue
