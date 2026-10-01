"""
Round 277 (2026-10-01, PRE-REGISTERED): the support/resistance approach of the video "Automated Support and Resistance Detection in
PYTHON" (CodeTrading, aJ8Og-iLaas), backtested with real MT5 broker bid/ask costs. the trader: "backtest this support and resistance approach
learned from the video". The video defines LEVELS only (no entry rule, no results); this round formalizes the levels exactly as shown
and adds the two textbook uses -- BOUNCE and BREAKOUT -- with fixed brackets, no tuning.

LEVELS (video [02:38-03:20], [04:58-07:20]): on DAILY bars (trading day = 17:00 NY to 17:00 NY, built from the bid M1 bars). Candle l is a
SUPPORT pivot if the lows of the n1 = 3 candles before it fall strictly into it (low[l-3] > low[l-2] > low[l-1] > low[l]) and the n2 = 2
candles after it rise strictly (low[l] < low[l+1] < low[l+2]); the level is low[l]. RESISTANCE is the mirror with highs. Levels are kept
for a 200-day lookback (the video's 200 candles) and levels closer than 0.3 x the daily ATR14 are merged (the video merges lines closer
than a fixed 0.005 on EURUSD). CAUSALITY: the video's detector uses the n2 candles AFTER the pivot, so a pivot at day l is usable only
from day l + n2 + 1; at a decision on day d only pivots with l + n2 <= d - 1 are known (no look-ahead).
SIGNALS, evaluated at every closed M15 bar 03:00-15:00 NY on weekdays (tolerance tau = 0.10 x daily ATR14 of the previous day):
  BOUNCE long  : a support level L with bar low <= L + tau, bar low >= L - 0.5 x ATRd, close > L and close > open (a rejection candle);
  BOUNCE short : mirror at a resistance level (bar high >= L - tau, <= L + 0.5 x ATRd, close < L, close < open);
  BREAK  long  : previous close <= a resistance level L and this close >= L + 0.1 x ATRd; BREAK short : mirror through a support level.
If a bar qualifies for both directions it is skipped. Entry at the next M1 bar (real ask for longs, bid for shorts), one position at a time per
instrument, stop = s x ATR14(M15) with s in (1, 2), target = rr x stop with rr in (1, 2) (so 1:1 and 1:2), forced flat after 32 M15 bars or
16:50 NY. COSTS = the free-trial measurements: fills at the quote, NO added slippage (a stop that gaps still fills at the bar's open),
$6/lot round-trip commission on gold and FX (indices 0), as in Round 272. Net R = P&L / stop distance.
UNIVERSE: US100, US500, US30, GER40, FRA40, UK100, XAUUSD, EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF.
CELLS: 13 instruments x 2 families x 2 s x 2 rr = 104; k = 670 + 104 = 774. IS = 2022-01-01..2025-06-30 (the first year warms the levels),
OOS = 2025-07-01..2026-09-30. Per cell: trades, win rate, mean net R, break-even win rate 1/(1+rr) + cost, bootstrap P(mean > 0) (4,000 draws).
CANDIDATE (the repo's rule, fixed now): IS P >= 0.95 AND OOS P >= 1 - 0.01/774 AND OOS mean net R > 0 AND OOS trades >= 150; also Benjamini-Hochberg
q = 0.10 over the 104 OOS one-sided p-values (cells with OOS n >= 150). No parameter (n1, n2, lookback, merge, tolerance, brackets) is tuned;
all 104 cells are reported. Pooled results per (family, s, rr) are reported too.
PRIOR: the repo's S/R bounce tests (MGC, Broker) were a regime bet (2025-26 gold rally) and lost on MT5 broker gold (Round 248, -0.090 R); Rounds 256,
261, 271, 274 found no edge in level-based rules. The honest expectation is no survivor.
POWER_NOTES: 1,000 OOS trades give a mean-R standard error of ~0.04 at 1:1 and ~0.06 at 1:2.
"""
import os, sys, json, time, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import round271_one_to_one_generator as M

