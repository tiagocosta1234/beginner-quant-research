"""The apprentice's rubric (desk.py, as applied by Claude since day F017 without overrides) run by code on every allowed weekday, to give the 28 hand-made
blind trades of 22 Oct 2026 a large sample. Descriptive, not a pre-registered test: the rubric was written before the blind days, but its thresholds were
not fixed for a research test, and every mechanical form of the trader's setup has already failed on MT5 broker prices (CLAUDE.md START HERE).
Per day (same frame, costs and S1 bracket as desk.py): scan the candles 07:59-08:14 local; at every EMA-12 cross that passes the card and has an S1 level,
record the grade and the S1 result; the trade taken is the first A / B one (C is skipped). Days: COMEX gold futures (Databento GC, continuous front month)
2020-01-02 .. 2025-12-31, without contract-roll days and the reserved data (2025-04-01..05-31 the trader's recorded trades, 2025-02-28..03-29 and 2023-11-28..12-27
extension windows; 2026 is not loaded). Usage: python forex/apprentice/rubric_backtest.py"""
import os, numpy as np, pandas as pd
import desk as D

RESERVED = [("2023-11-28", "2023-12-27"), ("2025-02-28", "2025-03-29"), ("2025-04-01", "2025-05-31")]
d = D.raw()
rows, days = [], 0
for day in pd.bdate_range("2020-01-02", "2025-12-31"):
    ds = str(day.date())
    if any(a <= ds <= b for a, b in RESERVED): continue
    x = d[(d["lis"] >= day - pd.Timedelta(hours=4)) & (d["lis"] < day + pd.Timedelta(hours=21))].copy().reset_index(drop=True)
    w = x[(x["lis"] >= day + pd.Timedelta(hours=6)) & (x["lis"] < day + pd.Timedelta(hours=20))]
    if len(w[w["lis"] < day + pd.Timedelta(hours=8, minutes=16)]) < 120 or (w["mo"] - w["mc"].shift()).abs().max() > 8: continue
    x["ema"] = x["mc"].ewm(span=12, adjust=False).mean()
    tr = np.maximum(x["mh"] - x["ml"], np.maximum((x["mh"] - x["mc"].shift()).abs(), (x["ml"] - x["mc"].shift()).abs()))
    x["atr"] = tr.rolling(14).mean().shift(1); x["vmed"] = x["v"].rolling(60).median().shift(1)
    i6 = int(np.argmax(x["lis"] >= day + pd.Timedelta(hours=6)))
    base = x["mo"][i6] - 1000.0
    for k in ("mo", "mh", "ml", "mc", "ema"): x[k] = x[k] - base
    x["lis"] = x["lis"] - (day - pd.Timestamp("2000-01-03"))
    y = x[["lis", "mo", "mh", "ml", "mc", "v", "ema", "atr", "vmed"]].reset_index(drop=True)
    day0 = pd.Timestamp("2000-01-03"); taken = False; days += 1
    for m in range(7 * 60 + 59, 8 * 60 + 15):
        hit = np.where(y["lis"] == day0 + pd.Timedelta(minutes=m))[0]
        if not len(hit): continue
        s = D.setup_at(y, int(hit[0]), i6)
        if s is None or not s["valid"]: continue
        sim = D.simulate(y, s["side"], s["time"], s["s1"]["stop"], s["s1"]["target"])
        if sim is None: continue
        take = (not taken) and s["grade"] in ("A", "B"); taken |= take
        rows.append({"date": ds, "year": day.year, "time": s["time"], "side": s["side"], "grade": s["grade"], "taken": take, **{k: v for k, v in s["rubric"].items()}, **sim})
out = pd.DataFrame(rows); out.to_csv(os.path.join(D.HERE, "RUBRIC_BACKTEST_SETUPS.csv"), index=False)
t = out[out["taken"]]
print("days scanned %d; card-valid setups %d; trades taken (first A/B a day) %d" % (days, len(out), len(t)))
f = lambda v: "n %4d, wins %4.1f%%, mean R %+.3f (se %.3f)" % (len(v), 100 * (v["R"] > 0).mean(), v["R"].mean(), v["R"].std() / np.sqrt(max(len(v), 1)))
print("TAKEN: " + f(t))
for k, v in t.groupby("year"): print("  %d: %s" % (k, f(v)))
for k, v in out.groupby("grade"): print("all setups grade %s: %s" % (k, f(v)))
for col in ("trend", "body>=1ATR", "volume>=median", "not chop"):
    print("all setups %-15s yes: %s | no: %s" % (col, f(out[out[col]]), f(out[~out[col]])))
print("hand-made blind days (Sep-Nov 2024) in this run: %s" % f(t[(t["date"] >= "2024-09-01") & (t["date"] <= "2024-11-30")]))
