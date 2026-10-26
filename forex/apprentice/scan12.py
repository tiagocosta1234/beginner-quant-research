"""scan_allowed.py for read12.py: advance the scan past candidates the READ12 constraints already forbid (signal before 08:02, or side
against the sign of the 30-minute trend) and stop at the first candidate where a call is possible.
Usage (from forex/apprentice): python scan11.py train|test"""
import re, subprocess, sys

CAND = re.compile(r"CANDIDATE (\d\d:\d\d) (LONG|SHORT) .*with_trend30=(True|False)")
ph = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
rows = []
for _ in range(60):
    out = subprocess.run([sys.executable, "read12.py", ph, "scan"], capture_output=True, text=True).stdout
    m = CAND.search(out)
    if not m:
        print("\n".join(rows)); print(out.strip()); break
    t, side, wt = m.groups()
    if t >= "08:02" and wt == "True":
        print("\n".join(rows)); print(out.strip()); break
    rows.append("  (auto-pass %s %s: %s)" % (t, side, "before 08:02" if t < "08:02" else "against the 30-min trend"))
