"""
Round 314 (2026-10-02, PRE-REGISTERED): the trader: "we need much more frequent trades though" (the Reversal Signal Detector at stop 4 ATR / RR 3 on the 5-minute chart fires a few times a week per pair).
Frequency is not free: every extra trade pays the same spread + commission, and Rounds 311-313 found a gross edge of about +0.04R at 1 minute and ~0 at 5-15 minutes on FX. This round measures the trade-off with a fixed LADDER of
loosened signals, fixed before the run, so that "more trades" can be priced in net R per trade AND net R per day.

LADDER (cumulative; stop 4 ATR and target 3 x the stop for every level; the signal as in Round 312-313 unless stated):
  L0  as built: ATR spike 1.0, divergence lookback 3, MACD histogram rising / falling required, one position at a time per pair.
  L1  ATR spike 0.5.
  L2  ATR spike 0 (any bar; only the divergence and the MACD histogram direction remain).
  L3  L2 and the MACD-histogram-direction condition removed (RSI divergence alone).
  L4  L3 and lookback 2.
  L5  L4 and overlapping trades: every signal is traded independently, no one-at-a-time rule (the exposure is several 1% risks at once).
Timeframes 1 and 5 minutes. Pairs: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF pooled (MT5 M1 bid/ask 2021-10-04..2026-09-30, indicator on bid candles, long entries at the ask, exits on the bid book, shorts reversed,
stop wins a tie, hold <= 120 / 60 bars, MT5 $6/lot commission in quote-currency price units, the original's absolute MACD thresholds as in Round 312-313). 12 ledger rows (6 levels x 2 timeframes, pooled), k 2006 -> 2018.
Reported per level: trades, trades per pair per day, gross / cost / net R per trade, net R per trading day (all pairs), the mirrored bet's gross R (the signal's skill = gross minus the mirror's gross), TRAIN / VALID / TEST net R.
CANDIDATE (idea_harness.test_idea): positive before AND after costs, IS P(edge>0) >= 0.95, OOS P(edge>0) >= 1 - 0.01/k.

Step 0 (ledger k = 2006): the same signal at stop 4 ATR / RR 3 was run on five pairs in Round 313 (net -0.21R / -0.09R / -0.10R at 1 / 5 / 15 minutes, gross +0.04 / +0.01 / -0.05R); the looser levels are new.
Honest expectation (stated before the run): trades per day rise 3-30x down the ladder; the gross edge per trade does not grow (it likely falls as the filters that selected the stronger setups are removed), and the cost per trade is
unchanged, so net R per trade stays negative and net R PER DAY becomes more negative with frequency. A level counts as a "frequency win" only if its net R per trade is positive, which I do not expect.

DRY-RUN COUNTS (no P&L read; the ladder only ever adds signals, checked on random data): signals per pair per calendar day over 1,560 days, 6 pairs pooled.
  1-minute: L0 21,641 (2.31), L1 56,911 (6.08), L2 63,759 (6.81), L3 172,183 (18.40), L4 187,482 (20.03), L5 same signals as L4 but all traded.
  5-minute: L0 4,970 (0.53), L1 13,648 (1.46), L2 14,812 (1.58), L3 39,596 (4.23), L4 44,397 (4.74), L5 same as L4 but overlapping.
POWER: pooled trades are 4,000-190,000 per level, so the standard error of the mean net R at RR 3 (outcome sd about 1.7R) is 0.004-0.027R: any change in net R per trade larger than about 0.05R between levels is real; the question is its sign.
"""
import os, sys, json, time, subprocess
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idea_harness as H
import round271_one_to_one_generator as M
import round312_reversal_detector_eurusd_tweaks as R
import round313_reversal_detector_five_pairs_confirmation as R3

HERE = os.path.dirname(os.path.abspath(__file__))
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF"]
TFS = [1, 5]
STOPM, RR = 4.0, 3.0
CHUNK = 20000
LEVELS = {
    "L0": dict(spike=1.0, look=3, macd_dir=True, overlap=False),
    "L1": dict(spike=0.5, look=3, macd_dir=True, overlap=False),
    "L2": dict(spike=0.0, look=3, macd_dir=True, overlap=False),
    "L3": dict(spike=0.0, look=3, macd_dir=False, overlap=False),
    "L4": dict(spike=0.0, look=2, macd_dir=False, overlap=False),
    "L5": dict(spike=0.0, look=2, macd_dir=False, overlap=True),
}


