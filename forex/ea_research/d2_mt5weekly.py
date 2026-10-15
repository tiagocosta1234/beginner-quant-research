"""PREREG_D2_MT5WEEKLY: D2 HOLD mode with no next-day re-entry (flat until the next Monday decision). python -m forex.ea_research.d2_mt5weekly"""
import numpy as np
import pandas as pd

from forex.ea_research import d2_mt5rule as R
from forex.ea_research import swapfree_mt5sim as Q


def main():
    DE, DH = R.S.build("MT5"), R.S.build("HD"); R.C = R.S.spliced_closes(DE, DH)
    cache = R.build_cache(); W = R.weekly_weights(cache, R.C); days = list(cache)
    starts = [d for d in days if pd.Timestamp("2022-01-03") <= d <= pd.Timestamp("2025-06-30")][::5]
    H = max(Q.HZ.values()) + 1
    for flag in (True, False):
        R.REENTER_NEXT_DAY = flag
        for G in (100_000, 150_000):
            res = [R.hold_path(cache, days[days.index(s):], W, G, H) for s in starts]
            st = np.array([r[0] for r in res]); dy = np.array([r[1] for r in res])
            cells = {kk: (100 * np.mean((st == 1) & (dy < h)), 100 * np.mean((st == 2) & (dy < h))) for kk, h in Q.HZ.items()}
            tag = "next-day re-entry (D2_MT5RULE)" if flag else "flat until next Monday (W1)"
            print(f"{tag:32s} G {G/1000:.0f}k, {len(starts)} starts: " + " | ".join(f"{kk} {p:.1f}/{b:.1f}" for kk, (p, b) in cells.items()), flush=True)


if __name__ == "__main__":
    main()
