"""
Round 340 (2026-10-04, PRE-REGISTERED; ONE ledger row, k + 1): the @quantstackai "never trade the open" 5-minute breakout (Instagram DeE2Zk6xTpp, video uploaded by the trader) on every MT5 broker symbol with minute bars in the repo.

THE VIDEO (watched from 25 frames; audio not transcribed, the speech model could not be downloaded; every number below is read off the slides): 'The test. SIGNAL a simple breakout. BUY: a 5-min bar closes ABOVE the last 30 min's high. SELL: close BELOW the low. EXIT: hold 30 minutes.' NQ, 5 years (2021-2026), 21,640 signals; per NQ contract, hold 30 min, BEFORE costs: the rest of the day +$14 a trade, the open (09:30-10:00) +$59 a trade; the open swings harder (+/-$1,735 vs +/-$1,147 spread of outcomes), 'P = 0.19, not proof'; a random-entry control at the open is stopped out 49.2% of the time with a 25-point stop vs 39.6% at the rest of the day. The video's conclusion: 'the open isn't dangerous.' Narrated results are selected with hindsight: this round formalizes the rule and tests it on real MT5 broker fills.
RULE (one, fixed, identical on every symbol): 5-minute bars built from the minute bars (24-hour data, New York clock). At the close of 5-minute bar b: BREAKOUT UP if close_b > the highest bid high of bars b-6..b-1 (the previous 30 minutes); BREAKOUT DOWN if close_b < the lowest bid low of bars b-6..b-1. Direction FOLLOW: up -> LONG, down -> SHORT. ENTRY at the open of bar b+1: a long buys the ASK open, a short sells the BID open; EXIT 30 minutes later at the close of bar b+6 (the sixth bar after the signal): a long sells at the BID close, a short buys at the ASK close. All seven bars (b-6..b+6) must be present and contiguous.
BUCKETS (as the video): OPEN = signal bars closing in 09:30-10:00 New York (bars starting 09:30..09:55); REST = signal bars closing from 10:00 to 15:30 (the 30-minute hold then ends by 16:00); ALL = both. 3 buckets x 6 symbols = 18 hypotheses. The same clock is used for XAUUSD and BTCUSD (a convention, not a market open for them).
COSTS: spread paid through the ask / bid fills; plus a 0.5 bp allowance on every trade; BTCUSD adds the 6.5 bp commission (3.25 bp a side, to be confirmed). Net bp of the entry price.
SYMBOLS (all MT5 broker minute bid / ask in forex/data): US100.cash, US500.cash, US30.cash, US2000.cash, XAUUSD (2021-10-01..2026-10-02; US2000 from 2022-01-10) and BTCUSD (24/7 build, 2021-10-01..2026-10-03). ETHUSD has hourly bars only (cannot run). Symbols the second PC pulled but the repo lacks (EURUSD and others) are not tested.
TWO VERSIONS of every bucket: (1) EVERY SIGNAL (overlapping allowed: the video's convention, to compare with its numbers), (2) ONE POSITION AT A TIME (a signal while a trade is open is skipped: the tradable version). THE CANDIDATE TEST uses version (2).
SPLIT: IS = signal dates 2021-10-01..2023-12-31, OOS = 2024-01-01 onward. Statistic: mean net bp per trade, day-clustered bootstrap (5,000 draws, seed 340), P(mean > 0). CANDIDATE (fixed now): IS mean net > 0 with P >= 0.95 AND OOS mean net >= +1.0 bp with P >= 1 - 0.05/18 = 0.9972 AND the FADE (the opposite direction on the same signals) OOS mean <= 0 (not drift). Also reported: the video's claim, OPEN minus REST mean GROSS bp (before spread and allowance), per symbol.
Not widened after the run: no other lookback, hold, stop, filter, time bucket or symbol to rescue a failure.
DRY-RUN COUNTS (signals only, no P&L): US100.cash every-signal ALL 10,027 IS / 11,826 OOS = 21,853 over the 5 years (the video: 21,640 on NQ: the rule reproduces its signal count), OPEN 1,276 / 1,579, REST 8,751 / 10,247; one-position-at-a-time ALL 4,521 / 5,331, OPEN 549 / 667, REST 4,015 / 4,706.
Other symbols, single-position ALL (IS / OOS): US500 4,437 / 5,262; US30 4,403 / 5,318; US2000 3,926 / 5,390; XAUUSD 4,215 / 5,182; BTCUSD 5,140 / 7,167; the OPEN bucket has 479-551 IS and 583-793 OOS trades per symbol.
A bug was found by reading before any P&L (the one-position rule waited two bars too long: span 7 instead of 5); fixed. Hand-check of one trade (US100, signal bar 2021-12-03 09:35, breakdown, short at the bid open 15,988.95 of 09:40, exit at the ask close 15,754.55 of the 10:05 bar, 30 minutes): gross +148.78 bp by hand and by the function.
POWER: per-trade sd about 20-40 bp for the indices (30 minutes), 50 bp for BTC; with 480-7,000 trades per bucket the s.e. of a bucket mean is about 0.4-2 bp; the OPEN buckets (about 500 IS trades) can show only effects above about +3-4 bp net.
"""
import os, sys, json
import numpy as np
import pandas as pd
from numba import njit

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
from mt5 import clock

