"""
Round 131: invert the losing strategies.

the trader: "get the worst strategy we have and invert it." Pre-registered -- committed
before any result was run.

Which: every ledger variant with a fixed stop AND a fixed target (so the inverse
is an exact mirror) whose net expectancy was negative: Rounds 124, 125, 125b,
126 (B1/B3 hold-to-close excluded -- no target; B2 half-fill; B4), 127, 128.
26 variants. Not inverted: trailing-stop strategies (Rounds 121, 130) and
hold-to-close ones (Round 129) -- flipping their direction with the same exit is
a different strategy, not a mirror.

How: same signals, same bars, same flat time; direction flipped, stop and target
swapped (the original's target is the inverse's stop). Sized on the inverse's
own stop distance, $300 risk; the stop still wins a tie (conservative both ways).
Each original is first re-run and must reproduce its ledger net/trade (+-$0.15).

Costs are paid on both sides, so inverse net = -(original before-cost) - costs:
only an original that loses BEFORE costs can flip into a winner.

Bar: 26 variants take the ledger from k=66 to k=92; a candidate needs positive
net and before-cost expectancy, IS P(edge>0) >= 0.95, OOS P(edge>0) >= 1 - 0.01/92.
"""
import os, sys, json, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round124_codetrading_scalper as R124
import round126_batch_b as B
import round127_stdv_projection_fade as R127
import round128_hrl_vs_lrl as R128
from round11_fvg_bias import TICK_SIZE

T = dt.time


def judas_signals(days, window_end, target, scale):
    """Round 125's rules (and Round 125b's stop scaling) as signals."""
    tick, out = TICK_SIZE["MNQ"], []
    for d in days:
        on, s = d["on"], d["session"]
        on_hi, on_lo = on["high"].max(), on["low"].min()
        hi, lo, cl, t = s["high"].values, s["low"].values, s["close"].values, s.index.time
        swept_hi = swept_lo = False
        for i in range(len(s) - 1):
            if t[i] > window_end:
                break
            swept_hi |= hi[i] > on_hi
            swept_lo |= lo[i] < on_lo
            if swept_hi and cl[i] < on_hi:
                dd, stop = -1, hi[: i + 1].max() + tick
            elif swept_lo and cl[i] > on_lo:
                dd, stop = 1, lo[: i + 1].min() - tick
            else:
                continue
            dist = abs(cl[i] - stop) * scale
            if dist < 8 * tick:
                continue
            tp = cl[i] + dd * 2 * dist if target == "2R" else (on_lo if dd == -1 else on_hi)
            if dd * (tp - cl[i]) <= 0:
                continue
            out.append((s.index[i], dd, cl[i], cl[i] - dd * dist, tp))
            break
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


def invert(sig):
    return sig.assign(direction=-sig["direction"], sl=sig["tp"], tp=sig["sl"])


if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    mnq_rth = H.load_mnq_rth()
    mnq, mgc = H.load_days("MNQ"), H.load_days("MGC")
    nq_sess, nq_all, gc_all = H.bars_from_days(mnq, "session"), H.bars_from_days(mnq, "all"), H.bars_from_days(mgc, "all")
    nq_days, gc_days = [d["tday"] for d in mnq], [d["tday"] for d in mgc]
    rth_days = mnq_rth.index.normalize().unique()

    def r124(sl, bb):
        s = R124.signals(mnq_rth, sl, bb)
        return s.assign(sl=s["entry"] - s["direction"] * s["dist"], tp=s["entry"] + s["direction"] * 1.5 * s["dist"])

    # (label, ledger net/trade of the original, signal frame, bars, days, symbol, flat_time)
    runs = []
    for (sl, bb), led in zip([(1.1, 1.5), (1.1, 2.0), (1.2, 1.5), (1.2, 2.0)], [-21.8, -14.5, -18.7, -14.3]):
        runs.append((f"R124 scalper SL {sl} BB {bb}", led, r124(sl, bb), mnq_rth, rth_days, "MNQ", None))
    for (w, tg, sc), led in zip([(T(10, 30), "2R", 1.0), (T(10, 30), "opp", 1.0), (T(11, 0), "2R", 1.0), (T(11, 0), "opp", 1.0),
                                 (T(11, 0), "2R", 0.5), (T(11, 0), "2R", 1.5), (T(11, 0), "opp", 0.5), (T(11, 0), "opp", 1.5)],
                                [-24.7, -14.6, -26.0, -8.0, -87.2, -14.7, -49.8, -19.7]):
        runs.append((f"R125 Judas to {w.strftime('%H:%M')} {tg} stop {sc}x", led, judas_signals(mnq, w, tg, sc),
                     nq_sess, nq_days, "MNQ", None))
    for thr, led in [(0.001, -1.4), (0.003, -0.9)]:
        runs.append((f"R126 B2 gap fill {thr:.1%} half", led, B.as_frame(B.gap_signals(mnq, thr, "half")), nq_sess, nq_days, "MNQ", None))
    for (w, sc), led in zip([(T(5, 0), 1.0), (T(5, 0), 1.5), (T(8, 0), 1.0), (T(8, 0), 1.5)], [-53.4, -76.5, -59.3, -74.0]):
        runs.append((f"R126 B4 gold London fade to {w.strftime('%H:%M')} stop {sc}x", led,
                     B.as_frame(B.london_fade_signals(mgc, w, sc)), gc_all, gc_days, "MGC", T(11, 0)))
    for (k, tg), led in zip([(2.0, "1 SD back"), (2.0, "range edge"), (2.5, "1 SD back"), (2.5, "range edge")], [-52.0, -74.8, -22.1, -6.6]):
        runs.append((f"R127 STDV fade {k} SD {tg}", led, R127.stdv_signals(mnq, k, tg), nq_all, nq_days, "MNQ", None))
    for (st, ra), led in zip([("1:1", 1.0), ("1:1", 1.5), ("other level", 1.0), ("other level", 1.5)], [-25.9, -39.6, -12.6, -15.5]):
        runs.append((f"R128 toward LRL stop {st} ratio {ra}", led, R128.signals(mnq, st, ra), nq_sess, nq_days, "MNQ", None))

    k_final = H.ledger_count() + len(runs)
    print(f"{len(runs)} inverted variants; k after this round = {k_final}, bar OOS P >= {H.oos_bar(k_final):.5f}\n")
    rows, mismatches = [], []
    for label, led, sig, bars, days, sym, flat in runs:
        orig = H.resolve_bracket(sig, bars, sym, flat_time=flat)
        if abs(orig["pnl"].mean() - led) > 0.15:
            mismatches.append(f"{label}: re-run ${orig['pnl'].mean():.2f} vs ledger ${led}")
        inv = H.resolve_bracket(invert(sig), bars, sym, flat_time=flat)
        print(f"  (original re-run ${orig['pnl'].mean():+.1f}, ledger ${led:+.1f})", end="")
        rows.append(H.test_idea(f"INVERTED {label}", inv, days, sym, k_final))
    if mismatches:
        print("\nORIGINALS DID NOT REPRODUCE -- results not written:\n  " + "\n  ".join(mismatches))
        sys.exit(1)
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(H.ledger_rows(rows, "Round 131 (inverted losers, pre-registered)", commit)) + "\n")
    with open(os.path.join(H.HERE, "round131_results.json"), "w") as f:
        json.dump(rows, f, indent=1, default=str)
    print(f"\n==== {sum(r['candidate'] for r in rows)} of {len(rows)} inverted variants meet the bar; ledger now k={H.ledger_count()} ====")
