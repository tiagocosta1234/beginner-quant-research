"""
Round 303 (2026-10-02, PRE-REGISTERED): a MASSIVE MULTI-ASSET TECHNICAL-ANALYSIS SWEEP on MT5 broker's 44 non-crypto instruments (the trader: "lets run a massive multi assets strategy, ideas for technical analysis?" -- "go ahead" on the list of ideas; the Dalio 'many uncorrelated streams' premise needs several streams that each have a real NET edge, so this round looks for them).
Step 0 (ledger checked first, k = 1324): trend / momentum (Rounds 253, 280, 284: real before MT5 broker's swap, erased by it), cross-sectional long-short (284), index pairs (283), carry (280), the 3-day-fall reversal (285-293: confirmed on indices only; 291: not in FX / metals / energy), dollar / gold / copper / oil / 10Y leaders (155-164), day-of-week and hour-of-day (163, 298), the overnight drift (298, Part A: +1.8 bp gross, eaten by cost), intraday patterns (121, 122, 129, 138, 159, 160, 221, 222, 290, 301), seconds (302) -- all no edge or a lead too small. NOT in the ledger as daily multi-asset signals: RSI(2) reversal, daily sweep-and-reclaim, Donchian breakout / its fade, volatility-squeeze breakout, outside-bar continuation / reversal, one-day shock continuation / reversal. Month-of-year seasonality and the overnight / intraday split were considered and NOT run (Round 156 / 122 tested Halloween and the turn of the month; month-by-IS-sign has ~5 out-of-sample observations per cell; the 17:00-17:00 D1 bar has no overnight leg).
DATA / COSTS (Round 279 / 280 machinery, `R8.prep()`): D1 bars of the 44 non-crypto MT5 broker instruments (bar = 17:00-17:00 NY; bad prints > 10 sigma or > 50% zeroed in the return series), from each instrument's first bar; costs of a trade held from the close of day i to the close of day i + H (H = 1 or 2 or 3 as stated): net = side x sum of daily returns over the held days + swap x nights (today's per-night swap fraction of price for the side, triple on the instrument's own weekday) - half the median D1 spread at entry and again at exit - the per-side FX / metal commission twice.
Positions are weekend-flat (the exit weekday is later than the entry weekday and <= H + 2 calendar days, Round 285's `eligible`) so every cell is usable on the live account; one position per instrument at a time (no new signal until the exit). Swap values are today's, applied to the whole history (this overstates the swap before 2022: a disclosed bias).
GROUPS (pooled hypotheses, 5): IDX = 12 index CFDs; FX = 15 pairs (DXY excluded); MET = 5 metals; ENG = 4 energies; AGR = 7 agricultural markets.
FAMILIES (all signals causal at the close of day i; the trade enters at that close). Direction: +1 long, -1 short.
  F1 RSI(2) reversal (Wilder, alpha = 1/2): LONG when RSI2 <= 10, SHORT when RSI2 >= 90; variants PLAIN and TREND (long only above the 200-day mean, short only below); sides long and short as separate hypotheses; H in (1, 2, 3).  -> 2 variants x 2 sides x 3 H x 5 groups = 60.
  F2 Sweep-and-reclaim (daily 'turtle soup'): LONG when low[i] < min(low[i-n .. i-1]) and close[i] > that minimum; SHORT mirror; n in (5, 20); sides separate; H in (1, 3).  -> 2 x 2 x 2 x 5 = 40.
  F3 Donchian breakout and its fade: an UP-break = close[i] > max(high[i-n .. i-1]), a DOWN-break the mirror; n in (20, 55); the trade direction is FOLLOW (up-break long, down-break short) or FADE (up-break short, down-break long); the 4 combinations (follow-up, follow-down, fade-up, fade-down) separate; H in (1, 3).  -> 2 x 4 x 2 x 5 = 80.
  F4 Volatility-squeeze breakout: the 5-day range (max high - min low over days i-5 .. i-1) is in the lowest 20% of its own previous 250 values (causal) and the close of day i is above that range's high (UP) or below its low (DOWN); FOLLOW or FADE x UP / DOWN pooled in 2 hypotheses (follow, fade, the direction of the break being the reference); H in (1, 3).  -> 2 x 2 x 5 = 20.
  F5 Outside bar: high[i] > high[i-1] and low[i] < low[i-1]; BULL if close > open, BEAR otherwise; the trade follows or fades the bar's colour; the 4 combinations separate; H in (1, 3).  -> 4 x 2 x 5 = 40.
  F6 One-day shock: z1 = return[i] / SD of daily returns over days i-60 .. i-1 (causal); UP shock z1 >= 2, DOWN shock z1 <= -2; follow or fade, the 4 combinations separate; H in (1, 3).  -> 4 x 2 x 5 = 40.
HYPOTHESES: 60 + 40 + 80 + 20 + 40 + 40 = 280; K_TOTAL = 1324 + 280 = 1,604.
BENCHMARK (the unconditional trade): for every (group, side, H) the mean net of the same trade taken on EVERY eligible day (so drift and carry are not credited to a signal); a signal cell's EXCESS = its mean net minus the benchmark of its side and H over the same period.
SPLIT: IS = each instrument's start .. 2021-10-31, OOS = 2021-11-01 .. 2026-09-30 (Rounds 284 / 285).
STATISTICS: per cell and half: trades, mean net bp, mean gross bp (before swap and costs), the benchmark, the excess, and a DATE-CLUSTERED bootstrap (4,000 draws, seed 3031; trades of the same date fall together) of P(mean net > 0) and P(excess > 0).
CANDIDATE (the repo's rule + the excess test; fixed now): IS P(net > 0) >= 0.95 AND OOS P(net > 0) >= 1 - 0.01 / 1604 AND OOS mean net > 0 AND OOS trades >= 300 AND OOS P(excess > 0) >= 0.95, plus Benjamini-Hochberg at q = 0.10 over the 280 OOS one-sided p-values (p = 1 - OOS P net, floored at 1/4000).
IF ANY CANDIDATE: a follow-up round (not this one) builds the equal-risk portfolio of the survivors plus the confirmed 3-day-fall reversal and runs the 1-Step simulations; if none, the sweep is a negative result for these 6 families.
PRIOR (stated now): 0 candidates. About 5% of the 280 cells (14) will show IS P >= 0.95 by chance and most will not carry over; the leads most likely to survive in sample are the short-horizon reversals on indices (F1 plain long, F6 down-shock fade, which restate the confirmed 3-day-fall effect) -- they would be duplicates of Rounds 285-293, not new streams; the breakout (F3) and squeeze (F4) families are expected to lose to costs in FX and to carry a small continuation in energy / agricultural markets at best.
POWER_NOTES: the pooled cells hold hundreds to a few thousand OOS trades each with a daily standard deviation of ~100 bp, a standard error of the mean of ~3-6 bp, so only an excess above ~10 bp a trade is detectable against the 1,604-test bar; trades on the same day across instruments are correlated (the date-clustered bootstrap handles it); one data source (MT5 D1); swaps are today's.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import round280_swap_aware_long_short as R8
import round285_multi_day_dip_reversal as R5
from mt5broker import universe as U

GROUPS = {"IDX": [s for s in U.INDICES if s in R8.SYMS], "FX": [s for s in U.FX if s in R8.SYMS and s != "DXY.cash"], "MET": [s for s in U.METALS if s in R8.SYMS],
          "ENG": [s for s in U.ENERGY if s in R8.SYMS], "AGR": [s for s in U.AGRI if s in R8.SYMS]}
OOS_FROM, LAST = pd.Timestamp("2021-11-01"), pd.Timestamp("2026-09-30")
K_TOTAL, BOOT, SEED = 1324 + 280, 4000, 3031


# ------------------------------------------------------------------ series and features
def build(P):
    S = {}
    for s in R8.SYMS:
        D = P["D1"][s]
        c = P["close"][s].dropna()
        d = c.index
        d = d[d <= LAST + pd.Timedelta(days=5)]
        c = c.reindex(d)
        o, h, l = (D[k].reindex(d).values.astype(float) for k in ("open", "high", "low"))
        r = P["ret"][s].reindex(d).fillna(0.0).values
        sd = P["ret"][s].reindex(d).rolling(60, min_periods=40).std().shift(1).values        # SD of the 60 returns BEFORE day i
        wd = d.weekday.values
        nights = np.ones(len(d))
        nights[1:] = np.where(wd[:-1] == P["trip"][s], 3.0, 1.0)
        S[s] = dict(d=d, o=o, h=h, l=l, c=c.values.astype(float), r=r, sd=sd, wd=wd, nights=nights, hs=P["hs"][s], fl=P["frac_l"][s], fs=P["frac_s"][s], comm=P["comm"][s])
    return S


def rsi2(c):
    x = pd.Series(c)
    dlt = x.diff()
    up, dn = dlt.clip(lower=0), (-dlt).clip(lower=0)
    au, ad = up.ewm(alpha=0.5, adjust=False).mean(), dn.ewm(alpha=0.5, adjust=False).mean()
    au, ad = au.values, ad.values
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(ad == 0, np.where(au > 0, 100.0, 50.0), 100 - 100 / (1 + au / ad))
    out[~np.isfinite(au) | ~np.isfinite(ad)] = np.nan
    return out


def rollmax_prev(x, n):
    return pd.Series(x).shift(1).rolling(n, min_periods=n).max().values


def rollmin_prev(x, n):
    return pd.Series(x).shift(1).rolling(n, min_periods=n).min().values


def signals(S1):
    """dict {(family, variant): direction array in {-1, 0, +1}} for one instrument (the trade direction at the close of day i)."""
    c, o, h, l, r, sd = S1["c"], S1["o"], S1["h"], S1["l"], S1["r"], S1["sd"]
    n = len(c)
    out = {}
    rs = rsi2(c)
    sma = pd.Series(c).rolling(200, min_periods=200).mean().values
    ok = np.isfinite(rs) & np.isfinite(sma)
    long_, short_ = ok & (rs <= 10), ok & (rs >= 90)
    out[("F1", "plain", "long")] = np.where(long_, 1, 0)
    out[("F1", "plain", "short")] = np.where(short_, -1, 0)
    out[("F1", "trend", "long")] = np.where(long_ & (c > sma), 1, 0)
    out[("F1", "trend", "short")] = np.where(short_ & (c < sma), -1, 0)
    for nn in (5, 20):
        mn, mx = rollmin_prev(l, nn), rollmax_prev(h, nn)
        out[("F2", f"n{nn}", "long")] = np.where(np.isfinite(mn) & (l < mn) & (c > mn), 1, 0)
        out[("F2", f"n{nn}", "short")] = np.where(np.isfinite(mx) & (h > mx) & (c < mx), -1, 0)
    for nn in (20, 55):
        mx, mn = rollmax_prev(h, nn), rollmin_prev(l, nn)
        up, dn = np.isfinite(mx) & (c > mx), np.isfinite(mn) & (c < mn)
        out[("F3", f"n{nn}", "follow_up")] = np.where(up, 1, 0)
        out[("F3", f"n{nn}", "follow_down")] = np.where(dn, -1, 0)
        out[("F3", f"n{nn}", "fade_up")] = np.where(up, -1, 0)
        out[("F3", f"n{nn}", "fade_down")] = np.where(dn, 1, 0)
    hi5, lo5 = pd.Series(h).shift(1).rolling(5, min_periods=5).max().values, pd.Series(l).shift(1).rolling(5, min_periods=5).min().values
    rng5 = hi5 - lo5
    q20 = pd.Series(rng5).shift(1).rolling(250, min_periods=250).quantile(0.2).values           # the lowest 20% of the PREVIOUS 250 five-day ranges
    sq = np.isfinite(rng5) & np.isfinite(q20) & (rng5 <= q20)
    up, dn = sq & (c > hi5), sq & (c < lo5)
    out[("F4", "squeeze", "follow")] = np.where(up, 1, 0) + np.where(dn, -1, 0)
    out[("F4", "squeeze", "fade")] = np.where(up, -1, 0) + np.where(dn, 1, 0)
    ph, pl = np.r_[np.nan, h[:-1]], np.r_[np.nan, l[:-1]]
    outside = np.isfinite(ph) & (h > ph) & (l < pl)
    bull, bear = outside & (c > o), outside & (c < o)
    out[("F5", "bull", "follow")] = np.where(bull, 1, 0)
    out[("F5", "bear", "follow")] = np.where(bear, -1, 0)
    out[("F5", "bull", "fade")] = np.where(bull, -1, 0)
    out[("F5", "bear", "fade")] = np.where(bear, 1, 0)
    z1 = np.where(np.isfinite(sd) & (sd > 0), r / sd, np.nan)
    ups, dns = np.isfinite(z1) & (z1 >= 2), np.isfinite(z1) & (z1 <= -2)
    out[("F6", "up", "follow")] = np.where(ups, 1, 0)
    out[("F6", "down", "follow")] = np.where(dns, -1, 0)
    out[("F6", "up", "fade")] = np.where(ups, -1, 0)
    out[("F6", "down", "fade")] = np.where(dns, 1, 0)
    return out


def hold_masks(S1, Hs):
    d, wd = S1["d"], S1["wd"]
    n = len(d)
    out = {}
    for H in Hs:
        m = np.zeros(n, bool)
        if n > H:
            m[: n - H] = (wd[H:] > wd[:-H]) & ((d[H:] - d[:-H]).days <= H + 2)
        out[H] = m
    return out


def trades_for(S1, dirs, H, elig):
    """Greedy non-overlapping trades of one direction array: [(entry date index in S1, net bp, gross bp, side)]."""
    r, c, nights = S1["r"], S1["c"], S1["nights"]
    cr, cn = np.r_[0.0, np.cumsum(r)], np.r_[0.0, np.cumsum(nights)]
    rows = []
    n = len(c)
    i = 0
    idx = np.flatnonzero((dirs != 0) & elig)
    nxt = -1
    for i in idx:
        if i < nxt:
            continue
        side = int(dirs[i])
        gross = side * (cr[i + H + 1] - cr[i + 1])
        f = S1["fl"] if side > 0 else S1["fs"]
        swap = f * (cn[i + H + 1] - cn[i + 1])
        cost = S1["hs"] / c[i] + S1["hs"] / c[i + H] + 2 * S1["comm"]
        rows.append((i, (gross + swap - cost) * 1e4, gross * 1e4, side))
        nxt = i + H
    return rows


def benchmark_trades(S1, side, H, elig):
    d = np.full(len(S1["c"]), side)
    r, c, nights = S1["r"], S1["c"], S1["nights"]
    cr, cn = np.r_[0.0, np.cumsum(r)], np.r_[0.0, np.cumsum(nights)]
    idx = np.flatnonzero(elig)
    gross = side * (cr[idx + H + 1] - cr[idx + 1])
    f = S1["fl"] if side > 0 else S1["fs"]
    swap = f * (cn[idx + H + 1] - cn[idx + 1])
    cost = S1["hs"] / c[idx] + S1["hs"] / c[idx + H] + 2 * S1["comm"]
    return idx, (gross + swap - cost) * 1e4


# ------------------------------------------------------------------ statistics
def pb(num, den, W):
    return float((W @ num / np.maximum(W @ den, 1e-9) > 0).mean())


def cell_hypotheses():
    H_F1 = (1, 2, 3)
    cells = []
    for g in GROUPS:
        for var in ("plain", "trend"):
            for side in ("long", "short"):
                for H in H_F1:
                    cells.append((("F1", var, side), g, H))
        for nn in (5, 20):
            for side in ("long", "short"):
                for H in (1, 3):
                    cells.append((("F2", f"n{nn}", side), g, H))
        for nn in (20, 55):
            for v in ("follow_up", "follow_down", "fade_up", "fade_down"):
                for H in (1, 3):
                    cells.append((("F3", f"n{nn}", v), g, H))
        for v in ("follow", "fade"):
            for H in (1, 3):
                cells.append((("F4", "squeeze", v), g, H))
        for col in ("bull", "bear"):
            for v in ("follow", "fade"):
                for H in (1, 3):
                    cells.append((("F5", col, v), g, H))
        for sh in ("up", "down"):
            for v in ("follow", "fade"):
                for H in (1, 3):
                    cells.append((("F6", sh, v), g, H))
    return cells


def dry_run():
    P = R8.prep()
    S = build(P)
    cells = cell_hypotheses()
    print(f"{len(S)} instruments; groups: " + ", ".join(f"{g} {len(v)}" for g, v in GROUPS.items()) + f"; hypotheses {len(cells)} (expected 280); K_TOTAL {K_TOTAL}")
    assert len(cells) == 280
    # 1) the cost model equals Round 285's trade_net (no commission) on random index trades
    Ss = R5.prep_series(P)
    rng = np.random.default_rng(1)
    worst = 0.0
    for s in ("US100.cash", "GER40.cash", "JP225.cash"):
        a, b = S[s], Ss[s]
        n = len(b["d"])
        for _ in range(30):
            i = int(rng.integers(300, n - 5)); H = int(rng.integers(1, 4)); side = int(rng.choice((-1, 1)))
            if not (b["wd"][i + H] > b["wd"][i]):
                continue
            ia = a["d"].get_loc(b["d"][i])
            mine = trades_for(a, np.where(np.arange(len(a["c"])) == ia, side, 0), H, hold_masks(a, (H,))[H])
            ref = R5.trade_net(b, i, H, side)
            worst = max(worst, abs(mine[0][1] - ref) if mine else 0.0)
    print(f"cost model vs Round 285's trade_net on 90 random index trades: largest difference {worst:.6f} bp")
    assert worst < 1e-6
    # 2) RSI(2) on a known series: a long fall drives RSI2 to ~0
    x = np.array([100, 99, 98, 97, 96, 95.0]); r_ = rsi2(x)
    assert r_[-1] < 5 and abs(rsi2(np.array([1, 2, 3, 4, 5.0]))[-1] - 100) < 1e-6
    print(f"RSI2 on a falling series ends at {r_[-1]:.2f}")
    # 3) causality: signals at day i unchanged when every later bar is removed
    s = "US100.cash"
    full = signals(S[s])
    cut = {k: (v[:800] if isinstance(v, np.ndarray) else v) for k, v in S[s].items()}
    part = signals(cut)
    for key in full:
        assert np.array_equal(full[key][:800], part[key]), key
    print(f"causality: all {len(full)} signal arrays of US100.cash are unchanged when the data after day 800 is removed")
    # 4) counts per family and group
    for fam in ("F1", "F2", "F3", "F4", "F5", "F6"):
        row = []
        for g, syms in GROUPS.items():
            tot = 0
            for s in syms:
                sg = signals(S[s])
                tot += sum(int((v != 0).sum()) for k, v in sg.items() if k[0] == fam)
            row.append(f"{g} {tot:,}")
        print(f"   {fam} signal-days (all variants): " + ", ".join(row))
    print("DRY RUN OK")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    P = R8.prep()
    S = build(P)
    alld = pd.DatetimeIndex(sorted(set().union(*[set(S[s]["d"]) for s in S])))
    alld = alld[alld <= LAST]
    pos = {d: i for i, d in enumerate(alld)}
    ND = len(alld)
    is_d = np.array([d < OOS_FROM for d in alld])
    rng = np.random.default_rng(SEED)
    # bootstrap weight matrices over the dates of each half
    W = {}
    for name, m in (("IS", is_d), ("OOS", ~is_d)):
        n = int(m.sum()); p = np.flatnonzero(m)
        Wm = np.zeros((BOOT, ND))
        idx = rng.integers(0, n, (BOOT, n))
        for b in range(BOOT):
            np.add.at(Wm[b], p[idx[b]], 1.0)
        W[name] = Wm
    sig = {s: signals(S[s]) for s in S}
    elig = {s: hold_masks(S[s], (1, 2, 3)) for s in S}
    # benchmarks: (group, side, H) -> per-date sum / count arrays
    bench = {}
    for g, syms in GROUPS.items():
        for side in (1, -1):
            for H in (1, 2, 3):
                tot, cnt = np.zeros(ND), np.zeros(ND)
                for s in syms:
                    idx, net = benchmark_trades(S[s], side, H, elig[s][H])
                    if len(idx) == 0:
                        continue
                    dd = S[s]["d"][idx]
                    keep = np.asarray(dd <= LAST)
                    di = np.array([pos[d] for d in dd[keep]], dtype=int)
                    np.add.at(tot, di, net[keep]); np.add.at(cnt, di, 1.0)
                bench[(g, side, H)] = (tot, cnt)
    print(f"setup done ({time.time() - t0:.0f}s)", flush=True)
    rows = []
    for (key, g, H) in cell_hypotheses():
        tot, cnt, gro = np.zeros(ND), np.zeros(ND), np.zeros(ND)
        sides = set()
        for s in GROUPS[g]:
            tr = trades_for(S[s], sig[s][key], H, elig[s][H])
            for i, net, gross, sd_ in tr:
                d = S[s]["d"][i]
                if d > LAST:
                    continue
                j = pos[d]
                tot[j] += net; cnt[j] += 1.0; gro[j] += gross
                sides.add(sd_)
        # a cell's benchmark: the same trade on every eligible day, on the side the cell trades (both sides averaged only for the mixed-side squeeze cells)
        if sides == {1}:
            bt, bc = bench[(g, 1, H)]
        elif sides == {-1}:
            bt, bc = bench[(g, -1, H)]
        else:
            bt = (bench[(g, 1, H)][0] + bench[(g, -1, H)][0]) / 2.0; bc = (bench[(g, 1, H)][1] + bench[(g, -1, H)][1]) / 2.0
        row = dict(family=key[0], variant=key[1], mode=key[2], group=g, H=H)
        for name, m in (("IS", is_d), ("OOS", ~is_d)):
            n = float(cnt[m].sum())
            mean = float(tot[m].sum() / max(n, 1)); gmean = float(gro[m].sum() / max(n, 1))
            bmean = float(bt[m].sum() / max(bc[m].sum(), 1))
            Wm = W[name]
            P_net = pb(tot, cnt, Wm) if n > 0 else float("nan")
            exc = (Wm @ tot / np.maximum(Wm @ cnt, 1e-9)) - (Wm @ bt / np.maximum(Wm @ bc, 1e-9))
            row[name] = dict(n=int(n), net=mean, gross=gmean, bench=bmean, excess=mean - bmean, P=P_net, P_excess=float((exc > 0).mean()) if n > 0 else float("nan"))
        rows.append(row)
    ps = np.array([max(1.0 - (r["OOS"]["P"] if np.isfinite(r["OOS"]["P"]) else 0.0), 1.0 / BOOT) for r in rows])
    order = np.argsort(ps)
    thr = 0.0
    for rank, i in enumerate(order, 1):
        if ps[i] <= 0.10 * rank / len(rows):
            thr = max(thr, ps[i])
    for r, p in zip(rows, ps):
        r["p_oos"] = float(p)
        r["bh"] = bool(thr > 0 and p <= thr)
        r["candidate"] = bool(r["IS"]["P"] >= 0.95 and r["OOS"]["P"] >= 1 - 0.01 / K_TOTAL and r["OOS"]["net"] > 0 and r["OOS"]["n"] >= 300 and r["OOS"]["P_excess"] >= 0.95 and r["bh"])
    cand = [r for r in rows if r["candidate"]]
    isg = [r for r in rows if np.isfinite(r["IS"]["P"]) and r["IS"]["P"] >= 0.95]
    print(f"{len(rows)} hypotheses; IS P >= 0.95: {len(isg)} (about {0.05 * len(rows):.0f} expected by chance); of those positive OOS net {sum(r['OOS']['net'] > 0 for r in isg)}, OOS excess P >= 0.95 {sum(r['OOS']['P_excess'] >= 0.95 for r in isg)}; CANDIDATES {len(cand)}")
    ok = [r for r in rows if r["OOS"]["n"] >= 300]
    for r in sorted(ok, key=lambda r: -r["OOS"]["net"])[:12]:
        print(f"   {r['family']} {r['variant']:>7} {r['mode']:>11} {r['group']} H{r['H']} | IS n {r['IS']['n']:>5} net {r['IS']['net']:+.1f} P {r['IS']['P']:.2f} | OOS n {r['OOS']['n']:>5} net {r['OOS']['net']:+.1f} gross {r['OOS']['gross']:+.1f} bench {r['OOS']['bench']:+.1f} excess {r['OOS']['excess']:+.1f} P {r['OOS']['P']:.3f} Pex {r['OOS']['P_excess']:.2f}")
    for fam in ("F1", "F2", "F3", "F4", "F5", "F6"):
        f = [r for r in ok if r["family"] == fam]
        if f:
            print(f"   {fam}: {len(f)} cells with OOS n >= 300; mean OOS net {np.mean([r['OOS']['net'] for r in f]):+.1f} bp, mean excess {np.mean([r['OOS']['excess'] for r in f]):+.1f} bp, positive-net cells {sum(r['OOS']['net'] > 0 for r in f)}")
    json.dump(dict(K_TOTAL=K_TOTAL, rows=rows, n_hypotheses=len(rows), is_significant=len(isg), candidates=len(cand)), open(os.path.join(HERE, "round303_results.json"), "w"), indent=1, default=float)
    print(f"Saved round303_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
