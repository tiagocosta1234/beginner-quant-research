"""
Round 329 (2026-10-03, PRE-REGISTERED, DESCRIPTIVE -- no ledger row, k stays 2031): does adding the two sparse leads (daily dip reversal, pre-FOMC drift) as OVERLAY tickets lift the deployed 1-Step table's pass probability?

Standing goal: beat the coin-flip bold play (about 40% pass in 57 trading days). The table trades every day with a coin-flip direction; the leads are sparse, independent-ish and positive: dip reversal (+35 bp a trade, about 20 a year; Rounds 285-305),
pre-FOMC drift (+31 bp, 8 a year; Round 328). Overlay = on those days an extra ticket in the lead's direction, sized from its own stop, on top of the table's ticket. Round 322 says +1 point of direction accuracy is about +2.8 points of
pass probability; the overlays touch only about 30 days a year, so the expected lift is small; this round measures it instead of guessing.

PATH PROXY (Round 321, unchanged): NQ and ES 2020-2026 09:30 sessions as US100 proxy, table = forex/onestep.py Policy round275 risk $1,000, Round 321 costs, every start day, 57-day window, 20 coin draws per start for the table.
OVERLAY TICKETS (rules fixed now; the daily bars are the same instrument's RTH closes, the FOMC trade uses the Globex 1-minute bars):
  DIP: after a session close with z3 <= -2 (3-day log return / (60-session sigma x sqrt 3), Monday-Thursday), long at that close, exit at the NEXT session close; stop = 2 sigma below the entry; R = max(return / (2 x sigma_daily), -1) (a stop fills at its level: optimistic, no gap-through) minus
  a cost of 1 bp / (2 x sigma_daily); risk = min($1,000, 0.5 x room to the nearer floor), skipped under $250; the P&L is booked on the exit session.
  FOMC: long at the 14:00 ET bar open the trading day before a scheduled FOMC statement, exit at the 13:59 close on the statement day; stop = 150 bp below the entry; R = max(return / 150 bp, -1) minus 1 bp / 150 bp; same risk rule; booked on the statement day.
VARIANTS (4): TABLE (coin only; Round 321 COIN), TABLE+DIP, TABLE+FOMC, TABLE+BOTH; OVERLAY_ONLY (no table) is reported as a control.
DECISION RULE (fixed now): the overlay 'beats the current best' only if TABLE+BOTH exceeds TABLE by >= 8 points of 57-day pass probability on BOTH NQ and ES AND OVERLAY_ONLY alone is not what carries it (OVERLAY_ONLY pass probability < TABLE+BOTH - TABLE). Overlapping windows
are autocorrelated (about 28 independent windows): a +/-10 point difference is noise, so the pairing on identical paths and draws is what makes a small lift readable. Not widened after the run.
DRY-RUN COUNTS (no pass probability): NQ 1,635 sessions with 27 DIP overlay signals (Monday-Thursday, z3 <= -2 at the session close) and 49 FOMC overlay signals; ES 1,649 sessions, 36 DIP and 51 FOMC signals. A floor bug was found by reading
before any P&L (the first draft recomputed the daily floor from the updated balance, so it could never bind); the daily floor is now fixed from the day-start balance, as in the real rules and in Round 321.
POWER: the overlays add about 12-15 tickets a year to about 250 table tickets; at +0.2 R each the added drift over 57 days is about +0.4% of the balance, worth roughly +3 points of pass probability by Round 322's curve, which is below the
+8 point bar: the pre-registered expectation is a null result; the round exists to measure it.
"""
import os, sys, json
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import round321_long_bias_bold_play as R
import round328_pre_fomc_drift as F
from mt5 import onestep as OS


