"""Session system lab (see PREREG_SESSION.md). python -m forex.self_improving.session.session_lab [--train] [--test] """
import sys
ARGV = sys.argv[1:]
import os
os.environ["DA_Z"] = "1.5"; os.environ["NQ3_FLOOR"] = "1.67"
import itertools, argparse
import numpy as np, pandas as pd
from forex.ea_research import combo_grid as G, clean_boot_lib as L
from forex.ea_research.combo_grid import news_flat, bars, CH

UP, MMAX, DAYLIM, COUNTCAP = 2000.0, 6.0, 2500.0, 2000.0   # COUNTCAP: MT5 broker counts at most 2,000 of profit per day
FINMODE = None; FINQMAX = 2000.0; FINJ = 10.94   # finisher: forced gold position per session when still unresolved ('safe' = size so one 99.9th pct 1-minute jump cannot cross the loss lock, 'max' = 20 lots)
BOOST = 0.0   # anti-martingale boost: size multiplied by 1 + BOOST * max(day PnL, 0) / UP at each entry
COLLECT = None   # when a list: run() appends (day, P path to the barrier, net signed open q) per session (stress tests)
VOLF = None   # optional per-trade size multiplier array (volatility sizing), aligned with the loaded trade list
LOCKJ = None   # USD per unit q of the adverse 1-minute move (99.9th pct): when set, total open size is capped so one such jump cannot cross the loss lock


def load(pool, lo_s=None, hi_s=None):
    src, a, b = L.POOLS[pool]; lo = L.day(lo_s or a); hi = L.day(hi_s or b)
    tr = news_flat(L.merge(L.ea_trades(src, "sdb", CH["sdb"], lo), L.ea_trades(src, "xau5", CH["xau5"], lo)), G.EV, bars)
    o = np.argsort(tr["in_s"], kind="stable"); tr = {k: v[o] for k, v in tr.items()}; return tr, lo, hi


def scale_for(P, hleft, Lc, m0, k, r, hstop):
    if hleft < hstop and P < UP: return 0.0
    el = 1.0 - hleft / 23.0; room = float(np.clip((Lc + P) / Lc, 0.25, 1.5))
    return float(np.clip(m0 * (1 + k * max(el, 0)) * room ** r, 0.0, MMAX))


