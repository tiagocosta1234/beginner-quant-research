"""
Round 334 (2026-10-03, PRE-REGISTERED; ONE ledger row, k + 1): BTCUSD intraday patterns on MT5 H1 bars, trades held INSIDE one server day (flat before 00:00 server = 17:00 New York, so no swap is ever paid).

Why this scope: the contract (forex/specs/BTCUSD_crypto_specs_20261003.json) has swap_mode 5 with swap -30 on BOTH sides (if read correctly, an annual interest of 30% on the notional: about 8 bp a night, about 25 bp on the triple-swap night), commission about 6.5 bp
round trip (3.25 bp a side, to be confirmed with a deal), median bar spread 2.5 bp: a position held across a rollover costs 15-25 bp, more than any edge seen so far (Round 257's only BTC lead was +9 bp a day, P 0.64-0.81). Hourly returns have lag-1 autocorrelation -0.008. So only intraday holds are tested.
Ledger checked first (k = 2035): BTC / ETH daily trend (Rounds 139, 257), weekend-gap fades, 1-60 second HFT cost check: BTC hourly time-of-day and N-hour momentum / reversal inside the day are NOT in the ledger.

DATA: forex/data/BTCUSD_H1.parquet (MT5 H1 bid bars, MT5 server clock = New York + 7 h, pulled 2026-10-03; real 24/7 trading from about mid-2021: weekend bars are 1-2% of the bars in 2019-2020 and 20-27% from 2021). Sample 2021-07-01 .. 2026-10-03, IS 2021-07-01..2023-12-31, OOS 2024-01-01..
HYPOTHESES (60): (A) HOUR OF DAY, 48: for each server hour h in 0..23 and direction long / short: enter at the open of bar h, exit at the close of bar h (one hour). (B) N-HOUR MOMENTUM / REVERSAL, 12: the return of the N hours before bar h (N in 4, 12, 24: close of bar h-1 over the close of bar h-1-N), first signal of the day where |return| >= 1.5 x the trailing 30-day std of N-hour returns, entry at the open of bar h (h from 0 to 24 - H; the lookback may cross midnight, it is all past data), hold H in (1, 4) hours, exit at the close of bar h+H-1 and never after server hour 23; follow (direction of the prior move) or fade: 3 x 2 x 2 = 12.
Both need every bar of the window present (a missing hour drops the trade). COST: 9.0 bp a round trip, fixed now (6.5 commission + 2.5 median spread); gross is reported too. Trades: BTCUSD one unit, return in bp of the entry price.
SELECTION: Benjamini-Hochberg q = 0.10 on IS one-sided p-values of mean net bp > 0 (day-clustered bootstrap, 2,000 draws, seed 334); OOS touched only for IS survivors. CANDIDATE: BH survivor in IS AND OOS net mean > 0 with day-clustered P >= 0.99 AND the opposite direction's OOS mean <= 0.
Not widened after the run (no new hours, windows, thresholds, costs or instruments to rescue a failure). ETHUSD is available and untouched: it is the confirmation set for any candidate.
POWER: per-trade sd about 56 bp (1 hour) to 110 bp (4 hours); IS about 900-1,300 days per hour slot, s.e. about 1.6-3.7 bp. After the 9 bp cost only a gross edge above about +13 bp a trade can show up as significant: any effect that large in hourly BTC would be a big, well-known anomaly; the prior is a null.
DRY-RUN COUNTS (trades only, no P&L): 60 cells. Hour-of-day cells: IS 860-911 trades, OOS 956-990 per hour and direction. Momentum / reversal cells (IS / OOS trades): N4 H1 535 / 626, N4 H4 490 / 569, N12 H1 398 / 506, N12 H4 358 / 459, N24 H1 316 / 418, N24 H4 284 / 379 (follow and fade share entries).
A bug was found in the first dry run before any P&L (an unnecessary 'hour >= N' entry restriction left the N = 24 cells empty, 56 cells); it is fixed and the cell count is the declared 60.
POWER: see above; the s.e. of an IS mean is about 1.6 bp (hour slots) to 3.7 bp (the 284-trade 4-hour cells).
"""
import os, sys, json
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "..", "mt5broker", "data", "BTCUSD_H1.parquet")
COST = 9.0
IS_END = pd.Timestamp("2023-12-31")
START = pd.Timestamp("2021-07-01")


def load():
    d = pd.read_parquet(PATH)
    d.index = pd.to_datetime(d.time, unit="s")
    d = d[d.index >= START - pd.Timedelta(days=45)]
    return d[["open", "high", "low", "close"]]


