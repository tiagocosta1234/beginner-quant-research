"""Advance read_test3.py's scan past candidates the frozen v9 rules already forbid (signal before 08:02, or side against
the sign of the 30-minute trend: read_test3.py refuses those calls anyway), and stop at the first candidate where a call is
possible, so every allowed candidate still gets its own decision. Prints one note per candidate it passed.
Usage (from forex/apprentice): python scan_allowed.py"""
import re, subprocess, sys

CAND = re.compile(r"CANDIDATE (\d\d:\d\d) (LONG|SHORT) .*with_trend30=(True|False)")

rows = []
for _ in range(60):
    out = subprocess.run([sys.executable, "read_test3.py", "scan"], capture_output=True, text=True).stdout
    m = CAND.search(out)
    if not m:
        print("\n".join(rows)); print(out.strip()); break
    t, side, wt = m.groups()
    if t >= "08:02" and wt == "True":
        print("\n".join(rows)); print(out.strip()); break
    rows.append("  (auto-pass %s %s: %s)" % (t, side, "before 08:02" if t < "08:02" else "against the 30-min trend"))
