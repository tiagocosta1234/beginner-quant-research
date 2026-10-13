"""
Round 257 (2026-10-01): a from-scratch daily-direction scan on the whole liquid MT5 broker universe, in the one window
that pays no swap. the trader: "keep trying to find a new edge, start from scratch ideas".
PRE-REGISTRATION -- every choice below is fixed before any return of this scan is computed.

THE IDEA. Our two kinds of failure were costs on short-term trades (Rounds 248-256: US100 fades, forex and GER40
patterns) and MT5 broker's overnight swap on multi-day holds (Round 253: trend is real BEFORE swap, ~+0.3 Sharpe). A
position opened at 17:05 New York and closed at 16:55 New York the next day crosses no 17:00 rollover, so it pays
no swap; it also holds a whole day's move, so the spread (measured below) is a few hundredths of the move. That
window is exactly one MT5 D1 bar (server day 00:00-24:00 = 17:00-17:00 New York). This round asks, on every
liquid MT5 broker instrument, whether the direction of that day's move is predictable from what has already happened.

UNIVERSE (forex/universe.py, 52 symbols, fixed): 12 cash indices, 5 metals, 4 energy, 7 agricultural, 15 forex
pairs (the 7 USD pairs, 6 crosses, EURJPY, GBPJPY -- trimmed from 28 before any data was read, because the other crosses
download slowly and repeat the majors), DXY, 8 crypto. Equities and exotic currencies are excluded. MT5 D1 bars from each symbol's first bar to
2026-09-30; Monday-Friday server dates only (crypto weekend bars are dropped: no weekend holds); a symbol enters
a hypothesis only with >= 300 in-sample days.
TRADED RETURN r_t = ln(close_t / open_t) of the D1 bar (bid). Net of the real quote: a long pays the ask at
entry, a short buys back at the ask at exit: long net = r - s_in/price, short net = -r - s_out/price, where
s_in / s_out are the symbol's MEDIAN bid-ask spreads at 17:05 and 16:55 New York, measured on the first tick of
each minute over ~100 sampled weekdays 2024-10..2026-09 (forex/rollover_spread.py -> forex/specs/rollover_spreads.json).
Harsh = 3x those spreads. Bars with |r| > 10 trailing sd, and bars with open == close, are dropped.
UNIT: sd_t = trailing 60-day sd of r (>= 40 days, known before day t); a position is sized so a 1-sd day is K
dollars.

PREDICTORS (all use bars before day t only; each gives a position +-1, or 0 when it is exactly 0):
  X1 r(t-1) (yesterday's window); X2 close-to-close return(t-1); X3 sum of r over t-5..t-1; X4 sum of
  close-to-close over t-20..t-1; X5 over t-120..t-1; X6 over t-250..t-1; X7 close(t-1) minus its 20-day mean;
  X8 0.5 - IBS(t-1) with IBS = (close - low)/(high - low); X9 r(t-1) only when yesterday's range was > 1.5 x its
  20-day mean range; X10 constant +1 (drift). Position = sign(predictor) x s, s = the in-sample sign of the
  gross mean (so continuation and reversal are both covered by one hypothesis).
FAMILY: one hypothesis per (symbol, predictor), statistic = mean of position x r / sd_t (gross), two-sided t on the
in-sample days (< 2025-07-01); ONE Benjamini-Hochberg pass at q = 0.10 over ALL hypotheses. A BH survivor must also
have an in-sample NET mean > 0 (spread-adjusted) to be a rule.
CONFIRMATION (out of sample, >= 2025-07-01, untouched until here): a rule is CONFIRMED if its OOS net mean > 0 with
one-sided bootstrap P(mean > 0) >= 0.95 (20,000 resamples, seed 257).
PORTFOLIO AND MT5 REPLAY (only if rules are confirmed): the confirmed rules, each 1 unit = K dollars per sd; day
P&L = sum, day worst mark = sum of each position's worst (long: ln(low/open) - s; short: -ln((high + s)/open) - s,
capped at its net result); exact forex.backtest.replay / ChallengeState from every start day with >= 63 trading days
after it, entry 17:05 New York the evening before; K from (250, 500, 750, 1000, 1500, 2000, 3000) chosen on IS starts
by P(live <= 63), applied to OOS starts. Candidate = the repo's four checks: (1) ledger rule on daily net $ at that
K (IS P >= 0.95, OOS P >= 1 - 0.01/k); (2) OOS P(live <= 63) >= 0.50; (3) >= the random-direction control (each
rule's direction flipped by a fair coin per day, 200 draws, seed 257) median + 10pp; (4) OOS mean daily net $ > 0 under
harsh costs. No confirmed rule -> "no survivors".
LEDGER: one row for the scan (k = 442), one more per confirmed portfolio.

EXPECTATION: public daily-horizon predictors are nearly priced out; with ~600 hypotheses the best IS t will look
significant by chance, which is what the BH pass and the untouched OOS are for. Most likely: no survivors.

POWER NOTES (--dry-run, counts and costs only): 52 symbols with D1 bars and measured spreads; 48 have >= 300 IS days
(excluded: XCUUSD, NATGAS, HEATOIL, SUGAR, COTTON, DXY, SOLUSD -- under a year of MT5 broker history) -> 450 hypotheses (45
symbols... see the run for the exact count). IS days: FX ~6,500 (2000-), gold 5,359, silver 4,235, BTC 3,654, indices
1,150-1,900 (2017/2019-), oil 1,119-2,329, agriculture 438-574, crypto alts 952-2,341; OOS 310-328 days per symbol
(2025-07..2026-09). If the true gross edge were 0.05 sd/day (Sharpe 0.8), the IS t would be ~3.9 on 6,500 FX days but
only ~2.2 on 1,900 index days; BH over 450 tests at q = 0.10 needs |t| ~ 3.3-3.6 for a handful of discoveries, so only
effects of ~0.06 sd/day or more can be found on the short-history instruments. Measured spreads (median, base): US
indices 0.6-1.0 bp, GER40/EU50 1.6-2.3, UK100 6.5, JP225 4.4 in / 1.0 out, gold 0.9 / 1.3, silver 7.9, platinum 43,
palladium 64, oil 2.7-2.8, agriculture 10-36, USD forex 3-11 bp in / 1-2 out (the entry window is just after the
17:00 rollover, when spreads are still wide), BTC 0.1, ETH 2.3, other crypto 0.3-18. Round-trip spread over the median
absolute daily move: median 0.17 across symbols. Disclosed: today's spreads are applied to all history, so old forex
costs are understated (spreads were wider before ~2015); D1 history before each symbol's MT5 broker era comes from MT5 broker's
own feed as served.
"""
import os, sys, json, argparse, time
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import numpy as np
import pandas as pd
from scipy import stats
import idea_harness as H
from forex.universe import ALL, GROUP

