"""
Build live_bot/data/nq_daily_rth_seed.csv: one row per trading day of NQ's regular
session (09:30-16:00 ET) -- open, high, low, close -- from the Databento 1-minute
history (2019-10-01..2026-09-25), using Round 229's loader (the same sessions Round
244's confluence features were computed from).

live_bot's daily-history cache (live_bot/daily_history.py) starts from this file and
tops it up from the broker's live 1-minute feed, which only covers ~22 sessions.
Rerun only to regenerate the seed.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pandas as pd
import round229_rth_vs_24x5 as R229

OUT = os.path.join(HERE, "..", "..", "live_bot", "data", "nq_daily_rth_seed.csv")

if __name__ == "__main__":
    rows = []
    for d in R229.load_days():
        b, m = d["bars"], d["mins"]
        rth = b[(m >= 570) & (m < 960)]
        if rth.empty:
            continue
        rows.append(dict(date=rth.index[0].date().isoformat(), open=float(rth["open"].iloc[0]),
                         high=float(rth["high"].max()), low=float(rth["low"].min()), close=float(rth["close"].iloc[-1])))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    df = pd.DataFrame(rows).drop_duplicates("date", keep="last").sort_values("date")
    df.to_csv(OUT, index=False)
    print(f"wrote {len(df)} sessions {df['date'].iloc[0]}..{df['date'].iloc[-1]} -> {OUT}")
