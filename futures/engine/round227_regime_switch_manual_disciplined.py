"""
Round 227 (the trader, 2026-09-30): "the target is to find the edge we're looking
for the plan" -- continuing the search for a genuine new edge after the
the trader confluence-filter branch (Rounds 223-226) closed out negative.

A genuinely untested question, distinct from everything tried this session:
does a real, CAUSAL regime signal predict which specific days
disciplined_bracket beats the trader, well enough to build a real switch rule
between the two? This has a clean logical starting point: Round 207 already
found the trader beats disciplined_bracket UNCONDITIONALLY on average (its real
risk-managed series is ~13x disciplined_bracket's own $23.02/day) -- so a
switch rule can only ever help if it can flag, in advance, the specific
days where disciplined_bracket is the better choice, not just "disciplined
bracket is calmer in general" (the trader's own -$1,000/+$1,650 clip already
provides that). Checked first, directly: on the real 956-day overlap
between both series' real histories (2022-12-12 -> 2026-09-23), disciplined
bracket actually DOES beat the trader on 46.3% of days, by a real, sizeable
average of $2,774.38 on those days -- so there is real day-to-day variation
worth trying to predict, not a foregone conclusion.

Two real, causal regime candidates tested, using idea_harness's own
`load_days("MNQ")` and the SAME expanding-quantile convention Round 134
already established (no new causality primitive invented):
  1. Trend-strength score -- Round 134's own |r20|/vol construction,
     reused directly (`round134_batch_c.regime_table`), tercile split.
  2. Realized-volatility percentile -- 20-day trailing realized vol of
     daily log returns, expanding percentile rank (same causal shape as
     regime_table, built fresh here since Round 134 never computed this
     specific series).
Both split into IS (< 2025-07-01) / OOS (>= 2025-07-01) terciles, with a
20,000-draw bootstrap on the full-period tercile split for the candidate
that showed a consistent-direction lean.

Not ledger-eligible (a regime-signal check on two already-existing real
strategies, not a new standalone idea test in idea_harness's own trade-
level sense) -- same convention as the the trader/disciplined_bracket variant
rounds (206-226). Neither strategy's code is touched.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round134_batch_c import regime_table
from round204_multi_account_best_strategies import build_manual_full_history
import round120_goal_judge as J

HERE = os.path.dirname(os.path.abspath(__file__))
N_BOOT = 20_000


def load_aligned():
    raw_manual = build_manual_full_history()
    with open(os.path.join(HERE, "live_disciplined_bracket_daily.json")) as f:
        db_raw = json.load(f)
    db = pd.Series(db_raw)
    db.index = pd.to_datetime(db.index)
    db = db.sort_index()
    common = raw_manual.index.intersection(db.index)
    k, d = raw_manual.reindex(common), db.reindex(common)
    return k, d, (k - d)


def vol_percentile_regime(days, common_index):
    close = pd.Series({dd["tday"]: float(dd["session"]["close"].iloc[-1]) for dd in days}).sort_index()
    lr = np.log(close).diff()
    vol20 = lr.shift(1).rolling(20).std()
    vol_pct = vol20.expanding(min_periods=60).apply(lambda s: (s.iloc[-1] >= s).mean(), raw=False)
    return vol_pct.reindex(common_index)


def tercile_test(signal, y, label):
    s = signal.dropna()
    yy = y.reindex(s.index)
    valid = yy.notna() & s.notna()
    s, yy = s[valid], yy[valid]
    is_m = s.index < J.OOS_START
    is_s = s[is_m]
    q1, q2 = is_s.quantile([1 / 3, 2 / 3])
    print(f"\n{label}:")
    for phase, mask in [("IS", is_m), ("OOS", ~is_m)]:
        ss, yy_p = s[mask], yy[mask]
        low, high = yy_p[ss <= q1], yy_p[ss > q2]
        print(f"  {phase}  low tercile (n={len(low)}): P(DB wins)={low.mean():.1%}   "
              f"high tercile (n={len(high)}): P(DB wins)={high.mean():.1%}")
    return q1, q2, s, yy


if __name__ == "__main__":
    k, d, diff = load_aligned()
    y = (diff < 0).astype(int)
    print(f"Real overlap: {len(diff)} days, {diff.index.min().date()} -> {diff.index.max().date()}")
    print(f"Mean daily diff (the trader - DB): ${diff.mean():+.2f}")
    print(f"Days DB beat the trader: {(diff < 0).sum()} of {len(diff)} ({(diff < 0).mean():.1%}), "
          f"mean diff on those days ${diff[diff < 0].mean():+.2f}")

    days = H.load_days("MNQ")
    rt = regime_table(days)
    trend_score = rt["score"].reindex(diff.index)
    q1t, q2t, st, yt = tercile_test(trend_score, y, "Trend-strength score (Round 134's |r20|/vol)")

    vol_pct = vol_percentile_regime(days, diff.index)
    q1v, q2v, sv, yv = tercile_test(vol_pct, y, "Realized-vol percentile (20-day)")

    print("\n=== Full-period bootstrap on the vol-percentile lean (the only consistent-direction candidate) ===")
    rng = np.random.default_rng(0)
    low_mask, high_mask = sv <= q1v, sv > q2v
    low_y, high_y = yv[low_mask].values.astype(float), yv[high_mask].values.astype(float)
    boot_low = rng.choice(low_y, size=(N_BOOT, len(low_y)), replace=True).mean(axis=1)
    boot_high = rng.choice(high_y, size=(N_BOOT, len(high_y)), replace=True).mean(axis=1)
    p_winrate = float((boot_low > boot_high).mean())
    print(f"Win-rate: low-vol P(DB wins)={low_y.mean():.1%} (n={len(low_y)})  "
          f"high-vol P(DB wins)={high_y.mean():.1%} (n={len(high_y)})  "
          f"bootstrap P(low>high) = {p_winrate:.4f}")

    diff_v = diff.reindex(sv.index)
    low_d, high_d = diff_v[low_mask].values, diff_v[high_mask].values
    boot_low_d = rng.choice(low_d, size=(N_BOOT, len(low_d)), replace=True).mean(axis=1)
    boot_high_d = rng.choice(high_d, size=(N_BOOT, len(high_d)), replace=True).mean(axis=1)
    p_dollar = float((boot_low_d < boot_high_d).mean())
    print(f"$ magnitude: mean diff low-vol=${low_d.mean():+.2f}  high-vol=${high_d.mean():+.2f}  "
          f"bootstrap P(the trader's edge smaller in low-vol) = {p_dollar:.4f}")

    verdict = "no edge -- neither regime candidate clears the 0.95 bar (trend-strength reverses sign OOS; " \
              "vol-percentile is sub-threshold on win-rate and not significant on $ magnitude)"
    print(f"\nVerdict: {verdict}")

    with open(os.path.join(HERE, "round227_results.json"), "w") as f:
        json.dump(dict(n_overlap_days=len(diff), mean_diff=float(diff.mean()),
                       db_win_rate=float((diff < 0).mean()), db_win_mean=float(diff[diff < 0].mean()),
                       p_winrate_low_gt_high=p_winrate, p_dollar_low_lt_high=p_dollar, verdict=verdict),
                  f, indent=1, default=str)
