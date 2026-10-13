"""
Round 302 (2026-10-02, PRE-REGISTERED): is there a HIGH-FREQUENCY (seconds-scale) strategy on MT5 broker's US100.cash that survives the real spread and a realistic latency? (the trader: "build a HTF strategy" -- 'HTF is high frequency trading'.)
Step 0 (ledger checked first, k = 1260): 1-minute-and-slower patterns on US index CFDs were tested (Round 290: 0 of 138 always-in-market / event cells; Round 138: 5-minute slots on futures; Round 121: time-series momentum 5-15 min; Round 298: 30-minute slots; Round 301: level rebounds), all no edge. NOT tested: the SUB-MINUTE horizon, on MT5 broker's own tick stream.
WHAT 'HIGH FREQUENCY' CAN MEAN HERE (stated now, so nobody is misled): true HFT (microsecond, co-located, rebate-driven, order-book signals) is impossible on a retail MT5 CFD account: the quote stream updates every ~110 ms, a market order takes ~0.2-0.6 s to fill (the 2026-10-02 probe: 0.2-0.6 s), the spread is ~1.45 points (~0.5 bp) a round trip, and MT5 broker caps automated robots at 2,000 server requests a day
(opening, modifying or closing a trade each count: at most ~1,000 round trips a day) and requires strategies to be 'reasonably replicable in the actual market' (mt5broker.com forbidden-trading-practices page, read 2026-10-02). This round tests the feasible version: a trade every few seconds to minutes, entered with a delay, paying the real bid/ask.
DATA: raw MT5 US100.cash quote ticks (MT5 copy_ticks_range, bid and ask with millisecond stamps, read-only on the demo terminal) for the US cash session 09:30:00-16:00:00 NY on the last ~260 weekdays up to 2026-09-30; days with < 40,000 ticks or no tick after 15:55 NY are dropped (holidays, early closes). IS = the first 60% of the kept days (by date), OOS = the last 40%.
SIGNALS (decided at every whole second s of the session from the last mid-price at or before s; mid = (bid + ask)/2): D_w(s) = mid(s) - mid(s - w), w in (1, 3, 10, 30) seconds. A trade is triggered when |D_w(s)| >= theta, theta in (1.5, 3.0) index points (about 1 and 2 spreads); direction = sign(D_w) for FOLLOW (momentum), the opposite for FADE (reversal).
EXECUTION: entry at the FIRST TICK AT OR AFTER s + L with L = 0.3 s (the measured fill delay), at the ask for a long and the bid for a short; the position is closed at the first tick at or after (entry tick time + h), h in (2, 5, 15, 60) seconds, at the bid for a long and the ask for a short. One position at a time per cell (no new trade until the exit); decisions only until 15:58:00 NY so every exit is inside the session.
Net P&L per trade in points and in bp of the entry mid: long = bid_exit - ask_entry, short = bid_entry - ask_exit; GROSS = mid-to-mid after the same latency (so gross includes the latency drift and excludes only the spread). Cells: 4 x 2 x 4 x 2 = 64 hypotheses; K_TOTAL = 1260 + 64 = 1324.
STATISTICS: per cell and half (IS / OOS): trades, trades per day, mean net bp, mean gross bp, win rate, and a day-clustered bootstrap P(mean net per trade > 0) (4,000 draws, seed 3021: resample days, mean = sum of net / number of trades). CANDIDATE (the repo's rule): IS P >= 0.95 AND OOS P >= 1 - 0.01/1324 AND OOS mean net > 0 AND OOS trades >= 1,000, plus Benjamini-Hochberg q = 0.10 over the 64 OOS one-sided p-values. USABLE: a candidate also needs
<= 1,000 trades per day on average (the 2,000-request cap, one open and one close each) and an OOS net mean >= 0.3 bp (the positive margin that survives the 1.0 s latency check below).
LATENCY CHECK (descriptive, not hypotheses): the best IS cell (by IS mean net) and every candidate are re-run with L = 1.0 s; the OOS mean net must stay > 0 for the cell to count as robust to latency.
PRIOR (stated now): no candidate. At a spread of ~0.5 bp the best a 1-10-second pattern can do is gross +0.1-0.3 bp of drift (short-horizon quote momentum from the feed's own update lag is the plausible source); with the spread and 0.3 s of latency the net should be below zero in every cell, and most negative for FADE. Any positive cell would most likely be FOLLOW at w = 1-3 s and h = 2-5 s, where the feed's stepwise quote updates could create a few-tenths-of-a-point drift; that drift is
what a faster fill or another broker's quote would erase, and it is not replicable at 0.3 s of latency.
POWER_NOTES: ~100 sessions OOS with hundreds of trades a day give a standard error of ~0.02-0.05 bp per cell; a net mean above ~0.1 bp would be detectable. Quote-driven CFD prices are set by the broker's own feed, so a tick-level pattern may be a feature of the feed, not of the market (MT5 broker may treat quote-feed exploitation as latency arbitrage; no judgement is made here). One instrument and one year of ticks.
"""
import os, sys, json, time, datetime as dt, warnings
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
warnings.filterwarnings("ignore")
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