def trades():
    d = load()
    full = d.reindex(pd.date_range(d.index[0], d.index[-1], freq="h"))
    o, c = full.open.values, full.close.values
    idx = full.index
    rows = []
    # (A) hour of day
    for i in range(len(idx)):
        if idx[i] < START or np.isnan(o[i]) or np.isnan(c[i]):
            continue
        r = (c[i] / o[i] - 1) * 1e4
        for dr, nm in ((1, "long"), (-1, "short")):
            rows.append(("A", f"h{idx[i].hour:02d}|{nm}", idx[i].normalize(), dr * r - COST, dr * r))
    # (B) N-hour momentum / reversal, first signal of the day
    cl = pd.Series(c, index=idx)
    for N in (4, 12, 24):
        rN = (cl.shift(1) / cl.shift(1 + N) - 1) * 1e4                     # return of the N hours before bar h (both closes known at the bar's open)
        thr = 1.5 * rN.rolling(30 * 24, min_periods=24 * 20).std().shift(1)
        sig = (rN.abs() >= thr)
        for H in (1, 4):
            seen = set()
            for i in range(len(idx)):
                if idx[i] < START or not sig.iloc[i] or idx[i].hour + H > 24:
                    continue
                day = idx[i].normalize()
                if day in seen:
                    continue
                if i + H - 1 >= len(idx) or np.isnan(o[i]) or np.isnan(c[i + H - 1]) or np.isnan(cl.iloc[i - 1 - N]) or np.isnan(cl.iloc[i - 1]):
                    continue
                seen.add(day)
                r = (c[i + H - 1] / o[i] - 1) * 1e4
                s = np.sign(rN.iloc[i])
                for mode, dr in (("follow", s), ("fade", -s)):
                    rows.append(("B", f"N{N}|H{H}|{mode}", day, dr * r - COST, dr * r))
    return pd.DataFrame(rows, columns=["fam", "cell", "date", "net", "gross"])


def boot(x, rng, col="net"):
    g = x.groupby("date")[col].agg(["sum", "count"])
    idx = rng.integers(0, len(g), (2000, len(g)))
    m = g["sum"].values[idx].sum(1) / g["count"].values[idx].sum(1)
    return float(x[col].mean()), float((m > 0).mean())


def main(dry):
    t = trades(); rng = np.random.default_rng(334); res = []
    cells = sorted(t.cell.unique())
    for c in cells:
        x = t[t.cell == c]; a, b = x[x.date <= IS_END], x[x.date > IS_END]
        if dry:
            print(f"{c}: IS {len(a)} OOS {len(b)}"); continue
        mi, pi = boot(a, rng); mo, po = boot(b, rng)
        res.append(dict(cell=c, n_is=len(a), n_oos=len(b), is_net=mi, is_gross=float(a.gross.mean()), p_is=1 - pi, oos_net=mo, oos_P=po))
    if dry:
        print("cells", len(cells)); return
    df = pd.DataFrame(res).sort_values("p_is").reset_index(drop=True); m = len(df); q = 0.10
    ok = df.p_is.values <= (np.arange(1, m + 1) / m) * q
    k = int(np.flatnonzero(ok).max() + 1) if ok.any() else 0
    df["bh"] = False; df.loc[:k - 1, "bh"] = True
    opp = lambda c: c.replace("long", "SHORT").replace("short", "long").replace("SHORT", "short") if c.startswith("h") else c.replace("follow", "FADE").replace("fade", "follow").replace("FADE", "fade")
    df["cand"] = False
    for i in range(k):
        r = df.iloc[i]; o_ = df[df.cell == opp(r.cell)]
        df.loc[i, "cand"] = bool(r.oos_net > 0 and r.oos_P >= .99 and len(o_) and float(o_.oos_net.iloc[0]) <= 0)
    print(f"hypotheses m={m}; BH survivors in IS: {k}; candidates: {int(df.cand.sum())}")
    print(df.head(12).round(3).to_string()); print("mean IS net", round(df.is_net.mean(), 2), " mean IS gross", round(df.is_gross.mean(), 2), " mean OOS net", round(df.oos_net.mean(), 2))
    df.to_csv(os.path.join(HERE, "round334_grid.csv"), index=False)
    json.dump(dict(m=m, bh=k, candidates=int(df.cand.sum()), mean_is_net=float(df.is_net.mean()), mean_is_gross=float(df.is_gross.mean()), mean_oos_net=float(df.oos_net.mean())), open(os.path.join(HERE, "round334_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
