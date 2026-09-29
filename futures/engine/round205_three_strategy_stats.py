"""
Round 205 (the trader, 2026-09-29): "calculate the sharpe ratio from the three and
bunch of other numbers." The three from Round 204 ("Best Strategies,
Parallel $50K Accounts"): Combined POC+VA (live, uncapped), Disciplined
Bracket (eval, capped, live), the trader TOD+VWAP-Z (full MNQ_CONTINUOUS.txt
history).

Computed from each strategy's own RAW daily $ P&L series (imported directly
from round204_multi_account_best_strategies.py's builder functions), NOT
the post-replay $50K account balance -- the account balance resets to $0 on
every real blowup (3-8 times per strategy over the real history), which
would inject artificial discontinuities into a returns-based Sharpe/Sortino
calculation. The raw daily P&L series is also what every other real-vs-real
comparison this session has used (mean $/day, daily Sharpe) for exactly
this reason.

Reports BOTH Sharpe conventions, reconciled explicitly: this campaign's own
established "Sharpe" (disciplined_bracket_eval.md: "Sharpe (0.0493 vs
0.0480)") is the RAW DAILY mean/std ratio, unannualized -- confirmed by
direct reproduction here (combined signal: 60.11/1251.78 = 0.0480, an exact
match). The standard finance convention annualizes by sqrt(252) trading
days; both are printed side by side (`sharpe_daily` = this campaign's own
number, `sharpe_annualized` = the standard one) so nothing here looks
inconsistent with the existing strategy cards. Same reconciliation applied
to Sortino. Max drawdown and Calmar computed on the raw cumulative P&L
curve (not the reset-on-blowup account balance) since that answers "how bad
does the underlying edge's own equity curve get," a different, cleaner
question from "how many times does a real live account blow up" (already
answered in Round 204's own numbers).

Not ledger-eligible (a statistics/reporting round on three already-existing
real signals, no new idea tested).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd

from round204_multi_account_best_strategies import (
    build_combined_poc_va, build_disciplined_bracket, build_manual_full_history,
)

TRADING_DAYS_PER_YEAR = 252


def max_drawdown(daily):
    cum = daily.cumsum()
    running_max = cum.cummax()
    dd = cum - running_max
    return float(dd.min())


def stats_for(daily, label):
    d = daily.values
    active = d[d != 0]
    n_days = len(d)
    n_active = len(active)
    mean_all = d.mean()
    std_all = d.std(ddof=1)
    sharpe_daily = (mean_all / std_all) if std_all > 0 else float("nan")  # this campaign's own convention
    sharpe_annualized = sharpe_daily * np.sqrt(TRADING_DAYS_PER_YEAR)

    downside = d[d < 0]
    downside_std = downside.std(ddof=1) if len(downside) > 1 else float("nan")
    sortino_daily = (mean_all / downside_std) if downside_std and downside_std > 0 else float("nan")
    sortino_annualized = sortino_daily * np.sqrt(TRADING_DAYS_PER_YEAR)

    wins = active[active > 0]
    losses = active[active < 0]
    win_rate = len(wins) / n_active if n_active else float("nan")
    profit_factor = wins.sum() / abs(losses.sum()) if len(losses) and losses.sum() != 0 else float("nan")
    avg_win = wins.mean() if len(wins) else float("nan")
    avg_loss = losses.mean() if len(losses) else float("nan")

    mdd = max_drawdown(daily)
    total_pnl = d.sum()
    n_years = n_days / TRADING_DAYS_PER_YEAR
    calmar = (total_pnl / n_years) / abs(mdd) if mdd != 0 else float("nan")

    skew = pd.Series(active).skew() if n_active > 2 else float("nan")

    return dict(
        label=label, n_days=n_days, n_active=n_active,
        start=str(daily.index.min().date()), end=str(daily.index.max().date()),
        mean_per_day=mean_all, std_per_day=std_all,
        sharpe_daily=sharpe_daily, sharpe_annualized=sharpe_annualized,
        sortino_daily=sortino_daily, sortino_annualized=sortino_annualized,
        win_rate=win_rate, profit_factor=profit_factor, avg_win=avg_win, avg_loss=avg_loss,
        max_drawdown=mdd, calmar=calmar, total_pnl=total_pnl, skew=skew,
    )


if __name__ == "__main__":
    strategies = [
        ("Combined POC+VA (live, uncapped)", build_combined_poc_va),
        ("Disciplined Bracket (eval, capped, LIVE)", build_disciplined_bracket),
        ("the trader: TOD + VWAP-Z combined", build_manual_full_history),
    ]

    rows = []
    for label, builder in strategies:
        daily = builder()
        rows.append(stats_for(daily, label))

    hdr = (f"{'Strategy':<42} {'Days':>6} {'Active':>7} {'Mean/day':>10} {'Std/day':>10} "
           f"{'Sharpe(d)':>9} {'Sharpe(ann)':>11} {'Sortino(d)':>10} {'Sortino(ann)':>12} "
           f"{'WinRate':>8} {'ProfFac':>8} {'AvgWin':>9} {'AvgLoss':>10} {'MaxDD':>10} {'Calmar':>7} {'Skew':>7}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(f"{r['label']:<42} {r['n_days']:>6} {r['n_active']:>7} {r['mean_per_day']:>10.2f} "
              f"{r['std_per_day']:>10.2f} {r['sharpe_daily']:>9.4f} {r['sharpe_annualized']:>11.3f} "
              f"{r['sortino_daily']:>10.4f} {r['sortino_annualized']:>12.3f} {r['win_rate']:>8.1%} "
              f"{r['profit_factor']:>8.2f} {r['avg_win']:>9.2f} {r['avg_loss']:>10.2f} "
              f"{r['max_drawdown']:>10.2f} {r['calmar']:>7.3f} {r['skew']:>7.2f}")

    print()
    for r in rows:
        print(f"{r['label']}: {r['start']} -> {r['end']}, total P&L ${r['total_pnl']:,.2f}")

    import json
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "round205_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
