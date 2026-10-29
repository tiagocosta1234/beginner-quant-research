"""PREREG_D2_MT5RULE: the D2 book under MT5 Pro's balance-based daily line, carried floating P&L and the 2,000-a-day counted cap.
Modes HOLD (weekly rebalance, guard, profit skim, pass lock) and DAILY (open 01:05, close 22:45 server every weekday).
   python -m forex.ea_research.d2_mt5rule"""
import numpy as np
import pandas as pd

from forex.ea_research import swapfree_drift as S
from forex.ea_research import swapfree_mt5sim as Q

MK = S.MK
LED = "data/si_ledgers"
START_BAL = Q.START_BAL
GUARD, BREACH, SKIM, LOCK = 1500.0, 2500.0, 1800.0, 108_100.0
NOSTOP = False    # stats run: rules active but the path never stops at a pass or a breach; events recorded in EVENTS
EVENTS = []
REENTER_NEXT_DAY = True   # False: after a skim / guard close the book stays flat until the next weekly decision (PREREG_D2_MT5WEEKLY)
NOCHECK = False   # engine check only: no guard / skim / lock / breach / pass and no counted cap; hold_path then returns the final equity
M18, M0105, M2245, M2230 = 18 * 60, 65, 22 * 60 + 45, 22 * 60 + 30


def build_cache():
    raw = {m: S.load_mt5(m) for m in MK + ("EURUSD", "USDJPY")}
    for d in raw.values():
        d["date"] = d.ts // 86400; d["mn"] = (d.ts % 86400) // 60
    fx = {m: raw[m].groupby("date").bc.last() for m in ("EURUSD", "USDJPY")}
    g = {m: dict(tuple(raw[m].groupby("date"))) for m in MK}
    dates = sorted(set(g["SP"]) | set(g["XAUUSD"])); cache = {}; last = np.full(len(MK), np.nan)
    for dt in dates:
        x = pd.Timestamp(dt * 86400, unit="s")
        if x.weekday() >= 5: continue
        fr = [g[m].get(dt) for m in MK]
        mins = np.array(sorted(set().union(*[set(f.mn) for f in fr if f is not None])))
        if not len(mins): continue
        arr = {}
        for col in ("bo", "ao", "bc", "bl"):
            cols = []
            for j, f in enumerate(fr):
                if f is None: cols.append(np.full(len(mins), np.nan)); continue
                s = pd.Series(f[col].to_numpy(), index=f.mn.to_numpy()).reindex(mins)
                cols.append(s.ffill().to_numpy() if col != "bl" else s.to_numpy())
            arr[col] = np.column_stack(cols)
        ref = last.copy()
        for col in ("bo", "ao", "bc"):
            a = arr[col]; arr[col] = np.where(np.isnan(a), ref[None, :], a)
        arr["ao"] = np.where(np.isnan(arr["ao"]), arr["bo"], arr["ao"])
        arr["bl"] = np.where(np.isnan(arr["bl"]), arr["bc"], arr["bl"])
        have = np.array([f is not None for f in fr])
        fe = fx["EURUSD"][fx["EURUSD"].index < dt]; fj = fx["USDJPY"][fx["USDJPY"].index < dt]
        k = np.array([1.0, 1.0, fe.iloc[-1] if len(fe) else 1.13, 1.0 / fj.iloc[-1] if len(fj) else 1 / 114, 1.0])
        idx = lambda mn: int(np.searchsorted(mins, mn))
        ok = lambda i, mn: i < len(mins) and mins[i] - mn < 30 and have.all()
        i18, i01, i22, i2230 = idx(M18), idx(M0105), idx(M2245), idx(M2230)
        cache[x] = dict(T=len(mins), k=k, i18=i18 if ok(i18, M18) else None, i01=i01 if ok(i01, M0105) else None,
                        i22=i22 if ok(i22, M2245) else None, i2230=i2230 if i2230 < len(mins) else None, **arr)
        for j, f in enumerate(fr):
            if f is not None: last[j] = f.bc.iloc[-1]
    return cache


def weekly_weights(cache, C):
    W = {}; week = None
    for x, c in cache.items():
        wk = x.isocalendar()[:2]
        if wk != week and c["i18"] is not None:
            week = wk; w, on = S.signals(C[list(MK)], x, "D2"); W[x] = (w.to_numpy(), on.to_numpy())
    return W


