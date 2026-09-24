"""
Round 89: the trader asked directly for the MES/MYM/M2K/MGC/SIL numbers to be made
"trustworthy/real" after Round 88 flagged them as thin-sample. Two things checked,
neither of which is "get more real data" -- re-pulled the freshest possible
BrokerAPI/BrokerAPI snapshot first (fetch_brokerapi_history.py, 2026-09-24) and every
symbol is still bounded to the SAME real active-contract window (2026-07-26 ->
today, ~60 real days) -- this is a real, structural ceiling (the Gateway does not
retain 1-minute history on expired contracts), not something more fetching fixes.

So "trustworthy" here means: properly quantify how much confidence the EXISTING
real trades actually support, rather than reporting a bare point estimate. Two
checks added, per symbol, on top of Round 88's exact walk-forward output:

  1. Bootstrap confidence interval on per-trade expectancy (resample the REAL
     walk-forward TEST trades, with replacement, 10,000 times; report the 90% CI
     of the mean and P(mean > 0)). This is standard, honest small-sample
     inference -- it does not invent data, it quantifies how much the small real
     sample size alone could be masking pure noise. Round 88's eval-stage Monte
     Carlo already captures ORDINARY trading variance (sequencing risk); this is
     a DIFFERENT question -- is there evidence of a real edge at all, given how
     few real trades exist.
  2. Contract-count-per-trade sanity check at the selected (stop, RR)'s real
     sizing -- a backtest showing profit that requires holding an unrealistic
     number of micro contracts simultaneously is not "trustworthy" even if the
     P&L arithmetic is correct, since real fills/liquidity at that size are
     unverified in this repo.

Reuses Round 88's exact walk-forward (same folds, same selection, same gates) --
this is a significance layer on top of it, not a different backtest.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
import numpy as np
import pandas as pd
from round11_fvg_bias import load_1m_brokerapi, resample_causal, detect_fvgs, fold_stats, POINT_VALUE
from round76_ote_pdarray_formalized import detect_ote_signals, resolve_outcomes_gated
from round83_ote_true_walkforward import (
    select_best_params, single_trade_win_dollars, RISK_DOLLAR, DAY_CAP,
    INITIAL_TRAIN_FRAC, N_TEST_FOLDS, MIN_TRAIN_TRADES,
)
from round85_ote_ny_rth_only import RTH_START, RTH_END
from round86_ote_max_daily_profit_cap import MAX_DAILY_PROFIT

SYMBOLS = ["MNQ", "MES", "MYM", "M2K", "MGC", "SIL"]  # MNQ included as the trusted baseline
DATA_DIR = os.path.join("..", "data")
N_BOOTSTRAP = 10_000
BOOT_SEED = 0


def bootstrap_expectancy_ci(pnl: np.ndarray, n_boot=N_BOOTSTRAP, seed=BOOT_SEED):
    """Resamples the REAL trades with replacement n_boot times; returns the 90%
    CI of the mean and P(resampled mean > 0). Answers 'how much could the small
    real sample size alone be hiding pure noise', not 'what will future trading
    variance do' (that's the separate eval-stage Monte Carlo)."""
    if len(pnl) == 0:
        return {"p05": np.nan, "p50": np.nan, "p95": np.nan, "p_positive": np.nan}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(pnl), size=(n_boot, len(pnl)))
    means = pnl[idx].mean(axis=1)
    return {
        "p05": float(np.percentile(means, 5)),
        "p50": float(np.percentile(means, 50)),
        "p95": float(np.percentile(means, 95)),
        "p_positive": float((means > 0).mean()),
    }


def run_symbol(symbol: str) -> dict | None:
    path = os.path.join(DATA_DIR, f"{symbol}_1MIN_BROKERAPI.csv")
    if not os.path.exists(path):
        print(f"\n{symbol}: SKIPPED -- no real data pull found at {path}")
        return None

    df1m = load_1m_brokerapi(path)
    htf15 = resample_causal(df1m, "15min")
    fvg_zones = detect_fvgs(htf15)
    sig_df_all = detect_ote_signals(df1m, fvg_zones)
    start, end = df1m.index.min(), df1m.index.max()

    if sig_df_all.empty:
        print(f"\n{'='*84}\n{symbol}: {len(df1m):,} real bars, {start} -> {end} "
              f"({(end - start).days} real days) -- detector never fired ONE signal. Not enough to assess.")
        return {"symbol": symbol, "n": 0}

    t = sig_df_all["ts"].dt.time
    sig_df = sig_df_all[(t >= RTH_START) & (t < RTH_END)].reset_index(drop=True)
    print(f"\n{'='*84}\n{symbol}: {len(df1m):,} real bars, {start} -> {end} "
          f"({(end - start).days} real days), n_signals(NY RTH-only)={len(sig_df)}")

    span = end - start
    train_end0 = start + span * INITIAL_TRAIN_FRAC
    remaining = end - train_end0
    fold_bounds = [train_end0 + remaining * i / N_TEST_FOLDS for i in range(N_TEST_FOLDS + 1)]

    all_test_trades = []
    contracts_used = []
    for i in range(N_TEST_FOLDS):
        train_cutoff = fold_bounds[i]
        test_start, test_end = fold_bounds[i], fold_bounds[i + 1]
        sig_train = sig_df[sig_df["ts"] < train_cutoff]
        sig_test = sig_df[(sig_df["ts"] >= test_start) & (sig_df["ts"] < test_end)]

        best = select_best_params(sig_train, df1m, symbol, max_daily_profit=MAX_DAILY_PROFIT,
                                   max_single_trade_win=MAX_DAILY_PROFIT)
        if best is None:
            continue
        train_exp, stop, rr, n_train = best
        pv = POINT_VALUE[symbol]
        contracts = max(1, int(RISK_DOLLAR // (stop * pv)))
        contracts_used.append(contracts)
        test_trades, _ = resolve_outcomes_gated(sig_test, df1m, symbol, rr, RISK_DOLLAR, stop, DAY_CAP,
                                                  max_daily_profit=MAX_DAILY_PROFIT)
        print(f"  Fold {i+1}: stop={stop:.0f}pts/RR=1:{rr:.0f} -> {contracts} contracts/trade "
              f"(${RISK_DOLLAR:.0f} risk / {stop:.0f}pts / ${pv:,.2f} per point) | test n={len(test_trades)}")
        all_test_trades.append(test_trades)

    if not all_test_trades:
        print(f"  {symbol}: no walk-forward test trades produced -- not enough real signal frequency to assess.")
        return {"symbol": symbol, "n": 0}

    wf = pd.concat(all_test_trades, ignore_index=True).sort_values("ts").reset_index(drop=True)
    s = fold_stats(wf)
    ci = bootstrap_expectancy_ci(wf["pnl"].to_numpy())
    max_contracts = max(contracts_used) if contracts_used else 0

    print(f"  Real trades: n={s['n']}, win%={s['winrate']*100:.1f}, total=${s['total']:,.2f}, "
          f"expectancy=${s['expectancy']:.2f}/trade")
    print(f"  Bootstrap 90% CI on expectancy (resampling these SAME real {s['n']} trades, "
          f"{N_BOOTSTRAP:,}x): [${ci['p05']:.2f}, ${ci['p95']:.2f}], median=${ci['p50']:.2f}, "
          f"P(true mean > $0)={ci['p_positive']:.1%}")
    print(f"  Largest position size any fold selected: {max_contracts} contracts/trade")

    return {
        "symbol": symbol, "n": s["n"], "total": s["total"], "winrate": s["winrate"],
        "expectancy": s["expectancy"], "ci_p05": ci["p05"], "ci_p95": ci["p95"],
        "p_positive": ci["p_positive"], "max_contracts": max_contracts,
    }


if __name__ == "__main__":
    print("=== Round 89: is the Round 88 multi-symbol result statistically trustworthy? ===")
    print(f"Freshest real BrokerAPI/BrokerAPI pull as of today -- every symbol's active contract still")
    print(f"bounded to the same ~60 real days (a structural ceiling, not something re-fetching fixes).")
    print(f"Bootstrap CI answers 'given ONLY these real trades, how confident can we be the true\n"
          f"expectancy is actually positive' -- separate from the eval-stage Monte Carlo's sequencing risk.\n")

    results = []
    for symbol in SYMBOLS:
        r = run_symbol(symbol)
        if r is not None:
            results.append(r)

    print(f"\n{'='*84}\n=== VERDICT: which symbols' results survive a real significance check? ===")
    for r in results:
        if r["n"] == 0:
            print(f"{r['symbol']:6s}: not enough real trades to assess at all.")
            continue
        trustworthy = r["p_positive"] >= 0.90 and r["n"] >= 30
        verdict = "PASSES the significance bar (n>=30 AND P(edge>0)>=90%)" if trustworthy else \
                  "does NOT pass -- " + ("sample too thin (n<30)" if r["n"] < 30 else f"P(edge>0) only {r['p_positive']:.1%}")
        print(f"{r['symbol']:6s}: n={r['n']:3d}  expectancy=${r['expectancy']:7.2f}  "
              f"90% CI=[${r['ci_p05']:.2f}, ${r['ci_p95']:.2f}]  P(edge>0)={r['p_positive']:.1%}  "
              f"max_contracts={r['max_contracts']:3d}  -> {verdict}")
    print("\nDONE.")
