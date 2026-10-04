"""
Round 333 (2026-10-03, PRE-REGISTERED; ONE ledger row, k + 1): day-level paired test of "follow the opening drive at 10:30" on the MT5 broker indices it was not found on (US30.cash, US2000.cash), plus reported rows.

Why this round exists (disclosed): Round 332 tested the same lead with 57-day pass probabilities (about 20 independent windows, +/-10 points of noise) and did NOT confirm it on US30 / US2000 (+2.6 / +6.8 points over the same-time coin). That statistic was too noisy to
refute a modest effect. The right statistic is day-level: on every session compare the R of the FOLLOW side with the R of the opposite side. This is a second test of one hypothesis after a failed first one: it is counted in k and the bar is Bonferroni-adjusted for two attempts.
Effect size on the indices the lead came from (MT5 US100 / US500, real fills, 1,209 / 1,207 sessions, Round 324 day tables; looked at before writing this): excess of FOLLOW over the coin = 0.5 x (R_follow - R_opposite) averages +0.06-0.09 R (US100) and +0.05-0.06 R (US500)
per trade at every table target multiple k, t about 1.3-2.6. Neither of these is the confirmation sample.

DATA / MECHANICS: MT5 M1 bid/ask, real fills (ROUND_DATA=mt5broker, ROUND_FILLS=ask, set by the script), Round 324's day_table_T at T = 10:30: stop 0.25 x the mean RTH range of the last 20 sessions, target k x stop with k in (1.5, 2.5, 4, 6, 9), stop wins a tie, exit 15:59, slippage 1.0 / 0.5 point scaled.
DAILY STATISTIC (fixed): s = sign(10:30 bar open - 09:30 open) (days with s = 0 dropped); R_follow = R of the side s; R_opp = R of the side -s; excess_k = 0.5 (R_follow - R_opp) = R_follow - the coin's expected R; EXCESS = the mean over the five k of excess_k (no k is selected).
TEST SAMPLE (counted): US30.cash + US2000.cash pooled (one row per instrument-day, clustered by date). Reported, not counted: US100, US500 (found-on), XAUUSD (a different asset, same rule).
CANDIDATE (fixed now): pooled EXCESS > +0.02 R AND date-clustered bootstrap P(EXCESS > 0) >= 1 - 0.05/2 = 0.975 (5,000 draws, seed 333) AND positive in both halves (before / from 2024-01-01). Not widened after the run: no other time, rule, k, or instrument.
POWER (honest): sd of daily excess about 1.1-1.3 R; the YM and RTY days are highly correlated, so the effective sample is about 1,150-1,200 dates and the s.e. of the pooled mean is about 0.035 R. To reach P >= 0.975 the pooled mean must be about +0.07 R, the TOP of the found-on range: a pass is strong evidence;
a miss is INCONCLUSIVE, not a refutation (the test cannot see an effect of +0.03 R, which is what a graded Nasdaq > Dow / Russell effect would look like).
DRY-RUN COUNTS (days only, no excess R of the test sample printed): US30.cash 1,207 days from 2021-10-29 (529 before 2024, 678 from 2024); US2000.cash 1,141 days from 2022-02-08 (464 / 677); US100.cash 1,209; US500.cash 1,207; XAUUSD 1,211 (reported-only rows).
The US30 / US2000 pass probabilities of Round 332 were seen before this round was written (disclosed); their day-level excess R had not been computed.
"""
import os, sys, json
os.environ["ROUND_DATA"] = "mt5broker"; os.environ["ROUND_FILLS"] = "ask"
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", ".."))
import round321_long_bias_bold_play as R
import round324_post_open_drive_entry as Q

T = Q.TS["1030"]; SPLIT = pd.Timestamp("2024-01-01"); KS = R.KS
NAME = {"YM": "US30.cash", "RTY": "US2000.cash", "NQ": "US100.cash", "ES": "US500.cash", "GC": "XAUUSD"}


def daily_excess(sym):
    df = Q.day_table_T(sym, T); df = df[df.move != 0]
    s = np.sign(df.move.values)
    ex = []
    for k in KS:
        Rl, Rs = df[f"R_1_{k}"].values, df[f"R_-1_{k}"].values
        ex.append(0.5 * (np.where(s > 0, Rl, Rs) - np.where(s > 0, Rs, Rl)))
    return pd.DataFrame({"date": df.index, "excess": np.mean(ex, axis=0), "sym": sym})


def boot(x, rng):
    g = x.groupby("date")["excess"].agg(["sum", "count"])
    idx = rng.integers(0, len(g), (5000, len(g)))
    m = g["sum"].values[idx].sum(1) / g["count"].values[idx].sum(1)
    return float(x.excess.mean()), float((m > 0).mean())


def main(dry):
    rng = np.random.default_rng(333); rows = {s: daily_excess(s) for s in NAME}
    if dry:
        for s, d in rows.items():
            print(f"{NAME[s]}: {len(d)} days from {d.date.min().date()} to {d.date.max().date()}, before 2024 {(d.date < SPLIT).sum()}, from 2024 {(d.date >= SPLIT).sum()}")
        return
    out = {}
    for label, syms in (("TEST US30+US2000", ("YM", "RTY")), ("found-on US100+US500", ("NQ", "ES")), ("US30", ("YM",)), ("US2000", ("RTY",)), ("US100", ("NQ",)), ("US500", ("ES",)), ("XAUUSD", ("GC",))):
        x = pd.concat([rows[s] for s in syms]); a, b = x[x.date < SPLIT], x[x.date >= SPLIT]
        m, p = boot(x, rng); ma, _ = boot(a, rng) if len(a) else (float("nan"), 0); mb, _ = boot(b, rng)
        out[label] = dict(n=len(x), excess_R=m, P=p, first_half=ma, second_half=mb, sd=float(x.excess.std()))
        print(label, {k: round(v, 3) if isinstance(v, float) else v for k, v in out[label].items()})
    t = out["TEST US30+US2000"]
    out["CONFIRMED"] = bool(t["excess_R"] > 0.02 and t["P"] >= 0.975 and t["first_half"] > 0 and t["second_half"] > 0)
    print("CONFIRMED:", out["CONFIRMED"])
    json.dump(out, open(os.path.join(HERE, "round333_results_mt5broker_ask.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
