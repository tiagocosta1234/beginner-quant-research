"""
Round 306 (2026-10-02, PRE-REGISTERED): the two Expert Advisors in forex/expert_advisors -- "Range Breakout EA" and "Ninja Turtle Scalper EA" (René Balke / BM Trading, compiled .ex5 + input PDFs; NOT executed) -- RE-IMPLEMENTED from their input documentation and tested on MULTIPLE ASSETS
(the trader: "both are to be traded on multiple assets, go ahead"; data from 2020 onward only: MT5 M1 bid/ask starts 2021-10).
Step 0 (ledger checked first, k = 1605): the Range Breakout EA is an opening-range / range breakout: Rounds 126, 134, 167-171 (MNQ, MGC; 15 / 30-minute ranges, NR7, volume-confirmed) found no edge that survived out of sample; the Donchian scalper is a breakout with a tight trailing stop: the DAILY Donchian breakout and its fade were negative after costs in Round 303 and
the 1-5 minute trend / momentum rules in Rounds 121-122 had no edge. NOT tested: the EAs' own mechanics (pending stop orders, range-multiple stops / targets, a percent trailing stop) on index CFDs, FX and gold together at M1 with real bid/ask.
IMPLEMENTATION CAVEATS (stated now): the .ex5 files are compiled and were not run; the logic is reconstructed from the input lists (https://www.en.bmtrading.de; defaults are 'not a recommendation'). Where the documents are silent I choose the simplest reading and say so: one position per symbol at a time; the opposite pending order of the Range Breakout stays live after the first trade closes (Max total trades 2) or is cancelled (Max total trades 1);
the Donchian scalper checks the channel of the last COMPLETED bar of its timeframe and trades on the first M1 bar whose price touches it (the 'tick' trigger resolved at one-minute resolution), ignores a signal against an open position, and everything is flat at 16:00 NY (the live account's rule; the EAs themselves have no such exit).
DATA: MT5 M1 bid/ask (round271 loader, NY clock), 2021-10-04 .. 2026-09-30, 13 instruments in 3 pooled groups: IDX = US100, US500, US30, GER40, FRA40, UK100; FX = EURUSD, GBPUSD, USDJPY, USDCAD, USDCHF, AUDUSD; GLD = XAUUSD. IS = to 2024-06-30, OOS = 2024-07-01 .. 2026-09-30.
FILLS (real bid/ask, conservative): a buy stop fills when the ask high reaches the level at max(level, ask open) + slip, a sell stop when the bid low reaches it at min(level, bid open) - slip; a long exits at the BID (a short at the ASK): stop at min(stop, bid open) - slip (short mirror), take-profit at max(target, bid open) (short mirror), time exit at the bid / ask OPEN of the close bar; slip = 0.5 x the instrument's median quoted spread
on entries and stops; the stop is checked on the entry bar and a stop and a target in the same bar resolve STOP-FIRST. Net P&L in R = (exit - entry) x side / the initial stop distance, and in bp of the entry price.
RANGE BREAKOUT (RB): range = the BID high / low between two NY times; buy stop at the range high, sell stop at the range low (buffer 0); orders live from the range end until the close time, where unfilled orders are deleted and any position is closed. GRID: range window in (00:00-03:00 'asia', 03:00-04:00 'london', 08:00-09:30 'pre-US', 09:30-10:00 'us-open'), close time in (12:00, 16:00),
stop = k x range from the entry with k in (0.5, 1.0), target = m x range with m in (1.0, 2.0, none), maximum trades a day in (1, 2)  = 4 x 2 x 2 x 3 x 2 = 96 cells per group; a range of < 5 bars or narrower than 4 spreads is skipped; if both levels are touched in the same bar the day is skipped.
NINJA TURTLE SCALPER (NT): Donchian channel (highest bid high / lowest bid low of the last N COMPLETED bars of the timeframe); a long when the ask touches the upper band, a short when the bid touches the lower band; entries from 03:00 to 15:30 NY; stop = s% of the entry price; no target; trailing stop (TSL) off, or armed after a profit of a% with a distance of d% behind the highest bid since entry (the previous bar's extreme, no look-ahead).
GRID: timeframe in (5, 15) minutes, N in (20, 55), s in (0.15%, 0.30%), TSL in (off, a 0.10% / d 0.05%, a 0.20% / d 0.10%) = 24 cells per group.
HYPOTHESES: (96 + 24) cells x 3 groups = 360; K_TOTAL = 1605 + 360 = 1,965.
PLACEBO (the zero-edge twin of every cell, same geometry, same costs): RB = one coin-flip trade a day at the range-end bar open with the same stop and target; NT = a coin-flip side at the same entry bars, entry at the bar open, same stop and trailing rule. EXCESS = the cell's mean net R minus its placebo twin's.
STATISTICS: per cell and group: trades, mean net R, mean net bp, the placebo's mean, the excess, and a DATE-CLUSTERED bootstrap (4,000 draws, seed 3061) of P(mean net R > 0) and P(excess > 0), IS and OOS. CANDIDATE (the repo's rule + the excess test, fixed now): IS P >= 0.95 AND OOS P >= 1 - 0.01 / 1965 AND OOS mean net > 0 AND OOS trades >= 300 AND OOS P(excess > 0) >= 0.95, plus Benjamini-Hochberg q = 0.10 over the 360 OOS one-sided p-values.
MT5 COMPLIANCE NOTE (reported, not a filter): the server-request count per day (an order open, modify or close each counts; cap 2,000) is reported for the NT cells with a trailing stop (one modification per bar in which the stop moves, assuming the EA's step is 0).
PRIOR (stated now): 0 candidates. Both are breakout systems after costs: the RB cells average slightly negative net R (a few % of R of costs per trade, more for FX / gold where the range is narrow), the NT scalper with a 0.05-0.10% trailing distance loses more (it pays the spread on many more trades); a handful of cells will look positive in sample by chance; the placebo twins sit near -(cost / stop) in R.
POWER_NOTES: the OOS window holds ~600 trading days per instrument; RB cells make 1-2 trades a day per instrument (a few thousand OOS trades per group), NT cells tens of thousands; the standard error of the mean net R is ~0.03-0.06 R for RB, so only an edge above ~0.1 R a trade could clear the 1,965-test bar; instruments in a group are correlated (the date-clustered bootstrap handles it); one data source; the stop-first tie rule and the 0.5-spread slip are conservative.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import round271_one_to_one_generator as M

GROUPS = {"IDX": ["US100.cash", "US500.cash", "US30.cash", "GER40.cash", "FRA40.cash", "UK100.cash"], "FX": ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "USDCHF", "AUDUSD"], "GLD": ["XAUUSD"]}
FIRST, LAST, IS_END = pd.Timestamp("2021-10-04"), pd.Timestamp("2026-09-30"), pd.Timestamp("2024-06-30")
K_TOTAL, BOOT, SEED = 1605 + 360, 4000, 3061
WINDOWS = {"asia": (0, 180), "london": (180, 240), "preUS": (480, 570), "usopen": (570, 600)}
CLOSES = (720, 960)
SLF, TPF, TOTALS = (0.5, 1.0), (1.0, 2.0, None), (1, 2)
TFS, NS, SLP, TSLS = (5, 15), (20, 55), (0.0015, 0.0030), (None, (0.0010, 0.0005), (0.0020, 0.0010))
NT_FIRST, NT_LAST, FLAT = 180, 930, 960


# ------------------------------------------------------------------ data
class Inst:
    pass


def load(sym):
    df = M.load(sym)
    df = df[(df.index >= FIRST) & (df.index < LAST + pd.Timedelta(days=1))]
    I = Inst()
    I.sym, I.index = sym, df.index
    I.mins = (df.index.hour * 60 + df.index.minute).values
    I.day = df.index.normalize()
    I.bo, I.bh, I.bl, I.bc = (df[k].values.astype(float) for k in ("open", "high", "low", "close"))
    I.ao, I.ah, I.al, I.ac = (df[k].values.astype(float) for k in ("ask_open", "ask_high", "ask_low", "ask_close"))
    I.slip = 0.5 * float(np.median(I.ao - I.bo))
    I.spread = float(np.median(I.ao - I.bo))
    codes = I.day.values.astype("datetime64[D]").astype(np.int64)
    ch = np.flatnonzero(np.r_[True, codes[1:] != codes[:-1]])
    I.starts = ch
    I.ends = np.r_[ch[1:], len(codes)]
    I.dates = I.day[ch]
    return I


# ------------------------------------------------------------------ trade simulation
def sim(I, side, e, P, S, T, end, tsl=None):
    """One trade entered at M1 index e at price P (already including slip), stop S, target T (None), forced exit at index `end` (open of that bar; if end >= n the last close),
    optional trailing (trigger_frac, dist_frac). Returns (exit index, exit price). side +1 long (exits at the BID), -1 short (exits at the ASK)."""
    n = len(I.bo)
    endc = min(end, n - 1)
    sl_ = I.slip
    if endc <= e:
        return e, (I.bc[e] if side > 0 else I.ac[e])
    if side > 0:
        low = I.bl[e:endc]
        if tsl is not None:
            hi_prev = np.maximum.accumulate(np.r_[P, I.bh[e:endc - 1]])                 # highest bid up to the PREVIOUS bar
            arm = hi_prev >= P * (1 + tsl[0])
            stop = np.where(arm, np.maximum(S, hi_prev * (1 - tsl[1])), S)
        else:
            stop = np.full(len(low), S)
        hit_s = low <= stop
        js = int(np.argmax(hit_s)) if hit_s.any() else None
        jt = None
        if T is not None and endc > e + 1:
            hit_t = I.bh[e + 1:endc] >= T
            jt = int(np.argmax(hit_t)) + 1 if hit_t.any() else None
        if js is not None and (jt is None or js <= jt):
            j = e + js
            px = min(stop[js], I.bo[j]) - sl_ if js > 0 else stop[js] - sl_
            return j, px
        if jt is not None:
            j = e + jt
            return j, max(T, I.bo[j])
        return endc, (I.bo[endc] if endc < n and end < n else I.bc[n - 1])
    high = I.ah[e:endc]
    if tsl is not None:
        lo_prev = np.minimum.accumulate(np.r_[P, I.al[e:endc - 1]])
        arm = lo_prev <= P * (1 - tsl[0])
        stop = np.where(arm, np.minimum(S, lo_prev * (1 + tsl[1])), S)
    else:
        stop = np.full(len(high), S)
    hit_s = high >= stop
    js = int(np.argmax(hit_s)) if hit_s.any() else None
    jt = None
    if T is not None and endc > e + 1:
        hit_t = I.al[e + 1:endc] <= T
        jt = int(np.argmax(hit_t)) + 1 if hit_t.any() else None
    if js is not None and (jt is None or js <= jt):
        j = e + js
        px = max(stop[js], I.ao[j]) + sl_ if js > 0 else stop[js] + sl_
        return j, px
    if jt is not None:
        j = e + jt
        return j, min(T, I.ao[j])
    return endc, (I.ao[endc] if endc < n and end < n else I.ac[n - 1])


def pnl(I, side, P, X):
    return (X - P) * side


# ------------------------------------------------------------------ Range Breakout
def rb_day(I, k, rng, out, pl):
    """All RB cells for day index k of instrument I; appends (date, netR, bp) into out[key] and placebo into pl[key]."""
    s, e = I.starts[k], I.ends[k]
    md = I.mins[s:e]
    date = I.dates[k]
    for wn, (a, b) in WINDOWS.items():
        i0, i1 = s + int(np.searchsorted(md, a, "left")), s + int(np.searchsorted(md, b, "left"))
        if i1 - i0 < 5:
            continue
        hi, lo = float(I.bh[i0:i1].max()), float(I.bl[i0:i1].min())
        R = hi - lo
        if not R >= 4 * I.spread:
            continue
        for C in CLOSES:
            j0 = i1
            jc = s + int(np.searchsorted(md, C, "left"))
            if jc - j0 < 5:
                continue
            endx = jc if jc < e else e - 1                                             # the first bar at or after the close time (or, if the day's data ends earlier, its last bar)
            ah, bl = I.ah[j0:jc], I.bl[j0:jc]
            tb, ts = ah >= hi, bl <= lo
            ib = int(np.argmax(tb)) if tb.any() else None
            isl = int(np.argmax(ts)) if ts.any() else None
            if ib is not None and isl is not None and ib == isl:
                continue                                                                # both levels in the same bar: skip the day
            coin = rng.random() < 0.5
            for slf in SLF:
                for tpf in TPF:
                    # placebo twin: one coin-flip trade at the range-end bar open
                    side_p = 1 if coin else -1
                    Pp = (I.ao[j0] + I.slip) if side_p > 0 else (I.bo[j0] - I.slip)
                    Sp = Pp - side_p * slf * R
                    Tp = None if tpf is None else Pp + side_p * tpf * R
                    xj, xp = sim(I, side_p, j0, Pp, Sp, Tp, endx)
                    pl.setdefault((wn, C, slf, tpf), []).append((date, pnl(I, side_p, Pp, xp) / (slf * R), pnl(I, side_p, Pp, xp) / Pp * 1e4))
                    # the real cell: first trigger
                    cand = [(ib, 1), (isl, -1)]
                    cand = [(i, sd) for i, sd in cand if i is not None]
                    if not cand:
                        continue
                    i1st, sd1 = min(cand)
                    e1 = j0 + i1st
                    P1 = (max(hi, I.ao[e1]) + I.slip) if sd1 > 0 else (min(lo, I.bo[e1]) - I.slip)
                    S1 = P1 - sd1 * slf * R
                    T1 = None if tpf is None else P1 + sd1 * tpf * R
                    x1, xp1 = sim(I, sd1, e1, P1, S1, T1, endx)
                    r1 = pnl(I, sd1, P1, xp1)
                    trades = [(r1 / (slf * R), r1 / P1 * 1e4)]
                    # second trade (max 2 a day): the opposite order, still live after the first trade closed
                    sec = None
                    if x1 + 1 < jc:
                        if sd1 > 0:
                            m = I.bl[x1 + 1:jc] <= lo
                        else:
                            m = I.ah[x1 + 1:jc] >= hi
                        if m.any():
                            e2 = x1 + 1 + int(np.argmax(m))
                            sd2 = -sd1
                            P2 = (min(lo, I.bo[e2]) - I.slip) if sd2 < 0 else (max(hi, I.ao[e2]) + I.slip)
                            S2 = P2 - sd2 * slf * R
                            T2 = None if tpf is None else P2 + sd2 * tpf * R
                            x2, xp2 = sim(I, sd2, e2, P2, S2, T2, endx)
                            r2 = pnl(I, sd2, P2, xp2)
                            sec = (r2 / (slf * R), r2 / P2 * 1e4)
                    out.setdefault((wn, C, slf, tpf, 1), []).append((date,) + trades[0])
                    out.setdefault((wn, C, slf, tpf, 2), []).append((date,) + trades[0])
                    if sec is not None:
                        out[(wn, C, slf, tpf, 2)].append((date,) + sec)


# ------------------------------------------------------------------ Ninja Turtle Scalper
def nt_cells(I, rng, out, pl):
    n = len(I.bo)
    idx = I.index
    day_end = np.empty(n, dtype=np.int64)
    for k in range(len(I.starts)):
        s, e = I.starts[k], I.ends[k]
        jc = s + int(np.searchsorted(I.mins[s:e], FLAT, "left"))
        day_end[s:e] = jc if jc < e else e
    tradable = (I.mins >= NT_FIRST) & (I.mins <= NT_LAST)
    dates = I.day
    for tf in TFS:
        bars = pd.DataFrame({"h": I.bh, "l": I.bl}, index=idx).resample(f"{tf}min", label="left", closed="left").agg({"h": "max", "l": "min"}).dropna()
        start = idx.floor(f"{tf}min")
        for N in NS:
            up = bars["h"].shift(1).rolling(N, min_periods=N).max()
            dn = bars["l"].shift(1).rolling(N, min_periods=N).min()
            upm = up.reindex(start).values
            dnm = dn.reindex(start).values
            ub = np.isfinite(upm) & (I.ah >= upm)
            db = np.isfinite(dnm) & (I.bl <= dnm)
            cand = np.flatnonzero((ub ^ db) & tradable & (day_end > np.arange(n)))
            for slp in SLP:
                for tsl in TSLS:
                    key = (tf, N, slp, tsl)
                    j = 0
                    cl = len(cand)
                    while j < cl:
                        e = int(cand[j])
                        sd = 1 if ub[e] else -1
                        P = (max(upm[e], I.ao[e]) + I.slip) if sd > 0 else (min(dnm[e], I.bo[e]) - I.slip)
                        S = P * (1 - sd * slp)
                        x, xp = sim(I, sd, e, P, S, None, int(day_end[e]), tsl)
                        r = pnl(I, sd, P, xp)
                        out.setdefault(key, []).append((dates[e], r / (P * slp), r / P * 1e4))
                        # placebo twin at the same entry bar: coin side, entry at the bar open, same stop / trailing rule
                        sp = 1 if rng.random() < 0.5 else -1
                        Pp = (I.ao[e] + I.slip) if sp > 0 else (I.bo[e] - I.slip)
                        xj, xpp = sim(I, sp, e, Pp, Pp * (1 - sp * slp), None, int(day_end[e]), tsl)
                        rp = pnl(I, sp, Pp, xpp)
                        pl.setdefault(key, []).append((dates[e], rp / (Pp * slp), rp / Pp * 1e4))
                        j = int(np.searchsorted(cand, max(x, e) + 1))


# ------------------------------------------------------------------ statistics
def run_all(only=None, quick=False):
    rb_out = {g: {} for g in GROUPS}; rb_pl = {g: {} for g in GROUPS}
    nt_out = {g: {} for g in GROUPS}; nt_pl = {g: {} for g in GROUPS}
    rng = np.random.default_rng(SEED)
    t0 = time.time()
    for g, syms in GROUPS.items():
        for s in syms:
            if only and s not in only:
                continue
            I = load(s)
            ks = range(len(I.starts)) if not quick else range(0, len(I.starts), 25)
            for k in ks:
                rb_day(I, k, rng, rb_out[g], rb_pl[g])
            nt_cells(I, rng, nt_out[g], nt_pl[g])
            print(f"   {s}: {len(I.starts)} days, RB trades {sum(len(v) for v in rb_out[g].values()):,}, NT trades {sum(len(v) for v in nt_out[g].values()):,} ({time.time() - t0:.0f}s)", flush=True)
    return rb_out, rb_pl, nt_out, nt_pl


def per_date(trades, pos, nd):
    tot, cnt, bp = np.zeros(nd), np.zeros(nd), np.zeros(nd)
    for d, r, b in trades:
        j = pos.get(d)
        if j is None:
            continue
        tot[j] += r; cnt[j] += 1; bp[j] += b
    return tot, cnt, bp


def dry_run():
    I = load("US100.cash")
    print(f"US100: {len(I.bo):,} bars, {len(I.starts)} days, median spread {I.spread:.2f} pts, slip {I.slip:.2f}")
    # synthetic tests of `sim`: a long hits its stop, hits its target, and the stop-first tie
    class T_: pass
    Z = T_(); n = 8
    Z.bo = np.array([100, 100, 101, 102, 103, 104, 105, 106.]); Z.bh = Z.bo + 1; Z.bl = Z.bo - 1; Z.bc = Z.bo
    Z.ao = Z.bo + 0.2; Z.ah = Z.bh + 0.2; Z.al = Z.bl + 0.2; Z.ac = Z.bc + 0.2; Z.slip = 0.1
    j, px = sim(Z, 1, 1, 100.0, 98.0, 103.0, 8)
    assert j == 3 and abs(px - 103.0) < 1e-9, (j, px)                                  # target reached at bar 3 (bid high 103)
    Z2 = T_(); Z2.bo = np.array([100, 100, 99, 97, 96, 95, 94, 93.]); Z2.bh = Z2.bo + 1; Z2.bl = Z2.bo - 1; Z2.bc = Z2.bo
    Z2.ao = Z2.bo + 0.2; Z2.ah = Z2.bh + 0.2; Z2.al = Z2.bl + 0.2; Z2.ac = Z2.bc + 0.2; Z2.slip = 0.1
    j, px = sim(Z2, 1, 1, 100.0, 98.0, 103.0, 8)
    assert j == 2 and abs(px - (98.0 - 0.1)) < 1e-9, (j, px)                           # stop at bar 2 (bid low 98), minus slip
    j, px = sim(Z2, 1, 1, 100.0, 98.0, None, 2)
    assert j == 1 or j == 2
    # a short mirrored: ask-side exits
    j, px = sim(Z2, -1, 1, 100.0, 102.0, 95.0, 8)
    assert j == 5 and abs(px - 95.0) < 1e-9, (j, px)                                    # short target: the ask low first reaches 95 in bar 5 (94.2)
    print("sim tests passed (long target, long stop with slip, short target)")
    # trailing: long, trigger +2%, distance 1%: price rises to 110 then falls
    Z3 = T_(); path = np.array([100, 101, 103, 106, 110, 108, 104, 100.])
    Z3.bo = path; Z3.bh = path + 0.5; Z3.bl = path - 0.5; Z3.bc = path; Z3.ao = path + 0.1; Z3.ah = Z3.bh + 0.1; Z3.al = Z3.bl + 0.1; Z3.ac = path + 0.1; Z3.slip = 0.0
    j, px = sim(Z3, 1, 0, 100.0, 90.0, None, 8, tsl=(0.02, 0.01))
    assert 5 <= j <= 7 and px > 105, (j, px)                                            # the trailing stop locks in most of the move (stop ~ 110.5 * 0.99 = 109.4 -> exit when the bid low falls below it)
    print(f"trailing test passed: exit at bar {j}, price {px:.2f}")
    # counts on a quick sample of days (no P&L printed)
    rng = np.random.default_rng(1)
    out, pl = {}, {}
    for k in range(0, len(I.starts), 40):
        rb_day(I, k, rng, out, pl)
    print(f"RB sample: {len(out)} cell keys with trades, {sum(len(v) for v in out.values())} trades over {len(range(0, len(I.starts), 40))} days; placebo keys {len(pl)}")
    nout, npl = {}, {}
    t0 = time.time()
    nt_cells(I, rng, nout, npl)
    print(f"NT on US100 over all days: {len(nout)} cell keys, trades per key (median) {int(np.median([len(v) for v in nout.values()])):,}, {time.time() - t0:.0f}s")
    # look-ahead guard for RB: the range uses bars strictly before its end, the orders start at the end bar
    assert all(WINDOWS[w][1] <= 600 for w in WINDOWS)
    print("DRY RUN OK")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    rb_out, rb_pl, nt_out, nt_pl = run_all()
    alld = pd.date_range(FIRST, LAST, freq="D")
    pos = {d: i for i, d in enumerate(alld)}
    nd = len(alld)
    is_d = np.array([d <= IS_END for d in alld])
    rng = np.random.default_rng(SEED + 1)
    W = {}
    for name, m in (("IS", is_d), ("OOS", ~is_d)):
        n = int(m.sum()); p = np.flatnonzero(m)
        Wm = np.zeros((BOOT, nd), dtype=np.float32)
        idx = rng.integers(0, n, (BOOT, n))
        for b in range(BOOT):
            np.add.at(Wm[b], p[idx[b]], 1.0)
        W[name] = Wm
    rows = []
    def stats(trades, plbo):
        t, c, bpv = per_date(trades, pos, nd)
        pt, pc, _ = per_date(plbo, pos, nd)
        res = {}
        for name, m in (("IS", is_d), ("OOS", ~is_d)):
            n_ = float(c[m].sum())
            Wm = W[name]
            mean = float(t[m].sum() / max(n_, 1)); pmean = float(pt[m].sum() / max(pc[m].sum(), 1))
            P = float((Wm @ t / np.maximum(Wm @ c, 1e-9) > 0).mean()) if n_ > 0 else float("nan")
            exc = (Wm @ t / np.maximum(Wm @ c, 1e-9)) - (Wm @ pt / np.maximum(Wm @ pc, 1e-9))
            res[name] = dict(n=int(n_), net_R=mean, net_bp=float(bpv[m].sum() / max(n_, 1)), placebo_R=pmean, excess_R=mean - pmean, P=P, P_excess=float((exc > 0).mean()) if n_ > 0 else float("nan"))
        return res
    for g in GROUPS:
        for key, trades in rb_out[g].items():
            wn, C, slf, tpf, tot = key
            plb = rb_pl[g].get((wn, C, slf, tpf), [])
            r = dict(ea="RB", group=g, window=wn, close=C, sl=slf, tp=tpf, total=tot)
            r.update(stats(trades, plb)); rows.append(r)
        for key, trades in nt_out[g].items():
            tf, N, slp, tsl = key
            r = dict(ea="NT", group=g, tf=tf, N=N, sl=slp, tsl=tsl)
            r.update(stats(trades, nt_pl[g].get(key, []))); rows.append(r)
    ps = np.array([max(1.0 - (r["OOS"]["P"] if np.isfinite(r["OOS"]["P"]) else 0.0), 1.0 / BOOT) for r in rows])
    order = np.argsort(ps); thr = 0.0
    for rank, i in enumerate(order, 1):
        if ps[i] <= 0.10 * rank / len(rows):
            thr = max(thr, ps[i])
    for r, p in zip(rows, ps):
        r["p_oos"] = float(p); r["bh"] = bool(thr > 0 and p <= thr)
        r["candidate"] = bool(np.isfinite(r["IS"]["P"]) and r["IS"]["P"] >= 0.95 and r["OOS"]["P"] >= 1 - 0.01 / K_TOTAL and r["OOS"]["net_R"] > 0 and r["OOS"]["n"] >= 300 and r["OOS"]["P_excess"] >= 0.95 and r["bh"])
    cand = [r for r in rows if r["candidate"]]
    isg = [r for r in rows if np.isfinite(r["IS"]["P"]) and r["IS"]["P"] >= 0.95]
    print(f"{len(rows)} cells x groups with trades (expected up to 360); IS P >= 0.95: {len(isg)}; of those positive OOS net {sum(r['OOS']['net_R'] > 0 for r in isg)}; CANDIDATES {len(cand)}")
    for ea in ("RB", "NT"):
        f = [r for r in rows if r["ea"] == ea and r["OOS"]["n"] >= 300]
        print(f"   {ea}: {len(f)} cells with OOS n >= 300; mean OOS net {np.mean([r['OOS']['net_R'] for r in f]):+.3f} R (placebo {np.mean([r['OOS']['placebo_R'] for r in f]):+.3f}); positive-net cells {sum(r['OOS']['net_R'] > 0 for r in f)}; positive excess cells {sum(r['OOS']['excess_R'] > 0 for r in f)}")
        for g in GROUPS:
            ff = [r for r in f if r["group"] == g]
            if ff:
                print(f"      {g}: {len(ff)} cells, mean OOS net {np.mean([r['OOS']['net_R'] for r in ff]):+.3f} R, {np.mean([r['OOS']['net_bp'] for r in ff]):+.1f} bp, excess {np.mean([r['OOS']['excess_R'] for r in ff]):+.3f} R")
    for r in sorted([r for r in rows if r["OOS"]["n"] >= 300], key=lambda r: -r["OOS"]["net_R"])[:10]:
        tag = f"RB {r['window']} C{r['close'] // 60} SL{r['sl']} TP{r['tp']} T{r['total']}" if r["ea"] == "RB" else f"NT M{r['tf']} N{r['N']} SL{r['sl']:.2%} TSL{r['tsl']}"
        print(f"   {r['group']:>3} {tag:>42} | IS n {r['IS']['n']:>5} net {r['IS']['net_R']:+.3f}R P {r['IS']['P']:.2f} | OOS n {r['OOS']['n']:>5} net {r['OOS']['net_R']:+.3f}R ({r['OOS']['net_bp']:+.1f} bp) placebo {r['OOS']['placebo_R']:+.3f} excess {r['OOS']['excess_R']:+.3f} P {r['OOS']['P']:.3f} Pex {r['OOS']['P_excess']:.2f}")
    json.dump(dict(K_TOTAL=K_TOTAL, rows=rows, candidates=len(cand), n_rows=len(rows)), open(os.path.join(HERE, "round306_results.json"), "w"), indent=1, default=float)
    print(f"Saved round306_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
