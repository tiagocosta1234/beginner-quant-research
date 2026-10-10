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
import itertools, time
def series(src, lots, P, L, lo, hi):
    trs = [trades_mt5broker("77900", lots["sdb"]), trades_mt5broker("mkt_xau5min", lots["xau5"])] if src == "mt5broker" else [GC.trades("77900", lots["sdb"]), GC.trades("mkt_xau5min", lots["xau5"])]
    tr = C.prep(trs)
    if src == "mt5broker":
        keep = tr["out_s"] >= lo * 86400; [tr.__setitem__(k, v[keep]) for k, v in list(tr.items())]; f = 4100.0 / tr["entry"]; tr["q"] = tr["q"] * f; tr["pl"] = tr["pl"] * f
    r = C.simulate(bars, tr, lo, hi, P, L); return {k: r[k].tolist() for k in ("V", "B", "Hi")}
CPOL = [("1.2/L2000", dict(m=1.2, L=2000.0)), ("1.5/L2000", dict(m=1.5, L=2000.0)), ("1.8/L2000", dict(m=1.8, L=2000.0)), ("1.5/L1500", dict(m=1.5, L=1500.0)), ("1.8/L1500", dict(m=1.8, L=1500.0))]
for D, f, m2 in itertools.product((10, 20), (0.5, 0.75), (1.8, 2.5)): CPOL.append((f"1.2->{m2} if behind {f:.2f} after d{D}", dict(m=1.2, L=2000.0, D=D, f=f, m2=m2)))
FPOL = [(m1, m2, T) for m1 in (1.5, 2.0, 2.5, 3.0) for m2 in (1.0, 1.5, 2.0) for T in (0.03, 0.05)]
def chal(ser, pol, i0):
    base = ser[(pol["m"], pol["L"])]; alt = ser.get((pol.get("m2"), pol["L"])) if "D" in pol else None; bal = cnt = 0.0
    for j in range(H):
        k = i0 + j; s = base
        if alt is not None and j >= pol["D"] and cnt < pol["f"] * TARGET * (j + 1) / 37.0: s = alt
        if s["B"][k] <= -0.025 * A or A + cnt + s["B"][k] <= 0.92 * A: return None
        if cnt + min(s["Hi"][k], CAPD) >= LOCK: return k
        v = s["V"][k]; x = min(v, CAPD) if v > 0 else v; cnt += x
        if cnt >= TARGET: return k
    return -1
def fund(f1, f2, k0, kend, T):
    bal, floor, paid, first = A, 0.92 * A, 0.0, False
    for k in range(k0, kend):
        s = f2 if first else f1
        if s["B"][k] <= -0.025 * A or bal + s["B"][k] <= floor: break
        v = s["V"][k]; bal += min(v, CAPD) if v > 0 else v
        if bal - A >= T * A: p = 0.5 * (bal - A); paid += p; bal -= p; floor = A; first = True
    return paid
pools = {"12M": ("mt5", dd("2025-10-01"), dd("2026-09-30")), "5Y": ("mt5broker", dd("2022-01-01"), dd("2026-09-30"))}
RES = {}
for pn, (src, lo, hi) in pools.items():
    t0 = time.time(); cs = {}; fs = {}
    for m, L in {(p["m"], p["L"]) for _, p in CPOL} | {(p.get("m2"), p["L"]) for _, p in CPOL if "m2" in p}: cs[(m, L)] = series(src, {k: v * m for k, v in CH.items()}, None, L, lo, hi)
    for m in {x for t in FPOL for x in t[:2]}: fs[m] = series(src, {k: v * m for k, v in FU.items()}, None, CAPD, lo, hi)
    n = len(cs[(1.2, 2000.0)]["V"]); starts = range(n - H + 1); print(f"{pn}: series built in {time.time()-t0:.0f}s, starts {len(starts)}", flush=True)
    for cname, cp in CPOL:
        out = [(i0, chal(cs, cp, i0)) for i0 in starts]; npass = sum(1 for _, k in out if k is not None and k >= 0); nbr = sum(1 for _, k in out if k is None)
        for (m1, m2, T) in FPOL:
            paid = [fund(fs[m1], fs[m2], k + 1, i0 + H, T) if (k is not None and k >= 0) else 0.0 for i0, k in out]; N = len(paid)
            RES[(pn, cname, m1, m2, T)] = dict(pass_=npass / N, breach=nbr / N, any=sum(p > 0 for p in paid) / N, p5=sum(p >= 5000 for p in paid) / N, p10=sum(p >= 10000 for p in paid) / N, mean=sum(paid) / N)
    print(f"{pn}: done in {time.time()-t0:.0f}s", flush=True)
keys = sorted({k[1:] for k in RES})
def row(k, pn): r = RES[(pn,) + k]; return f"pass {100*r['pass_']:4.1f} breach {100*r['breach']:4.1f} any {100*r['any']:4.1f} >=5k {100*r['p5']:4.1f} >=10k {100*r['p10']:4.1f} mean {r['mean']:6,.0f}"
base = ("1.2/L2000", 1.5, 1.5, 0.05)
print("\n=== BASELINE (current plan after the x1.2 decision): test 1.2 / live 1.5 then 1.5, request at 5%")
for pn in pools: print(f"  {pn}: {row(base, pn)}")
print("\n=== TOP 8 by the SUM of P(>=5k) over both pools (breach in the test <= 6% in the 12M window), shown for both pools")
ok = [k for k in keys if RES[("12M",) + k]["breach"] <= 0.06 and RES[("5Y",) + k]["breach"] <= 0.06]
for k in sorted(ok, key=lambda k: RES[("12M",) + k]["p5"] + RES[("5Y",) + k]["p5"], reverse=True)[:8]:
    print(f"  {k}\n     12M: {row(k,'12M')}\n     5Y : {row(k,'5Y')}")
print("\n=== TOP 5 chosen on 12M only, evaluated on 5Y;   TOP 5 chosen on 5Y only, evaluated on 12M (out-of-sample check)")
for a, b in (("12M", "5Y"), ("5Y", "12M")):
    for k in sorted(ok, key=lambda k: RES[(a,) + k]["p5"], reverse=True)[:5]: print(f"  pick on {a}: {k} -> {a}: >=5k {100*RES[(a,)+k]['p5']:4.1f} | {b}: >=5k {100*RES[(b,)+k]['p5']:4.1f} any {100*RES[(b,)+k]['any']:4.1f} breach {100*RES[(b,)+k]['breach']:4.1f}")