SYMS = M.SYMS
COMM = {"XAUUSD": 0.06, "EURUSD": 0.00006, "GBPUSD": 0.00006, "AUDUSD": 0.00006, "USDJPY": 0.009, "USDCAD": 0.0000822, "USDCHF": 0.000054}
N1, N2, LOOKBACK, MERGE, TOL, BRK = 3, 2, 200, 0.3, 0.10, 0.10
FAMS, SS, RRS = ("BOUNCE", "BREAK"), (1.0, 2.0), (1.0, 2.0)
IS_FROM, OOS_FROM, END = pd.Timestamp("2022-01-01"), pd.Timestamp("2025-07-01"), pd.Timestamp("2026-10-02")
K_TOTAL = 670 + len(SYMS) * len(FAMS) * len(SS) * len(RRS)
H_BARS, FLAT_H, FLAT_M = M.H_BARS, M.FLAT_H, M.FLAT_M


def sim_rr(side, i0, iend, S, rr, a):
    o, h, l, c, ao, ah, al, ac = a
    if side == 1:
        fill = ao[i0]
        stop, tgt = fill - S, fill + rr * S
        hs, ht = np.flatnonzero(l[i0:iend] <= stop), np.flatnonzero(h[i0:iend] >= tgt)
    else:
        fill = o[i0]
        stop, tgt = fill + S, fill - rr * S
        hs, ht = np.flatnonzero(ah[i0:iend] >= stop), np.flatnonzero(al[i0:iend] <= tgt)
    js, jt = (hs[0] if len(hs) else 10 ** 9), (ht[0] if len(ht) else 10 ** 9)
    if js == 10 ** 9 and jt == 10 ** 9:
        j, ex = iend - 1 - i0, (c[iend - 1] if side == 1 else ac[iend - 1])
    elif js <= jt:
        j = js
        ex = ((min(stop, o[i0 + js]) if js > 0 else stop) if side == 1 else (max(stop, ao[i0 + js]) if js > 0 else stop))
    else:
        j, ex = jt, tgt
    return ((ex - fill) if side == 1 else (fill - ex)) / S, i0 + j


def pivots(low, high):
    n = len(low)
    pl, ph = np.zeros(n, bool), np.zeros(n, bool)
    for l in range(N1, n - N2):
        if all(low[l - N1 + j] > low[l - N1 + j + 1] for j in range(N1)) and all(low[l + j] < low[l + j + 1] for j in range(N2)):
            pl[l] = True
        if all(high[l - N1 + j] < high[l - N1 + j + 1] for j in range(N1)) and all(high[l + j] > high[l + j + 1] for j in range(N2)):
            ph[l] = True
    return pl, ph


def merge(levels, thr):
    if len(levels) == 0:
        return np.array([])
    lv = np.sort(np.asarray(levels, float))
    out, cur = [], [lv[0]]
    for x in lv[1:]:
        if x - cur[-1] < thr:
            cur.append(x)
        else:
            out.append(np.mean(cur)); cur = [x]
    out.append(np.mean(cur))
    return np.array(out)


