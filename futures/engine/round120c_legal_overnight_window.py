"""
Round 120c (descriptive): Broker's trading day runs 5:00 PM CT -> 3:10 PM CT, so a
position opened after the 6:00 PM ET reopen may be held into the next session;
only holding across the 3:10 PM CT flat is prohibited. Measures 1-contract long
returns in the legal windows on the 24-hour contract files (data/nasdaq_extended,
data/gold_extended), converted UTC -> America/New_York. For each trading day it
uses the contract with the most volume in that window, so rolls don't create jumps."""
import sys, glob, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from round115_extended_hours_data_and_search import _load_one

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
def load(dirn):
    out = []
    for f in sorted(glob.glob(os.path.join(D, dirn, "*.Last.txt"))):
        df = _load_one(f)
        df.index = df.index.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
        df["contract"] = os.path.basename(f)
        out.append(df)
    return out

def check_break(frames):
    df = pd.concat(frames)
    h = df.index.hour.value_counts().sort_index()
    print("  bars per ET hour:", dict(h))

def windows(frames, pv, cost, name):
    # trading day key: bars at/after 18:00 ET belong to the next day's session
    rows = []
    for df in frames:
        t = df.index
        tday = (t + pd.Timedelta(hours=6)).normalize()  # 18:00 ET -> next date
        mins = t.hour * 60 + t.minute
        g = df.assign(tday=tday, mins=mins)
        for label, lo, hi in [("night 18:00->09:30", None, 9*60+30), ("RTH 09:30->16:00", 9*60+30, 16*60),
                              ("full 18:00->16:00", None, 16*60)]:
            if lo is None:  # from 18:00 (mins>=1080) through next day < hi
                m = (g["mins"] >= 18*60) | (g["mins"] < hi)
            else:
                m = (g["mins"] >= lo) & (g["mins"] < hi)
            w = g[m]
            if w.empty: continue
            agg = w.groupby("tday").agg(o=("open", "first"), c=("close", "last"), v=("vol", "sum"), n=("close", "size"))
            agg["window"] = label; agg["contract"] = df["contract"].iloc[0]
            rows.append(agg.reset_index())
    r = pd.concat(rows)
    r = r[r["n"] >= 30]
    r = r.sort_values("v").groupby(["window", "tday"]).tail(1)
    r["pnl"] = (r["c"] - r["o"]) * pv - cost
    print(f"\n{name}: 1 contract long, net of ${cost:.2f} round-trip")
    for wname, g in r.groupby("window"):
        g = g.sort_values("tday"); p = g["pnl"].to_numpy()
        yrs = g["tday"].dt.year
        by = " ".join(f"{y}:{g.loc[yrs==y,'pnl'].mean():+.1f}" for y in sorted(yrs.unique()))
        print(f"  {wname:<20} days={len(p):>4} mean ${p.mean():+6.2f} sd ${p.std():6.2f} "
              f"daily Sharpe {p.mean()/p.std():+.3f} (annual {p.mean()/p.std()*np.sqrt(252):+.2f}) | by year {by}")

mnq = load("nasdaq_extended"); check_break(mnq)
windows(mnq, 2.0, 1.24 + 2*0.25*2.0, "MNQ")
mgc = load("gold_extended"); check_break(mgc)
windows(mgc, 10.0, 1.24 + 2*0.1*10.0, "MGC")
