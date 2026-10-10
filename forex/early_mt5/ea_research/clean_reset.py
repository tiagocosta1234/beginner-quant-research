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
            x = min(Vc[k], CAPD) if Vc[k] > 0 else Vc[k]; bal += x; cnt += x
            if cnt >= TARGET: res[i0] = k; break
    return res
def live(rf, k0, kend, T):
    Vf, Bf = rf["V"], rf["B"]; bal, floor, paid, br = A, 0.92 * A, 0.0, False
    for k in range(k0, kend):
        if Bf[k] <= -0.025 * A or bal + Bf[k] <= floor: br = True; break
        bal += min(Vf[k], CAPD) if Vf[k] > 0 else Vf[k]
        if bal - A >= T * A: p = 0.5 * (bal - A); paid += p; bal -= p; floor = A
    return paid, br
pools = {"LAST 12M": ("mt5", dd("2025-10-01"), dd("2026-09-30")), "2022-26": ("mt5broker", dd("2022-01-01"), dd("2026-09-30"))}
MC, MF, TS = (1.2, 1.5, 1.8), (1.0, 1.5, 2.0, 2.5, 3.0), (0.01, 0.03, 0.05, 0.08, 0.10)
for pn, (src, lo, hi) in pools.items():
    print(f"\n##### {pn}", flush=True); chal = {m: passidx(series(src, {k: v * m for k, v in CH.items()}, None, CAPD, lo, hi), H) for m in MC}
    fund = {m: series(src, {k: v * m for k, v in FU.items()}, None, CAPD, lo, hi) for m in MF}; rows = []
    for mc, mf, T in itertools.product(MC, MF, TS):
        paids, brs, pas = [], [], []
        for i0, k in chal[mc].items():
            if k is None: paids.append(0.0); brs.append(False); pas.append(False); continue
            p, b = live(fund[mf], k + 1, i0 + H, T); paids.append(p); brs.append(b); pas.append(True)
        rows.append((mc, mf, T, np.array(paids), np.array(brs), np.array(pas)))
    n = len(rows[0][3]); print(f"  starts {n}; metrics per account; k identical accounts => cash x k, fees x k", flush=True)
    for k in (1, 2, 3, 4, 5):
        best = max(rows, key=lambda r: ((k * r[3] >= GOAL).mean(), (k * r[3]).mean()))
def challenge_run(r, start, hmax):
    """returns ('pass'|'breach'|'run', day index) for a fresh test starting at day index `start`, up to hmax days."""
    V, B, Hi = r["V"], r["B"], r["Hi"]; bal, cnt = A, 0.0
    for j in range(hmax):
        k = start + j
        if k >= len(V): return "run", k
        if B[k] <= -0.025 * A or bal + B[k] <= 0.92 * A: return "breach", k
        if cnt + min(Hi[k], CAPD) >= LOCK: return "pass", k
        x = min(V[k], CAPD) if V[k] > 0 else V[k]; bal += x; cnt += x
        if cnt >= TARGET: return "pass", k
    return "run", start + hmax
def with_reset(r, i0, hmax, free_reset=True, lag=1):
    st, k = challenge_run(r, i0, hmax)
    if st == "pass": return "pass", k - i0 + 1, 0
    if st == "run": return "run", hmax, 0
    if not free_reset: return "dead", hmax, 0
    k2 = k + lag + 1; rem = hmax - (k2 - i0)
    if rem <= 0: return "run", hmax, 1
    st2, kk = challenge_run(r, k2, rem)
    if st2 == "pass": return "pass", kk - i0 + 1, 1
    if st2 == "breach": return "dead", hmax, 1
    return "run", hmax, 1
pools = {"LAST 12M": ("mt5", dd("2025-10-01"), dd("2026-09-30")), "2022-26": ("mt5broker", dd("2022-01-01"), dd("2026-09-30"))}
for pn, (src, lo, hi) in pools.items():
    print(f"\n##### {pn}: test with loss cap + pass lock; breach -> ONE free reset next business day (MT5 broker promo, to be confirmed on the dashboard), a second breach ends it", flush=True)
    for m in (1.0, 1.2, 1.5, 1.8, 2.1, 2.5):
        r = series(src, {k: v * m for k, v in CH.items()}, None, CAPD, lo, hi); n = len(r["V"])
        for H2, lab in ((37, "30 Nov"), (53, "22 Dec")):
            starts = range(n - H2 + 1); out0 = [with_reset(r, i, H2, False)[0] for i in starts]; out1 = [with_reset(r, i, H2, True) for i in starts]
            p0 = np.mean([o == "pass" for o in out0]); p1 = np.mean([o[0] == "pass" for o in out1]); used = np.mean([o[2] == 1 for o in out1]); dead = np.mean([o[0] == "dead" for o in out1]); dead0 = np.mean([o == "dead" for o in out0])
            days = np.array([o[1] for o in out1 if o[0] == "pass"])
            print(f"  x{m} by {lab}: pass without reset {100*p0:4.1f}% (dead {100*dead0:4.1f}%) | WITH free reset pass {100*p1:4.1f}% (reset used {100*used:4.1f}%, dead {100*dead:4.1f}%) | days to pass mean {days.mean() if len(days) else float('nan'):4.1f} median {np.median(days) if len(days) else float('nan'):3.0f}", flush=True)
