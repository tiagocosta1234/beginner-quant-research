"""
Round 126, batch B: four session-structure ideas never tested with honest exits.
Pre-registered 2026-09-26 -- rules, variants and the bar are committed before any
result is run. All are legal inside Broker's trading day (entries after the
18:00 ET reopen, flat before the 16:10 ET cutoff). Tested through idea_harness
(24-hour contract files, one contract per day, $300 risk, commission + 2 ticks,
stop wins a tie).

Bars are stamped at their close: the 09:30 bar is the last pre-market minute, the
16:00 bar the last RTH minute.

B1  Opening-range breakout, MNQ. Range = bars (09:30, 09:30+N]. From then to
    12:00, the first close above the range high -> long at that close (below the
    low -> short). Stop = the other side of the range. Flat at 16:00.
    Variants: N in {15, 30} min x exit in {2R target, hold to the close}.
B2  Overnight gap fill, MNQ. Gap = the 09:30 bar's close (the open) minus the same
    contract's previous 16:00 close. If |gap| >= THR of price, fade it at the
    09:30 bar's close: target = previous close (full fill) or half the gap;
    stop = 1 x gap beyond entry. Flat at 16:00.
    Variants: THR in {0.1%, 0.3%} x target in {full, half}.
B3  Gold London-open breakout, MGC. Asian range = bars (18:00, 02:00]. Between
    02:00 and 05:00, the first close above the Asian high -> long (below the low
    -> short). Stop = the other side of the range, or its midpoint. Flat at 11:00.
    Variants: stop in {other side, midpoint} x exit in {2R, hold to 11:00}.
B4  Gold London sweep-and-reclaim fade, MGC. Same Asian range. Between 02:00 and
    W, price trades beyond the Asian high and a bar closes back below it -> short
    at that close (mirror at the low); stop = the extreme since 02:00 + 1 tick,
    scaled by S; target = the Asian midpoint. First valid setup per day. Flat at 11:00.
    Variants: W in {05:00, 08:00} x S in {1.0, 1.5}.

Every setup needs a stop of at least 8 ticks. One trade per day per variant.

Bar (plan of 2026-09-26): 16 variants take the ledger from k=35 to k=51, so a
variant is a candidate only if net and before-cost expectancy are both > 0, IS
P(edge>0) >= 0.95 and OOS P(edge>0) >= 1 - 0.01/51 = 0.9998.
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
from round11_fvg_bias import TICK_SIZE

MIN_STOP_TICKS = 8
T = dt.time


def orb_signals(days, minutes, target):
    tick, out = TICK_SIZE["MNQ"], []
    end_or = (dt.datetime.combine(dt.date.today(), T(9, 30)) + dt.timedelta(minutes=minutes)).time()
    for d in days:
        s = d["session"]
        t = s.index.time
        rng = s[(t > T(9, 30)) & (t <= end_or)]
        if len(rng) < minutes * 0.8:
            continue
        hi_, lo_ = rng["high"].max(), rng["low"].min()
        win = s[(t > end_or) & (t <= T(12, 0))]
        for ts, c in win["close"].items():
            dd = 1 if c > hi_ else -1 if c < lo_ else 0
            if dd == 0:
                continue
            sl = lo_ if dd == 1 else hi_
            dist = abs(c - sl)
            if dist >= MIN_STOP_TICKS * tick:
                out.append((d["tday"], ts, dd, c, sl, c + dd * 2 * dist if target == "2R" else np.nan))
            break
    return out


def gap_signals(days, thr, target):
    tick, out = TICK_SIZE["MNQ"], []
    for d in days:
        s, pc = d["session"], d["prev_close"]
        first = s[s.index.time == T(9, 30)]
        if np.isnan(pc) or first.empty:
            continue
        ts, entry = first.index[0], float(first["close"].iloc[0])
        gap = entry - pc
        if abs(gap) < thr * pc:
            continue
        dd = -int(np.sign(gap))
        sl = entry + np.sign(gap) * abs(gap)
        tp = pc if target == "full" else pc + gap / 2
        if abs(entry - sl) >= MIN_STOP_TICKS * tick:
            out.append((d["tday"], ts, dd, entry, sl, tp))
    return out


def asian_range(on):
    t = on.index.time
    a = on[(t > T(18, 0)) | (t <= T(2, 0))]
    return (a["high"].max(), a["low"].min()) if len(a) >= 300 else (np.nan, np.nan)


def london_breakout_signals(days, stop, target):
    tick, out = TICK_SIZE["MGC"], []
    for d in days:
        on = d["on"]
        hi_, lo_ = asian_range(on)
        if np.isnan(hi_):
            continue
        t = on.index.time
        win = on[(t > T(2, 0)) & (t <= T(5, 0))]
        for ts, c in win["close"].items():
            dd = 1 if c > hi_ else -1 if c < lo_ else 0
            if dd == 0:
                continue
            sl = ((lo_ if dd == 1 else hi_) if stop == "other side" else (hi_ + lo_) / 2)
            dist = dd * (c - sl)
            if dist >= MIN_STOP_TICKS * tick:
                out.append((d["tday"], ts, dd, c, sl, c + dd * 2 * dist if target == "2R" else np.nan))
            break
    return out


def london_fade_signals(days, window_end, scale):
    tick, out = TICK_SIZE["MGC"], []
    for d in days:
        on = d["on"]
        hi_, lo_ = asian_range(on)
        if np.isnan(hi_):
            continue
        mid = (hi_ + lo_) / 2
        t = on.index.time
        win = on[(t > T(2, 0)) & (t <= window_end)]
        h, l, c, idx = win["high"].values, win["low"].values, win["close"].values, win.index
        swept_hi = swept_lo = False
        for i in range(len(win)):
            swept_hi |= h[i] > hi_
            swept_lo |= l[i] < lo_
            if swept_hi and c[i] < hi_:
                dd, ext = -1, h[: i + 1].max() + tick
            elif swept_lo and c[i] > lo_:
                dd, ext = 1, l[: i + 1].min() - tick
            else:
                continue
            dist = abs(c[i] - ext) * scale
            if dist < MIN_STOP_TICKS * tick or dd * (mid - c[i]) <= 0:
                continue
            out.append((d["tday"], idx[i], dd, c[i], c[i] - dd * dist, mid))
            break
    return out


def as_frame(rows):
    return pd.DataFrame([r[1:] for r in rows], columns=["ts", "direction", "entry", "sl", "tp"])


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    k_final = H.ledger_count() + 16
    mnq, mgc = H.load_days("MNQ"), H.load_days("MGC")
    mnq_bars, mgc_bars = H.bars_from_days(mnq, "session"), H.bars_from_days(mgc, "all")
    mnq_days, mgc_days = [d["tday"] for d in mnq], [d["tday"] for d in mgc]
    print(f"MNQ {len(mnq)} days {mnq_days[0].date()}..{mnq_days[-1].date()}, MGC {len(mgc)} days "
          f"{mgc_days[0].date()}..{mgc_days[-1].date()}; k after this batch = {k_final}\n")
    runs = []
    for m in [15, 30]:
        for tg in ["2R", "hold to close"]:
            runs.append((f"B1 MNQ opening-range breakout, {m}-min range, {tg}", "MNQ", orb_signals(mnq, m, tg), None))
    for thr in [0.001, 0.003]:
        for tg in ["full", "half"]:
            runs.append((f"B2 MNQ gap fill, gap >= {thr:.1%}, {tg} fill target", "MNQ", gap_signals(mnq, thr, tg), None))
    for st in ["other side", "midpoint"]:
        for tg in ["2R", "hold to 11:00"]:
            runs.append((f"B3 MGC London breakout, stop {st}, {tg}", "MGC", london_breakout_signals(mgc, st, tg), T(11, 0)))
    for w in [T(5, 0), T(8, 0)]:
        for sc in [1.0, 1.5]:
            runs.append((f"B4 MGC London sweep fade, to {w.strftime('%H:%M')}, stop {sc}x", "MGC",
                         london_fade_signals(mgc, w, sc), T(11, 0)))
    rows = []
    for name, sym, sig, flat in runs:
        bars, days = (mnq_bars, mnq_days) if sym == "MNQ" else (mgc_bars, mgc_days)
        tr = H.resolve_bracket(as_frame(sig), bars, sym, flat_time=flat)
        rows.append(H.test_idea(name, tr, days, sym, k_final))
    lines = H.ledger_rows(rows, "Round 126 batch B (pre-registered)", commit)
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(H.HERE, "round126_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} variants meet the bar "
          f"(OOS P >= {H.oos_bar(k_final):.4f}); ledger now k={H.ledger_count()} ====")
