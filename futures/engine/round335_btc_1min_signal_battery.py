"""
Round 335 (2026-10-03, PRE-REGISTERED; ONE ledger row, k + 1): the 1-minute BTCUSD signal battery on real MT5 broker bid / ask minute bars. Research only (the trader: "your job will be creating a profitable strategy of 1 minute btc").

Round 334 and the cost table said what has to be beaten: commission about 6.5 bp a round trip (3.25 bp a side, to be confirmed with a deal's commission field) plus the REAL spread paid by filling a long at the ask and a short at the bid (median 3.3 bp in 2021-2025, 0.14 bp in 2026), against 1-minute
moves of 4.7 bp on average. So no minute-long hold can pay; signals read from 1-minute data must carry a 5-60 minute hold. This round tests the natural families with all the data's own resolution, 2.5M minute bars, so effects of a few tenths of a bp are visible.
Ledger checked first (k = 2036): BTC hourly patterns (Round 334), D1 crypto scans (Round 257), BTC TSMOM (139) are done; 1-minute BTC signals are not in the ledger.

DATA: forex/data/BTCUSD_M1_ticks247.parquet (built from MT5 MT5 ticks, 2021-10-01..2026-10-03, 2,505,029 minutes, bid and ask OHLC, tick_volume; about 25 hours of weekly closure and 444 gaps over an hour, 4.9% of minutes missing). Server clock (New York + 7 h).
EXECUTION (identical for every cell): the signal is read at the close of minute i (all inputs known); ENTRY at the open of minute i+1: a LONG buys at the ask open, a SHORT sells at the bid open; EXIT at the close of minute i+H: a long sells at the bid close, a short buys at the ask close. Net bp of the entry price minus 6.5 bp commission.
VALIDITY: every minute i .. i+H present (time difference exactly 60 x H seconds) and minutes i+1 and i+H in the same server day (no rollover, so no swap is ever paid). One position at a time: a signal while a trade is open is skipped.
SIGNALS (128 hypotheses): sd60 = std of the 1-minute log returns of the last 60 minutes (at least 45 valid, includes minute i). (S1) MOVE: z_k = log(close_i / close_{i-k}) / (sd60 x sqrt(k)) with k in (1, 3, 5, 15, 30, 60); trigger when |z_k| >= theta, theta in (2, 3); direction = sign(move) FOLLOW or FADE (opposite); hold H in (5, 15, 30, 60): 6 x 2 x 4 x 2 = 96.
(S2) BREAKOUT: close_i above the highest bid high (or below the lowest bid low) of the previous N minutes, N in (15, 60, 240); FOLLOW the break or FADE it; H in (5, 15, 30, 60): 3 x 4 x 2 = 24. (S3) VOLUME SPIKE: tick_volume_i z-score vs the previous 60 minutes >= 3 AND |z_1| >= 2; FOLLOW or FADE the minute's direction; H in (5, 15, 30, 60): 4 x 2 = 8.
SPLIT: IS = server dates 2021-10-01..2023-12-31, OOS = 2024-01-01 onward. SELECTION: Benjamini-Hochberg q = 0.10 on the IS one-sided p-values of mean net bp > 0 (day-clustered bootstrap, 2,000 draws, seed 335); OOS touched only for IS survivors.
CANDIDATE (fixed now): BH survivor in IS AND OOS mean net >= +1.0 bp with day-clustered P(>0) >= 0.99 AND the opposite direction's OOS mean <= 0 (so it is not a one-sided drift). Not widened after the run: no new k, theta, H, N, features, costs or instruments to rescue a failure. ETHUSD ticks are not pulled: they are the confirmation set for any candidate.
DRY-RUN COUNTS (trade counts only, no P&L): 128 cells. After the one-position rule the smallest cells have about 100 IS trades (S1 k60 theta3 H60 follow: 97 IS / 195 OOS), the largest about 75,000 (S2 N15 H5: 75,692 IS / 103,311 OOS); S1 k1 theta2 H5 has 39,400 IS / 51,001 OOS, S3 spike H5 5,069 / 5,663.
Hand-check of the mapping on one trade (S1 k5 theta3 H15 follow, trade 1000: signal 2022-04-01 02:44, short at the bid open 45,459.26 of 02:45, exit at the ask close 45,532.69 of 02:59, 15 minutes after the signal): gross -16.15 bp by hand and by the function; no two trades overlap in time.
POWER: per-trade sd is about 8 bp x sqrt(H) (18 bp at 5 minutes, 62 bp at 60 minutes); with 1,000-75,000 trades the s.e. of a cell mean is 0.1-2 bp, so an edge of a few tenths of a bp is visible in the big cells and only about +4-6 bp in the smallest. With a 6.5 bp commission plus about 3 bp of spread, the mean gross must exceed 9-10 bp a trade (0.14 bp spread in 2026).
"""
import os, sys, json
import numpy as np
import pandas as pd
from numba import njit

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "..", "mt5", "data", "BTCUSD_M1_ticks247.parquet")
COMM = 6.5
IS_END = pd.Timestamp("2023-12-31")
KS, THS, HS, NS = (1, 3, 5, 15, 30, 60), (2.0, 3.0), (5, 15, 30, 60), (15, 60, 240)


