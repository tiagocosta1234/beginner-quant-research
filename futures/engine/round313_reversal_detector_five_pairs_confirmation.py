"""
Round 313 (2026-10-02, PRE-REGISTERED): independent confirmation of Round 312's only lead, on pairs the search never touched. Round 312 (the trader's Reversal Signal Detector as written, MT5 EURUSD, original direction)
found a small positive GROSS edge (+0.02 to +0.12R) at 1, 5 and 15 minutes that costs eat, and that "more pips" (a 4 ATR stop) cuts costs to about the size of the edge at 5-15 minutes (5-minute stop 4 RR 3: net -0.010R; 15-minute:
+0.037R on about 250 trades, unstable across periods). A lead found on one instrument after looking at its results is not evidence; the cheapest honest check is a fixed, untuned configuration on five other MT5 broker pairs.

FIXED CONFIGURATION (chosen from Round 312's EURUSD full-period table BEFORE any other pair is run, so it is NOT out-of-sample for EURUSD, which is therefore excluded here): the signal as written (spike 1.0, lookback 3,
all sessions, original direction), stop 4 ATR, target 3 x the stop (RR 3), on 1, 5 and 15 minute bars. Everything else exactly as Round 312: MT5 M1 bid/ask 2021-10-04..2026-09-30 aggregated to the timeframe, the indicator on bid candles,
long entries at the ask close of the signal bar, exits on the bid book (shorts reversed), stop wins a tie, hold <= 120 / 60 / 40 bars for 1 / 5 / 15 minutes, no position through a gap, one position at a time per pair, the original's
MACD-change thresholds kept ABSOLUTE (+-0.01 in price units: meaningful on USDJPY, a no-op on the others).
PAIRS: GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF. COMMISSION: MT5 broker's measured $6 a lot round trip, converted to quote-currency price units: 6e-5 x (the pair's price for USD-base pairs USDJPY / USDCAD / USDCHF, 1 for USD-quote pairs).
Splits as Round 312 (TRAIN 2021-10..2023-12, VALID 2024-01..2025-06, TEST 2025-07..2026-09); for the ledger test_idea's IS is everything before 2025-07-01 and OOS the rest.

Step 0 (ledger k = 2003): no other pair has been tested with this signal. Honest expectation (stated before the run): the gross edge of +0.02 to +0.12R is of the size that disappears when pooled across instruments; I expect the pooled
net R at a 4 ATR stop to be about -0.05R at 5 minutes and between -0.1R and 0 at 15 minutes, and no candidate.

ROWS: 3 ledger rows (1 / 5 / 15 minutes, pooled over the five pairs, one fixed configuration each; k -> 2006). Diagnostics (not ledger): per pair and per period gross, cost and net R; the share of pairs with a positive gross edge.
CANDIDATE (idea_harness.test_idea): positive before AND after costs, IS P(edge>0) >= 0.95, OOS P(edge>0) >= 1 - 0.01/k.

DRY-RUN COUNTS (no P&L read; the signal logic and resolver are the self-tested Round 312 code, the commission conversion is unit-tested): signals as written per pair, 1 / 5 / 15 minutes: GBPUSD 3,689 / 834 / 282;
USDJPY 3,892 / 877 / 265; AUDUSD 3,540 / 835 / 287; USDCAD 3,678 / 873 / 264; USDCHF 3,463 / 725 / 245; pooled about 18,260 / 4,144 / 1,343. A 1 ATR move is 1.0-1.5 (1-minute), 2.4-3.7 (5-minute), 4.5-6.8 (15-minute) times the
spread + commission, so a 4 ATR stop costs about 0.17 / 0.07 / 0.04 R a trade on these pairs.
POWER: the standard error of the pooled mean net R at RR 3 (outcome standard deviation about 1.7R) is about 0.013R (1-minute), 0.026R (5-minute), 0.047R (15-minute); TEST alone about 0.03 / 0.06 / 0.11R. An edge smaller than about
+0.05R (5-minute) / +0.09R (15-minute) net cannot be told from zero on the full period; stated before the run.
"""
import os, sys, json, time, subprocess
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idea_harness as H
import round271_one_to_one_generator as M
import round312_reversal_detector_eurusd_tweaks as R

HERE = os.path.dirname(os.path.abspath(__file__))
PAIRS = ["GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF"]
TFS = [1, 5, 15]
STOPM, RR = 4.0, 3.0
SPIKE, LOOK = 1.0, 3
RISK = 300.0


def load_pair(sym):
    df = M.load(sym)
    return df[(df.index >= "2021-10-04") & (df.index < "2026-10-01")]


def comm_price(sym, price):
    return 6e-5 * (price if sym.startswith("USD") else 1.0)


def resolve(D, idx, side, W, stopm, rr, comm):
    HD = R.HOLD[D["tf"]]
    N = len(idx)
    dist = stopm * D["atr"][idx]
    vl = D["valid_len"][idx]
    beyond = np.arange(HD)[None, :] >= vl[:, None]
    entry = np.where(side > 0, D["ac"][idx], D["bc"][idx])
    stop = entry - side * dist
    tgt = entry + side * rr * dist
    lo_b = np.where(beyond, np.inf, W["bl"]); hi_b = np.where(beyond, -np.inf, W["bh"])
    lo_a = np.where(beyond, np.inf, W["al"]); hi_a = np.where(beyond, -np.inf, W["ah"])
    lm = (side > 0)[:, None]
    hit_stop = np.where(lm, lo_b <= stop[:, None], hi_a >= stop[:, None])
    hit_tgt = np.where(lm, hi_b >= tgt[:, None], lo_a <= tgt[:, None])
    fs = np.where(hit_stop.any(1), hit_stop.argmax(1), HD)
    ft = np.where(hit_tgt.any(1), hit_tgt.argmax(1), HD)
    stopped = (fs < HD) & (fs <= ft)
    targeted = (ft < HD) & (ft < fs)
    off = np.clip(np.where(stopped, fs, np.where(targeted, ft, vl - 1)), 0, HD - 1)
    ex_abs = idx + 1 + off
    exit_close = np.where(side > 0, W["bc"][np.arange(N), off], W["ac"][np.arange(N), off])
    r_fill = np.where(stopped, -1.0, np.where(targeted, rr, side * (exit_close - entry) / dist))
    cR = comm / dist
    cost_R = ((D["ac"][idx] - D["bc"][idx]) + (D["ac"][ex_abs] - D["bc"][ex_abs])) / 2.0 / dist + cR
    return ex_abs, r_fill - cR, cost_R


