import numpy as np, pandas as pd
from forex.ea_research import d2_mt5rule as R
from forex.ea_research import swapfree_mt5sim as Q
DE, DH = R.S.build("MT5"), R.S.build("HD"); R.C = R.S.spliced_closes(DE, DH)
cache = R.build_cache(); W = R.weekly_weights(cache, R.C); days = list(cache)
starts = [d for d in days if pd.Timestamp("2022-01-03") <= d <= pd.Timestamp("2025-06-30")][::5]
h = int(np.busday_count(Q.START, np.datetime64("2026-12-01")))
for flag in (False, True):
    R.REENTER_NEXT_DAY = flag
    for G in (100_000, 150_000, 200_000):
        res = [R.hold_path(cache, days[days.index(s):], W, G, h + 1) for s in starts]
        st = np.array([r[0] for r in res]); dy = np.array([r[1] for r in res])
        print(f"{'next-day' if flag else 'W1 weekly'} G {G//1000}k: by 30 Nov pass {100*np.mean((st==1)&(dy<h)):.1f}% breach {100*np.mean((st==2)&(dy<h)):.1f}%  (horizon {h} business days)", flush=True)