def run_symbol(sym):
    df = M.load(sym)
    b = M.m15(df)
    dk = (b.index - pd.Timedelta(hours=17)).normalize()
    g = pd.DataFrame({"o": b["o"].values, "h": b["h"].values, "l": b["l"].values, "c": b["c"].values, "dk": dk}).groupby("dk")
    D = g.agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), n=("o", "count"))
    D = D[D["n"] >= 20]
    tr = pd.concat([D["h"] - D["l"], (D["h"] - D["c"].shift()).abs(), (D["l"] - D["c"].shift()).abs()], axis=1).max(axis=1)
    atrd = tr.rolling(14).mean().to_numpy()
    low, high = D["l"].to_numpy(), D["h"].to_numpy()
    pl, ph = pivots(low, high)
    dpos = {k: i for i, k in enumerate(D.index)}
    # M15 arrays
    c15, o15, h15, l15 = b["c"].to_numpy(), b["o"].to_numpy(), b["h"].to_numpy(), b["l"].to_numpy()
    tr15 = pd.concat([b["h"] - b["l"], (b["h"] - b["c"].shift()).abs(), (b["l"] - b["c"].shift()).abs()], axis=1).max(axis=1)
    atr15 = tr15.rolling(14).mean().to_numpy()
    tc = b.index + pd.Timedelta(minutes=15)
    ok = (tc.hour >= 3) & (tc.hour < 15) & (tc.dayofweek < 5) & (atr15 > 0)
    # M1 arrays
    t_ns = df.index.values.astype("datetime64[ns]").astype(np.int64)
    arr = tuple(df[k].to_numpy(float) for k in ("open", "high", "low", "close", "ask_open", "ask_high", "ask_low", "ask_close"))
    tcn = tc.values.astype("datetime64[ns]").astype(np.int64)
    cache = {}
    signals = {f: [] for f in FAMS}
    for r in np.flatnonzero(ok):
        d = dpos.get(dk[r])
        if d is None or d < LOOKBACK // 4 or np.isnan(atrd[d - 1]):
            continue
        if d not in cache:
            lo, hi = max(0, d - LOOKBACK), d - N2                # pivots l with l + n2 <= d - 1
            thr = MERGE * atrd[d - 1]
            cache[d] = (merge(low[lo:hi][pl[lo:hi]], thr), merge(high[lo:hi][ph[lo:hi]], thr), atrd[d - 1])
        sup, res, A_ = cache[d]
        tau, brk = TOL * A_, BRK * A_
        o_, h_, l_, c_ = o15[r], h15[r], l15[r], c15[r]
        pc = c15[r - 1] if r > 0 else c_
        longs, shorts = {}, {}
        # bounce
        longs["BOUNCE"] = bool(len(sup) and np.any((l_ <= sup + tau) & (l_ >= sup - 0.5 * A_) & (c_ > sup)) and c_ > o_)
        shorts["BOUNCE"] = bool(len(res) and np.any((h_ >= res - tau) & (h_ <= res + 0.5 * A_) & (c_ < res)) and c_ < o_)
        # breakout
        longs["BREAK"] = bool(len(res) and np.any((pc <= res) & (c_ >= res + brk)))
        shorts["BREAK"] = bool(len(sup) and np.any((pc >= sup) & (c_ <= sup - brk)))
        for f in FAMS:
            if longs[f] != shorts[f]:
                signals[f].append((r, 1 if longs[f] else -1))
    res = {}
    for f in FAMS:
        for s in SS:
            for rr in RRS:
                last_exit, rec = -1, []
                for (r, side) in signals[f]:
                    if tcn[r] < last_exit:
                        continue
                    i0 = int(np.searchsorted(t_ns, tcn[r]))
                    if i0 >= len(t_ns) - 5 or t_ns[i0] - tcn[r] > 2 * 60 * 10 ** 9:
                        continue
                    day = tc[r].normalize()
                    flat = (day + pd.Timedelta(hours=FLAT_H, minutes=FLAT_M)).to_datetime64().astype("datetime64[ns]").astype(np.int64)
                    iend = min(i0 + H_BARS * 15, int(np.searchsorted(t_ns, flat)))
                    if iend - i0 < 5:
                        continue
                    S = s * float(atr15[r])
                    rn, ie = sim_rr(side, i0, iend, S, rr, arr)
                    rn -= COMM.get(sym, 0.0) / S
                    last_exit = int(t_ns[min(ie, len(t_ns) - 1)])
                    rec.append((tcn[r], rn))
                res[(f, s, rr)] = np.array(rec, float) if rec else np.zeros((0, 2))
    return res, {f: len(v) for f, v in signals.items()}, int(pl.sum()), int(ph.sum()), len(D)


def stats(a, lo, hi, rr):
    if len(a) == 0:
        return dict(n=0)
    t = pd.to_datetime(a[:, 0].astype("int64"))
    x = a[(t >= lo) & (t < hi), 1]
    if len(x) == 0:
        return dict(n=0)
    return dict(n=int(len(x)), win=float((x > 0).mean()), meanR=float(x.mean()), P=M.boot_p(x), be=float(1 / (1 + rr)))


