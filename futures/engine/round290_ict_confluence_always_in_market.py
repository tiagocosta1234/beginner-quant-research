"""
Round 290 (2026-10-01, PRE-REGISTERED): an ALWAYS-IN-THE-MARKET 1-minute ICT-confluence algorithm on MT5 broker index CFDs (the trader: "what if we create a frequent trading algorithm that analyzes 1minute ict
confluences and its always on a trade, either long or short, research on that").
Step 0 (ledger checked first, k = 897): the pieces were tested separately on MNQ + MGC futures and all found no edge -- FVG retests (Rounds 150, 189), order-block retests and Silver Bullet (159), OTE (76, 201), Judas swing
(125), sweep fades (126), inverted versions of all of them (160), 1-minute EMA stop-and-reverse, i.e. always-in-market (121). Not yet tested: (a) the same primitives as ONE combined confluence signal, (b) on MT5 broker's CFD M1 bid/ask data (real
spreads, 2021-10 .. 2026-09), (c) as an always-in-the-market position. This round does (a)-(c). The honest prior (stated now): no edge; an always-in-market book flips often and each flip costs a spread (0.5 bp in US hours, ~0.9 bp in
the early hours on US100), so unless the confluence predicts the next minutes by more than that, the book's net result is about minus its flip count x the spread.

DATA / SESSION. MT5 M1 bid/ask (round271_one_to_one_generator.load), NY wall clock, US100.cash, US500.cash, GER40.cash. A session = the bars from 18:00 NY of the previous evening to 16:00 NY (the 16:00-18:00 gap is excluded); features
use the whole session (so the Asian and London ranges are inside the look-back), but SIGNALS are only acted on from 03:00 NY and everything is flat from 15:55 NY (no overnight, no weekend, no swap). A session needs >= 400 bars.
FEATURES (all from bid OHLC, causal: the state at bar t uses bars <= t only; a dry-run test re-computes every feature on a prefix and compares). Each gives +1 (bullish), -1 (bearish) or 0:
  F1 SWEEP     within the last 5 bars the low (high) took out the lowest low (highest high) of bars t-120..t-6 and the bar closes back above (below) that level -> +1 (-1).
  F2 DISPLACE  the bar closes above (below) the highest high (lowest low) of the prior 30 bars and its range >= 2 x the mean range of the prior 60 bars -> +1 (-1).
  F3 FVG       a 3-bar gap (low[j] > high[j-2], size >= the mean range of the prior 60 bars; mirror for bearish) is retested within 60 bars: the first bar whose low (high) re-enters the gap with a close that has not gone through the
               far side -> +1 (-1) at that bar (impulse).
  F4 OTE       over the last 60 bars the range >= 6 x the mean bar range; after an up-leg (low before high) the close sits 62%-79% of the way back down from the high -> +1; after a down-leg the mirror -> -1.
  F5 OB        Round 159's `detect_order_blocks` unchanged (the last opposite candle before a close beyond the prior 60-bar extreme; the signal is the first retest, in the breakout direction), applied per session -> impulse.
Each feature impulse (F1, F2, F4: the bar the state becomes non-zero or flips) stays ACTIVE for 15 bars (the latest impulse within 15 bars counts). SCORE S_t = sum of the five active directions. C1: sign(S_t) when |S_t| >= 1; C2: sign(S_t) when |S_t| >= 2 (a
confluence of at least two features in the same direction net of conflicts).
PART A -- does any of it predict the next minutes? Events: each feature's impulse bars (F1-F5) and the bars where sign(C1) / sign(C2) becomes non-zero or flips, between 03:00 NY and the end of the session, de-clustered per (feature, horizon) so that events are >= h bars apart. Trade:
enter at the NEXT bar's open (long at the ask, short at the bid), exit h bars later at that bar's open (long at the bid, short at the ask), h in (5, 15, 60) minutes; net bps = P&L / entry price x 10^4 after the real spread. Both sides are tested: FOLLOW (trade the signal) and FADE (the opposite).
Cells: 7 signals x 3 horizons x 3 instruments x 2 sides = 126 (ledger rows 898-1023).
PART B -- the always-in-market book. Decision at each bar's close, fill at the next bar's open; position = sign(C) when the signal is non-zero, otherwise the previous position (hysteresis); flat before the first signal after 03:00 NY and from 15:55 NY. One unit of notional;
P&L from open to open of consecutive bars; each unit traded costs half the spread at the fill bar (a flip long->short costs one full spread). Variants C1 and C2 x 3 instruments x FOLLOW/FADE = 12 cells (rows 1024-1035); daily net bps.
SAMPLE. Session dates 2021-10-04 .. 2026-09-30; IS = to 2024-06-30, OOS = 2024-07-01 .. 2026-09-30.
STATISTICS. Part A: per cell n, win rate, mean net bps, day-clustered bootstrap P(mean > 0) (4,000 draws over session days). Part B: per cell days, mean net / gross / cost bps per day, annualised Sharpe of the daily series, flips and entries per day, P(mean > 0) by day bootstrap.
CANDIDATE (the repo's rule, fixed now; K_TOTAL = 897 + 126 + 12 = 1,035): IS P >= 0.95 AND OOS P >= 1 - 0.01/1035 AND OOS mean net > 0 AND OOS n >= 150 (Part A events, Part B days), plus Benjamini-Hochberg at q = 0.10 over the OOS one-sided p-values of eligible
cells. SECOND VERDICT (practical): the always-in-market book is worth building only if a candidate in Part B has an OOS annualised Sharpe >= 1.0 after costs (the 1-Step 10%-in-a-month math needs far more; this only says the book is a usable sleeve).
POWER_NOTES: a 15-minute event has a standard deviation of ~8-15 bps; with several thousand events per cell the standard error is ~0.2-0.3 bp against a 0.5-1 bp round-trip cost, so edges of ~1 bp gross are detectable in Part A; Part B has ~1,200 days
(about 600 out of sample), a daily standard deviation that an always-in-market book makes large relative to its mean, so only a Sharpe of roughly 1 or more is detectable out of sample.
LIMITS stated now: this formalises ICT in six mechanical rules; the trader's discretionary version (higher-timeframe bias, news, narrative) is not captured, and a negative result here does not test that.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view as sw
import round271_one_to_one_generator as M

try:
    from round159_ict_order_blocks_silver_bullet import detect_order_blocks
except Exception:                                   # fallback: Round 159's function, copied unchanged
    K_SWING, LOOKBACK_OB, MAX_WAIT_BARS = 60, 10, 240

    def detect_order_blocks(bars):
        op, hi, lo, cl = bars["open"].values, bars["high"].values, bars["low"].values, bars["close"].values
        ts = bars.index.values
        n = len(bars)
        signals = []
        i = K_SWING
        while i < n:
            prior_hi, prior_lo = hi[i - K_SWING:i].max(), lo[i - K_SWING:i].min()
            direction, ob_lo, ob_hi = 0, None, None
            if cl[i] > prior_hi:
                for j in range(i - 1, max(i - LOOKBACK_OB - 1, -1), -1):
                    if cl[j] < op[j]:
                        direction, ob_lo, ob_hi = 1, lo[j], hi[j]
                        break
            elif cl[i] < prior_lo:
                for j in range(i - 1, max(i - LOOKBACK_OB - 1, -1), -1):
                    if cl[j] > op[j]:
                        direction, ob_lo, ob_hi = -1, lo[j], hi[j]
                        break
            if direction == 0:
                i += 1
                continue
            found = False
            for k in range(i + 1, min(i + MAX_WAIT_BARS, n)):
                touched = lo[k] <= ob_hi and hi[k] >= ob_lo
                if touched:
                    entry = cl[k]
                    sl = ob_lo - 0.1 * (ob_hi - ob_lo) if direction == 1 else ob_hi + 0.1 * (ob_hi - ob_lo)
                    signals.append((ts[k], direction, entry, sl))
                    found = True
                    break
            i = (k if found else i + MAX_WAIT_BARS) + 1
        return pd.DataFrame(signals, columns=["ts", "direction", "entry", "sl"])

SYMS = ["US100.cash", "US500.cash", "GER40.cash"]
FIRST, OOS_FROM, LAST = pd.Timestamp("2021-10-04"), pd.Timestamp("2024-07-01"), pd.Timestamp("2026-09-30")
HS = (5, 15, 60)
SIGS = ("F1", "F2", "F3", "F4", "F5", "C1", "C2")
ACTIVE = 15
K_TOTAL = 897 + 126 + 12
START_MIN, FLAT_MIN = 3 * 60, 15 * 60 + 55
NS = 10 ** 9 * 60


# ------------------------------------------------------------------ data
def sessions(sym):
    df = M.load(sym)
    t = df.index
    keep = (t.hour < 16) | (t.hour >= 18)
    df = df[keep]
    sd = (df.index + pd.Timedelta(hours=6)).normalize()
    out = []
    for d, g in df.groupby(sd):
        if d < FIRST or d > LAST or d.weekday() > 4 or len(g) < 400:
            continue
        out.append((d, g))
    return out


def arr(g):
    ts = g.index.values.astype("datetime64[ns]").astype(np.int64)
    mins = (g.index.hour * 60 + g.index.minute).values
    return dict(ts=ts, mins=mins, idx=g.index, bo=g["open"].values.astype(float), bh=g["high"].values.astype(float), bl=g["low"].values.astype(float), bc=g["close"].values.astype(float),
                ao=g["ask_open"].values.astype(float), ac=g["ask_close"].values.astype(float))


# ------------------------------------------------------------------ features (causal)
def impulse(state):
    prev = np.concatenate([[0], state[:-1]])
    return np.where((state != 0) & (state != prev), state, 0).astype(np.int8)


def f_sweep(hi, lo, cl):
    Lref = pd.Series(lo).rolling(115).min().shift(6).values
    Href = pd.Series(hi).rolling(115).max().shift(6).values
    R5l = pd.Series(lo).rolling(5).min().values
    R5h = pd.Series(hi).rolling(5).max().values
    up = (R5l < Lref) & (cl > Lref)
    dn = (R5h > Href) & (cl < Href)
    return impulse(up.astype(np.int8) - dn.astype(np.int8))


def f_disp(hi, lo, cl, mr):
    rng = hi - lo
    ph = pd.Series(hi).rolling(30).max().shift(1).values
    pl = pd.Series(lo).rolling(30).min().shift(1).values
    big = rng >= 2.0 * mr
    up = (cl > ph) & big
    dn = (cl < pl) & big
    return impulse(up.astype(np.int8) - dn.astype(np.int8))


def f_fvg(hi, lo, cl, mr):
    n = len(hi)
    out = np.zeros(n, np.int8)
    if n < 4:
        return out
    j = np.arange(2, n)
    bull = np.flatnonzero((lo[j] > hi[j - 2]) & ((lo[j] - hi[j - 2]) >= mr[j])) + 2
    bear = np.flatnonzero((hi[j] < lo[j - 2]) & ((lo[j - 2] - hi[j]) >= mr[j])) + 2
    for jj in bull:
        bot = hi[jj - 2]; top = lo[jj]
        for t in range(jj + 1, min(jj + 61, n)):
            if cl[t] < bot:
                break
            if lo[t] <= top:
                out[t] += 1
                break
    for jj in bear:
        top = lo[jj - 2]; bot = hi[jj]
        for t in range(jj + 1, min(jj + 61, n)):
            if cl[t] > top:
                break
            if hi[t] >= bot:
                out[t] -= 1
                break
    return np.sign(out).astype(np.int8)


def f_ote(hi, lo, cl, mr):
    W = 60
    n = len(hi)
    out = np.zeros(n, np.int8)
    if n < W:
        return out
    H, Lw = sw(hi, W), sw(lo, W)
    ih, il = H.argmax(1), Lw.argmin(1)
    Hh, Ll = H.max(1), Lw.min(1)
    c = cl[W - 1:]
    rng = Hh - Ll
    big = rng >= 6.0 * mr[W - 1:]
    with np.errstate(invalid="ignore", divide="ignore"):
        d_up = (Hh - c) / rng
        d_dn = (c - Ll) / rng
    bull = (il < ih) & big & (d_up >= 0.62) & (d_up <= 0.79)
    bear = (ih < il) & big & (d_dn >= 0.62) & (d_dn <= 0.79)
    st = np.zeros(n, np.int8)
    st[W - 1:] = bull.astype(np.int8) - bear.astype(np.int8)
    return impulse(st)


def f_ob(A):
    n = len(A["bo"])
    out = np.zeros(n, np.int8)
    if n < 70:
        return out
    bars = pd.DataFrame({"open": A["bo"], "high": A["bh"], "low": A["bl"], "close": A["bc"]}, index=pd.DatetimeIndex(A["idx"]))
    sg = detect_order_blocks(bars)
    if len(sg):
        pos = np.searchsorted(A["idx"].values, sg["ts"].values)
        for p, d in zip(pos, sg["direction"].values):
            out[p] += np.int8(d)
    return np.sign(out).astype(np.int8)


def features(A):
    hi, lo, cl = A["bh"], A["bl"], A["bc"]
    mr = pd.Series(hi - lo).rolling(60).mean().shift(1).values
    imp = {"F1": f_sweep(hi, lo, cl), "F2": f_disp(hi, lo, cl, mr), "F3": f_fvg(hi, lo, cl, mr), "F4": f_ote(hi, lo, cl, mr), "F5": f_ob(A)}
    n = len(hi)
    ar = np.arange(n)
    S = np.zeros(n)
    for k in imp:
        v = imp[k]
        last = np.maximum.accumulate(np.where(v != 0, ar, -1))
        act = np.where((last >= 0) & (ar - last < ACTIVE), v[np.maximum(last, 0)], 0)
        S = S + act
    c1 = np.sign(S).astype(np.int8)
    c2 = np.where(np.abs(S) >= 2, np.sign(S), 0).astype(np.int8)
    imp["C1"] = impulse(c1)
    imp["C2"] = impulse(c2)
    return imp, c1, c2


# ------------------------------------------------------------------ Part A
def events_for(A, imp, d, sym):
    rows = []
    n = len(A["bo"])
    ts, mins = A["ts"], A["mins"]
    for sig in SIGS:
        idx = np.flatnonzero(imp[sig] != 0)
        idx = idx[(mins[idx] >= START_MIN) & (mins[idx] < 16 * 60)]
        for h in HS:
            last = -10 ** 9
            for t in idx:
                if t < last + h:
                    continue
                e, x = t + 1, t + 1 + h
                if x >= n or ts[x] - ts[e] > (h + 2) * NS:
                    continue
                last = t
                rows.append((sym, d, sig, h, int(imp[sig][t]), (A["bo"][x] - A["ao"][e]) / A["ao"][e] * 1e4, (A["bo"][e] - A["ao"][x]) / A["bo"][e] * 1e4))
    return rows


# ------------------------------------------------------------------ Part B
def book(A, c, variant_unused=None):
    n = len(c)
    mins = A["mins"]
    tg = np.zeros(n)
    cur = 0
    for t in range(n):
        m = mins[t]
        if m < START_MIN or m >= FLAT_MIN:
            cur = 0
            continue
        s = c[t]
        if s != 0:
            cur = s
        tg[t] = cur
    tg[max(n - 2, 0):] = 0
    return tg


def day_pnl(A, tg):
    n = len(tg)
    mo = (A["bo"] + A["ao"]) / 2.0
    spr = A["ao"] - A["bo"]
    ts = A["ts"]
    gross = cost = 0.0
    flips = ent = 0
    prev = 0.0
    for t in range(n - 2):
        d = abs(tg[t] - prev)
        if d > 0:
            cost += d * 0.5 * spr[t + 1] / mo[t + 1] * 1e4
            if d == 2: flips += 1
            else: ent += 1
        if tg[t] != 0 and ts[t + 2] - ts[t + 1] <= 5 * NS:
            gross += tg[t] * (mo[t + 2] - mo[t + 1]) / mo[t + 1] * 1e4
        prev = tg[t]
    if prev != 0:
        pass
    return gross, cost, flips, ent


# ------------------------------------------------------------------ statistics
def cboot(dates, x, nb=4000, seed=7):
    """day-clustered bootstrap P(mean > 0): resample session days, event-weighted mean."""
    dates = np.asarray(dates); x = np.asarray(x, float)
    u, inv = np.unique(dates, return_inverse=True)
    s = np.bincount(inv, weights=x); c = np.bincount(inv).astype(float)
    rng = np.random.default_rng(seed)
    ix = rng.integers(0, len(u), (nb, len(u)))
    m = s[ix].sum(1) / c[ix].sum(1)
    return float((m > 0).mean())


def bh(ps, q=0.10):
    p = np.array(ps, float); o = np.argsort(p); m = len(p)
    ok = np.zeros(m, bool); thr = -1
    for r, i in enumerate(o, 1):
        if p[i] <= q * r / m:
            thr = r
    if thr > 0:
        ok[o[:thr]] = True
    return ok


def build(syms=SYMS, limit=None):
    ev, books = [], []
    for sym in syms:
        for k, (d, g) in enumerate(sessions(sym)):
            if limit and k >= limit:
                break
            A = arr(g)
            imp, c1, c2 = features(A)
            ev += events_for(A, imp, d, sym)
            for var, c in (("C1", c1), ("C2", c2)):
                tg = book(A, c)
                gr, co, fl, en = day_pnl(A, tg)
                books.append((sym, d, var, gr, co, fl, en))
    E = pd.DataFrame(ev, columns=["sym", "date", "sig", "h", "dir", "long", "short"])
    B = pd.DataFrame(books, columns=["sym", "date", "var", "gross", "cost", "flips", "entries"])
    return E, B


def dry_run():
    t0 = time.time()
    # causality: every feature recomputed on a prefix must equal the full computation on that prefix
    ss = sessions("US100.cash")
    rng = np.random.default_rng(11)
    pick = rng.choice(len(ss), 6, replace=False)
    nchk = 0
    for p in pick:
        d, g = ss[p]
        A = arr(g)
        full, c1, c2 = features(A)
        n = len(g)
        for t in rng.integers(150, n - 1, 5):
            Ap = arr(g.iloc[: t + 1])
            part, p1, p2 = features(Ap)
            for k in full:
                assert np.array_equal(full[k][: t + 1], part[k]), (str(d), int(t), k)
            assert np.array_equal(c1[: t + 1], p1) and np.array_equal(c2[: t + 1], p2), (str(d), int(t))
            nchk += 1
    print(f"causality test passed on {nchk} prefixes (7 signals, C1, C2)")
    # counts and placebo on a 40-session sample of each instrument (no real-signal means printed)
    E, B = build(limit=40)
    print(f"sample: {len(E)} events over {E['date'].nunique()} session-days x 3 instruments; events per (signal, h=15): " + ", ".join(f"{s} {len(E[(E['sig'] == s) & (E['h'] == 15)])}" for s in SIGS))
    r = np.random.default_rng(5)
    pl = np.where(r.random(len(E)) < 0.5, E["long"], E["short"])
    print(f"placebo (random side) mean net {pl.mean():+.2f} bps; mean cost per event {-(E['long'] + E['short']).mean() / 2:.2f} bps")
    for var in ("C1", "C2"):
        b = B[B["var"] == var]
        print(f"book {var}: flips/day {b['flips'].mean():.1f}, entries/day {b['entries'].mean():.2f}, mean cost {b['cost'].mean():.2f} bps/day (counts and costs only)")
    print(f"sessions per instrument: " + ", ".join(f"{s} {len(sessions(s))}" for s in SYMS))
    print(f"dry-run time {time.time() - t0:.0f}s")
    print("DRY RUN OK")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    E, B = build()
    E.to_pickle(os.path.join(HERE, "round290_events.pkl")); B.to_pickle(os.path.join(HERE, "round290_books.pkl"))
    print(f"built {len(E)} events and {len(B)} book-days ({time.time() - t0:.0f}s)")
    rows = []
    for sym in SYMS:
        for sig in SIGS:
            for h in HS:
                x = E[(E["sym"] == sym) & (E["sig"] == sig) & (E["h"] == h)]
                for side, name in ((1, "follow"), (-1, "fade")):
                    net = np.where(x["dir"].values * side > 0, x["long"].values, x["short"].values)
                    y = x.assign(net=net)
                    cell = dict(part="A", sym=sym, sig=sig, h=h, side=name)
                    for lab, m in (("IS", y["date"] < OOS_FROM), ("OOS", y["date"] >= OOS_FROM)):
                        z = y[m]
                        cell[lab] = dict(n=int(len(z)), mean=float(z["net"].mean()) if len(z) else float("nan"), win=float((z["net"] > 0).mean()) if len(z) else float("nan"),
                                         P=cboot(z["date"].values, z["net"].values) if len(z) > 20 else float("nan"))
                    rows.append(cell)
    for sym in SYMS:
        for var in ("C1", "C2"):
            b = B[(B["sym"] == sym) & (B["var"] == var)]
            for side, name in ((1, "follow"), (-1, "fade")):
                net = side * b["gross"] - b["cost"]
                y = b.assign(net=net)
                cell = dict(part="B", sym=sym, sig=var, h=0, side=name)
                for lab, m in (("IS", y["date"] < OOS_FROM), ("OOS", y["date"] >= OOS_FROM)):
                    z = y[m]
                    sd = z["net"].std()
                    cell[lab] = dict(n=int(len(z)), mean=float(z["net"].mean()), gross=float((side * z["gross"]).mean()), cost=float(z["cost"].mean()), flips=float(z["flips"].mean()),
                                     entries=float(z["entries"].mean()), sharpe=float(z["net"].mean() / sd * np.sqrt(252)) if sd > 0 else float("nan"), win=float((z["net"] > 0).mean()),
                                     P=M.boot_p(z["net"].values) if len(z) > 20 else float("nan"))
                rows.append(cell)
    print(f"\n{'part':>4} {'sym':>10} {'sig':>3} {'h':>3} {'side':>6} | {'IS n':>6} {'mean':>7} {'P':>5} | {'OOS n':>6} {'mean':>7} {'win':>5} {'P':>5}")
    for r in rows:
        i, o = r["IS"], r["OOS"]
        print(f"{r['part']:>4} {r['sym'][:6]:>10} {r['sig']:>3} {r['h']:>3} {r['side']:>6} | {i['n']:>6} {i['mean']:>+7.2f} {i['P']:>5.2f} | {o['n']:>6} {o['mean']:>+7.2f} {o['win']:>5.1%} {o['P']:>5.2f}")
    bar = 1 - 0.01 / K_TOTAL
    cand = [r for r in rows if r["IS"]["P"] >= 0.95 and r["OOS"]["P"] >= bar and r["OOS"]["mean"] > 0 and r["OOS"]["n"] >= 150]
    elig = [r for r in rows if r["OOS"]["n"] >= 150 and np.isfinite(r["OOS"]["P"])]
    ok = bh([1 - r["OOS"]["P"] for r in elig], 0.10)
    print(f"\nCANDIDATES (IS P >= 0.95, OOS P >= {bar:.6f}, OOS mean > 0, n >= 150): {len(cand)} of {len(rows)}; Benjamini-Hochberg q=0.10 over {len(elig)} eligible cells: {int(ok.sum())}")
    for r in cand:
        print("   ", r["part"], r["sym"], r["sig"], r["h"], r["side"], "IS", r["IS"], "OOS", r["OOS"])
    allm = np.array([r["OOS"]["mean"] for r in rows if r["part"] == "A" and np.isfinite(r["OOS"]["mean"])])
    print(f"Part A OOS mean net bps over {len(allm)} cells: mean {allm.mean():+.2f}, positive in {np.mean(allm > 0):.0%}")
    bm = [r for r in rows if r["part"] == "B"]
    print("Part B OOS (mean net bps/day, Sharpe, flips/day, cost bps/day): " + "; ".join(f"{r['sym'][:5]} {r['sig']} {r['side']} {r['OOS']['mean']:+.1f}, {r['OOS']['sharpe']:+.2f}, {r['OOS']['flips']:.1f}, {r['OOS']['cost']:.1f}" for r in bm))
    json.dump(dict(rows=rows, n_candidates=len(cand), n_bh=int(ok.sum()), k_total=K_TOTAL, bar=bar), open(os.path.join(HERE, "round290_results.json"), "w"), indent=1, default=float)
    print(f"Saved round290_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