OOS = pd.Timestamp("2025-07-01")
SD_WIN, SD_MIN, BAD_SD = 60, 40, 10.0
MIN_IS = 300
FDR_Q = 0.10
N_BOOT, SEED = 20_000, 257
PREDS = ["X1_prev_window", "X2_prev_c2c", "X3_5d_window", "X4_20d_c2c", "X5_120d_c2c", "X6_250d_c2c", "X7_ma20_dev", "X8_ibs", "X9_range_exp", "X10_drift"]
KS = (250, 500, 750, 1000, 1500, 2000, 3000)
HARSH_MULT = 3.0
N_CTRL = 200


def spreads():
    return json.load(open(os.path.join(ROOT, "mt5broker", "specs", "rollover_spreads.json")))


def load(sym, SP):
    df = pd.read_parquet(os.path.join(ROOT, "mt5broker", "data", f"{sym}_D1.parquet"))
    idx = pd.to_datetime(df["time"], unit="s").dt.normalize()
    d = df.set_index(idx)[["open", "high", "low", "close"]]
    d = d[~d.index.duplicated(keep="last")].sort_index()
    d = d[(d.index.weekday < 5) & (d["open"] > 0) & (d["close"] > 0) & (d["open"] != d["close"])]
    d["r"] = np.log(d["close"] / d["open"])
    d["c2c"] = np.log(d["close"] / d["close"].shift(1))
    d["sd"] = d["r"].shift(1).rolling(SD_WIN, min_periods=SD_MIN).std()
    d = d[(d["r"].abs() <= BAD_SD * d["sd"]) | d["sd"].isna()]
    s = SP.get(sym, {})
    d.attrs["s_in"], d.attrs["s_out"] = s.get("in_pct"), s.get("out_pct")
    rng = (d["high"] - d["low"]) / d["open"]
    ibs = (d["close"] - d["low"]) / (d["high"] - d["low"]).replace(0, np.nan)
    X = pd.DataFrame(index=d.index)
    X["X1_prev_window"] = d["r"].shift(1)
    X["X2_prev_c2c"] = d["c2c"].shift(1)
    X["X3_5d_window"] = d["r"].rolling(5).sum().shift(1)
    X["X4_20d_c2c"] = d["c2c"].rolling(20).sum().shift(1)
    X["X5_120d_c2c"] = d["c2c"].rolling(120).sum().shift(1)
    X["X6_250d_c2c"] = d["c2c"].rolling(250).sum().shift(1)
    X["X7_ma20_dev"] = ((d["close"] - d["close"].rolling(20).mean()) / d["close"]).shift(1)
    X["X8_ibs"] = (0.5 - ibs).shift(1)
    X["X9_range_exp"] = d["r"].shift(1).where((rng > 1.5 * rng.rolling(20).mean()).shift(1).fillna(False))
    X["X10_drift"] = 1.0
    return d, X