def hold_path(cache, days, W, G, H):
    """One path from days[0] for H business days. Returns (status, day) with status 1 pass, 2 breach, 0 none."""
    u = np.zeros(len(MK)); basis = np.zeros(len(MK)); bal = START_BAL; last_on = None; tgt = None; reenter = False
    for n, x in enumerate(days[:H]):
        c = cache[x]; k = c["k"]; dsb = bal; real = 0.0; T = c["T"]
        new = u.copy(); sw = None
        if x in W:
            w, on = W[x]; px = c["bo"][c["i18"]] * k; tgt = G * w / px
            flip = (on != last_on) if last_on is not None else np.zeros(len(MK), bool)
            chg = (u == 0) | (tgt == 0) | (np.abs(tgt - u) > 0.25 * np.abs(tgt)) | flip
            new = np.where(chg, tgt, u); last_on = on; sw = c["i18"]; reenter = False
        elif reenter and REENTER_NEXT_DAY and c["i18"] is not None and tgt is not None:
            new = tgt.copy(); sw = c["i18"]; reenter = False
        # piecewise path: [0, sw) with u/basis, [sw, T) with new/basis2
        seg = []
        e1 = T if sw is None else sw
        seg.append((0, e1, u.copy(), basis.copy(), 0.0))
        if sw is not None:
            bo, ao = c["bo"][sw], c["ao"][sw]; dq = new - u; r = 0.0; b2 = basis.copy()
            for j in range(len(MK)):
                if dq[j] > 0: b2[j] = (u[j] * basis[j] + dq[j] * ao[j]) / new[j]
                elif dq[j] < 0: r += -dq[j] * (bo[j] - basis[j]) * k[j]
                if new[j] == 0: b2[j] = 0.0
            seg.append((sw, T, new.copy(), b2, r))
        closed = False; status = 0
        for (a, b, uu, bb, r0) in seg:
            if a >= b: u, basis = uu, bb; real += r0; continue
            real += r0
            fl = (c["bc"][a:b] - bb) @ (uu * k); lo = (c["bl"][a:b] - bb) @ (uu * k)
            lo = np.minimum(lo, fl); eq_lo = real + lo; eq = real + fl
            ev = []
            gi = np.flatnonzero(eq_lo <= -GUARD); li = np.flatnonzero(dsb + eq >= LOCK)
            if NOCHECK: gi, li = [], []
            if len(gi): ev.append((gi[0], "guard"))
            if len(li): ev.append((li[0], "lock"))
            if not NOCHECK and c["i2230"] is not None and a <= c["i2230"] < b and (c["bc"][c["i2230"]] - bb) @ (uu * k) >= SKIM: ev.append((c["i2230"] - a, "skim"))
            if ev:
                i, kind = min(ev)
                if NOSTOP: EVENTS.append((x, kind, float(eq_lo[i] if kind == "guard" else eq[i])))
                if kind == "guard":
                    v = eq_lo[i]
                    if (v <= -BREACH or dsb + v <= 92_000) and not NOSTOP: return 2, n
                    real = v
                else:
                    if ((eq_lo[:i] <= -BREACH).any() or (dsb + eq_lo[:i] <= 92_000).any()) and not NOSTOP: return 2, n
                    real = eq[i]
                u = np.zeros(len(MK)); basis = np.zeros(len(MK)); closed = True; reenter = True
                break
            if not NOCHECK and not NOSTOP and ((eq_lo <= -BREACH).any() or (dsb + eq_lo <= 92_000).any()): return 2, n
            u, basis = uu, bb
            last_eq = dsb + eq[-1]
        if NOCHECK: bal = dsb + real; continue
        bal = dsb + (min(real, 2000.0) if real > 0 else real)
        if NOSTOP: EVENTS.append((x, "day", bal)); continue
        if bal >= 108_000: return 1, n
    if NOCHECK: return last_eq, H
    return 0, H


def daily_series(cache, W, G):
    """DAILY mode: each weekday open the latest weekly targets at 01:05, close at 22:45. Returns a frame of realised day P&L V and day low B (from the day-start balance)."""
    rows = []; w = None
    for x, c in cache.items():
        V = B = 0.0
        if w is not None and c["i01"] is not None and c["i22"] is not None and c["i22"] > c["i01"]:
            k = c["k"]; a, b = c["i01"], c["i22"]; ao = c["ao"][a]; uu = G * w / (ao * k)
            fl = (c["bc"][a:b] - ao) @ (uu * k); lo = np.minimum((c["bl"][a:b] - ao) @ (uu * k), fl)
            gi = np.flatnonzero(lo <= -GUARD)
            if len(gi): V = B = float(lo[gi[0]])
            else: V = float((c["bo"][b] - ao) @ (uu * k)); B = float(min(lo.min(), V))
        rows.append((x, V, B))
        if x in W: w = W[x][0] * W[x][1]   # applies from the next 01:05
    return pd.DataFrame(rows, columns=["day", "V", "B"]).set_index("day")


