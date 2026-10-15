"""Descriptive (not an edge trial): the registered D2 swap-free drift book sized by a CPPI rule on the MT5 broker account from today.
Gross G_t = min(GCAP, m * (equity_t - 92,000 - SAFE)); equity from 97,708.08; MT5 broker rules as in swapfree_mt5sim (day gain counted up to +2,000,
breach at a day low <= -2,500 or equity + day low <= 92,000, pass at 108,000). Day series per 100k gross from the D2 runs (2020-25, and 2020-26).
Also the gold EA pair x1.2 (FT 2022-26 pool, same dates) plus the CPPI-sized D2 book.   python -m forex.ea_research.swapfree_cppi"""
import numpy as np
import pandas as pd

from forex.ea_research import clean_boot_lib as L

START_BAL = 97_708.08
START = np.datetime64("2026-10-16")
HZ = {k: int(np.busday_count(START, np.datetime64(v))) for k, v in {"22 Dec": "2026-12-23", "31 Mar 27": "2027-04-01", "30 Jun 27": "2027-07-01", "31 Dec 27": "2028-01-01"}.items()}
LED = "D:/finance/si_ledgers"


def sim(r, b, m, gcap, safe, rng, pair=None, paths=20000):
    H = max(HZ.values()) + 1; n = len(r); nb = H // 5 + 2
    s0 = rng.integers(0, n - 5, size=(paths, nb)); idx = (s0[:, :, None] + np.arange(5)[None, None, :]).reshape(paths, -1)[:, :H]
    bal = np.full(paths, START_BAL); st = np.zeros(paths, np.int8); day = np.full(paths, -1)
    for j in range(H):
        G = np.clip(m * (bal - 92_000 - safe), 0, gcap)
        v = r[idx[:, j]] * G; lo = b[idx[:, j]] * G
        if pair is not None: v = v + pair[0][idx[:, j]]; lo = lo + pair[1][idx[:, j]]
        act = st == 0
        br = act & ((lo <= -2500) | (bal + lo <= 92_000)); st[br], day[br] = 2, j
        act = st == 0
        bal = np.where(act, bal + np.minimum(v, 2000.0), bal)
        ps = act & (bal >= 108_000); st[ps], day[ps] = 1, j
    return st, day


def line(label, st, day):
    c = " | ".join(f"{k} {100*np.mean((st == 1) & (day < h)):.1f}/{100*np.mean((st == 2) & (day < h)):.1f}" for k, h in HZ.items())
    print(f"  {label}: {c}", flush=True)
    return dict(label=label, **{f"pass {k}": 100 * np.mean((st == 1) & (day < h)) for k, h in HZ.items()}, **{f"breach {k}": 100 * np.mean((st == 2) & (day < h)) for k, h in HZ.items()})


def main():
    rng = np.random.default_rng(1510262)
    R = pd.read_parquet(f"{LED}/SWAPFREE_RUN_series.parquet"); Hd = pd.read_parquet(f"{LED}/SWAPFREE_HOLD_D2_series.parquet").loc["D2_HOLD"]
    s25 = pd.concat([R.loc[f"D2_{p}"] for p in ("OOT", "DEV", "VAL")]); s26 = pd.concat([s25, Hd])
    print("business days from Fri 16 Oct:", HZ, "\ncells pass% / breach%")
    rows = []
    for nm, s in (("2020-25", s25), ("2020-26", s26)):
        r, b = (s.V / 1e5).to_numpy(), (s.B / 1e5).to_numpy()
        for m, gcap, safe in ((5, 40_000, 500), (10, 40_000, 500), (15, 40_000, 500), (10, 60_000, 500), (20, 60_000, 500), (10, 100_000, 0)):
            rows.append(line(f"D2 {nm} CPPI m={m} cap={gcap/1000:.0f}k safe={safe}", *sim(r, b, m, gcap, safe, rng)))
    P = L.series("FT", 1.2); pdf = pd.DataFrame({"V": P["V"], "B": P["B"]}, index=pd.to_datetime(P["days"], unit="D"))
    s = pd.concat([R.loc["D2_DEV"], R.loc["D2_VAL"], Hd]); j = pdf.join(s, rsuffix="_d", how="inner")
    r, b = (j.V_d / 1e5).to_numpy(), (j.B_d / 1e5).to_numpy(); pair = (j.V.to_numpy(), j.B.to_numpy())
    print(f"pair x1.2 (FT) + D2 CPPI on {len(j)} common days 2022-26:")
    rows.append(line("pair x1.2 alone", *sim(r, b, 0, 0, 0, rng, pair)))
    for m, gcap in ((5, 20_000), (5, 40_000), (10, 40_000)):
        rows.append(line(f"pair x1.2 + D2 CPPI m={m} cap={gcap/1000:.0f}k", *sim(r, b, m, gcap, 1500, rng, pair)))
    pd.DataFrame(rows).to_csv(f"{LED}/SWAPFREE_CPPI.csv", index=False)


if __name__ == "__main__":
    main()
