"""
Round 344 (2026-10-04, PRE-REGISTERED; ONE ledger row, k + 1): 25 risk-management schemes on the MT5 1-Step $100K test.

the trader's request: "go through 25 types of risk management". Round 343 kept the deployed policy table (coin flip on US100.cash at the 09:30 open, state-dependent risk and target).
This round asks whether any other way of sizing or managing the same ticket passes the 1-Step more often. Honest prior: with no direction edge, risk management cannot create
expected profit; it only reshapes the distribution of outcomes, and the deployed table was solved by dynamic programming for exactly this objective, so it should be hard to beat.

DATA / TICKET: MT5 US100.cash M1 bid / ask, 09:30-16:00 NY sessions (Round 343's build_symbol rules: >= 370 bars, first bar 09:30), 2021-10..2026-10-02. One trade a day at
the 09:30 open, coin-flip direction (20 draws per start, seed 344), real fills (long buys the ask, exits the bid; short the reverse), 0.4 bp entry and 0.2 bp stop slippage.
Base stop = 0.25 x mean session range of the last 20 sessions; exit at the target, the stop, or the 15:59 close.
UNIVERSAL RULES (every scheme, so no scheme can breach intraday through a single loss): risk is clipped to 0.9 x the room to the nearer floor (3% daily, 10% end-of-day
trailing); a planned risk under $250 skips the day; once the balance is above $110,000 with the best-day rule unmet, every scheme trades the table's $250 / k 1.5 ticket.
Pass = balance > $110,000 with the best day <= 50% of the profitable days' total.

THE 25 SCHEMES (fixed now; % = of the $100,000 initial balance unless stated; k = target in R):
  S01 TABLE           the deployed table (forex/specs/round275_onestep_policy_risk1000.npz), max $1,000, payoff cap $5,000
  S02 TABLE_075       the table with risk capped at $750
  S03 TABLE_X1.5      the table x 1.5 (max $1,500)
  S04 TABLE_PAUSE2    the table, but skip the day after two losses in a row
  S05 FIX_0.5_K4      0.5% risk, k 4
  S06 FIX_1_K2        1% risk, k 2
  S07 FIX_1_K3        1% risk, k 3
  S08 FIX_1.5_K2.5    1.5% risk, k 2.5
  S09 FIX_2_K2        2% risk, k 2
  S10 FIX_2.5_K1.5    2.5% risk, k 1.5 (high win rate, big size)
  S11 PCT_BAL_1.5     1.5% of the CURRENT balance (compounding), k 2.5
  S12 DD_STEP         1.5%, halved for each full 3% of drawdown from the high-water mark, k 2.5
  S13 HWM             1.5% when the balance is at its high-water mark, 0.75% when below it, k 2.5
  S14 ANTI_MART       1% start, +0.25% after each win (cap 2%), back to 1% after a loss, k 2.5
  S15 MART            1% start, doubled after each loss (cap 2.5%), back to 1% after a win, k 2.5 (martingale; shown as the warning case)
  S16 ROOM_THIRD      one third of the room to the trailing floor (cap 2.5%), k 2.5
  S17 BOLD_TARGET     risk = distance to the target / 4 (cap 2.5%), k 4: one win finishes
  S18 RAMP_UP         0.75% on day 1 rising linearly to 2% on day 57, k 2.5
  S19 FRONT_LOAD      2% for the first 20 trading days, 1% after, k 2.5
  S20 LOCK_IN         1.5% until +5%, then 0.75%; within 2% of the target risk = distance / 2.5 (at least $250), k 2.5
  S21 BREAKEVEN_1R    1% risk, k 3, stop moved to the entry once price has gone +1R
  S22 PARTIAL_1R      1% risk, half closed at +1R, the other half to k 3 (stop unchanged)
  S23 TRAIL_1R        1% risk, no target, stop trails 1R behind the best price, exit at the close
  S24 WIDE_STOP       1% risk with the stop at 0.5 x the 20-session range, k 2
  S25 TIGHT_STOP      1% risk with the stop at 0.125 x the 20-session range, k 4
Path rules for S21-S23 (bar by bar, conservative): within a bar the current stop is checked before the target and before the stop is moved; a stop moved to breakeven
or trailed exits at that level (+ 0.2 bp slippage). Long trades are tracked on the bid, shorts on the ask.

OUTPUT: for every scheme the 57-trading-day pass probability over IS starts (window inside 2021-10..2023-12) and OOS starts (from 2024-01-01), the breach share, the
still-open share, the median days to pass, and the maximum risk a trade ever takes (MT5 broker recommends <= 1%; schemes above it are flagged).
DECISION (fixed now): a scheme REPLACES S01 only if its OOS pass >= S01's OOS + 5 points AND its IS pass >= S01's IS AND the 90% lower bound of a circular block bootstrap
(blocks of 57 starts, 2,000 draws) of the paired OOS difference is > 0. 24 alternatives are compared, so a lone near-miss is expected by chance. Not widened after the run.
BUG FOUND AFTER THE FIRST RUN AND DISCLOSED: S04's loss streak was not reset by the paused day, so after two losses in a row it never traded again (3% pass);
fixed to pause exactly one day as written; no other scheme is affected (only S04 returns no ticket). Also added after the first run: because every scheme clips its risk to
0.9 x the room, a losing account never breaches, it ends unable to risk $250 to the trailing floor; that is now reported as 'stuck' (it is the practical failure) instead of
'open'. The other 24 schemes' pass numbers are unchanged by both edits.
POWER: about 9 independent IS and 12 OOS 57-day windows: differences under about 10 points are noise.
DRY-RUN COUNTS: 1,215 US100 sessions 2021-10-29..2026-10-02, 475 IS starts, 628 OOS starts, 12 ticket variants, 25 schemes. UNIT CHECK: the standard ticket equals
Round 343's on every session, side and k (max difference 0.0). Read in the unit check and disclosed: the cost-inclusive mean R per ticket over all sessions is about
-0.02 to +0.08 R for every variant (long slightly above short: index drift); breakeven / partial / trail / wide / tight do not change the per-ticket mean by more than a few
hundredths of R, they only change the win share (0.21 to 0.44).
"""
import os, sys, json, time
os.environ["ROUND_DATA"] = "mt5broker"; os.environ["ROUND_FILLS"] = "ask"
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..")); sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
from mt5 import onestep as OS
import round343_master_strategy_1step as M