@njit(cache=True)
def greedy(idx, H):
    keep = np.zeros(len(idx), dtype=np.bool_)
    busy = -1
    for j in range(len(idx)):
        if idx[j] > busy:
            keep[j] = True
            busy = idx[j] + H
    return keep


def load():
    d = pd.read_parquet(PATH).sort_values("time").reset_index(drop=True)
    t = d.time.values.astype(np.int64)
    a = {c: d[c].values.astype(np.float64) for c in ("open", "high", "low", "close", "ask_open", "ask_close", "tick_volume")}
    return t, a


def features(t, a):
    n = len(t)
    c = a["close"]
    cont = np.r_[False, np.diff(t) == 60]
    r1 = np.where(cont, np.log(c / np.r_[np.nan, c[:-1]]), np.nan)
    sd60 = pd.Series(r1).rolling(60, min_periods=45).std().values
    f = {"sd60": sd60, "t": t}
    for k in KS:
        prev = np.r_[np.full(k, np.nan), c[:-k]]
        ok = np.r_[np.zeros(k, dtype=bool), (t[k:] - t[:-k]) == 60 * k]
        f[f"z{k}"] = np.where(ok, np.log(c / prev) / (sd60 * np.sqrt(k)), np.nan)
    hi, lo = pd.Series(a["high"]), pd.Series(a["low"])
    for N in NS:
        f[f"up{N}"] = (c > hi.shift(1).rolling(N, min_periods=N).max().values)
        f[f"dn{N}"] = (c < lo.shift(1).rolling(N, min_periods=N).min().values)
    tv = pd.Series(a["tick_volume"])
    f["zv"] = ((tv - tv.shift(1).rolling(60, min_periods=45).mean()) / tv.shift(1).rolling(60, min_periods=45).std()).values
    return f