SYMBOL = "US100.cash"
NY = ZoneInfo("America/New_York")
CACHE = os.path.join(os.environ.get("TEMP", "."), "r302_ticks")
FIRST, LAST = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-09-30")
WS, THETAS, HS, MODES = (1, 3, 10, 30), (1.5, 3.0), (2, 5, 15, 60), ("follow", "fade")
L_MAIN, L_ALT = 0.3, 1.0
K_TOTAL, BOOT, SEED, IS_FRAC = 1324, 4000, 3021, 0.6
OPEN_S, CLOSE_S, LAST_DECISION_S = 9 * 3600 + 30 * 60, 16 * 3600, 15 * 3600 + 58 * 60
CELLS = [(w, th, h, m) for w in WS for th in THETAS for h in HS for m in MODES]


def window_utc(day):
    a = dt.datetime(day.year, day.month, day.day, 9, 30, tzinfo=NY).astimezone(dt.timezone.utc).replace(tzinfo=None)
    b = dt.datetime(day.year, day.month, day.day, 16, 0, tzinfo=NY).astimezone(dt.timezone.utc).replace(tzinfo=None)
    return a, b


def pull():
    from forex.data_pull import attach
    os.makedirs(CACHE, exist_ok=True)
    mt5 = attach()
    kept = []
    try:
        for d in pd.bdate_range(FIRST, LAST):
            f = os.path.join(CACHE, f"{d:%Y%m%d}.npz")
            if os.path.exists(f):
                continue
            a, b = window_utc(d)
            # tz-aware UTC stamps: the MT5 API reads NAIVE datetimes as the PC's local time (this PC is on London time, so a naive window was one hour early in summer; found by the dry-run alignment check)
            t = mt5.copy_ticks_range(SYMBOL, a.replace(tzinfo=dt.timezone.utc), b.replace(tzinfo=dt.timezone.utc), mt5.COPY_TICKS_ALL)
            if t is None or len(t) < 1000:
                np.savez_compressed(f, empty=np.array([1]))
                continue
            np.savez_compressed(f, t=np.asarray(t["time_msc"], dtype=np.int64), bid=np.asarray(t["bid"], dtype=np.float64), ask=np.asarray(t["ask"], dtype=np.float64))
    finally:
        mt5.shutdown()


def load_days():
    out = {}
    for d in pd.bdate_range(FIRST, LAST):
        f = os.path.join(CACHE, f"{d:%Y%m%d}.npz")
        if not os.path.exists(f):
            continue
        z = np.load(f)
        if "empty" in z.files:
            continue
        t, bid, ask = z["t"], z["bid"], z["ask"]
        a, b = window_utc(d)
        a_ms = int((a - dt.datetime(1970, 1, 1)).total_seconds() * 1000)
        sec = (t - a_ms) / 1000.0 + OPEN_S                           # seconds since NY midnight
        ok = (ask > bid) & (bid > 0)
        t, bid, ask, sec = t[ok], bid[ok], ask[ok], sec[ok]
        if len(t) < 40_000 or sec[-1] < 15 * 3600 + 55 * 60:
            continue
        out[d] = dict(sec=sec, bid=bid, ask=ask)
    return out


