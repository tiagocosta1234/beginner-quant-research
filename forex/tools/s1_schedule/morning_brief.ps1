# 07:35 on weekdays: runs the read-only pre-London brief (london_brief.py: terminal state, balance, floor, spread, Asia range, EMA12 / ATR, stop / target table) and opens it in Notepad.
$out = "D:\finance\scratch\london_brief_today.txt"
"S1 morning brief, local clock $(Get-Date -Format 'ddd dd MMM HH:mm')" | Out-File $out -Encoding utf8
& "C:\Python314\python.exe" -B "D:\finance\beginner-quant-research\mt5\ea_research\ema12\london_brief.py" 2>&1 | Out-File $out -Append -Encoding utf8
"`r`n==== size card (stop distance -> lots) ====" | Out-File $out -Append -Encoding utf8
& "C:\Python314\python.exe" -B "D:\finance\beginner-quant-research\mt5\ea_research\ema12\s1_size_card.py" 2>&1 | Out-File $out -Append -Encoding utf8
Start-Process notepad.exe $out
