"""Bar 5 of PREREG_SWAPFREE_DRIFT (reported, not an edge test): the D2 / D4 drift books on the MT5 broker account from today (balance 97,708.08, counted -2,291.92, first day Fri 16 Oct).
MT5 broker rules: day gain counted up to +2,000, breach at an intraday day low <= -2,500 or equity <= 92,000, pass at balance >= 108,000. 5-day block bootstrap, 20,000 paths.
Pool: 2020-25 days (OOT + DEV + VAL; HOLD 2026 added as a sensitivity). Day low = the conservative sum of each market's worst bid.
Also: daily correlation with the gold EA pair (clean_boot_lib FT pool, x1.2, 2022-26) and the pair x1.2 with / without the book on the same dates.
   python -m forex.ea_research.swapfree_mt5sim"""
import numpy as np
import pandas as pd

from forex.ea_research import clean_boot_lib as L

START_BAL = 97_708.08
START = np.datetime64("2026-10-16")
HZ = {k: int(np.busday_count(START, np.datetime64(v))) for k, v in {"30 Oct": "2026-10-31", "22 Dec": "2026-12-23", "31 Mar 27": "2027-04-01", "30 Jun 27": "2027-07-01"}.items()}
GS = (50_000, 100_000, 150_000, 200_000)
LED = "data/si_ledgers"


def simulate(V, B, H, rng, paths=20000):
    n = len(V); nb = H // 5 + 2
    st0 = rng.integers(0, n - 5, size=(paths, nb))
    idx = (st0[:, :, None] + np.arange(5)[None, None, :]).reshape(paths, -1)[:, :H]
    bal = np.full(paths, START_BAL); st = np.zeros(paths, np.int8); day = np.full(paths, -1)
    for j in range(H):
        v, b = V[idx[:, j]], B[idx[:, j]]
        act = st == 0
        br = act & ((b <= -2500) | (bal + b <= 92_000)); st[br], day[br] = 2, j
        act = st == 0
        bal = np.where(act, bal + np.minimum(v, 2000.0), bal)
        ps = act & (bal >= 108_000); st[ps], day[ps] = 1, j
    return st, day


def table(V, B, label, rng):
    H = max(HZ.values()) + 1; out = []
    for g in GS:
        st, day = simulate(V * g / 1e5, B * g / 1e5, H, rng)
        cells = [f"{k} {100*np.mean((st == 1) & (day < h)):.1f}/{100*np.mean((st == 2) & (day < h)):.1f}" for k, h in HZ.items()]
        print(f"  {label} G={g/1000:.0f}k: " + " | ".join(cells))
        out.append(dict(label=label, G=g, **{f"pass {k}": 100 * np.mean((st == 1) & (day < h)) for k, h in HZ.items()}, **{f"breach {k}": 100 * np.mean((st == 2) & (day < h)) for k, h in HZ.items()}))
    return out


def main():
    rng = np.random.default_rng(151026)
    R = pd.read_parquet(f"{LED}/SWAPFREE_RUN_series.parquet")
    rows = []
    print("trading days from Fri 16 Oct:", HZ, "\ncells: pass% / breach% (G = gross notional of the book)")
    for v in ("D2", "D4"):
        s = pd.concat([R.loc[f"{v}_{p}"] for p in ("OOT", "DEV", "VAL")])
        h = pd.read_parquet(f"{LED}/SWAPFREE_HOLD_{v}_series.parquet").loc[f"{v}_HOLD"]
        print(f"{v}: {len(s)} days 2020-25, mean {s.V.mean():+.1f}/day per 100k, sd {s.V.std():.0f}, worst low {s.B.min():.0f}, days with low < -2,500 per 100k: {int((s.B < -2500).sum())}")
        rows += table(s.V.to_numpy(), s.B.to_numpy(), f"{v} 2020-25", rng)
        sh = pd.concat([s, h]); rows += table(sh.V.to_numpy(), sh.B.to_numpy(), f"{v} 2020-26", rng)
    # correlation and combination with the gold EA pair (FT pool, x1.2)
    P = L.series("FT", 1.2); pd_ = pd.DataFrame({"V": P["V"], "B": P["B"]}, index=pd.to_datetime(P["days"], unit="D"))
    for v in ("D2", "D4"):
        s = pd.concat([R.loc[f"{v}_DEV"], R.loc[f"{v}_VAL"], pd.read_parquet(f"{LED}/SWAPFREE_HOLD_{v}_series.parquet").loc[f"{v}_HOLD"]])
        j = pd_.join(s, rsuffix="_d", how="inner")
        print(f"\n{v} vs gold EA pair x1.2 (FT 2022-26, {len(j)} common days): daily correlation {np.corrcoef(j.V, j.V_d)[0, 1]:+.3f}")
        for g in (0, 25_000, 50_000):
            V = j.V.to_numpy() + j.V_d.to_numpy() * g / 1e5; B = j.B.to_numpy() + j.B_d.to_numpy() * g / 1e5
            H = max(HZ.values()) + 1; st, day = simulate(V, B, H, rng)
            cells = [f"{k} {100*np.mean((st == 1) & (day < h)):.1f}/{100*np.mean((st == 2) & (day < h)):.1f}" for k, h in HZ.items()]
            print(f"  pair x1.2 + {v} G={g/1000:.0f}k{' (pair alone)' if g == 0 else ''}: " + " | ".join(cells))
            rows.append(dict(label=f"pair x1.2 + {v}", G=g, **{f"pass {k}": 100 * np.mean((st == 1) & (day < h)) for k, h in HZ.items()}, **{f"breach {k}": 100 * np.mean((st == 2) & (day < h)) for k, h in HZ.items()}))
    pd.DataFrame(rows).to_csv(f"{LED}/SWAPFREE_MT5SIM.csv", index=False)


if __name__ == "__main__":
    main()