def run(tr, lo, hi, Lc, m0, k, r, hstop):
    tm, bc, sp = bars; n = len(tr["in_s"]); in_s, side, entry, q = tr["in_s"], tr["side"], tr["entry"], tr["q"]; out = tr["out_s"].astype(float).copy(); pl = tr["pl"].astype(float).copy()
    sc = np.zeros(n); rows = []; fin = tr.get("fin")
    for d in range(lo, hi + 1):
        t0 = d * 86400; t1 = t0 + 86400; i0 = int(np.searchsorted(tm, t0)); i1 = int(np.searchsorted(tm, t1))
        if i1 - i0 < 30: continue
        T = tm[i0:i1]; bid = bc[i0:i1]; ask = bid + sp[i0:i1]; P = np.zeros(len(T)); NQ = np.zeros(len(T))
        def add(j, sign=1.0):
            s = sc[j] * sign; first = int(np.searchsorted(T, in_s[j])) if in_s[j] >= t0 else 0; last = int(np.searchsorted(T, out[j])); mark = bid if side[j] > 0 else ask
            base = 0.0 if in_s[j] >= t0 else side[j] * (mark[0] - entry[j]) * q[j]
            if last > first: P[first:last] += s * (side[j] * (mark[first:last] - entry[j]) * q[j] - base); NQ[first:last] += s * side[j] * q[j]
            if last < len(T): P[last:] += s * (pl[j] - base)
        carried = np.nonzero((in_s < t0) & (out > t0) & (sc > 0))[0]
        for j in carried: add(j)
        todays = np.nonzero((in_s >= t0) & (in_s < t1))[0]; hit = None; cursor = 0
        def barrier(upto):
            h = np.nonzero((P[:upto] >= UP) | (P[:upto] <= -Lc))[0]; return int(h[0]) if len(h) else None
        for j in todays:
            e = int(np.searchsorted(T, in_s[j])); hit = barrier(min(e + 1, len(T)))
            if hit is not None: break
            hr = (in_s[j] - t0) / 3600.0
            if FINMODE is not None and fin is not None and fin[j]:
                act = (sc > 0) & (in_s <= in_s[j]) & (out > in_s[j]); openq = float((sc[act] * q[act]).sum()); room = Lc + P[min(e, len(T) - 1)]
                tq = FINQMAX if FINMODE == "max" else max(min(FINQMAX, room / FINJ - openq), 0.0)
                if tq > 0: sc[j] = tq / q[j]; add(j)
                continue
            if hr < 1.0 or hr >= 23.0: continue
            s = scale_for(P[min(e, len(T) - 1)], 24.0 - hr, Lc, m0, k, r, hstop)
            if BOOST and s > 0: s = float(min(s * (1 + BOOST * max(P[min(e, len(T) - 1)], 0.0) / UP), MMAX))
            if VOLF is not None: s = float(np.clip(s * VOLF[j], 0.0, MMAX))
            if s > 0.0 and LOCKJ:
                act = (sc > 0) & (in_s <= in_s[j]) & (out > in_s[j]); openq = float((sc[act] * q[act]).sum()); room = Lc + P[min(e, len(T) - 1)]
                s = min(s, max(room / LOCKJ - openq, 0.0) / q[j])
            if s > 0.0: sc[j] = s; add(j)
        if hit is None: hit = barrier(len(T))
        if hit is not None:
            tb = int(T[hit]); act = np.nonzero((sc > 0) & (in_s <= tb) & (out > tb))[0]
            for j in act:
                mk = bid[hit] if side[j] > 0 else ask[hit]; out[j] = tb; pl[j] = side[j] * (mk - entry[j]) * q[j]
            rows.append((d, float(P[hit]), 1 if P[hit] >= UP else -1, float(P[: hit + 1].min())))
            if COLLECT is not None: COLLECT.append((d, P[: hit + 1].copy(), NQ[: hit + 1].copy()))
        else:
            rows.append((d, float(P[-1]), 0, float(P.min())))
            if COLLECT is not None: COLLECT.append((d, P.copy(), NQ.copy()))
    return pd.DataFrame(rows, columns=["day", "pnl", "res", "low"])


def account(df):
    p = df.pnl.values; lo_ = df.low.values; out = []
    for k in range(len(p)):
        c = 0.0; cum = 0.0
        for j in range(k, len(p)):
            if lo_[j] <= -DAYLIM: out.append(("breach", j - k + 1)); break
            c += min(p[j], COUNTCAP) if p[j] > 0 else p[j]; cum = c
            if c >= 8000: out.append(("pass", j - k + 1)); break
            if c <= -8000: out.append(("breach", j - k + 1)); break
    return pd.DataFrame(out, columns=["r", "bd"])


def summarize(df):
    o = account(df); ps = o[o.r == "pass"]
    return dict(days=len(df), up=100 * (df.res == 1).mean(), down=100 * (df.res == -1).mean(), open=100 * (df.res == 0).mean(), starts=len(o), pass_pct=100 * (o.r == "pass").mean() if len(o) else np.nan,
                breach_pct=100 * (o.r == "breach").mean() if len(o) else np.nan, med_bd=float(ps.bd.median()) if len(ps) else np.nan)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--L", default="1000,1500,2000"); a = ap.parse_args(ARGV)
    import time
    TR = load("FT", "2022-01-01", "2024-12-31"); out = "D:/finance/si_ledgers/SESSION_train.csv"
    grid = [(1.5, 0, 0, 0)] if a.smoke else list(itertools.product((1.0, 1.5, 2.0, 3.0, 4.0), (0.0, 1.0, 3.0), (0.0, 1.0), (0.0, 3.0)))
    for Lc in map(float, a.L.split(",")):
        for m0, k, r, hs in grid:
            t = time.time(); df = run(*TR, Lc, m0, k, r, hs); row = dict(L=Lc, m0=m0, k=k, r=r, hstop=hs, **summarize(df))
            pd.DataFrame([row]).to_csv(out, mode="a", header=not os.path.exists(out), index=False); print({kk: (round(v, 1) if isinstance(v, float) else v) for kk, v in row.items()}, f"{time.time() - t:.0f}s", flush=True)
            if a.smoke: return


if __name__ == "__main__":
    main()