DATA = os.path.join(ROOT, "mt5broker", "data")
SYMS = {"US100.cash": "US100.cash_M1_ticks_full.parquet", "US500.cash": "US500.cash_M1_ticks_full.parquet", "US30.cash": "US30.cash_M1_ticks_full.parquet",
        "US2000.cash": "US2000.cash_M1_ticks_full.parquet", "XAUUSD": "XAUUSD_M1_ticks_full.parquet", "BTCUSD": "BTCUSD_M1_ticks247.parquet"}
ALLOW = 0.5; COMM = {"BTCUSD": 6.5}
IS_END = pd.Timestamp("2023-12-31")
LOOK, HOLD = 6, 6


@njit(cache=True)
def greedy(idx, span):
    keep = np.zeros(len(idx), dtype=np.bool_); busy = -1
    for j in range(len(idx)):
        if idx[j] > busy:
            keep[j] = True; busy = idx[j] + span
    return keep


def bars5(sym):
    raw = pd.read_parquet(os.path.join(DATA, SYMS[sym]))
    ny = clock.server_to_ny(raw["time"].to_numpy())
    d = pd.DataFrame({"o": raw.open.values, "h": raw.high.values, "l": raw.low.values, "c": raw.close.values, "ao": raw.ask_open.values, "ac": raw.ask_close.values}, index=ny)
    d = d[~d.index.duplicated(keep="first")].sort_index()
    key = d.index.floor("5min")
    g = d.groupby(key)
    b = pd.DataFrame({"o": g.o.first(), "h": g.h.max(), "l": g.l.min(), "c": g.c.last(), "ao": g.ao.first(), "ac": g.ac.last(), "n": g.c.count()})
    return b[b.n >= 5].drop(columns="n")           # complete 5-minute bars only


def signals(b):
    t = b.index.values.astype("datetime64[s]").astype(np.int64)
    n = len(b); c, h, l = b.c.values, b.h.values, b.l.values
    hi = pd.Series(h).shift(1).rolling(LOOK).max().values; lo = pd.Series(l).shift(1).rolling(LOOK).min().values
    up, dn = c > hi, c < lo
    idx = np.flatnonzero((up | dn) & ~np.isnan(hi))
    idx = idx[(idx >= LOOK) & (idx + HOLD < n)]
    ok = (t[idx + HOLD] - t[idx - LOOK]) == 300 * (HOLD + LOOK)               # all 13 bars contiguous
    idx = idx[ok]; sgn = np.where(up[idx], 1.0, -1.0)
    return t, idx, sgn


