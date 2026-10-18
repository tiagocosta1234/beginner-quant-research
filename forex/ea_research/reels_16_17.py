"""Reel 16 (NY 30-min box: breakout close vs retest) and reel 17 (first 5-min candle vs EMA12, trailing stop) on MT5 NSDQ.
Pre-registration: forex/ea_research/PREREG_REELS_16_17.md.   python -m forex.ea_research.reels_16_17"""
import numpy as np, pandas as pd
from forex.ea_research.brk_patterns import load, walk
from forex.ea_research.brk50 import ts, NYZ
from forex.ea_research.orbx import ct

DEV, VAL, HOLD = ("2022-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-10-17")


def day_list(t):
    d = np.unique(t // 86400)
    return [pd.Timestamp(int(x) * 86400, unit="s") for x in d if pd.Timestamp(int(x) * 86400, unit="s").weekday() < 5]


def reel16(D, day):
    t = D["t"]; mc = (D["bc"] + D["ac"]) / 2
    b0, b1, w1, x1 = (ts(day.year, day.month, day.day, h, m, NYZ) for h, m in ((9, 30), (10, 0), (12, 0), (16, 0)))
    i0, i1, iw, ix = np.searchsorted(t, [b0, b1, w1, x1])
    if i1 - i0 < 24 or ix >= len(t) or iw - i1 < 30:
        return None
    hi, lo = D["bh"][i0:i1].max(), D["bl"][i0:i1].min()
    j = (t[i1:iw] - b1) // 300
    for c in range(int((w1 - b1) // 300)):
        sel = np.flatnonzero(j == c)
        if len(sel) < 3:
            continue
        cl = mc[i1 + sel[-1]]
        if cl > hi or cl < lo:
            side = 1 if cl > hi else -1
            k = int(np.searchsorted(t, b1 + (c + 1) * 300))
            if k >= ix - 1:
                return None
            e1 = D["ao"][k] if side > 0 else D["bo"][k]
            stop = lo if side > 0 else hi; risk = abs(e1 - stop); tgt = e1 + side * risk
            if side * (e1 - stop) <= 0:
                return None
            ex1, _ = walk(D, side, k, ix, stop, tgt)
            pts1 = (ex1 - e1) * side
            # trader 2: limit at the edge, same stop / target levels
            edge = hi if side > 0 else lo; pts2 = np.nan; filled = False
            for q in range(k, ix - 1):
                tgt_hit = (D["bh"][q] >= tgt) if side > 0 else (D["al"][q] <= tgt)
                fill = (D["al"][q] <= edge) if side > 0 else (D["bh"][q] >= edge)
                if fill:
                    e2 = min(edge, D["ao"][q]) if side > 0 else max(edge, D["bo"][q])
                    ex2, _ = walk(D, side, q, ix, stop, tgt); pts2 = (ex2 - e2) * side; filled = True; break
                if tgt_hit:
                    break
            return dict(day=day, side=side, risk=risk, pts1=pts1, R1=pts1 / risk, filled=filled, pts2=pts2,
                        R2=(pts2 / risk) if filled else np.nan, delay=int((t[k] - b1) // 60))
    return None


def reel17(D, day, trail, ema, key5, st5, hi5, lo5, cl5):
    t = D["t"]
    s0 = ts(day.year, day.month, day.day, 9, 30, NYZ); x1 = ts(day.year, day.month, day.day, 16, 0, NYZ)
    b = int(np.searchsorted(key5, s0 // 300))
    if b >= len(key5) or key5[b] != s0 // 300 or b < 20:
        return None
    k = int(np.searchsorted(t, s0 + 300)); ix = int(np.searchsorted(t, x1))
    if ix >= len(t) or k >= ix - 1:
        return None
    side = 1 if cl5[b] > ema[b] else (-1 if cl5[b] < ema[b] else 0)
    if side == 0:
        return None
    e = D["ao"][k] if side > 0 else D["bo"][k]
    stop = lo5[b] if side > 0 else hi5[b]
    if side * (e - stop) <= 0:
        return None
    risk = abs(e - stop)
    o, h, l, c = (D["bo"], D["bh"], D["bl"], D["bc"]) if side > 0 else (D["ao"], D["ah"], D["al"], D["ac"])
    q = k; bb = b + 1
    while True:
        seg_end = int(np.searchsorted(t, (key5[bb] + 1) * 300)) if bb < len(key5) else ix
        seg_end = min(seg_end, ix)
        if seg_end <= q:
            seg_end = q + 1
        hit = (l[q:seg_end] <= stop) if side > 0 else (h[q:seg_end] >= stop)
        if hit.any():
            j = q + int(np.argmax(hit))
            ex = stop if j == k else (min(stop, o[j]) if side > 0 else max(stop, o[j]))
            break
        if seg_end >= ix:
            ex = c[ix - 1]; break
        # 5-min close of candle bb: tighten the stop
        cand = ema[bb] if trail == "ema" else (lo5[bb - 2:bb + 1].min() if side > 0 else hi5[bb - 2:bb + 1].max())
        stop = max(stop, cand) if side > 0 else min(stop, cand)
        q = seg_end; bb += 1
    return dict(day=day, side=side, risk=risk, R=(ex - e) * side / risk, pts=(ex - e) * side)


def bars5(D):
    t = D["t"]; key = t // 300
    st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    mh, ml, mc = (D["bh"] + D["ah"]) / 2, (D["bl"] + D["al"]) / 2, (D["bc"] + D["ac"]) / 2
    en = np.r_[st[1:], len(t)]
    cl = mc[en - 1]
    ema = pd.Series(cl).ewm(span=12, adjust=False).mean().to_numpy()
    return key[st], st, np.maximum.reduceat(mh, st), np.minimum.reduceat(ml, st), cl, ema


def run_market(sym):
    D = load(sym); days = [d for d in day_list(D["t"]) if d >= pd.Timestamp("2022-01-01")]
    key5, st5, hi5, lo5, cl5, ema = bars5(D)
    r16 = [x for x in (reel16(D, d) for d in days) if x]
    r17 = {tr: [x for x in (reel17(D, d, tr, ema, key5, st5, hi5, lo5, cl5) for d in days) if x] for tr in ("ema", "swing")}
    return pd.DataFrame(r16), {k: pd.DataFrame(v) for k, v in r17.items()}


def per(x, p):
    return x[(x.day >= p[0]) & (x.day < p[1])]


def stats(x, col):
    y = x.dropna(subset=[col]).assign(R=lambda z: z[col])
    if len(y) < 3:
        return dict(n=len(y))
    mu, t = ct(y); w = y.R[y.R > 0].sum(); ls = -y.R[y.R <= 0].sum()
    return dict(n=len(y), R=mu, t=t, win=(y.R > 0).mean(), pf=w / ls if ls > 0 else np.nan, yrs=y.groupby(y.day.dt.year).R.mean().round(3).to_dict())


def main():
    from forex.ea_research.usdjpy_account_env import account, HZ
    out = {}
    for sym in ("NSDQ", "SP", "DOW"):
        r16, r17 = run_market(sym); out[sym] = (r16, r17)
    r16, r17 = out["NSDQ"]
    trials = [("R16-T1", r16, "R1"), ("R16-T2", r16, "R2"), ("R17-EMA", r17["ema"], "R"), ("R17-SWING", r17["swing"], "R")]
    print("NSDQ trials (net R per trade; DEV 2022-24 / VAL 2025; HOLD sealed unless DEV + VAL pass)")
    for name, x, col in trials:
        d, v = stats(per(x, DEV), col), stats(per(x, VAL), col)
        ok = d.get("n", 0) >= 300 and d.get("R", -1) > 0 and d.get("t", 0) >= 2.5 and sum(val > 0 for val in d.get("yrs", {}).values()) >= 2
        okv = ok and v.get("R", -1) > 0 and v.get("t", 0) >= 1.65
        line = (f"  {name:9s} DEV n {d['n']} {d.get('R', np.nan):+.3f} R (t {d.get('t', np.nan):+.2f}) win {d.get('win', np.nan):.0%} PF {d.get('pf', np.nan):.2f} yrs {d.get('yrs')}"
                f" -> {'PASS' if ok else 'FAIL'} | VAL n {v['n']} {v.get('R', np.nan):+.3f} (t {v.get('t', np.nan):+.2f}) win {v.get('win', np.nan):.0%} PF {v.get('pf', np.nan):.2f}")
        if okv:
            hh = stats(per(x, HOLD), col); line += f" | HOLD n {hh['n']} {hh.get('R', np.nan):+.3f} (t {hh.get('t', np.nan):+.2f})"
        print(line)
    print("\nReel 16 claims on NSDQ (2022-25, points per trade at 1 contract; the reel: T1 $3,760 vs T2 $1,780; T2 out > half the days;"
          " on both-traded days T2 ~2x; no-retest days $2,840):")
    a = r16[r16.day < "2026-01-01"]
    both = a[a.filled]; nofill = a[~a.filled]
    print(f"  days with a signal {len(a)}; T2 never filled on {len(nofill)} ({len(nofill)/len(a):.0%})")
    print(f"  total points: T1 {a.pts1.sum():+.0f}, T2 {a.pts2.sum():+.0f}")
    print(f"  days both traded ({len(both)}): T1 {both.pts1.sum():+.0f} pts, T2 {both.pts2.sum():+.0f} pts; per trade T1 {both.R1.mean():+.3f} R, T2 {both.R2.mean():+.3f} R")
    print(f"  no-retest days ({len(nofill)}): T1 {nofill.pts1.sum():+.0f} pts ({nofill.R1.mean():+.3f} R a trade, win {(nofill.R1 > 0).mean():.0%})")
    print("\nReel 17 claims (NAS100 M5 2019-26: 1,448 trades, win 57%, PF 1.29): NSDQ 2022-25 here")
    for tr in ("ema", "swing"):
        x = r17[tr][r17[tr].day < "2026-01-01"]; s = stats(x, "R")
        print(f"  trail {tr:5s}: n {s['n']}, win {s['win']:.0%}, PF {s['pf']:.2f}, {s['R']:+.3f} R a trade, median stop {x.risk.median():.1f} pts")
    print("\nDescriptive: same rules on SP and DOW (2022-25, R per trade / win / PF)")
    for sym in ("SP", "DOW"):
        b16, b17 = out[sym]; b16 = b16[b16.day < "2026-01-01"]
        s1, s2 = stats(b16, "R1"), stats(b16, "R2")
        e_, w_ = stats(b17["ema"][b17["ema"].day < "2026-01-01"], "R"), stats(b17["swing"][b17["swing"].day < "2026-01-01"], "R")
        print(f"  {sym}: R16-T1 {s1['R']:+.3f}/{s1['win']:.0%}/{s1['pf']:.2f}  R16-T2 {s2['R']:+.3f}/{s2['win']:.0%}/{s2['pf']:.2f}"
              f"  R17-EMA {e_['R']:+.3f}/{e_['win']:.0%}/{e_['pf']:.2f}  R17-SWING {w_['R']:+.3f}/{w_['win']:.0%}/{w_['pf']:.2f}")
    print("\nAccount environment, NSDQ, $250 a trade, from 95,472 (2022-25 trades; pass% / breach%):")
    days = pd.bdate_range("2022-01-03", "2025-12-31"); Hh = max(HZ.values()); rng = np.random.default_rng(1622)
    for name, x, col in trials:
        x = x[x.day < "2026-01-01"].dropna(subset=[col])
        Rd = x.set_index("day")[col].reindex(days); trd = Rd.notna().to_numpy(); r = Rd.fillna(0).to_numpy()
        s = rng.integers(0, len(r) - 5, size=(20000, Hh // 5 + 2)); bi = (s[:, :, None] + np.arange(5)).reshape(20000, -1)[:, :Hh]
        st, ev, _ = account(r[bi], trd[bi], 250)
        print(f"  {name:9s} ({len(x)} trades, {x[col].mean():+.3f} R): " + "  ".join(
            f"{k} {100*np.mean((st==1)&(ev<h)):.1f}/{100*np.mean((st==2)&(ev<h)):.0f}" for k, h in HZ.items() if k in ("22 Dec", "31 Mar 27", "30 Jun 27")))
    pd.concat([r16.assign(market="NSDQ")]).to_parquet("C:/work/scratch/reel16_nsdq.parquet")


if __name__ == "__main__":
    main()
