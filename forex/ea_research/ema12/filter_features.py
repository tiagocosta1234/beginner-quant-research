"""PREREG_CLAUDE_FILTER step 2 input: facts known AT each logged entry minute (no bar after it is loaded). Usage: python filter_features.py"""
import json, numpy as np, pandas as pd
import blind_png as B

L = pd.read_csv("BLIND_LOG_FILTER.csv", dtype={"hhmm": str}); L = L[L.side.isin(["L", "S"])]
bias = {e["day"]: e["bias"] for e in map(json.loads, open("replay_events.jsonl", encoding="utf-8")) if e["event"] == "bias"}
rows = []
for r in L.itertuples():
    cut = pd.Timestamp(f"{r.date} {r.hhmm}")
    d = B.load_fut(r.date, cut)                                   # bars up to and including the entry minute only
    assert d.index.max() <= cut
    D = pd.Timestamp(r.date); sd = 1 if r.side == "L" else -1
    pre = d.loc[D + pd.Timedelta(hours=7):D + pd.Timedelta(hours=7, minutes=59)]; nz = float((pre.high - pre.low).median())
    c15 = d.close.resample("15min", label="left", closed="left").last().dropna(); e15 = c15.ewm(span=12, adjust=False).mean()
    c1h = d.close.resample("60min", label="left", closed="left").last().dropna(); e1h = c1h.ewm(span=12, adjust=False).mean()
    c1 = d.close; e1 = c1.ewm(span=12, adjust=False).mean()
    asia = d.loc[D:D + pd.Timedelta(hours=6, minutes=59)]; prev = d[d.index < D]; pday = prev[prev.index >= prev.index[-1].normalize()]
    k5 = d.close.iloc[-6] if len(d) > 6 else d.close.iloc[0]
    day = d.loc[D:]; dayrange = float(day.high.max() - day.low.min())
    move_0700 = float(d.close.iloc[-1] - d.loc[D + pd.Timedelta(hours=7):].open.iloc[0])
    rows.append(dict(date=r.date, side=r.side, hhmm=r.hhmm, bias=bias.get(r.date), entry=r.entry, stop_pt=round(abs(r.entry - r.stop), 1),
                     rr=round(abs(r.target - r.entry) / abs(r.entry - r.stop), 2), noise=round(nz, 2), stop_x_noise=round(abs(r.entry - r.stop) / nz, 1),
                     chase=round(sd * (d.close.iloc[-1] - k5) / nz, 1), with1m=bool(sd * (c1.iloc[-1] - e1.iloc[-1]) > 0),
                     with15=bool(sd * (c15.iloc[-1] - e15.iloc[-1]) > 0), slope15=round(sd * (e15.iloc[-1] - e15.iloc[-5]) / nz, 1),
                     with1h=bool(sd * (c1h.iloc[-1] - e1h.iloc[-1]) > 0), since0700=round(sd * move_0700 / nz, 1),
                     to_asiaH=round((asia.high.max() - r.entry) / nz, 1), to_asiaL=round((r.entry - asia.low.min()) / nz, 1),
                     to_PDH=round((pday.high.max() - r.entry) / nz, 1), to_PDL=round((r.entry - pday.low.min()) / nz, 1)))
F = pd.DataFrame(rows); F.to_csv("FILTER_FEATURES.csv", index=False)
pd.set_option("display.width", 250); print(F.to_string(index=False))
