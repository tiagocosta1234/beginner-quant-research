"""
Round 324 (2026-10-03, PRE-REGISTERED; the 24 cells are logged as ONE ledger row, k + 1): enter AFTER the opening drive -- does the move since 09:30 predict the rest of the session well enough for the 1-Step table?

Round 322: +1 point of daily direction hit rate = about +2.8 points of 1-Step pass probability. Round 323 found no pre-open predictor. This round gives the call more information: the direction of the move from the 09:30 open to the entry time T,
followed (continuation) or faded (reversal), then the same table trade from T. Ledger checked first (k = 2026): first-30 -> last-30 (Round 318, ledger 2019-2022) and ORB-style breakouts exist; a continuation / reversal call at six entry times scored by hit rate
and table pass probability does not.

DATA: Round 321's NQ and ES session proxy (Databento 1-minute, 2020-01-02..2026-09-25, Round 321's day table logic: stop = 0.25 x mean RTH range of the previous 20 sessions, targets k x stop with k in 1.5 / 2.5 / 4 / 6 / 9, stop wins a tie, exit at the
15:59 close, Round 296 BASE costs scaled to price level) but ENTERING at the open of the bar stamped T instead of 09:30. T in {09:35, 10:00, 10:30, 11:00, 12:00, 13:00} (the table's day index is unchanged).
RULES: FOLLOW = direction of (open of the T bar - 09:30 open); FADE = the opposite; no trade if the move is exactly zero. 6 x 2 x 2 instruments = 24 cells.
SCORE per cell: hit rate = P(direction == sign(15:59 close - open of the T bar)), and P(pass within 57 trading days) over every start day, baseline = Round 321's COIN at the SAME entry time is NOT available, so the baseline is a coin flip entered at the same
T (computed here, 20 draws per start) to keep the comparison fair.
CANDIDATE (fixed now): hit rate >= 53.0% on BOTH NQ and ES for the same (T, rule) AND pass probability at least 8 points above that cell's coin-at-T baseline on both AND positive uplift in both periods (2020-22, 2023-26).
Not widened after the run. Look-ahead rule (Round 321 lesson): every feature is the open of a bar at or before T; the entry is that same T-bar open, never a later bar.
DRY-RUN COUNTS (no hit rate or pass probability printed): NQ 1,634-1,635 sessions at every T (zero-move days 0-4); ES 1,648-1,649 sessions (zero-move days 3-22, a tick-size effect at 0.25); the entry bar exists on every kept session.
POWER: hit-rate s.e. 1.23 points at n about 1,640; 24 cells, a joint NQ-and-ES bar of 53.0% each; pass-probability noise about +/-10 points (about 28 independent windows per instrument), so the +8 point uplift is required together with the hit rate and both periods.
"""
import os, sys, json
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import round321_long_bias_bold_play as R
from mt5 import onestep as OS

TS = {"0935": 575, "1000": 600, "1030": 630, "1100": 660, "1200": 720, "1300": 780}     # minutes after midnight
KS = R.KS


def day_table_T(sym, tmin):
    b = R.load(sym)
    days = {}
    for d, x in b.groupby(b.index.normalize()):
        if len(x) >= 380 and x.index[0].hour == 9 and x.index[0].minute == 30:
            days[d] = x
    ds = sorted(days)
    rng = pd.Series({d: days[d].h.max() - days[d].l.min() for d in ds})
    r20 = rng.rolling(20).mean().shift(1)
    rows = []
    for d in ds:
        if not np.isfinite(r20.get(d, np.nan)) or d < pd.Timestamp("2020-01-02"):
            continue
        x = days[d]
        m = x.index.hour * 60 + x.index.minute
        if tmin not in set(m):
            continue
        i0 = int(np.flatnonzero(m == tmin)[0])
        o0 = x.o.values[0]; oT = x.o.values[i0]
        c = x.c.values[i0:]
        stop = 0.25 * r20[d]
        sc = oT / R.PRICE_REF
        entry_R, stop_R = R.COST_ENTRY * sc / stop, R.COST_STOP * sc / stop
        res = {(side, k): R.trade_R(x, i0, side, stop, k, sc, entry_R, stop_R) for side in (1, -1) for k in KS}
        rows.append(dict(date=d, move=oT - o0, real=np.sign(c[-1] - oT), **{f"R_{s}_{k}": v for (s, k), v in res.items()}))
    return pd.DataFrame(rows).set_index("date")


def main(dry):
    pol = OS.Policy(); out = {}
    for sym in ("NQ", "ES"):
        for name, tmin in TS.items():
            df = day_table_T(sym, tmin)
            if dry:
                print(sym, name, "sessions", len(df), "zero-move days", int((df.move == 0).sum())); continue
            recs = df.reset_index().to_dict("records")
            rng = np.random.default_rng(324)
            starts = range(0, len(recs) - 57)
            half = np.array([df.index[s] < pd.Timestamp("2023-01-01") for s in starts])
            coin = np.array([np.mean([R.run_window(recs, s, 57, lambda r, g: 1 if g.random() < .5 else -1, pol, rng)[0] == "pass" for _ in range(20)]) for s in starts])
            for rule, sg in (("FOLLOW", 1), ("FADE", -1)):
                fn = lambda r, g, sg=sg: 0 if r["move"] == 0 else int(sg * np.sign(r["move"]))
                res = np.array([R.run_window(recs, s, 57, fn, pol, rng)[0] == "pass" for s in starts], dtype=float)
                ok = (df.move != 0) & (df.real != 0)
                hit = float((sg * np.sign(df.move[ok]) == df.real[ok]).mean())
                out[f"{sym}|{name}|{rule}"] = dict(n=int(ok.sum()), hit=hit, P=float(res.mean()), coin=float(coin.mean()),
                                                   uplift=float(res.mean() - coin.mean()), up_2020_22=float(res[half].mean() - coin[half].mean()),
                                                   up_2023_26=float(res[~half].mean() - coin[~half].mean()))
            print(sym, name, {r: (round(out[f"{sym}|{name}|{r}"]["hit"] * 100, 1), round(out[f"{sym}|{name}|{r}"]["P"] * 100, 1), round(out[f"{sym}|{name}|{r}"]["coin"] * 100, 1)) for r in ("FOLLOW", "FADE")}, flush=True)
    if dry: return
    cand = []
    for name in TS:
        for rule in ("FOLLOW", "FADE"):
            a, b_ = out[f"NQ|{name}|{rule}"], out[f"ES|{name}|{rule}"]
            ok = all(x["hit"] >= 0.53 and x["uplift"] >= 0.08 and x["up_2020_22"] > 0 and x["up_2023_26"] > 0 for x in (a, b_))
            out[f"cand|{name}|{rule}"] = bool(ok)
            if ok: cand.append((name, rule))
    print("candidates:", cand)
    json.dump(out, open(R.result_path(HERE, "round324_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