def signals(D, spike, look, macd_dir):
    c, rsi, hist = pd.Series(D["bc"]), pd.Series(D["rsi"]), pd.Series(D["hist"])
    lc, lcp = c.rolling(look).min(), c.rolling(look).min().shift(1)
    hc, hcp = c.rolling(look).max(), c.rolling(look).max().shift(1)
    lr, lrp = rsi.rolling(look).min(), rsi.rolling(look).min().shift(1)
    hr, hrp = rsi.rolling(look).max(), rsi.rolling(look).max().shift(1)
    dh = hist.diff()
    bull = (lc < lcp) & (lr > lrp) & (dh > -0.01)
    bear = (hc > hcp) & (hr < hrp) & (dh < 0.01)
    sp = pd.Series(D["rng"] > D["atr"] * spike) if spike > 0 else pd.Series(D["rng"] > 0)
    if macd_dir:
        bull = bull & (hist > hist.shift(1))
        bear = bear & (hist < hist.shift(1))
    s = np.where((bull & sp).values, 1, np.where((bear & sp).values, -1, 0))
    s[:300] = 0
    s[~(D["valid_len"] >= 1)] = 0
    s[np.isnan(D["atr"]) | (D["atr"] <= 0)] = 0
    return s


def resolve_chunked(D, sym, idx, side):
    ex_l, r_l, c_l = [], [], []
    for a in range(0, len(idx), CHUNK):
        ii = idx[a:a + CHUNK]
        W = R.windows(D, ii)
        comm = R3.comm_price(sym, D["bc"][ii])
        ex, r, cst = R3.resolve(D, ii, side[a:a + CHUNK], W, STOPM, RR, comm)
        ex_l.append(ex); r_l.append(r); c_l.append(cst)
    return np.concatenate(ex_l), np.concatenate(r_l), np.concatenate(c_l)


def run_level(D, sym, lv):
    n = len(D["t"])
    s = signals(D, lv["spike"], lv["look"], lv["macd_dir"])
    idx = np.flatnonzero(s != 0); idx = idx[idx + 1 + R.HOLD[D["tf"]] < n]
    sgn = s[idx]
    ex, r, cst = resolve_chunked(D, sym, idx, sgn)
    _, rm, cm = resolve_chunked(D, sym, idx, -sgn)          # the mirrored bet, same entries
    keep = np.ones(len(idx), bool) if lv["overlap"] else R.one_at_a_time(idx, ex)
    tr = R.make_trades(D, idx, ex, r, cst, sgn, keep)
    tr["sym"] = sym
    mir = (rm[keep] + cm[keep]).mean() if keep.any() else float("nan")
    return tr, int(len(idx)), float(mir)


def selftest():
    R.selftest()
    rng = np.random.default_rng(3)
    n = 1500
    c = 1.1 + np.cumsum(rng.normal(0, 0.0003, n))
    D = dict(bc=c, rsi=np.clip(50 + np.cumsum(rng.normal(0, 3, n)), 1, 99), hist=np.cumsum(rng.normal(0, 0.0001, n)) * 0.2, rng=np.abs(rng.normal(0, 0.0005, n)) + 1e-5, atr=np.full(n, 0.0004),
             valid_len=np.full(n, 120))
    a = signals(D, 0.0, 3, True); b = signals(D, 0.0, 3, False)
    assert (b != 0).sum() >= (a != 0).sum() and ((a != 0) <= (b != 0)).all(), "dropping the MACD direction must only add signals"
    assert (signals(D, 0.0, 2, False) != 0).sum() >= (b != 0).sum()
    print("selftest ok (round314)")