def main():
    t0 = time.time()
    res = {}
    for sym in SYMS:
        r, sig, nsup, nres, nd = run_symbol(sym)
        res[sym] = r
        print(f"{sym}: {nd} daily bars, {nsup} support / {nres} resistance pivots, signals {sig} ({time.time() - t0:.0f}s)", flush=True)
    rows = []
    for sym in SYMS:
        for (f, s, rr), a in res[sym].items():
            rows.append(dict(sym=sym, fam=f, s=s, rr=rr, IS=stats(a, IS_FROM, OOS_FROM, rr), OOS=stats(a, OOS_FROM, END, rr)))
    pooled = []
    for f in FAMS:
        for s in SS:
            for rr in RRS:
                a = np.vstack([res[sym][(f, s, rr)] for sym in SYMS if len(res[sym][(f, s, rr)])])
                pooled.append(dict(fam=f, s=s, rr=rr, IS=stats(a, IS_FROM, OOS_FROM, rr), OOS=stats(a, OOS_FROM, END, rr)))
    thr = 1 - 0.01 / K_TOTAL
    print(f"\n=== Round 277: 104 cells, k = {K_TOTAL}; candidate bar IS P >= 0.95, OOS P >= {thr:.5f}, OOS mean R > 0, OOS n >= 150 ===")
    print(f"{'symbol':>11} {'fam':>6} {'s':>3} {'rr':>3} | {'IS n':>6} {'win%':>6} {'meanR':>7} {'P':>5} | {'OOS n':>6} {'win%':>6} {'meanR':>7} {'P':>5} {'b/e win':>7}")
    cands = []
    for r in sorted(rows, key=lambda r: -(r["IS"].get("meanR", -9))):
        i_, o_ = r["IS"], r["OOS"]
        line = f"{r['sym']:>11} {r['fam']:>6} {r['s']:>3} {r['rr']:>3} | "
        line += (f"{i_['n']:>6} {i_['win']:>6.1%} {i_['meanR']:>+7.3f} {i_['P']:>5.2f}" if i_["n"] else f"{'-':>6}") + " | "
        line += (f"{o_['n']:>6} {o_['win']:>6.1%} {o_['meanR']:>+7.3f} {o_['P']:>5.2f} {o_['be']:>7.0%}" if o_["n"] else f"{'-':>6}")
        print(line)
        if i_["n"] and o_["n"] >= 150 and i_["P"] >= 0.95 and o_["P"] >= thr and o_["meanR"] > 0:
            cands.append(r)
    ps = sorted([(max(1 - r["OOS"]["P"], 1 / 4000), r) for r in rows if r["OOS"]["n"] >= 150], key=lambda x: x[0])
    bh = [r for i, (p, r) in enumerate(ps, 1) if p <= 0.10 * i / max(len(ps), 1)]
    print(f"\nCANDIDATES under the pre-registered rule: {len(cands)}; BH q = 0.10 over {len(ps)} cells with OOS n >= 150: {len(bh)} pass")
    print("\n=== Pooled across the 13 instruments ===")
    for p in pooled:
        i_, o_ = p["IS"], p["OOS"]
        print(f"{p['fam']:>6} s={p['s']} rr={p['rr']}: IS n {i_.get('n', 0)} win {i_.get('win', float('nan')):.1%} meanR {i_.get('meanR', float('nan')):+.3f} P {i_.get('P', float('nan')):.2f} | "
              f"OOS n {o_.get('n', 0)} win {o_.get('win', float('nan')):.1%} meanR {o_.get('meanR', float('nan')):+.3f} P {o_.get('P', float('nan')):.2f} (break-even win {o_.get('be', float('nan')):.0%})")
    json.dump(dict(k=K_TOTAL, rows=rows, pooled=pooled, n_candidates=len(cands), bh=len(bh)), open(os.path.join(HERE, "round277_results.json"), "w"), indent=1, default=float)
    print(f"\nSaved round277_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
