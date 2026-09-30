"""
Round 246 (2026-09-30): Profile Rotation -- the frequent, high-win-rate version of the
repo's one evidenced effect, designed from the broker math video. PRE-REGISTRATION:
every rule, parameter and pass bar is fixed here before any P&L is computed.

the trader: "focus on what was shown on the broker math video, then think of a strategy that
fits, with frequent trading".

THE MATH IT HAS TO FIT (acct_math_fit.py, Broker $50K rules, 21 trading days): the
smallest NET edge per trade for a >= 70% one-month pass falls with trade frequency AND
with win rate -- ~0.68R at 1 trade/day and a 35% win rate (today's POC leg shape) vs
0.04-0.08R at 8-16 trades/day and a 65-80% win rate (winners 0.3-0.7R vs 1R losers).
MNQ costs are 2.24 / (2 x stop points) R per trade, so stops must be >= ~20 points.
Batch M (Round 147) already showed plain level fades (round numbers, prior-day high/low,
opening range) do NOT beat the random-walk win rate of such brackets. The one level family
with evidence in this repo is the prior-day volume profile (POC reversion at the open,
Round 178, IS P 0.98, 8/8 robustness; VA rejection OOS P 0.97) -- tested only ONCE a day,
at the open. This round asks whether the same pull toward the prior POC can be traded
repeatedly through the session with the video's high-win-rate shape.

STEP 0 (pass-speed screen): at ~8 trades/day and a 62.5% random-walk win rate, a 70%
one-month pass needs about 0.08R net + ~0.05R costs = ~0.13R gross per trade, i.e. a win
rate ~70.6% (+8 points over the bracket's own geometry). Batch M found -3 points on plain
levels. Prior odds are low; tested because it is the only frequent-trading construction
built on a level family with prior evidence.

RULES (NQ via MNQ, Databento 1-min, 2019-10 .. 2026-09, RTH only):
  Reference   prior RTH session POC (live bot's _session_profile, 1-min volume at price);
              S = mean of the prior 20 RTH ranges (>= 10 needed), same as the live bot.
  Bars        5-minute bars built from 1-min bars 09:30-15:59 ET (start-stamped); a
              5-min bar is known at its close.
  Zone        |close - prior POC| >= 0.15 x S (the POC leg's own threshold).
  Trigger     a rejection bar toward the POC: for a long (price below POC) the 5-min bar
              closes up (close > open) AND its low undercuts the previous 5-min bar's low;
              mirror for a short. Signals only on 5-min bars closing 09:45 .. 15:45 ET.
  Entry       at that 5-min bar's close. One position at a time; a new signal while in a
              trade is ignored.
  Bracket     stop 0.10 x S beyond the entry (~20-25 NQ points recently); target 0.6 x
              the stop toward the POC. Random-walk win rate of this bracket: 1/1.6 = 62.5%.
              Stop checked before target on each 1-min bar; flat at 16:00 ET.
  Day limits  at most 12 trades per day; no new trade once the day's closed P&L <= -3R.
  Size        $300 risk per trade, whole MNQ contracts (idea_harness.resolve_bracket),
              cost = commission + 2 ticks per contract.

CONTROLS AND REPLICATION (fixed):
  Placebo     same days, same number of trades per day, entries at uniformly random
              5-min bar closes 09:45-15:45, same direction rule (toward the prior POC),
              same bracket and day limits -- isolates the zone+trigger timing from the
              bracket's geometry. 20 placebo draws pooled.
  ES          the identical rules on Databento ES via MES (replication).

CANDIDATE (all required):
  (1) idea_harness rule on NQ: net and gross mean > 0; IS P(edge>0) >= 0.95 (< 2025-07-01);
      OOS P(edge>0) >= 1 - 0.01/k at this row's k.
  (2) NQ win rate beats the placebo's: bootstrap P(mean net P&L > placebo mean) >= 0.95.
  (3) ES replication of the SIGNAL: before-cost mean > 0 with full-history bootstrap
      P(before-cost mean > 0) >= 0.80. (Changed from net after the dry run showed ES stops
      of ~5 points -- MES costs ~0.15R/trade vs ~0.05R on NQ -- and BEFORE any P&L was
      computed; a net test on ES would measure costs, not the signal.)
  (4) Pass speed: pass_speed_gate.gate() on NQ's OOS daily results gives P(pass a $50K
      Test within 21 trading days) >= 0.50 (reported against the 70% goal too).
Ledger: 2 rows (NQ, ES), k 398 -> 400.

NOT DONE / DISCLOSED: one parameter set, no tuning; trades per day and the day-loss stop
are applied in order after resolution (trades never overlap, so earlier trades are
unaffected); the live bot's governor (DLL $1,000, 2-loss streak) is not modeled -- the
-3R day stop is this strategy's own rule.

POWER NOTES (from --dry-run, counts only; no P&L looked at): NQ 14,598 raw signals ->
11,428 trades after one-at-a-time + day limits (IS 9,333 / OOS 2,095), on 1,763 of 1,800
days; 6.48 trades per active day (median 7, max 12) -- inside the 4-8/day band the fit
table targets. NQ stop median 23.0 points (34.3 since 2025-07), ~6 MNQ contracts, cost
~0.05R/trade. ES 12,497 -> 9,760 trades, 5.6/day, stop median only 5.1 points (MES cost
~0.15R/trade) -- hence check (3) on before-cost P&L. With ~2,100 OOS trades and a per-trade
sd near 1R, a +0.05R net mean is ~2.3 standard errors: detectable, but the OOS ledger bar
(~0.999975) needs ~+0.09R or better. Hand-check: first NQ signal 2019-10-15 11:05 short at
7948.25 -- prior POC 7859.5, S 101.975 (0.87 S above POC), bar open 7953.5 > close 7948.25,
bar high 7957.5 > previous 5-min high 7954.0; stop 7958.45 (0.10 S), target 7942.13.
"""
import os, sys, json, argparse, time, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round171_databento_orb_replication import load_days_databento
import live_bot.disciplined_bracket_strategy as DBS
from pass_speed_gate import gate

