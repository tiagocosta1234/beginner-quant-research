# Weekdays 17:05: writes the read-only S1 day report (account, today's closed trades, live record since 23 Oct, chance to still pass) and opens it in Notepad. No command needed.
$out = "D:\finance\scratch\s1_day_report.txt"
& "C:\Python314\python.exe" -B "D:\finance\beginner-quant-research\mt5\ea_research\ema12\s1_eod_report.py" 2>&1 | Out-File $out -Encoding utf8
Start-Process notepad.exe $out