def main():
    DE, DH = S.build("MT5"), S.build("HD"); C = S.spliced_closes(DE, DH)
    cache = build_cache(); W = weekly_weights(cache, C); days = list(cache)
    starts = [d for d in days if pd.Timestamp("2022-01-03") <= d <= pd.Timestamp("2025-06-30")][::5]
    H = max(Q.HZ.values()) + 1; rng = np.random.default_rng(1510266); rows = []
    print(f"{len(starts)} rolling starts, horizon {H} business days; cells pass% / breach% by", list(Q.HZ))
    for G in (50_000, 75_000, 100_000, 150_000):
        res = [hold_path(cache, days[days.index(s):], W, G, H) for s in starts]
        st = np.array([r[0] for r in res]); dy = np.array([r[1] for r in res])
        cells = {kk: (100 * np.mean((st == 1) & (dy < h)), 100 * np.mean((st == 2) & (dy < h))) for kk, h in Q.HZ.items()}
        print(f"HOLD  G {G/1000:.0f}k rolling starts: " + " | ".join(f"{kk} {p:.1f}/{b:.1f}" for kk, (p, b) in cells.items()), flush=True)
        rows.append(dict(mode="HOLD", G=G, method="rolling", **{f"pass {kk}": p for kk, (p, b) in cells.items()}, **{f"breach {kk}": b for kk, (p, b) in cells.items()}))
        D = daily_series(cache, W, G)
        z = D[(D.index >= "2022-01-03")]; yr = z.V.groupby(z.index.year).sum().round(0).to_dict()
        print(f"DAILY G {G/1000:.0f}k: mean {z.V.mean():+.1f}/day, guard days {(z.V <= -GUARD).sum()}, worst {z.B.min():.0f}, by year {yr}")
        for nm, end in (("boot 2022-25", "2025-12-31"), ("boot 2022-26", "2026-10-02")):
            zz = z[z.index <= end]; s2, d2 = Q.simulate(zz.V.to_numpy(), zz.B.to_numpy(), H, rng)
            cells = {kk: (100 * np.mean((s2 == 1) & (d2 < h)), 100 * np.mean((s2 == 2) & (d2 < h))) for kk, h in Q.HZ.items()}
            print(f"DAILY G {G/1000:.0f}k {nm}: " + " | ".join(f"{kk} {p:.1f}/{b:.1f}" for kk, (p, b) in cells.items()), flush=True)
            rows.append(dict(mode="DAILY", G=G, method=nm, mean=zz.V.mean(), **{f"pass {kk}": p for kk, (p, b) in cells.items()}, **{f"breach {kk}": b for kk, (p, b) in cells.items()}))
        # DAILY on the same rolling starts (path = the day series from that start)
        V = z.V.to_numpy(); B = z.B.to_numpy(); zi = list(z.index); out = []
        for s in starts:
            i0 = zi.index(s); bal = START_BAL; stt, dd = 0, H
            for n in range(H):
                if i0 + n >= len(V): break
                if B[i0 + n] <= -BREACH or bal + B[i0 + n] <= 92_000: stt, dd = 2, n; break
                bal += min(V[i0 + n], 2000.0)
                if bal >= 108_000: stt, dd = 1, n; break
            out.append((stt, dd))
        st = np.array([o[0] for o in out]); dy = np.array([o[1] for o in out])
        cells = {kk: (100 * np.mean((st == 1) & (dy < h)), 100 * np.mean((st == 2) & (dy < h))) for kk, h in Q.HZ.items()}
        print(f"DAILY G {G/1000:.0f}k rolling starts: " + " | ".join(f"{kk} {p:.1f}/{b:.1f}" for kk, (p, b) in cells.items()), flush=True)
        rows.append(dict(mode="DAILY", G=G, method="rolling", **{f"pass {kk}": p for kk, (p, b) in cells.items()}, **{f"breach {kk}": b for kk, (p, b) in cells.items()}))
    pd.DataFrame(rows).to_csv(f"{LED}/D2_MT5RULE.csv", index=False)


if __name__ == "__main__":
    main()