SEED, H, SPLIT = 344, 57, pd.Timestamp("2024-01-01")
SLIP_E, SLIP_S = M.SLIP_E_BP * 1e-4, M.SLIP_S_BP * 1e-4
TABLE_KS = M.KS
STD_KS = sorted(set(TABLE_KS) | {2.0, 3.0})


def path_R(x, side, stop, mode, k):
    """R of one ticket entered at the open of bar 0 of the session arrays x and run to the last bar. mode: 'std' | 'be' | 'partial' | 'trail'."""
    if side == 1:
        entry, hi, lo, last = x["ao"][0], x["h"], x["l"], x["c"][-1]
    else:
        entry, hi, lo, last = x["o"][0], x["ah"], x["al"], x["ac"][-1]
    e_cost, s_cost = SLIP_E * entry / stop, SLIP_S * entry / stop
    fav = (hi - entry) / stop if side == 1 else (entry - lo) / stop          # best excursion inside the bar, in R
    adv = (entry - lo) / stop if side == 1 else (hi - entry) / stop          # worst excursion inside the bar, in R
    n = len(hi)
    if mode == "std":
        s_hit = np.flatnonzero(adv >= 1.0); t_hit = np.flatnonzero(fav >= k)
        i_s = s_hit[0] if len(s_hit) else n; i_t = t_hit[0] if len(t_hit) else n
        if i_s <= i_t and i_s < n:
            return -1.0 - s_cost - e_cost
        if i_t < n:
            return k - e_cost
        return side * (last - entry) / stop - e_cost
    stop_R, best, half_done, half_R = -1.0, 0.0, False, 0.0
    for i in range(n):
        if -adv[i] <= stop_R:                                                # current stop touched first
            r = stop_R - (s_cost if stop_R <= 0 else s_cost)
            return (0.5 * half_R + 0.5 * r if half_done else r) - e_cost
        if mode in ("be", "partial") and fav[i] >= k:
            return (0.5 * half_R + 0.5 * k if half_done else k) - e_cost
        if mode == "be" and fav[i] >= 1.0:
            stop_R = max(stop_R, 0.0)
        if mode == "partial" and not half_done and fav[i] >= 1.0:
            half_done, half_R = True, 1.0
        if mode == "trail":
            best = max(best, fav[i]); stop_R = max(stop_R, best - 1.0)
    r = side * (last - entry) / stop
    return (0.5 * half_R + 0.5 * r if half_done else r) - e_cost