def day_cells(D, L):
    """Per cell: (trades, sum net pts, sum net bp, sum gross bp, wins) for one day."""
    sec, bid, ask = D["sec"], D["bid"], D["ask"]
    mid = (bid + ask) / 2.0
    grid = np.arange(OPEN_S, LAST_DECISION_S + 1, 1.0)
    idx_at = np.searchsorted(sec, grid, side="right") - 1                 # last tick at or before each second
    res = np.zeros((len(CELLS), 5))
    for w in WS:
        prev = np.searchsorted(sec, grid - w, side="right") - 1
        valid = (prev >= 0) & (idx_at >= 0)
        dlt = np.where(valid, mid[np.maximum(idx_at, 0)] - mid[np.maximum(prev, 0)], 0.0)
        for th in THETAS:
            cand = np.flatnonzero(np.abs(dlt) >= th)
            if cand.size == 0:
                continue
            ent_i = np.searchsorted(sec, grid[cand] + L, side="left")       # first tick at or after s + L
            for h in HS:
                for m in MODES:
                    ci = CELLS.index((w, th, h, m))
                    free_until = -1.0
                    n = pn = bp = gb = wins = 0
                    for j, k in enumerate(cand):
                        if grid[k] < free_until:
                            continue
                        e = ent_i[j]
                        if e >= len(sec):
                            break
                        x = np.searchsorted(sec, sec[e] + h, side="left")
                        if x >= len(sec):
                            continue
                        s = np.sign(dlt[k]) * (1.0 if m == "follow" else -1.0)
                        if s > 0:
                            net = bid[x] - ask[e]
                        else:
                            net = bid[e] - ask[x]
                        gross = s * (mid[x] - mid[e])
                        em = mid[e]
                        n += 1; pn += net; bp += net / em * 1e4; gb += gross / em * 1e4; wins += net > 0
                        free_until = sec[x]
                    res[ci] = (n, pn, bp, gb, wins)
    return res


def pboot(sum_bp, n, rng):
    """Day-clustered bootstrap P(mean net per trade > 0): sum_bp, n are per-day arrays."""
    nd = len(n)
    idx = rng.integers(0, nd, (BOOT, nd))
    num = sum_bp[idx].sum(axis=1)
    den = n[idx].sum(axis=1)
    return float((num / np.maximum(den, 1) > 0).mean())