def dry_run():
    selftest()
    dfs = {s: R3.load_pair(s) if s != "EURUSD" else R.load_raw() for s in PAIRS}
    ndays = len(set(pd.DatetimeIndex(dfs["EURUSD"].index).normalize()))
    print(f"trading days in the sample: {ndays}")
    for tf in TFS:
        tot = {k: 0 for k in LEVELS}
        for sym in PAIRS:
            D = R.build(dfs[sym], tf); D["scale"] = 1.0
            for k, lv in LEVELS.items():
                s = signals(D, lv["spike"], lv["look"], lv["macd_dir"])
                tot[k] += int((s != 0).sum())
        print(f"{tf}-minute signals (6 pairs): " + ", ".join(f"{k} {v} ({v / ndays / len(PAIRS):.2f}/pair/day)" for k, v in tot.items()))
    print("\n--dry-run: counts only, no P&L is read.")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    selftest()
    t0 = time.time()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dfs = {s: (R3.load_pair(s) if s != "EURUSD" else R.load_raw()) for s in PAIRS}
    all_days = sorted(set(pd.DatetimeIndex(dfs["EURUSD"].index).normalize()))
    ndays = len(all_days)
    kk = H.ledger_count()
    rows_out, results = [], {}
    for tf in TFS:
        DS = {}
        for sym in PAIRS:
            D = R.build(dfs[sym], tf); D["scale"] = 1.0
            DS[sym] = D
        for k, lv in LEVELS.items():
            trs, mirs, nsig = [], [], 0
            for sym in PAIRS:
                tr, ns, mir = run_level(DS[sym], sym, lv)
                trs.append(tr); mirs.append(mir * len(tr)); nsig += ns
            tr = pd.concat(trs).sort_values("entry_ts")
            kk += 1
            name = f"Reversal Signal Detector frequency ladder {k} (spike {lv['spike']}, lookback {lv['look']}, MACD direction {'on' if lv['macd_dir'] else 'off'}, {'overlapping' if lv['overlap'] else 'one-at-a-time'}), stop 4 ATR RR 3, {tf}-min, 6 FX pairs pooled (MT5 broker bid/ask + $6/lot)"
            row = H.test_idea(name, R.as_trades(tr), all_days, "MNQ", kk)
            rows_out.append(row)
            net, gross, cost = tr["r_net"].mean(), tr["r_gross"].mean(), tr["cost_R"].mean()
            mir_gross = sum(mirs) / len(tr)
            per_day = len(tr) / ndays
            print(f"    {tf}m {k}: n {len(tr):6d} ({per_day / len(PAIRS):.2f}/pair/day, {per_day:.1f}/day all pairs) win {(tr['r_net'] > 0).mean():.1%} net {net:+.3f}R gross {gross:+.3f}R cost {cost:.3f}R mirror gross {mir_gross:+.3f}R skill {gross - mir_gross:+.3f}R | net R/day {per_day * net:+.2f} | TRAIN {tr[tr.per == 0]['r_net'].mean():+.3f} VALID {tr[tr.per == 1]['r_net'].mean():+.3f} TEST {tr[tr.per == 2]['r_net'].mean():+.3f}", flush=True)
            results[f"{tf}m|{k}"] = dict(cfg=lv, n=int(len(tr)), signals=nsig, per_pair_day=float(per_day / len(PAIRS)), win=float((tr["r_net"] > 0).mean()), net_R=float(net), gross_R=float(gross), cost_R=float(cost),
                                         mirror_gross_R=float(mir_gross), skill_R=float(gross - mir_gross), net_R_per_day=float(per_day * net),
                                         by_period={nm: dict(n=int((tr.per == p).sum()), net_R=float(tr[tr.per == p]["r_net"].mean())) for nm, p in (("TRAIN", 0), ("VALID", 1), ("TEST", 2))},
                                         row={a: (float(v) if isinstance(v, (np.floating, float)) else v) for a, v in row.items() if a != "name"})
    lr = H.ledger_rows([{**r} for r in rows_out], "Round 314 (pre-registered, frequency ladder for the Reversal Signal Detector)", commit, date="2026-10-02")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lr) + "\n")
    with open(os.path.join(HERE, "round314_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote round314_results.json and {len(lr)} ledger rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
