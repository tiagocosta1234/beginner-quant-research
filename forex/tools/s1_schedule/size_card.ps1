# Weekdays 07:56 (and inside the 07:35 brief): writes the read-only S1 size card (stop distance -> lots table at the live balance) and opens it in Notepad. No command needed.
$out = "D:\finance\scratch\s1_size_card.txt"
& "C:\Python314\python.exe" -B "D:\finance\beginner-quant-research\mt5\ea_research\ema12\s1_size_card.py" 2>&1 | Out-File $out -Encoding utf8
Start-Process notepad.exe $out