def dry_run():
    days = load_days()
    print(f"{len(days)} usable session days in the cache ({min(days):%Y-%m-%d} .. {max(days):%Y-%m-%d})")
    off = {d: (D["sec"][0] - OPEN_S, D["sec"][-1] - CLOSE_S) for d, D in days.items()}
    outside = [d for d, (a, b) in off.items() if a < -0.5 or b > 0.5]
    late = [d for d, (a, b) in off.items() if a > 2.0 or b < -2.0]
    assert not outside, f"ticks outside the 09:30:00-16:00:00 NY window on {outside[:3]}"
    assert all(off[d][0] < 60 and off[d][1] > -60 for d in days), "a kept day starts or ends more than a minute from the session edge"
    print(f"alignment: no tick outside 09:30:00-16:00:00 NY on any of {len(days)} days; {len(late)} days start or end 2-60 s inside the window (quiet edges): " + ", ".join(f"{d:%Y-%m-%d} ({off[d][0]:+.0f}s/{off[d][1]:+.0f}s)" for d in late))
    ks = sorted(days)[:: max(1, len(days) // 6)]
    for d in ks:
        D = days[d]
        gaps = np.diff(D["sec"]) * 1000
        sp = D["ask"] - D["bid"]
        print(f"   {d:%Y-%m-%d}: {len(D['sec']):,} ticks, median gap {np.median(gaps):.0f} ms, mean spread {sp.mean():.2f} pts (median {np.median(sp):.2f}, max {sp.max():.2f}), first {D['sec'][0] - OPEN_S:+.1f}s last {D['sec'][-1] - 15 * 3600 - 59 * 60:+.1f}s")
    # logic tests on a synthetic day: a +3 point jump at second 100 followed by a continuing drift
    sec = OPEN_S + (np.arange(6000) * 100) / 1000.0                  # integer-millisecond stamps, like the real data (no 0.1-step float drift)
    mid = np.full(len(sec), 20000.0)
    mid[sec >= OPEN_S + 100] += 3.0
    mid[sec >= OPEN_S + 101] += 3.0
    D = dict(sec=sec, bid=mid - 0.7, ask=mid + 0.7)
    saved = globals()["LAST_DECISION_S"]
    globals()["LAST_DECISION_S"] = OPEN_S + 500
    try:
        r = day_cells(D, 0.3)
    finally:
        globals()["LAST_DECISION_S"] = saved
    ci = CELLS.index((1, 3.0, 2, "follow"))
    assert r[ci][0] >= 1 and r[ci][1] > 0, r[ci]                      # a follow after the first jump gains the second jump (3 points) minus the spread (1.4)
    ci2 = CELLS.index((1, 3.0, 2, "fade"))
    assert r[ci2][1] < 0, r[ci2]
    print(f"synthetic jump test passed: follow {r[ci][1] / max(r[ci][0], 1):+.2f} pts per trade, fade {r[ci2][1] / max(r[ci2][0], 1):+.2f}")
    # causality: signals at second s must not change if every tick after s is removed
    d0 = days[ks[0]]
    s_test = OPEN_S + 3600
    i = np.searchsorted(d0["sec"], s_test, side="right") - 1
    j = np.searchsorted(d0["sec"], s_test - 3, side="right") - 1
    full = (d0["bid"][i] + d0["ask"][i]) / 2 - (d0["bid"][j] + d0["ask"][j]) / 2
    cut = {k: v[: i + 1] for k, v in d0.items()}
    i2 = np.searchsorted(cut["sec"], s_test, side="right") - 1
    j2 = np.searchsorted(cut["sec"], s_test - 3, side="right") - 1
    part = (cut["bid"][i2] + cut["ask"][i2]) / 2 - (cut["bid"][j2] + cut["ask"][j2]) / 2
    assert abs(full - part) < 1e-12
    print("causality: the 3-second signal at 10:30:00 is unchanged when every later tick is removed")
    t0 = time.time()
    day_cells(days[ks[0]], L_MAIN)
    print(f"one day over 64 cells in {time.time() - t0:.1f}s (results not printed)")
    print("DRY RUN OK")


def main():
    if "--pull" in sys.argv:
        t0 = time.time(); pull(); print(f"pulled/cached ({time.time() - t0:.0f}s)"); return
    if "--dry-run" in sys.argv:
        dry_run(); return
    t0 = time.time()
    days = load_days()
    keys = sorted(days)
    n_is = int(round(IS_FRAC * len(keys)))
    is_keys, oos_keys = keys[:n_is], keys[n_is:]
    print(f"{len(keys)} days: IS {len(is_keys)} ({is_keys[0]:%Y-%m-%d}..{is_keys[-1]:%Y-%m-%d}), OOS {len(oos_keys)} ({oos_keys[0]:%Y-%m-%d}..{oos_keys[-1]:%Y-%m-%d})", flush=True)
    R = {}
    for L in (L_MAIN, L_ALT):
        R[L] = np.stack([day_cells(days[d], L) for d in keys])           # (days, cells, 5)
        print(f"L = {L}s done ({time.time() - t0:.0f}s)", flush=True)
    rng = np.random.default_rng(SEED)
    ii, oo = np.arange(len(keys)) < n_is, np.arange(len(keys)) >= n_is
    rows = []
    for ci, (w, th, h, m) in enumerate(CELLS):
        row = dict(w=w, theta=th, h=h, mode=m)
        for name, msk in (("IS", ii), ("OOS", oo)):
            a = R[L_MAIN][msk][:, ci, :]
            n = a[:, 0]
            row[name] = dict(trades=int(n.sum()), per_day=float(n.mean()), net_bp=float(a[:, 2].sum() / max(n.sum(), 1)), gross_bp=float(a[:, 3].sum() / max(n.sum(), 1)), win=float(a[:, 4].sum() / max(n.sum(), 1)),
                             net_pts=float(a[:, 1].sum() / max(n.sum(), 1)), P=pboot(a[:, 2], n, rng))
            b = R[L_ALT][msk][:, ci, :]
            row[name]["net_bp_L1"] = float(b[:, 2].sum() / max(b[:, 0].sum(), 1))
        rows.append(row)
    # BH over the 64 OOS one-sided p-values
    ps = np.array([max(1.0 - r["OOS"]["P"], 1.0 / BOOT) for r in rows])
    order = np.argsort(ps)
    thr = 0.0
    for rank, i in enumerate(order, 1):
        if ps[i] <= 0.10 * rank / len(rows):
            thr = max(thr, ps[i])
    for r, p in zip(rows, ps):
        r["p_oos"] = float(p)
        r["bh"] = bool(thr > 0 and p <= thr)
        r["candidate"] = bool(r["IS"]["P"] >= 0.95 and r["OOS"]["P"] >= 1 - 0.01 / K_TOTAL and r["OOS"]["net_bp"] > 0 and r["OOS"]["trades"] >= 1000 and r["bh"])
        r["usable"] = bool(r["candidate"] and r["OOS"]["per_day"] <= 1000 and r["OOS"]["net_bp"] >= 0.3 and r["OOS"]["net_bp_L1"] > 0)
    cand = [r for r in rows if r["candidate"]]
    print(f"{len(rows)} cells; IS P >= 0.95: {sum(r['IS']['P'] >= 0.95 for r in rows)}; positive OOS net: {sum(r['OOS']['net_bp'] > 0 for r in rows)}; positive OOS gross: {sum(r['OOS']['gross_bp'] > 0 for r in rows)}; CANDIDATES {len(cand)}; usable {sum(r['usable'] for r in rows)}")
    for r in sorted(rows, key=lambda r: -r["OOS"]["net_bp"])[:8]:
        print(f"   w {r['w']:>2}s th {r['theta']:.1f} h {r['h']:>2}s {r['mode']:>6} | IS n {r['IS']['trades']:>6} net {r['IS']['net_bp']:+.2f} gross {r['IS']['gross_bp']:+.2f} P {r['IS']['P']:.2f} | OOS n {r['OOS']['trades']:>6} ({r['OOS']['per_day']:.0f}/day) net {r['OOS']['net_bp']:+.2f} gross {r['OOS']['gross_bp']:+.2f} P {r['OOS']['P']:.3f} | OOS net at L=1s {r['OOS']['net_bp_L1']:+.2f}")
    fo = [r for r in rows if r["mode"] == "follow"]; fa = [r for r in rows if r["mode"] == "fade"]
    print(f"mean OOS net bp: follow {np.mean([r['OOS']['net_bp'] for r in fo]):+.2f}, fade {np.mean([r['OOS']['net_bp'] for r in fa]):+.2f}; mean OOS gross bp: follow {np.mean([r['OOS']['gross_bp'] for r in fo]):+.2f}, fade {np.mean([r['OOS']['gross_bp'] for r in fa]):+.2f}")
    json.dump(dict(days=len(keys), n_is=len(is_keys), n_oos=len(oos_keys), rows=rows, candidates=len(cand)), open(os.path.join(HERE, "round302_results.json"), "w"), indent=1, default=float)
    print(f"Saved round302_results.json ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