def net_series(d, pos, mult=1.0):
    """Per-day net return (log units) of a +-1/0 position series."""
    si, so = d.attrs["s_in"], d.attrs["s_out"]
    cost = np.where(pos > 0, si, np.where(pos < 0, so, 0.0)) * mult
    return pos * d["r"] - cost


def boot_p(v, n=N_BOOT, seed=SEED):
    v = np.asarray(v, float)
    if len(v) < 20:
        return float("nan")
    rng = np.random.default_rng(seed)
    out = np.empty(n)
    for c in range(0, n, 2000):
        m = min(2000, n - c)
        out[c:c + m] = rng.choice(v, (m, len(v))).mean(1)
    return float((out > 0).mean())


def build():
    SP = spreads()
    data, skipped = {}, []
    for s in ALL:
        try:
            d, X = load(s, SP)
        except Exception as e:
            skipped.append((s, f"no D1 file ({type(e).__name__})")); continue
        if d.attrs["s_in"] is None or d.attrs["s_out"] is None:
            skipped.append((s, "no measured spread")); continue
        data[s] = (d, X)
    return data, skipped


def dry_run():
    data, skipped = build()
    print(f"symbols with D1 + spreads: {len(data)} of {len(ALL)}; skipped {skipped}")
    n_h = 0
    for s, (d, X) in data.items():
        is_ = d[d.index < OOS]["sd"].notna().sum()
        o = int((d.index >= OOS).sum())
        ok = is_ >= MIN_IS
        n_h += len(PREDS) if ok else 0
        print(f"  {s:12s} {GROUP[s]:7s} D1 {d.index.min().date()}..{d.index.max().date()}  IS days {is_:5d}  OOS {o:4d}  "
              f"spread in/out {d.attrs['s_in'] * 1e4:6.2f}/{d.attrs['s_out'] * 1e4:6.2f} bp  median |r| {d['r'].abs().median() * 1e4:6.1f} bp"
              + ("" if ok else "  (< 300 IS days: excluded)"))
    print(f"hypotheses: {n_h}")
    cr = [(d["r"].abs().median(), d.attrs["s_in"] + d.attrs["s_out"]) for d, _ in data.values()]
    print(f"round-trip spread / median |daily move|: median {np.median([c / m for m, c in cr]):.3f}")