def evaluate(b, sym):
    t, idx, sgn = signals(b)
    ao, ac, o, c = b.ao.values, b.ac.values, b.o.values, b.c.values
    e, x = idx + 1, idx + HOLD
    long_ = (c[x] / ao[e] - 1) * 1e4; short_ = (o[e] / ac[x] - 1) * 1e4
    gross_follow = np.where(sgn > 0, long_, short_); gross_fade = np.where(sgn > 0, short_, long_)
    cost = ALLOW + COMM.get(sym, 0.0)
    ts = pd.to_datetime(t[idx + 1], unit="s")                                  # entry time (New York)
    sig_close = pd.to_datetime(t[idx] + 300, unit="s")                         # the signal bar's close time
    mins = sig_close.hour * 60 + sig_close.minute
    bucket = {"OPEN": (mins > 570) & (mins <= 600), "REST": (mins > 600) & (mins <= 15 * 60 + 25 + 5), "ALL": ((mins > 570) & (mins <= 600)) | ((mins > 600) & (mins <= 15 * 60 + 30))}
    return t, idx, gross_follow, gross_fade, cost, ts, bucket


def boot(day, x, rng):
    s = pd.DataFrame({"d": day, "x": x}).groupby("d").x.agg(["sum", "count"])
    if len(s) < 5: return float(np.mean(x)) if len(x) else float("nan"), 0.0
    idx = rng.integers(0, len(s), (5000, len(s))); m = s["sum"].values[idx].sum(1) / s["count"].values[idx].sum(1)
    return float(np.mean(x)), float((m > 0).mean())


def main(dry):
    rng = np.random.default_rng(340); rows = []
    for sym in SYMS:
        b = bars5(sym); t, idx, gf, gx, cost, ts, bucket = evaluate(b, sym)
        for name, m in bucket.items():
            i_all = idx[m]; day = ts[m].normalize()
            keep = greedy(i_all.astype(np.int64), HOLD - 1)       # a signal on bar j is skipped while the previous trade (entered at i+1, exited at the close of i+6) is open: allowed from j = i + 6
            # version 2: one position at a time inside the bucket
            sel = np.flatnonzero(m)[keep]
            for ver, ss in (("every", np.flatnonzero(m)), ("single", sel)):
                d = ts[ss].normalize(); isi = d <= IS_END
                if dry:
                    rows.append((sym, name, ver, int(isi.sum()), int((~isi).sum()))); continue
                f_net, x_net = gf[ss] - cost, gx[ss] - cost
                mi, pi = boot(d[isi], f_net[isi], rng); mo, po = boot(d[~isi], f_net[~isi], rng)
                rows.append(dict(sym=sym, bucket=name, ver=ver, n_is=int(isi.sum()), n_oos=int((~isi).sum()), is_net=mi, is_P=pi, oos_net=mo, oos_P=po, fade_oos=float(np.mean(x_net[~isi])) if (~isi).any() else float("nan"),
                                 gross_all=float(np.mean(gf[ss])) if len(ss) else float("nan")))
    if dry:
        for r in rows: print(r)
        return
    df = pd.DataFrame(rows)
    one = df[df.ver == "single"].copy()
    one["cand"] = (one.is_net > 0) & (one.is_P >= .95) & (one.oos_net >= 1.0) & (one.oos_P >= 1 - .05 / 18) & (one.fade_oos <= 0)
    print(one.round(3).to_string())
    print("every-signal version (the video's convention):"); print(df[df.ver == "every"][["sym", "bucket", "n_is", "n_oos", "is_net", "oos_net", "gross_all"]].round(2).to_string())
    print("\nvideo's claim: OPEN minus REST, mean GROSS bp per trade (every signal):")
    ev = df[df.ver == "every"].pivot(index="sym", columns="bucket", values="gross_all"); ev["OPEN-REST"] = ev["OPEN"] - ev["REST"]; print(ev.round(2).to_string())
    print("candidates:", one[one.cand][["sym", "bucket"]].values.tolist())
    df.to_csv(os.path.join(HERE, "round340_grid.csv"), index=False)
    json.dump(dict(candidates=one[one.cand][["sym", "bucket"]].values.tolist()), open(os.path.join(HERE, "round340_results_mt5broker_ask.json"), "w"))


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