def run_pair(sym, tf, df):
    D = R.build(df, tf)
    D["scale"] = 1.0
    n = len(D["t"])
    s = R.base_signals(D, SPIKE, LOOK, "ALL")
    idx = np.flatnonzero(s != 0); idx = idx[idx + 1 + R.HOLD[tf] < n]
    sgn = s[idx]
    W = R.windows(D, idx)
    comm = comm_price(sym, D["bc"][idx])
    ex, r, cst = resolve(D, idx, sgn, W, STOPM, RR, comm)
    keep = R.one_at_a_time(idx, ex)
    tr = R.make_trades(D, idx, ex, r, cst, sgn, keep)
    tr["sym"] = sym
    return tr, R.agg(r[keep], cst[keep], R.period_of(D["t"][idx[keep]])), int((s != 0).sum())


def selftest():
    R.selftest()
    # commission conversion
    assert abs(comm_price("EURUSD", 1.1) - 6e-5) < 1e-12 and abs(comm_price("USDJPY", 150.0) - 0.009) < 1e-9
    print("selftest ok (round313)")


def dry_run():
    selftest()
    for sym in PAIRS:
        df = load_pair(sym)
        print(f"\n{sym}: {len(df)} M1 rows, median spread {np.median(df['ask_close'] - df['close']):.5f}")
        for tf in TFS:
            D = R.build(df, tf); D["scale"] = 1.0
            n = len(D["t"])
            s = R.base_signals(D, SPIKE, LOOK, "ALL")
            print(f"  {tf}m: {n} bars, median ATR14 {np.nanmedian(D['atr']):.5f} = {np.nanmedian(D['atr']) / (np.median(D['spr']) + comm_price(sym, np.median(D['bc']))):.1f} x (spread + commission); signals {int((s != 0).sum())}")
    print("\n--dry-run: counts only, no P&L is read.")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    selftest()
    t0 = time.time()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dfs = {s: load_pair(s) for s in PAIRS}
    all_days = sorted(set(pd.DatetimeIndex(dfs["GBPUSD"].index).normalize()))
    kk = H.ledger_count()
    rows_out, results = [], {}
    for tf in TFS:
        trs, per_pair = [], {}
        for sym in PAIRS:
            tr, a, nsig = run_pair(sym, tf, dfs[sym])
            trs.append(tr)
            per_pair[sym] = dict(signals=nsig, agg=a)
        tr = pd.concat(trs).sort_values("entry_ts")
        kk += 1
        name = f"Reversal Signal Detector AS WRITTEN, fixed stop 4 ATR RR 3, {tf}-min, pooled GBPUSD+USDJPY+AUDUSD+USDCAD+USDCHF (MT5 broker bid/ask + $6/lot), 2021-10..2026-09"
        row = H.test_idea(name, R.as_trades(tr), all_days, "MNQ", kk)
        rows_out.append(row)
        al = tr["r_net"]
        print(f"    {tf}m pooled: n {len(tr)} win {(al > 0).mean():.1%} net {al.mean():+.3f}R gross {tr['r_gross'].mean():+.3f}R cost {tr['cost_R'].mean():.3f}R | TRAIN {tr[tr.per == 0]['r_net'].mean():+.3f} VALID {tr[tr.per == 1]['r_net'].mean():+.3f} TEST {tr[tr.per == 2]['r_net'].mean():+.3f}", flush=True)
        for sym in PAIRS:
            a = per_pair[sym]["agg"]["ALL"]
            print(f"       {sym}: n {a['n']:4d} gross {a['gross_R']:+.3f} cost {a['cost_R']:.3f} net {a['net_R']:+.3f} | TRAIN {per_pair[sym]['agg']['TRAIN']['net_R']:+.3f} VALID {per_pair[sym]['agg']['VALID']['net_R']:+.3f} TEST {per_pair[sym]['agg']['TEST']['net_R']:+.3f}")
        pos_gross = sum(1 for s_ in PAIRS if per_pair[s_]["agg"]["ALL"]["gross_R"] > 0)
        print(f"       pairs with a positive gross edge: {pos_gross} of {len(PAIRS)}")
        results[f"{tf}m"] = dict(per_pair=per_pair, pooled=R.agg(tr["r_net"].to_numpy(), tr["cost_R"].to_numpy(), tr["per"].to_numpy()), pairs_positive_gross=pos_gross,
                                 row={k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in row.items() if k != "name"})
    lr = H.ledger_rows([{**r} for r in rows_out], "Round 313 (pre-registered, fixed-configuration confirmation of Round 312 on five other MT5 broker pairs)", commit, date="2026-10-02")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lr) + "\n")
    with open(os.path.join(HERE, "round313_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote round313_results.json and {len(lr)} ledger rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