def build():
    full = M.load_full("US100.cash")
    t = full.index.hour * 60 + full.index.minute
    s = full[(t >= 570) & (t < 960) & (full.index.dayofweek < 5)]
    codes, starts = np.unique(s.index.normalize().values, return_index=True)
    ends = np.r_[starts[1:], len(s)]
    arr = {c: s[c].to_numpy() for c in ("o", "h", "l", "c", "ao", "ah", "al", "ac")}
    fm = (s.index.hour * 60 + s.index.minute).to_numpy()
    days, spans = [], []
    for d, a, b in zip(codes, starts, ends):
        if b - a >= 370 and fm[a] == 570:
            days.append(pd.Timestamp(d)); spans.append((a, b))
    rng_ = pd.Series([arr["h"][a:b].max() - arr["l"][a:b].min() for a, b in spans], index=days)
    r20 = rng_.rolling(20).mean().shift(1)
    keys = [("std", 0.25, k) for k in STD_KS] + [("be", 0.25, 3.0), ("partial", 0.25, 3.0), ("trail", 0.25, 0.0), ("std", 0.5, 2.0), ("std", 0.125, 4.0)]
    rows, cal = [], []
    for d, (a, b), rr in zip(days, spans, r20.values):
        if not np.isfinite(rr) or d < pd.Timestamp("2021-10-01"):
            continue
        x = {c: v[a:b] for c, v in arr.items()}
        rows.append([[path_R(x, side, f * rr, mode, k) for (mode, f, k) in keys] for side in (1, -1)])
        cal.append(d)
    return pd.DatetimeIndex(cal), np.array(rows), keys        # rows: (n_days, 2 sides, n_keys)


class Ctx:
    def __init__(self, keys):
        self.key = {k: i for i, k in enumerate(keys)}

    def std(self, k, f=0.25):
        return self.key[("std", f, float(k))]


