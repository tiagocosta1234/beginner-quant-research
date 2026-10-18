"""BRK_PATTERNS: classic chart-pattern breakouts (triangles, wedges, trendlines, H&S, Darvas, VCP on H1/H4; 52-week high on D1)
on MT5 M1 bid/ask, with a random-entry control at the same risk geometry.
Pre-registration: forex/ea_research/PREREG_BRK_PATTERNS.md.  --dry-run: counts, truncation test, hand check (no R).  --run: results."""
import argparse, glob, os, numpy as np, pandas as pd
from multiprocessing import Pool
from forex.ea_research.orbx import ct

DATA = "forex/data_mt5/"
CACHE = "C:/work/scratch/brk_patterns_trades.parquet"
DEV, VAL, HOLD = ("2022-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-10-17")
TF = {"H1": 3600, "H4": 14400, "D1": 86400}
HOLDBARS = {"H1": 120, "H4": 60, "D1": 20}
PATS = ("TRI_SYM", "TRI_FLAT", "WEDGE", "TLINE", "HS", "DARVAS", "VCP")
TRIALS = [(p, tf) for p in PATS for tf in ("H1", "H4")] + [("HI52", "D1")]
K, WIN, FLAT, NCTRL = 3, 60, 0.02, 10


def load(sym, cut=None):
    d = pd.read_parquet(DATA + f"{sym}_M1_rates.parquet")
    d = d[(d.bo > 0) & (d.ao >= d.bo)].drop_duplicates("t").sort_values("t")
    if cut is not None:
        d = d[d.t < cut]
    # amendment 1: a zero-spread minute gets the median non-zero spread of the previous calendar month (causal)
    mon = pd.to_datetime(d.t, unit="s").dt.to_period("M")
    med = d.sp.where(d.sp > 0).groupby(mon).median()
    prev = med.shift(1).fillna(med).bfill()                   # amendment 2: months with no spread data at all take the next month's
    d = d.assign(sp=np.where(d.sp > 0, d.sp, mon.map(prev).to_numpy()))
    for k in ("o", "h", "l", "c"):
        d["a" + k] = d["b" + k] + d.sp
    D = {c: d[c].to_numpy() for c in ("t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "sp")}
    assert np.isfinite(D["sp"]).all(), f"{sym}: non-finite spreads after the zero-spread rule"
    sod = D["t"] % 86400
    D["roll"] = (sod >= 23 * 3600) | (sod < 3600)            # no fills / time exits in the server 23:00-00:59 window
    D["sod"] = sod
    return D


def bars(D, tf):
    key = D["t"] // tf
    st = np.flatnonzero(np.r_[True, key[1:] != key[:-1]]); en = np.r_[st[1:], len(key)]
    mh, ml = (D["bh"] + D["ah"]) / 2, (D["bl"] + D["al"]) / 2
    B = dict(st=st, en=en, o=(D["bo"][st] + D["ao"][st]) / 2, h=np.maximum.reduceat(mh, st), l=np.minimum.reduceat(ml, st),
             c=(D["bc"][en - 1] + D["ac"][en - 1]) / 2)
    pc = np.r_[B["c"][0], B["c"][:-1]]
    tr = np.maximum(B["h"], pc) - np.minimum(B["l"], pc)
    B["atr"] = pd.Series(tr).rolling(20 if tf == 86400 else 14).mean().to_numpy()
    B["sma50"] = pd.Series(B["c"]).rolling(50).mean().to_numpy()
    return B


def pivot_flags(h, l):
    n = len(h); sh = np.zeros(n, bool); sl = np.zeros(n, bool)
    for i in range(K, n - K):
        sh[i] = h[i] > h[i - K:i].max() and h[i] >= h[i + 1:i + K + 1].max()
        sl[i] = l[i] < l[i - K:i].min() and l[i] <= l[i + 1:i + K + 1].min()
    return sh, sl


def add_pivot(piv, p):
    if piv and piv[-1][2] == p[2]:
        if (p[2] == 1 and p[1] > piv[-1][1]) or (p[2] == -1 and p[1] < piv[-1][1]):
            piv[-1] = p
        return
    piv.append(p)
    del piv[:-8]


def lv(p1, p2, x):
    return p1[1] + (p2[1] - p1[1]) / (p2[0] - p1[0]) * (x - p1[0])


def orders(pat, B, piv, c, extra):
    """orders working during bar c+1, from bars <= c: list of (side, level, sl, tp or None, instance key)"""
    a = B["atr"][c]; x = c + 1; cl = B["c"][c]
    if not np.isfinite(a) or a <= 0:
        return []
    out = []
    H = [p for p in piv if p[2] == 1]; L = [p for p in piv if p[2] == -1]
    if pat in ("TRI_SYM", "TRI_FLAT", "WEDGE"):
        if len(H) < 2 or len(L) < 2:
            return []
        h1, h2, l1, l2 = H[-2], H[-1], L[-2], L[-1]
        first = min(h1[0], l1[0])
        if c - first > WIN:
            return []
        su, sl_ = (h2[1] - h1[1]) / (h2[0] - h1[0]) / a, (l2[1] - l1[1]) / (l2[0] - l1[0]) / a
        up, lo = lv(h1, h2, x), lv(l1, l2, x)
        hf = lv(h1, h2, first) - lv(l1, l2, first); hx = up - lo
        if not (0 < hx < hf) or not (lv(l1, l2, c) < cl < lv(h1, h2, c)):
            return []
        key = (pat, h1[0], h2[0], l1[0], l2[0])
        if pat == "TRI_SYM" and su < -FLAT and sl_ > FLAT:
            out += [(1, up, lo, up + hf, key), (-1, lo, up, lo - hf, key)]
        elif pat == "TRI_FLAT":
            if abs(su) <= FLAT and sl_ > FLAT:
                out.append((1, up, lo, up + hf, key))
            elif abs(sl_) <= FLAT and su < -FLAT:
                out.append((-1, lo, up, lo - hf, key))
        elif pat == "WEDGE":
            if su > FLAT and sl_ > FLAT:
                out.append((-1, lo, up, lo - hf, key))
            elif su < -FLAT and sl_ < -FLAT:
                out.append((1, up, lo, up + hf, key))
    elif pat == "TLINE":
        if len(H) >= 2 and len(L) >= 1:
            h1, h2 = H[-2], H[-1]
            if c - h1[0] <= WIN and h2[0] - h1[0] >= 10 and (h2[1] - h1[1]) / (h2[0] - h1[0]) / a < -FLAT:
                xs = np.arange(h1[0], c + 1)
                if (B["c"][h1[0]:c + 1] <= lv(h1, h2, xs)).all() and L[-1][1] < lv(h1, h2, x):
                    out.append((1, lv(h1, h2, x), L[-1][1], None, ("TL+", h1[0], h2[0])))
        if len(L) >= 2 and len(H) >= 1:
            l1, l2 = L[-2], L[-1]
            if c - l1[0] <= WIN and l2[0] - l1[0] >= 10 and (l2[1] - l1[1]) / (l2[0] - l1[0]) / a > FLAT:
                xs = np.arange(l1[0], c + 1)
                if (B["c"][l1[0]:c + 1] >= lv(l1, l2, xs)).all() and H[-1][1] > lv(l1, l2, x):
                    out.append((-1, lv(l1, l2, x), H[-1][1], None, ("TL-", l1[0], l2[0])))
    elif pat == "HS":
        if len(piv) >= 5:
            ls, t1, hd, t2, rs = piv[-5:]
            s = rs[2]                                           # +1: H-L-H-L-H top (sell); -1: inverse (buy)
            if c - ls[0] <= WIN and c - rs[0] <= 30 and s * (hd[1] - max(s * ls[1], s * rs[1]) * s) >= 0.5 * a \
                    and abs(ls[1] - rs[1]) <= a:
                nk = lv(t1, t2, x); ht = s * (hd[1] - lv(t1, t2, hd[0]))
                if s * (cl - lv(t1, t2, c)) > 0 and ht > 0:
                    out.append((-s, nk, rs[1], nk - s * ht, ("HS", ls[0], rs[0])))
    elif pat == "DARVAS":
        for s, top in ((1, extra["dtop"]), (-1, extra["dbot"])):
            j = top[c]
            if j < 0:
                continue
            hh, ll = (B["h"], B["l"]) if s == 1 else (-B["l"], -B["h"])
            if hh[j + 1:c + 1].max() > hh[j]:
                continue
            m = j + 1 + int(np.argmin(ll[j + 1:c + 1]))
            if c - m < 3 or c - (m + 3) > 20 or ll[m] >= hh[j]:
                continue
            out.append((s, s * hh[j], s * ll[m], None, ("DV", s, int(j), int(m))))
    elif pat == "VCP":
        if len(piv) >= 6 and c - piv[-6][0] <= WIN and np.isfinite(B["sma50"][c]):
            p = piv[-6:]; s = -p[-1][2]                         # last pivot a low -> +1 (long VCP); a high -> -1
            d = [s * (p[i][1] - p[i + 1][1]) for i in (0, 2, 4)]
            if s * (cl - B["sma50"][c]) > 0 and min(d) > 0 and d[1] <= 0.75 * d[0] and d[2] <= 0.75 * d[1] \
                    and s * (p[4][1] - cl) > 0:
                out.append((s, p[4][1], p[5][1], None, ("VCP", p[0][0], p[5][0])))
    elif pat == "HI52":
        if c >= 251:
            hi, lo = B["h"][c - 251:c + 1].max(), B["l"][c - 251:c + 1].min()
            out += [(1, hi, hi - 2 * a, None, ("52", c)), (-1, lo, lo + 2 * a, None, ("52", c))]
    return out


def walk(D, side, f, kend, sl, tp):
    o, h, l, c = (D["bo"], D["bh"], D["bl"], D["bc"]) if side == 1 else (D["ao"], D["ah"], D["al"], D["ac"])
    hs = (l[f:kend] <= sl) if side == 1 else (h[f:kend] >= sl)
    i_sl = int(np.argmax(hs)) if hs.any() else 1 << 40
    i_tp = 1 << 40
    if tp is not None:
        ht = (h[f:kend] >= tp) if side == 1 else (l[f:kend] <= tp); ht[0] = False
        i_tp = int(np.argmax(ht)) if ht.any() else 1 << 40
    if i_sl <= i_tp and i_sl < 1 << 40:
        return (sl if i_sl == 0 else (min(sl, o[f + i_sl]) if side == 1 else max(sl, o[f + i_sl]))), f + i_sl
    if i_tp < 1 << 40:
        return (max(tp, o[f + i_tp]) if side == 1 else min(tp, o[f + i_tp])), f + i_tp
    return c[kend - 1], kend - 1


def time_end(D, B, fbar, hold):
    """exclusive M1 end index of the time stop (close of pattern bar fbar + hold - 1); if that minute is in the rollover
    window the exit moves to 01:05 server; None if the data ends first"""
    n = len(D["t"])
    if fbar + hold >= len(B["st"]):
        return None
    j = B["st"][fbar + hold] - 1
    if D["roll"][j]:
        while j < n and (D["roll"][j] or D["sod"][j] < 3900):
            j += 1
    return j + 1 if j < n else None


def run_tf_pattern(D, B, pat, tf, extra, sh, slf, walk_exits=True):
    tfs = TF[tf]; n = len(B["c"]); piv = []; used = set(); busy = -1; out = []
    exit_bar = np.searchsorted(B["st"], np.arange(len(D["t"])), side="right") - 1 if walk_exits else None
    for c in range(n - 1):
        i = c - K                                               # pivot at bar i becomes known when bar i+K has closed
        if i >= K:
            if sh[i] and slf[i]:
                first, second = ((i, B["l"][i], -1), (i, B["h"][i], 1)) if B["c"][i] > B["o"][i] else ((i, B["h"][i], 1), (i, B["l"][i], -1))
                add_pivot(piv, first); add_pivot(piv, second)
            elif sh[i]:
                add_pivot(piv, (i, B["h"][i], 1))
            elif slf[i]:
                add_pivot(piv, (i, B["l"][i], -1))
        if c + 1 <= busy:
            continue
        od = [o for o in orders(pat, B, piv, c, extra) if o[4] not in used]
        if not od:
            continue
        s0, s1 = B["st"][c + 1], B["en"][c + 1]
        best = None
        for side, lvl, sl, tp, key in od:
            hit = (D["ah"][s0:s1] >= lvl) if side == 1 else (D["bl"][s0:s1] <= lvl)
            hit &= ~D["roll"][s0:s1]
            if not hit.any():
                continue
            k = s0 + int(np.argmax(hit))
            dist = abs(lvl - (D["bo"][k] + D["ao"][k]) / 2)
            if best is None or k < best[0] or (k == best[0] and dist < best[1]):
                best = (k, dist, side, lvl, sl, tp, key)
        if best is None:
            continue
        k, _, side, lvl, sl, tp, key = best
        e = max(lvl, D["ao"][k]) if side == 1 else min(lvl, D["bo"][k])
        if pat == "HI52":
            sl = e - side * 2 * B["atr"][c]                     # 2 ATR(20) from the actual fill
        if side * (e - sl) <= 0 or (tp is not None and side * (tp - e) <= 0):
            continue
        used.add(key)
        kend = time_end(D, B, c + 1, HOLDBARS[tf])
        row = dict(pat=pat, tf=tf, side=side, k=k, t=int(D["t"][k]), entry=e, sl=sl, tp=np.nan if tp is None else tp,
                   wsp=abs(e - sl) / max(D["sp"][k], 1e-12), key=str(key))
        if kend is None:
            row["R"] = np.nan; busy = n
        elif walk_exits:
            ex, kx = walk(D, side, k, kend, sl, tp)
            row["R"] = (ex - e) * side / abs(e - sl); row["kx"] = kx; busy = exit_bar[kx]
        out.append(row)
    return out


def darvas_tops(B, s):
    """for each bar c: index of the most recent Darvas top candidate known at c (highest of the previous 20 bars, not
    exceeded by the next 3), or -1"""
    hh = B["h"] if s == 1 else -B["l"]; n = len(hh); top = np.full(n, -1)
    last = -1
    for c in range(n):
        j = c - 3
        if j >= 20 and hh[j] > hh[j - 20:j].max() and hh[j + 1:j + 4].max() < hh[j]:
            last = j
        top[c] = last if last >= 0 and c - last <= WIN else -1
    return top


def control(D, B, tf, rows, rng):
    """NCTRL random market entries per real trade: same market, year, side, SL / TP distance as a share of the entry, time stop"""
    t = D["t"]; yr = pd.to_datetime(t[B["st"]], unit="s").year.to_numpy()
    # amendment 2: enter at the first minute of the drawn bar outside the rollover window (D1 bars all start inside it)
    free = np.flatnonzero(~D["roll"])
    j = np.searchsorted(free, B["st"]); j = np.minimum(j, len(free) - 1)
    first = free[j]; ok = (first >= B["st"]) & (first < B["en"])
    res = []
    for r in rows:
        y = pd.Timestamp(r["t"], unit="s").year
        cand = np.flatnonzero((yr == y) & ok)
        vals = []
        for b in rng.choice(cand, size=min(NCTRL, len(cand)), replace=False):
            f = first[b]; s = r["side"]
            e = D["ao"][f] if s == 1 else D["bo"][f]
            slf = abs(r["entry"] - r["sl"]) / r["entry"]
            sl = e * (1 - s * slf)
            tp = None if np.isnan(r["tp"]) else e * (1 + s * abs(r["tp"] - r["entry"]) / r["entry"])
            kend = time_end(D, B, b, HOLDBARS[tf])
            if kend is None:
                continue
            ex, _ = walk(D, s, f, kend, sl, tp)
            vals.append((ex - e) * s / abs(e - sl))
        res.append(np.mean(vals) if vals else np.nan)
    return res


def market(sym, cut=None, walk_exits=True, with_control=True, keep_open=False):
    D = load(sym, cut); out = []
    rng = np.random.default_rng(sum(map(ord, sym)) * 7919)
    for tf in ("H1", "H4", "D1"):
        B = bars(D, TF[tf]); sh, slf = pivot_flags(B["h"], B["l"])
        extra = {"dtop": darvas_tops(B, 1), "dbot": darvas_tops(B, -1)} if tf != "D1" else {}
        for pat, ptf in TRIALS:
            if ptf != tf:
                continue
            rows = run_tf_pattern(D, B, pat, tf, extra, sh, slf, walk_exits)
            if not keep_open:
                rows = [r for r in rows if not np.isnan(r["R"])]
            if walk_exits and with_control:
                for r, rc in zip(rows, control(D, B, tf, rows, rng)):
                    r["Rc"] = rc
            for r in rows:
                r["sym"] = sym
            out += rows
    return out


def build():
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    syms = sorted(os.path.basename(f)[:-17] for f in glob.glob(DATA + "*_M1_rates.parquet"))
    with Pool(4) as p:
        T = pd.DataFrame([r for rows in p.map(market, syms) for r in rows])
    T["day"] = pd.to_datetime(T.t, unit="s").dt.normalize()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True); T.to_parquet(CACHE)
    return T


def per(T, p):
    return (T.day >= p[0]) & (T.day < p[1])


def dry_run():
    syms = sorted(os.path.basename(f)[:-17] for f in glob.glob(DATA + "*_M1_rates.parquet"))
    print(f"markets {len(syms)}")
    with Pool(4) as p:
        T = pd.DataFrame([r for rows in p.starmap(market, [(s, None, True, False) for s in syms]) for r in rows])
    T["day"] = pd.to_datetime(T.t, unit="s").dt.normalize()
    for pat, tf in TRIALS:
        x = T[(T.pat == pat) & (T.tf == tf)]
        print(f"{pat:8s} {tf}  DEV {int(per(x, DEV).sum()):6d}  VAL {int(per(x, VAL).sum()):5d}  HOLD {int(per(x, HOLD).sum()):5d}"
              f"  markets {x.sym.nunique():2d}  long share {np.mean(x.side == 1) if len(x) else np.nan:.2f}"
              f"  width/spread median {x.wsp.median() if len(x) else np.nan:7.1f}")
    # truncation causality test: fills before the cut must be identical
    rng = np.random.default_rng(5)
    cols = ["pat", "tf", "side", "t", "entry", "sl", "tp", "key"]
    for sym in ("EURUSD", "XAUUSD", "NSDQ"):
        if sym not in syms:
            continue
        full = pd.DataFrame(market(sym, None, True, False, keep_open=True))
        cut = int(rng.uniform(full.t.quantile(.3), full.t.quantile(.9)))
        tr = pd.DataFrame(market(sym, cut, True, False, keep_open=True))
        nf = nd = nr = 0
        for (pat, tf), g in tr.groupby(["pat", "tf"]):
            # a trade still open at the cut legitimately blocks later entries in the truncated run: compare up to it
            lim = min(cut, g[g.R.isna()].t.min()) if g.R.isna().any() else cut
            a = full[(full.pat == pat) & (full.tf == tf) & (full.t <= lim)].reset_index(drop=True)
            b = g[g.t <= lim].reset_index(drop=True)
            nf += len(b)
            if len(a) != len(b) or not a[cols].fillna(0).equals(b[cols].fillna(0)):
                nd += 1
            closed = b.R.notna()
            if len(a) == len(b) and not np.allclose(a.R[closed].to_numpy(), b.R[closed].to_numpy()):
                nr += 1
        print(f"truncation {sym}: cut {pd.Timestamp(cut, unit='s')}, {nf} fills compared, trials with differing fills {nd}, "
              f"with differing exits {nr} (both must be 0)")
    # hand check: 3 random signals per pattern
    for pat, tf in TRIALS:
        x = T[(T.pat == pat) & (T.tf == tf)]
        for _, r in x.sample(min(3, len(x)), random_state=1).iterrows():
            print(f"  {pat} {tf} {r.sym} {pd.Timestamp(r.t, unit='s')} side {r.side:+d} entry {r.entry:.5g} sl {r.sl:.5g} "
                  f"tp {r.tp:.5g} width/spread {r.wsp:.0f} key {r.key}")


def run():
    T = build()
    print(f"trades {len(T)}, markets {T.sym.nunique()}, {T.day.min().date()}..{T.day.max().date()}")
    for pat, tf in TRIALS:
        x = T[(T.pat == pat) & (T.tf == tf)]
        row = [f"{pat:8s} {tf}"]
        d = x[per(x, DEV)]; v = x[per(x, VAL)]
        mu, t = ct(d) if len(d) > 2 else (np.nan, np.nan)
        dd = (d.R - d.Rc).dropna(); td = dd.mean() / (dd.std() / np.sqrt(len(dd))) if len(dd) > 2 else np.nan
        yrs = d.groupby(d.day.dt.year).R.mean()
        need_y = 2
        dev_ok = len(d) >= 200 and mu > 0 and t >= 2.71 and dd.mean() > 0 and td >= 2.0 and (yrs > 0).sum() >= need_y
        row.append(f"DEV n {len(d):5d} net {mu:+.3f} t {t:+.2f} ctrl {d.Rc.mean():+.3f} info {dd.mean():+.3f} (t {td:+.2f}) "
                   f"yrs {'/'.join(f'{m:+.2f}' for m in yrs)} -> {'PASS' if dev_ok else 'FAIL'}")
        mv, tv = ct(v) if len(v) > 2 else (np.nan, np.nan)
        val_ok = dev_ok and len(v) >= 60 and mv > 0 and tv >= 1.65
        row.append(f"VAL n {len(v):4d} net {mv:+.3f} t {tv:+.2f} ctrl {v.Rc.mean():+.3f}")
        if val_ok:
            h = x[per(x, HOLD)]; mh, th = ct(h)
            row.append(f"HOLD n {len(h)} net {mh:+.3f} t {th:+.2f} -> {'PASS' if mh > 0 and th >= 1.65 else 'FAIL'}")
        else:
            row.append("HOLD sealed")
        print(" | ".join(row))
    print("\nDescriptive (DEV + VAL only):")
    dv = T[per(T, (DEV[0], VAL[1]))]
    g = dv.groupby(["pat", "tf", "side"]).agg(n=("R", "size"), net=("R", "mean"), ctrl=("Rc", "mean"), wsp=("wsp", "median"))
    print(g.round(3).to_string())
    print("\nby class (DEV + VAL), net / ctrl:")
    from forex.ea_research.analog import mclass
    dv = dv.assign(cls=dv.sym.map(mclass))
    print(dv.pivot_table(index=["pat", "tf"], columns="cls", values="R", aggfunc="mean").round(3).to_string())
    print("\nwidth in spreads (DEV + VAL): R by quintile of |entry - SL| / spread")
    dv["wq"] = pd.qcut(dv.wsp, 5, labels=False, duplicates="drop")
    print(dv.groupby("wq").agg(wsp=("wsp", "median"), n=("R", "size"), net=("R", "mean"), ctrl=("Rc", "mean")).round(3).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        dry_run()
    if a.run:
        run()