def run(commit):
    t0 = time.time()
    data, skipped = build()
    hyp = []
    for s, (d, X) in data.items():
        if d[d.index < OOS]["sd"].notna().sum() < MIN_IS:
            continue
        for p in PREDS:
            sg = np.sign(X[p]).reindex(d.index)
            v = pd.concat([sg, d["r"] / d["sd"]], axis=1, keys=["sg", "z"]).dropna()
            v = v[(v["sg"] != 0) & (v.index < OOS)]
            if len(v) < MIN_IS:
                continue
            m = v["sg"] * v["z"]
            t, pv = stats.ttest_1samp(m, 0.0)
            hyp.append(dict(sym=s, grp=GROUP[s], pred=p, n_is=len(v), mean_is=float(m.mean()), t=float(t), p=float(pv), dir=1 if m.mean() > 0 else -1))
    Hy = pd.DataFrame(hyp).sort_values("p").reset_index(drop=True)
    n = len(Hy)
    Hy["bh_crit"] = (np.arange(1, n + 1) / n) * FDR_Q
    ok = Hy["p"] <= Hy["bh_crit"]
    Hy["bh_pass"] = Hy.index <= (ok[ok].index.max() if ok.any() else -1)
    print(f"{n} hypotheses on {Hy['sym'].nunique()} symbols; BH q={FDR_Q}: {int(Hy['bh_pass'].sum())} pass")
    print(Hy.head(15)[["sym", "pred", "n_is", "mean_is", "t", "p", "bh_crit", "bh_pass"]].to_string(index=False))
    rules = []
    for r in Hy[Hy["bh_pass"]].itertuples():
        d, X = data[r.sym]
        pos = (np.sign(X[r.pred]).reindex(d.index) * r.dir).fillna(0.0)
        net = net_series(d, pos)
        ni, no = net[(d.index < OOS) & (pos != 0)], net[(d.index >= OOS) & (pos != 0)]
        p_oos = boot_p(no)
        print(f"  BH survivor {r.sym} {r.pred} dir {r.dir:+d}: IS net {ni.mean() * 1e4:+.2f} bp/day (n {len(ni)}), OOS net {no.mean() * 1e4:+.2f} bp (n {len(no)}), P {p_oos:.3f}")
        if ni.mean() > 0:
            rules.append(dict(sym=r.sym, pred=r.pred, dir=int(r.dir), is_net_bp=float(ni.mean() * 1e4), oos_net_bp=float(no.mean() * 1e4), p_oos=p_oos,
                              confirmed=bool(no.mean() > 0 and p_oos >= 0.95)))
    conf = [x for x in rules if x["confirmed"]]
    result = dict(n_hyp=n, n_bh=int(Hy["bh_pass"].sum()), top=Hy.head(30).to_dict("records"), rules=rules, confirmed=[f"{x['sym']} {x['pred']}" for x in conf],
                  skipped=skipped)
    k_total = H.ledger_count() + 1
    row = dict(n=n, k=k_total)
    print(f"\nrules with IS net > 0: {len(rules)}; CONFIRMED out of sample: {len(conf)}")
    if not conf:
        print("NO SURVIVORS. Round ends here (pre-registered).")
        result["verdict"] = "NOT a candidate (no confirmed rule)"
        print("\nLedger row (append after review):")
        print(f"| {k_total} | 2026-10-01 | Swap-free daily window (17:05->16:55 NY), {n} hypotheses ({Hy['sym'].nunique()} MT5 broker symbols x 10 predictors), BH q=0.10 on IS -- {int(Hy['bh_pass'].sum())} pass, {len(conf)} confirmed OOS | Round 257 (pre-registered, MT5 broker universe scan) | {commit} | 0 | n/a | n/a | n/a / n/a | no edge |")
    else:
        print("Confirmed rules go to the MT5 broker replay stage -- see round257_portfolio.py (written only if needed).")
        result["verdict"] = "CONFIRMED RULES (portfolio stage pending)"
    json.dump(result, open(os.path.join(HERE, "round257_results.json"), "w"), indent=1, default=str)
    print(f"Saved round257_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", default="COMMIT")
    a = ap.parse_args()
    dry_run() if a.dry_run else run(a.commit)
