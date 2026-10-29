"""v3 platform: four asset classes from the MT5 M1 data, one decision bar per local day (PREREG_SELF_IMPROVING.md, Amendment 2).
   python -m forex.self_improving.platform_v3        (builds the cache, prints coverage)"""
from __future__ import annotations

import pickle
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from forex.self_improving import platform_pit as PIT

DATA = Path(__file__).resolve().parents[1] / "data_mt5"
CACHE = Path("data/scratch/si_cache"); CACHE.mkdir(parents=True, exist_ok=True)
NY = "America/New_York"
FX = ["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD",
      "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD", "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
CRYPTO = ["ADAUSD", "BCHUSD", "BNBUSD", "BTCUSD", "ETHUSD", "LTCUSD", "SOLUSD", "XRPUSD"]
CLASSES = {
    "idx": dict(carry=0.5, members={"SP": (NY, 1559), "NSDQ": (NY, 1559), "DOW": (NY, 1559), "DAX": ("Europe/Berlin", 1729), "NIKKEI": ("Asia/Tokyo", 1459), "ASX": ("Australia/Sydney", 1559)}),
    "fx": dict(carry=0.7, members={m: (NY, 1659) for m in FX}),
    "cmd": dict(carry=1.0, members={m: (NY, 1659) for m in ("XAUUSD", "XAGUSD", "WTI", "BRENT")}),
    "crypto": dict(carry=3.0, members={m: (NY, 1659) for m in CRYPTO}),
}
MIN_DAYS = 900
BLOCK = 1                       # placebo: every day shuffled (attempt 1 used 20-day blocks, which keep short-term structure)


def daily_base(m, tz, hm):
    f = CACHE / f"daily_{m}.pkl"
    if f.exists(): return pickle.load(open(f, "rb"))
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "ao"]).sort_values("t").drop_duplicates("t")
    d = d[(d.bo > 0) & (d.ao >= d.bo)]
    loc = pd.to_datetime(d.t, unit="s").dt.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").dt.tz_convert(tz)
    mins = loc.dt.hour * 60 + loc.dt.minute; target = (hm // 100) * 60 + hm % 100; gap = target - mins
    d = d.assign(date=loc.dt.tz_localize(None).dt.normalize(), gap=gap)[(gap >= 0) & (gap <= 30) & loc.notna()].dropna(subset=["date"])
    s = d.sort_values("t").groupby("date").last()[["t", "bo", "ao"]].rename(columns={"bo": "b", "ao": "a"})
    pickle.dump(s, open(f, "wb")); return s


def bases(cls):
    out = {}
    for m, (tz, hm) in CLASSES[cls]["members"].items():
        s = daily_base(m, tz, hm)
        if len(s) >= MIN_DAYS: out[m] = s
        else: print(f"dropped {m}: {len(s)} decision days")
    return out


def placebo_bases(b, seed):
    """One common permutation of BLOCK-day blocks (1 = every day shuffled) of the class calendar for all markets (cross-market structure kept), spreads kept."""
    master = sorted(set().union(*[set(s.index) for s in b.values()])); pos = {d: k for k, d in enumerate(master)}; n = len(master)
    rng = np.random.default_rng(seed + zlib.crc32(str(len(b)).encode()) % 1000); starts = list(range(0, n, BLOCK)); order = rng.permutation(len(starts))
    perm = np.concatenate([np.arange(starts[o], min(starts[o] + BLOCK, n)) for o in order]); out = {}
    for m, s in b.items():
        lr = np.zeros(n); r = np.log(s.b).diff().fillna(0.0).values; lr[[pos[d] for d in s.index]] = r
        cum = np.cumsum(lr[perm]); idx = [pos[d] for d in s.index]; nb = s.b.iloc[0] * np.exp(cum[idx] - cum[idx[0]])
        sp = (s.a - s.b).values / s.b.values; ns = s.copy(); ns["b"] = nb; ns["a"] = nb * (1 + sp); out[m] = ns
    return out


def tables(cls, placebo_seed=None):
    b = bases(cls)
    if placebo_seed is not None: b = placebo_bases(b, placebo_seed)
    return {m: PIT.features(s) for m, s in b.items()}


if __name__ == "__main__":
    for cls in CLASSES:
        t = tables(cls); lens = [len(x) for x in t.values()]
        print(f"{cls}: {len(t)} markets, decision days {min(lens)}-{max(lens)}, median spread {np.median([1e4 * ((x.a - x.b) / x.b).median() for x in t.values()]):.2f} bp")