def scheme_fns(ctx, pol):
    P = 1000.0           # 1% of the initial balance
    std = ctx.std

    def table(mult=1.0, cap=None, pause=False):
        def f(st):
            if pause and st["loss_streak"] >= 2:
                return 0.0, None
            r, k = pol.lookup(st["day"], st["bal"], st["hwm"])
            if r <= 0:
                return 0.0, None
            r = min(r * mult, cap or 1e18)
            r = min(r, OS.MAX_TICKET_PAYOFF / k) if mult == 1.0 else r
            return r, std(k)
        return f

    def fixed(pct, k, f=0.25):
        return lambda st: (pct * P, std(k, f))

    def dd_step(st):
        steps = int((st["hwm"] - st["bal"]) // 3000)
        return 1.5 * P / (2 ** steps), std(2.5)

    def anti(st):
        return min(1.0 + 0.25 * st["win_streak"], 2.0) * P, std(2.5)

    def mart(st):
        return min(1.0 * 2 ** st["loss_streak"], 2.5) * P, std(2.5)

    def room_third(st):
        return min((st["bal"] - (max(st["hwm"], OS.INITIAL) - OS.TRAIL)) / 3, 2.5 * P), std(2.5)

    def bold(st):
        return min(max(OS.TARGET - st["bal"], 0) / 4 + 1.0, 2.5 * P), std(4)

    def ramp(st):
        return (0.75 + (2.0 - 0.75) * min(st["day"], H - 1) / (H - 1)) * P, std(2.5)

    def front(st):
        return (2.0 if st["day"] < 20 else 1.0) * P, std(2.5)

    def lock(st):
        dist = OS.TARGET - st["bal"]
        if dist <= 2000:
            return max(dist / 2.5 + 1.0, 250.0), std(2.5)
        return (1.5 if st["bal"] < 105_000 else 0.75) * P, std(2.5)

    return {
        "S01 TABLE": table(), "S02 TABLE_075": table(cap=750.0), "S03 TABLE_X1.5": table(mult=1.5), "S04 TABLE_PAUSE2": table(pause=True),
        "S05 FIX_0.5_K4": fixed(0.5, 4), "S06 FIX_1_K2": fixed(1, 2), "S07 FIX_1_K3": fixed(1, 3), "S08 FIX_1.5_K2.5": fixed(1.5, 2.5),
        "S09 FIX_2_K2": fixed(2, 2), "S10 FIX_2.5_K1.5": fixed(2.5, 1.5),
        "S11 PCT_BAL_1.5": lambda st: (0.015 * st["bal"], std(2.5)),
        "S12 DD_STEP": dd_step,
        "S13 HWM": lambda st: ((1.5 if st["bal"] >= st["hwm"] else 0.75) * P, std(2.5)),
        "S14 ANTI_MART": anti, "S15 MART": mart, "S16 ROOM_THIRD": room_third, "S17 BOLD_TARGET": bold, "S18 RAMP_UP": ramp, "S19 FRONT_LOAD": front,
        "S20 LOCK_IN": lock,
        "S21 BREAKEVEN_1R": lambda st: (P, ctx.key[("be", 0.25, 3.0)]), "S22 PARTIAL_1R": lambda st: (P, ctx.key[("partial", 0.25, 3.0)]),
        "S23 TRAIL_1R": lambda st: (P, ctx.key[("trail", 0.25, 0.0)]),
        "S24 WIDE_STOP": fixed(1, 2, 0.5), "S25 TIGHT_STOP": fixed(1, 4, 0.125),
    }


def run(start, Rd, sides, fn, small_key):
    """One window -> (outcome 'pass'|'breach'|'open', days used, max risk taken)."""
    st = dict(bal=OS.INITIAL, hwm=OS.INITIAL, day=0, loss_streak=0, win_streak=0)
    pos, best, maxr = 0.0, 0.0, 0.0
    end = min(start + H, len(Rd))
    for j in range(start, end):
        st["hwm"] = max(st["hwm"], st["bal"]); st["day"] = j - start
        floor = max(max(st["hwm"], OS.INITIAL) - OS.TRAIL, st["bal"] - OS.DAILY_LOSS)
        if st["bal"] > OS.TARGET:
            risk, key = 250.0, small_key
        else:
            risk, key = fn(st)
        if key is None or risk <= 0:
            st["loss_streak"] = 0          # a paused day ends the pause (S04); no other scheme returns no key
            continue
        risk = min(risk, 0.9 * (st["bal"] - floor))
        if risk < OS.MIN_RISK_USD:
            continue
        maxr = max(maxr, risk)
        pnl = risk * Rd[j, 0 if sides[j] > 0 else 1, key]
        st["bal"] += pnl
        if pnl > 0:
            pos += pnl; best = max(best, pnl); st["win_streak"] += 1; st["loss_streak"] = 0
        else:
            st["loss_streak"] += 1; st["win_streak"] = 0
        if st["bal"] > OS.TARGET and best <= 0.5 * pos:
            return "pass", j - start + 1, maxr
        if st["bal"] <= floor + 1e-6:
            return "breach", j - start + 1, maxr
    floor = max(max(st["hwm"], OS.INITIAL) - OS.TRAIL, st["bal"] - OS.DAILY_LOSS)
    return ("stuck" if 0.9 * (st["bal"] - (max(st["hwm"], OS.INITIAL) - OS.TRAIL)) < OS.MIN_RISK_USD else "open"), H, maxr


def evaluate(starts, Rd, sides_all, fn, small_key):
    out = np.zeros((len(starts), 4)); days, maxr = [], 0.0
    for i, s in enumerate(starts):
        for sides in sides_all:
            o, d, mr = run(s, Rd, sides, fn, small_key)
            out[i, ("pass", "breach", "open", "stuck").index(o)] += 1
            maxr = max(maxr, mr)
            if o == "pass":
                days.append(d)
    out /= len(sides_all)
    return out, (float(np.median(days)) if days else float("nan")), maxr


def main(dry):
    t0 = time.time()
    cal, Rd, keys = build()
    ctx = Ctx(keys); pol = OS.Policy()
    is_end = int(np.searchsorted(cal, SPLIT)); n = len(cal)
    is_starts, oos_starts = np.arange(0, is_end - H + 1), np.arange(is_end, n - H + 1)
    print(f"US100 sessions {n} ({cal[0].date()}..{cal[-1].date()}), IS starts {len(is_starts)}, OOS starts {len(oos_starts)}, ladder keys {len(keys)}, {time.time() - t0:.0f}s", flush=True)
    fns = scheme_fns(ctx, pol)
    print(f"schemes {len(fns)}")
    if dry:
        return
    sides_all = np.where(np.random.default_rng(SEED).random((20, n)) < 0.5, 1, -1)
    small = ctx.std(1.5)
    res, vec = {}, {}
    for name, fn in fns.items():
        r_is, d_is, mr_is = evaluate(is_starts, Rd, sides_all, fn, small)
        r_oos, d_oos, mr_oos = evaluate(oos_starts, Rd, sides_all, fn, small)
        vec[name] = r_oos[:, 0]
        res[name] = dict(IS_pass=float(r_is[:, 0].mean()), IS_breach=float(r_is[:, 1].mean()), IS_open=float(r_is[:, 2].mean()), IS_stuck=float(r_is[:, 3].mean()),
                         OOS_pass=float(r_oos[:, 0].mean()), OOS_breach=float(r_oos[:, 1].mean()), OOS_open=float(r_oos[:, 2].mean()), OOS_stuck=float(r_oos[:, 3].mean()),
                         median_days_to_pass_OOS=d_oos, max_risk_usd=max(mr_is, mr_oos))
        r = res[name]
        print(f"{name:18s} IS pass {r['IS_pass']:.3f} breach {r['IS_breach']:.3f} | OOS pass {r['OOS_pass']:.3f} breach {r['OOS_breach']:.3f} open {r['OOS_open']:.3f} stuck {r['OOS_stuck']:.3f} "
              f"| days {d_oos:.0f} | max risk ${r['max_risk_usd']:,.0f} | {time.time() - t0:.0f}s", flush=True)
    base = res["S01 TABLE"]; brng = np.random.default_rng(SEED + 1)
    for name, r in res.items():
        if name == "S01 TABLE":
            continue
        diff = vec[name] - vec["S01 TABLE"]
        r["diff_OOS"] = float(diff.mean()); r["lb90"] = M.block_lb(diff, brng)
        r["REPLACES_TABLE"] = bool(r["diff_OOS"] >= 0.05 and r["IS_pass"] >= base["IS_pass"] and r["lb90"] > 0)
    print("replaces the table:", [k for k, v in res.items() if v.get("REPLACES_TABLE")])
    json.dump(res, open(os.path.join(HERE, "round344_results_mt5broker_ask.json"), "w"), indent=1)
    print(f"done {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
