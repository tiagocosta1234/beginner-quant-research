"""
Build live_bot/data/nq_session_seed.csv for live_bot/session_history.py: one row per
Databento NQ regular session (09:30-16:00 ET, 2019-10-01..2026-09-25) with its open,
range, POC, VAL, VAH and POC-reversion trade outcome -- computed with the Combined
bot's own functions via session_history.session_row, sequentially, so each outcome
uses only the sessions before it (exactly as the bot does live). Rerun only to
regenerate the seed.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import pandas as pd
import round229_rth_vs_24x5 as R229
from live_bot.session_history import COLUMNS, session_row

OUT = os.path.join(ROOT, "live_bot", "data", "nq_session_seed.csv")

if __name__ == "__main__":
    hist = pd.DataFrame(columns=COLUMNS)
    rows = []
    for d in R229.load_days():
        b, m = d["bars"], d["mins"]
        rth = b[(m >= 570) & (m < 960)]
        if rth.empty:
            continue
        row = session_row(rth, hist)
        if row is None:
            continue
        rows.append(row)
        hist = pd.DataFrame(rows, columns=COLUMNS)
    out = hist.copy()
    out["date"] = out["date"].map(lambda x: x.isoformat())
    out.to_csv(OUT, index=False)
    n_tr = int(out["poc_outcome"].notna().sum())
    print(f"wrote {len(out)} sessions {out['date'].iloc[0]}..{out['date'].iloc[-1]}, {n_tr} POC trades "
          f"(win rate {out['poc_outcome'].mean():.3f}) -> {OUT}")