def trades_for(sig_idx, sgn, H, t, a, mode):
    """sig_idx: signal minutes (sorted); sgn: +1 up / -1 down; mode follow / fade. Returns arrays of (server date, net, gross, entry index)."""
    n = len(t)
    ok = (sig_idx + H < n)
    sig_idx, sgn = sig_idx[ok], sgn[ok]
    valid = ((t[sig_idx + H] - t[sig_idx]) == 60 * H) & ((t[sig_idx + 1] // 86400) == (t[sig_idx + H] // 86400))
    sig_idx, sgn = sig_idx[valid], sgn[valid]
    keep = greedy(sig_idx, H)
    sig_idx, sgn = sig_idx[keep], sgn[keep]
    d = sgn if mode == "follow" else -sgn
    e = sig_idx + 1; x = sig_idx + H
    long_ = (a["close"][x] - a["ask_open"][e]) / a["ask_open"][e] * 1e4
    short_ = (a["open"][e] - a["ask_close"][x]) / a["open"][e] * 1e4
    gross = np.where(d > 0, long_, short_)
    day = pd.to_datetime(t[e], unit="s").normalize()
    return day, gross - COMM, gross


def cells(f, t, a):
    out = []
    for k in KS:
        z = f[f"z{k}"]
        for th in THS:
            idx = np.flatnonzero(np.abs(z) >= th); s = np.sign(z[idx])
            for H in HS:
                for mode in ("follow", "fade"):
                    out.append((f"S1|k{k}|th{th:g}|H{H}|{mode}", idx, s, H, mode))
    for N in NS:
        up, dn = f[f"up{N}"], f[f"dn{N}"]
        idx = np.flatnonzero(up | dn); s = np.where(up[idx], 1.0, -1.0)
        for H in HS:
            for mode in ("follow", "fade"):
                out.append((f"S2|N{N}|H{H}|{mode}", idx, s, H, mode))
    z1, zv = f["z1"], f["zv"]
    idx = np.flatnonzero((zv >= 3) & (np.abs(z1) >= 2)); s = np.sign(z1[idx])
    for H in HS:
        for mode in ("follow", "fade"):
            out.append((f"S3|spike|H{H}|{mode}", idx, s, H, mode))
    return out


def boot(day, x, rng):
    s = pd.DataFrame({"d": day, "x": x}).groupby("d").x.agg(["sum", "count"])
    idx = rng.integers(0, len(s), (2000, len(s)))
    m = s["sum"].values[idx].sum(1) / s["count"].values[idx].sum(1)
    return float(np.mean(x)), float((m > 0).mean())


def main(dry):
    t, a = load(); f = features(t, a); rng = np.random.default_rng(335); res = []
    for name, idx, s, H, mode in cells(f, t, a):
        day, net, gross = trades_for(idx, s, H, t, a, mode)
        ins = day <= IS_END
        if dry:
            print(f"{name}: signals {len(idx)}, trades IS {int(ins.sum())} OOS {int((~ins).sum())}"); continue
        mi, pi = boot(day[ins], net[ins], rng); mo, po = boot(day[~ins], net[~ins], rng)
        res.append(dict(cell=name, n_is=int(ins.sum()), n_oos=int((~ins).sum()), is_net=mi, is_gross=float(gross[ins].mean()), p_is=1 - pi, oos_net=mo, oos_gross=float(gross[~ins].mean()), oos_P=po))
    if dry:
        return
    df = pd.DataFrame(res).sort_values("p_is").reset_index(drop=True); m = len(df)
    ok = df.p_is.values <= (np.arange(1, m + 1) / m) * 0.10
    k = int(np.flatnonzero(ok).max() + 1) if ok.any() else 0
    opp = lambda c: c.replace("|follow", "|FADE").replace("|fade", "|follow").replace("|FADE", "|fade")
    df["bh"] = False; df.loc[:max(k - 1, -1), "bh"] = k > 0
    df["cand"] = False
    for i in range(k):
        r = df.iloc[i]; o_ = df[df.cell == opp(r.cell)]
        df.loc[i, "cand"] = bool(r.oos_net >= 1.0 and r.oos_P >= 0.99 and len(o_) and float(o_.oos_net.iloc[0]) <= 0)
    print(f"hypotheses m={m}; BH survivors in IS: {k}; candidates: {int(df.cand.sum())}")
    print(df.head(15).round(3).to_string())
    print("mean IS net %.2f  IS gross %.2f  OOS net %.2f  OOS gross %.2f" % (df.is_net.mean(), df.is_gross.mean(), df.oos_net.mean(), df.oos_gross.mean()))
    print("best OOS gross cells:"); print(df.sort_values("oos_gross", ascending=False).head(5)[["cell", "n_oos", "oos_gross", "oos_net"]].round(2).to_string())
    df.to_csv(os.path.join(HERE, "round335_grid.csv"), index=False)
    json.dump(dict(m=m, bh=k, candidates=int(df.cand.sum()), mean_is_net=float(df.is_net.mean()), mean_is_gross=float(df.is_gross.mean()), mean_oos_net=float(df.oos_net.mean()), mean_oos_gross=float(df.oos_gross.mean())), open(os.path.join(HERE, "round335_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
