import itertools, numpy as np, pandas as pd
from mt5broker.ea_research import clean_guard_sim as C
from mt5broker.ea_batch.mt5_mc_config import CH, FU
from mt5broker.ea_batch import mt5data_guard_carry as GC
from mt5broker.ea_batch.mt5data_sizing_long import trades_mt5broker
bars = C.load_bars(); dd = lambda s: (pd.Timestamp(s) - C.EPOCH).days
A, CAPD, TARGET, LOCK, FEE, GOAL = C.A, C.CAPD, C.TARGET, C.LOCK, 451.0, 15000.0
H = int(np.busday_count("2026-10-09", "2026-12-23")); print("last day withdrawals can be requested = 22 Dec; business days 9 Oct .. 22 Dec:", H, flush=True)
def series(src, lots, P, L, lo, hi):
    trs = [trades_mt5broker("77900", lots["sdb"]), trades_mt5broker("mkt_xau5min", lots["xau5"])] if src == "mt5broker" else [GC.trades("77900", lots["sdb"]), GC.trades("mkt_xau5min", lots["xau5"])]
    tr = C.prep(trs)
    if src == "mt5broker":
        keep = tr["out_s"] >= lo * 86400; [tr.__setitem__(k, v[keep]) for k, v in list(tr.items())]; f = 4100.0 / tr["entry"]; tr["q"] = tr["q"] * f; tr["pl"] = tr["pl"] * f
    return C.simulate(bars, tr, lo, hi, P, L)
def passidx(rc, H):
    Vc, Bc, Hc = rc["V"], rc["B"], rc["Hi"]; n = len(Vc); res = {}
    for i0 in range(n - H + 1):
        bal, cnt = A, 0.0; res[i0] = None
        for j in range(H):
            k = i0 + j
            if Bc[k] <= -0.025 * A or bal + Bc[k] <= 0.92 * A: break
            if cnt + min(Hc[k], CAPD) >= LOCK: res[i0] = k; break
def series(src, lots, P, L, lo, hi):
    trs = [trades_mt5broker("77900", lots["sdb"]), trades_mt5broker("mkt_xau5min", lots["xau5"])] if src == "mt5broker" else [GC.trades("77900", lots["sdb"]), GC.trades("mkt_xau5min", lots["xau5"])]
    tr = C.prep(trs)
    if src == "mt5broker":
        keep = tr["out_s"] >= lo * 86400; [tr.__setitem__(k, v[keep]) for k, v in list(tr.items())]; f = 4100.0 / tr["entry"]; tr["q"] = tr["q"] * f; tr["pl"] = tr["pl"] * f
    return C.simulate(bars, tr, lo, hi, P, L)
def addon_daily(eid, years):
    rows = []
    for y in years:
        d = pd.read_csv(f"forex/early_mt5/ea_batch/results_{y}/{eid}.csv"); d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S"); o = d[d.direction == "out"]
        rows.append(pd.DataFrame({"day": (o.time - C.EPOCH).dt.days, "pl": o.profit + o.commission}))      # closed P&L incl. commission, swap excluded (MT5 broker swap-free); the in-leg commission is in the 'in' row, so subtract it too
        i = d[d.direction == "in"]; rows.append(pd.DataFrame({"day": (i.time - C.EPOCH).dt.days, "pl": i.commission}))
    r = pd.concat(rows); return r.groupby("day").pl.sum()
lo, hi = dd("2025-10-01"), dd("2026-09-30")
r = series("mt5", {k: v * 1.2 for k, v in CH.items()}, None, CAPD, lo, hi); days = r["days"]; V0, B0, H0 = r["V"], r["B"], r["Hi"]; n = len(V0)
def passrate(V, B, Hh, H):
    p = b = N = 0
    for i0 in range(n - 53 + 1):
        N += 1; cnt = 0.0
        for j in range(53):
            k = i0 + j
            if B[k] <= -0.025 * A or A + cnt + B[k] <= 0.92 * A:
                if j < H: b += 1
                break
            if cnt + min(Hh[k], CAPD) >= LOCK:
                if j < H: p += 1
                break
            x = min(V[k], CAPD) if V[k] > 0 else V[k]; cnt += x
            if cnt >= TARGET:
                if j < H: p += 1
                break
    return 100 * p / N, 100 * b / N
print("baseline pair x1.2, last 12 months: pass by 30 Nov %.1f%% (breach %.1f%%), by 22 Dec %.1f%% (breach %.1f%%)" % (*passrate(V0, B0, H0, 37), *passrate(V0, B0, H0, 53)), flush=True)
for eid in ("22909", "19166", "22490"):
    ad = addon_daily(eid, ("2025", "2026")); s = pd.Series(0.0, index=days); common = ad.index.intersection(days); s.loc[common] = ad.loc[common]
    pair = pd.Series(V0, index=days); win = (days >= lo)
    corr = np.corrcoef(s.values, pair.values)[0, 1]; mean = s.mean(); sd = s.std(); t = mean / sd * np.sqrt(len(s)) if sd > 0 else 0
    print(f"\n{eid}: default-lot (0.1) closed P&L per business day: mean {mean:6.1f} USD, sd {sd:6.1f}, t {t:4.2f}, corr with the pair {corr:5.2f}, total {s.sum():8,.0f} USD, days with P&L {(s!=0).sum()}", flush=True)
    for sc in (1, 2, 4):
        V = [v + sc * x for v, x in zip(V0, s.values)]; B = [b + min(sc * x, 0.0) for b, x in zip(B0, s.values)]; Hh = [h + sc * x for h, x in zip(H0, s.values)]
        a, bb = passrate(V, B, Hh, 37), passrate(V, B, Hh, 53)
        print(f"   add-on x{sc} lots: pass by 30 Nov {a[0]:4.1f}% (breach {a[1]:4.1f}%), by 22 Dec {bb[0]:4.1f}% (breach {bb[1]:4.1f}%)", flush=True)
