"""
Round 31d: sanity-check Round 31c's suspiciously perfect 100% success result.

63 trading days of recent-fold data, block-bootstrapped with block_size=10 into
20-day Monte Carlo paths, has very few actually-distinct starting blocks (~54 max)
drawn from a SINGLE real market stretch. If that stretch happened to be a strong,
autocorrelated uptrend for this edge, the "Monte Carlo" is really just replaying
minor permutations of one good run over and over -- understating true variance,
not confirming genuine robustness. Check the underlying daily P&L stats directly.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath("round19_random_entry.py")))
from round11_fvg_bias import load_1m, resample_causal
from round19_random_entry import causal_atr15_lookup
from round31_combined_portfolio import combined_daily_series
from round31c_recent_regime_oos import build_mnq_daily_recent, build_mgc_daily_recent, RECENT_FOLD_START, RECENT_FOLD_END

if __name__ == "__main__":
    mnq_path = os.path.join("..","data","MNQ_CONTINUOUS.txt")
    mgc_path = os.path.join("..","data","MGC_CONTINUOUS.txt")
    df1m_mnq = load_1m(mnq_path); atr15_mnq = causal_atr15_lookup(df1m_mnq)
    df1m_mgc = load_1m(mgc_path); h15_mgc = resample_causal(df1m_mgc, "15min"); atr15_mgc = causal_atr15_lookup(df1m_mgc)

    mnq_seeds = build_mnq_daily_recent(df1m_mnq, atr15_mnq, 225, n_seeds=15)
    mgc_daily = build_mgc_daily_recent(df1m_mgc, h15_mgc, atr15_mgc, 600)
    combined = [combined_daily_series(s, mgc_daily) for s in mnq_seeds]

    all_days = np.concatenate([s.values for s in combined])
    print(f"Recent-fold pool ({RECENT_FOLD_START.date()}..{RECENT_FOLD_END.date()}): "
          f"{len(combined)} seeds x ~{len(combined[0])} days = {len(all_days)} daily P&L draws")
    print(f"mean/day=${all_days.mean():,.2f} std/day=${all_days.std():,.2f} "
          f"min=${all_days.min():,.2f} max=${all_days.max():,.2f}")
    print(f"negative days: {(all_days<0).mean():.1%}  losing-day magnitude 95th pct: ${np.percentile(-all_days[all_days<0], 95) if (all_days<0).any() else 0:,.2f}")
    print(f"days needed for target ($19,184.62) at mean/day: {19184.62/all_days.mean():.1f}")

    # compare vs full-history pool at same risk
    from round31_combined_portfolio import build_mnq_daily, build_mgc_daily
    mnq_seeds_full = build_mnq_daily(df1m_mnq, atr15_mnq, 225, n_seeds=15)
    mgc_daily_full = build_mgc_daily(df1m_mgc, h15_mgc, atr15_mgc, 600)
    combined_full = [combined_daily_series(s, mgc_daily_full) for s in mnq_seeds_full]
    all_days_full = np.concatenate([s.values for s in combined_full])
    print(f"\nFull-history pool: {len(all_days_full)} daily P&L draws, mean/day=${all_days_full.mean():,.2f} "
          f"std/day=${all_days_full.std():,.2f}, negative days: {(all_days_full<0).mean():.1%}")

    print(f"\nRecent-fold mean/day is {all_days.mean()/all_days_full.mean():.2f}x the full-history mean/day")