RISK = 300.0
ZONE, STOP_MULT, TARGET_FRAC = 0.15, 0.10, 0.6
MAX_TRADES, DAY_STOP_R = 12, -3.0
FIRST_SIG, LAST_SIG = dt.time(9, 45), dt.time(15, 45)
FLAT = dt.time(16, 0)
N_PLACEBO = 20
MICRO = {"NQ": "MNQ", "ES": "MES"}


def signals(days, rng=None, counts=None):
    """Rule signals, or (rng given) placebo signals with `counts` trades-to-try per day."""
    out, hist = [], []
    for d in days:
        s = d["session"]
        if s.empty:
            continue
        if len(hist) >= 10:
            prev = hist[-1]
            S = float(np.mean([h[0] for h in hist[-20:]]))
            poc = prev[1]
            one = s[s.index.time < dt.time(16, 0)]
            b5 = one.resample("5min", label="left", closed="left").agg(
                {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
            last_min = one.index.to_series().resample("5min", label="left", closed="left").max().reindex(b5.index)
            close_t = (b5.index + pd.Timedelta(minutes=5)).time
            ok = (close_t >= FIRST_SIG) & (close_t <= LAST_SIG)
            dist = poc - b5["close"].values
            zone = np.abs(dist) >= ZONE * S
            dirn = np.sign(dist).astype(int)
            if rng is None:
                prev_low, prev_high = b5["low"].shift(1).values, b5["high"].shift(1).values
                trig = np.where(dirn > 0, (b5["close"].values > b5["open"].values) & (b5["low"].values < prev_low),
                                (b5["close"].values < b5["open"].values) & (b5["high"].values > prev_high))
                idx = np.where(ok & zone & trig)[0]
            else:
                k = counts.get(d["tday"], 0)
                cand = np.where(ok & zone)[0]
                idx = np.sort(rng.choice(cand, min(k, len(cand)), replace=False)) if k and len(cand) else []
            for i in idx:
                e = float(b5["close"].iloc[i])
                dn = int(dirn[i])
                out.append(dict(ts=last_min.iloc[i], direction=dn, entry=e, sl=e - dn * STOP_MULT * S,
                                tp=e + dn * TARGET_FRAC * STOP_MULT * S, tday=d["tday"]))
        prof = DBS._session_profile(s.rename(columns={"vol": "volume"})[s.index.time < dt.time(16, 0)])
        if prof is not None:
            hist.append(prof)
    return pd.DataFrame(out)


def resolve(sig, bars, micro):
    tr = H.resolve_bracket(sig[["ts", "direction", "entry", "sl", "tp"]], bars, micro, risk=RISK, flat_time=FLAT)
    tr["tday"] = pd.to_datetime(tr["entry_ts"]).dt.normalize()
    kept = []
    for _, g in tr.groupby("tday", sort=True):
        cum = 0.0
        for j, r in enumerate(g.itertuples(index=False)):
            if j >= MAX_TRADES or cum <= DAY_STOP_R * RISK:
                break
            kept.append(r)
            cum += r.pnl
    return pd.DataFrame(kept, columns=tr.columns)


def market(sym, dry=False):
    days = load_days_databento(sym)
    bars = pd.concat([d[k] for d in days for k in ("on", "session")]).sort_index()
    micro = MICRO[sym]
    sig = signals(days)
    tr = resolve(sig, bars, micro)
    all_days = sorted({d["tday"] for d in days if not d["session"].empty})
    return days, bars, sig, tr, all_days


def daily(tr, days_idx):
    return tr.groupby(pd.to_datetime(tr["exit_ts"]).dt.normalize())["pnl"].sum().reindex(days_idx, fill_value=0.0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    res = {}
    M = {s: market(s) for s in ("NQ", "ES")}
    for s, (days, bars, sig, tr, all_days) in M.items():
        per_day = tr.groupby("tday").size()
        is_n, oos_n = int((tr["tday"] < J.OOS_START).sum()), int((tr["tday"] >= J.OOS_START).sum())
        stops = (sig["entry"] - sig["sl"]).abs()
        print(f"{s}: {len(sig)} raw signals, {len(tr)} trades after one-at-a-time + day limits (IS {is_n} / OOS {oos_n}); "
              f"{len(per_day)} trading days with trades of {len(all_days)}; trades/active day mean {per_day.mean():.2f} "
              f"median {per_day.median():.0f} max {per_day.max()}; stop points median {stops.median():.1f} "
              f"(recent 2025-07+: {stops[pd.to_datetime(sig['tday']) >= J.OOS_START].median():.1f}); "
              f"contracts median {tr['contracts'].median():.0f}; built {time.time() - t0:.0f}s", flush=True)
    if args.dry_run:
        s0 = M["NQ"][2].head(3)
        print("\nFirst 3 NQ signals (hand-check):\n" + s0.to_string())
        sys.exit(0)

    k0 = H.ledger_count()
    rows = []
    for i, (s, (days, bars, sig, tr, all_days)) in enumerate(M.items(), start=1):
        rows.append(H.test_idea(f"Profile rotation: 5-min rejection toward prior POC (>=0.15S), stop 0.10S, target 0.6 stop, "
                                f"<=12/day, -3R day stop, {MICRO[s]} $300, Databento", tr, all_days, MICRO[s], k0 + i))
        wins = float((tr["pnl"] > 0).mean())
        res[s] = dict(n=len(tr), win=wins, geometric_win=1 / (1 + TARGET_FRAC), mean=float(tr["pnl"].mean()),
                      mean_R=float((tr["pnl"] / RISK).mean()))
        print(f"  {s}: win {wins:.3f} vs random-walk bracket {1 / 1.6:.3f}; mean ${tr['pnl'].mean():+.2f} "
              f"({tr['pnl'].mean() / RISK:+.3f}R)")

    days, bars, sig, tr, all_days = M["NQ"]
    counts = tr.groupby("tday").size().to_dict()
    rng = np.random.default_rng(0)
    plc = pd.concat([resolve(signals(days, rng=rng, counts=counts), bars, "MNQ") for _ in range(N_PLACEBO)], ignore_index=True)
    b = np.random.default_rng(1)
    a, p = tr["pnl"].to_numpy(), plc["pnl"].to_numpy()
    p_vs_placebo = float((b.choice(a, (4000, len(a))).mean(1) > b.choice(p, (4000, len(p))).mean(1)).mean())
    res["placebo"] = dict(n=len(plc), win=float((plc["pnl"] > 0).mean()), mean=float(plc["pnl"].mean()), p_rule_gt=p_vs_placebo)
    print(f"\nPlacebo (random timing in the zone, {N_PLACEBO} draws): n {len(plc)} win {res['placebo']['win']:.3f} "
          f"mean ${plc['pnl'].mean():+.2f} | P(rule > placebo) {p_vs_placebo:.4f}")

    oos_days = pd.DatetimeIndex([d for d in all_days if d >= J.OOS_START])
    full_days = pd.DatetimeIndex(all_days)
    g_oos = gate((daily(tr[tr["tday"] >= J.OOS_START], oos_days) / RISK).to_numpy())
    g_full = gate((daily(tr, full_days) / RISK).to_numpy())
    res["gate_oos"], res["gate_full"] = g_oos, g_full
    print(f"Pass speed (best size): OOS P(pass<=21d) {g_oos['pass_21d']:.3f} (fail {g_oos['fail_21d']:.3f}) | "
          f"full history {g_full['pass_21d']:.3f}")

    es = res["ES"]
    es_tr = M["ES"][3]
    rng2 = np.random.default_rng(2)
    es_gross = es_tr["pnl"].to_numpy() + es_tr["contracts"].to_numpy() * H.cost_per_contract("MES")
    es_p = float((rng2.choice(es_gross, (4000, len(es_gross))).mean(1) > 0).mean())
    res["ES"]["gross_mean"] = float(es_gross.mean())
    checks = {"1_ledger_rule_NQ": rows[0]["candidate"], "2_beats_placebo": p_vs_placebo >= 0.95,
              "3_ES_replication_gross": es_gross.mean() > 0 and es_p >= 0.80, "4_pass_21d>=0.50": g_oos["pass_21d"] >= 0.50}
    res.update(checks=checks, es_p_pos=es_p, ledger_rows=rows)
    print("\n=== Candidate rule (pre-registered) ===")
    for k, v in checks.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"  VERDICT: {'CANDIDATE' if all(checks.values()) else 'NOT a candidate'}")
    print("\nLedger rows (append after review):")
    for line in H.ledger_rows(rows, "Round 246 (pre-registered, profile rotation)", "COMMIT", date="2026-09-30"):
        print(line)
    with open(os.path.join(HERE, "round246_results.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)
    print(f"\nSaved round246_results.json ({time.time() - t0:.0f}s)")