def overlays(sym, df):
    """df = R.day_table(sym) (index = session dates). Returns dict date -> list of (booking_date, R_multiple) and the signal count."""
    b = R.load(sym)
    g = b.groupby(b.index.normalize())
    close = g.c.last().reindex(df.index)
    ret = np.log(close).diff(); sig = ret.rolling(60).std().shift(1)
    z3 = np.log(close / close.shift(3)) / (sig * np.sqrt(3))
    dates = list(df.index)
    out = {}
    nd = 0
    for i in range(len(dates) - 1):
        d, d1 = dates[i], dates[i + 1]
        if z3.get(d, np.nan) <= -2 and d.dayofweek <= 3 and np.isfinite(sig.get(d, np.nan)):
            r = close[d1] / close[d] - 1
            s2 = 2 * sig[d]
            Rm = max(r / s2, -1.0) - 1e-4 / s2
            out.setdefault(("DIP", d), []).append((d1, Rm)); nd += 1
    full = F.bars(sym)
    days = pd.DatetimeIndex(sorted(set(full.index.normalize())))
    nf = 0
    for fd in F.fomc_dates():
        if fd not in df.index or fd not in days:
            continue
        prev = days[days < fd][-1]
        tin, tout = prev + pd.Timedelta(hours=14), fd + pd.Timedelta(hours=13, minutes=59)
        if tin in full.index and tout in full.index:
            r = full.c[tout] / full.o[tin] - 1
            Rm = max(r / 0.015, -1.0) - 1e-4 / 0.015
            out.setdefault(("FOMC", fd), []).append((fd, Rm)); nf += 1
    return out, nd, nf


def run(recs, start, h, pol, rng, coin, ov_kinds, ov, dates):
    bal, hwm, pos = OS.INITIAL, OS.INITIAL, []
    pending = {}
    for j in range(start, min(start + h, len(recs))):
        d = dates[j]
        day_start = bal
        hwm = max(hwm, day_start)
        floor = max(hwm - OS.TRAIL, day_start - OS.DAILY_LOSS)       # fixed for the day, as in the real rules
        for amt in pending.pop(d, []):                                  # overlay tickets that exit today
            bal += amt
            if amt > 0: pos.append(amt)
        if bal <= floor + 1e-6:
            return "breach"
        if coin:
            side = 1 if rng.random() < .5 else -1
            risk, k = pol.lookup(j - start, bal, hwm)
            if risk > 0:
                risk = min(risk, OS.MAX_RISK_USD, 0.9 * (bal - floor))
                if risk >= OS.MIN_RISK_USD and risk * k <= OS.MAX_TICKET_PAYOFF:
                    pnl = risk * recs[j][f"R_{side}_{k}"]
                    bal += pnl
                    if pnl > 0: pos.append(pnl)
        for kind in ov_kinds:
            for (bd, Rm) in ov.get((kind, d), []):
                risk = min(OS.MAX_RISK_USD, 0.5 * (bal - floor))
                if risk >= OS.MIN_RISK_USD:
                    if bd == d:
                        bal += risk * Rm
                        if risk * Rm > 0: pos.append(risk * Rm)
                    else:
                        pending.setdefault(bd, []).append(risk * Rm)
        if bal > OS.TARGET and pos and max(pos) <= 0.5 * sum(pos):
            return "pass"
        if bal <= floor + 1e-6:
            return "breach"
    return "open"


def main(dry):
    pol = OS.Policy(); out = {}
    for sym in ("NQ", "ES"):
        df = R.day_table(sym)
        ov, nd, nf = overlays(sym, df)
        if dry:
            print(sym, f"sessions {len(df)}, DIP overlay signals {nd}, FOMC overlay signals {nf}"); continue
        recs = df.reset_index().to_dict("records"); dates = list(df.index)
        starts = range(0, len(recs) - 57)
        half = np.array([dates[s] < pd.Timestamp("2023-01-01") for s in starts])
        for name, coin, kinds in (("TABLE", True, ()), ("TABLE+DIP", True, ("DIP",)), ("TABLE+FOMC", True, ("FOMC",)), ("TABLE+BOTH", True, ("DIP", "FOMC")), ("OVERLAY_ONLY", False, ("DIP", "FOMC"))):
            rng = np.random.default_rng(329)
            reps = 20 if coin else 1
            res = np.array([np.mean([run(recs, s, 57, pol, rng, coin, kinds, ov, dates) == "pass" for _ in range(reps)]) for s in starts])
            out[f"{sym}|{name}"] = dict(P=float(res.mean()), P_2020_22=float(res[half].mean()), P_2023_26=float(res[~half].mean()))
        print(sym, {n: round(out[f"{sym}|{n}"]["P"] * 100, 1) for n in ("TABLE", "TABLE+DIP", "TABLE+FOMC", "TABLE+BOTH", "OVERLAY_ONLY")}, flush=True)
    if not dry:
        json.dump(out, open(R.result_path(HERE, "round329_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
