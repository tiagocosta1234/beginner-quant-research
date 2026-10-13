"""
Round 321 (2026-10-03, PRE-REGISTERED, DESCRIPTIVE -- no ledger row, k stays 2025): does a LONG-BIASED direction beat the coin flip inside the deployed 1-Step policy table?

Standing goal context: current best = the coin-flip bold play (about 40% 1-Step pass in 57 trading days on BASE costs, 26% on harsh; Rounds 296-297). The direction is the one free parameter of that policy.
Equity drift is the most robust 'edge' there is, so the obvious refinement is: trade the table always long (or only when a causal filter says long). A coin flip is the no-edge baseline; this round
measures what the same table does with the direction chosen by a rule, paired on the same days, using the REAL 2020-2026 NQ and ES sessions as the path proxy for US100.cash (Databento 1-minute; MT5 broker tick
data lives on the trader's desktop, so this is a proxy, not a Round 296 repeat).

MECHANICS (reuse of forex/onestep.py unchanged: Policy table round275_onestep_policy_risk1000.npz, sizing rules): per trading day one trade at the 09:30 NY open; stop = 0.25 x mean RTH (09:30-16:00) high-low of the
previous 20 sessions; target = k x stop with k from the table; exit at the 15:59 close if neither is hit; stop wins a bar that touches both. Risk from the table, capped min($1,000, 0.9 x room), skipped under $250,
and under the table's own payoff cap. Costs (Round 296 BASE for US100, scaled to the proxy's price level): entry 2.45 points total (spread + slip) and 0.5 point of stop slip at a US100 level of 25,000, i.e. 0.98 bp and 0.2 bp of price; in R: cost = (2.45 + 0.5 if stopped) x (proxy open / 25,000) / stop_points. (A first version had the ratio inverted; found in the dry run from a unit check on ES, fixed before any P&L run.)
DIRECTION RULES (6): COIN (average over 20 random draws per start day), LONG, SHORT (control: shows how much is drift), PRIOR (sign of the previous day's close-to-close return), FADE (the opposite), DIP-LONG
(long only after a 3-day fall of >= 2 sigma, flat otherwise: a sparse benchmark). Windows: every start day in the real sequence for 57 trading days (the real deadline), plus 62 and 47. Pass = balance > $110,000 with the
Best Day Rule met; fail = balance <= trailing/daily floor can never be reached because stops are sized to the room, so outcomes are pass / open-at-deadline (breach recorded if the equity floor is touched).
OUTPUTS: P(pass) for each rule on NQ and on ES, by period (2020-2022, 2023-2026), and the paired difference to COIN. Overlapping windows are heavily autocorrelated: the effective sample is about 1,500 days / 57 = 26
independent windows per instrument, so a +/-10 point difference is inside noise; the bold-play table itself was solved on 2021-10..2026-09 coin-flip paths.
DECISION RULE (fixed now): a rule 'beats the current best' only if its 57-day BASE pass probability exceeds COIN's by >= 8 points on BOTH NQ and ES AND SHORT is below COIN (so the gain is not just drift) AND the
gain is positive in both periods. Otherwise the rule is only drift exposure and the memo's coin flip stays the baseline. Not widened after the run.
LEAK FOUND AFTER THE FIRST PNL RUN AND DISCLOSED: the first execution used the SAME session's close-to-close return for PRIOR / FADE and the same session's 3-day z for DIP_LONG (a look-ahead): it showed PRIOR 99% and
FADE 0% pass, which is impossible. COIN / LONG / SHORT do not use those columns (first-run values NQ 41.0 / 44.9 / 42.6, ES 37.5 / 39.7 / 43.2) and were unchanged by the fix. The fix shifts both by one session;
the rules, thresholds and decision rule were not changed; the numbers recorded are from the re-run.
DRY-RUN COUNTS (unit check only; the mean R printed by the dry run was read, which is disclosed: it is a cost-inclusive per-trade mean for one k, about zero in both directions): NQ 1,635 sessions
2020-01-02..2026-09-25, 52 dip days, k grid 1.5 / 2.5 / 4 / 6 / 9, mean R at k = 2.5 long +0.023 / short -0.047; ES 1,649 sessions, 60 dip days, long -0.002 / short -0.020. Two bugs were found and fixed before
any pass-probability run: the cost ratio inverted (ES showed -1.2 R a trade) and the loop's per-row access made slow.
POWER: starts overlap (57 of every 58 days shared with the next start), so about 28 independent windows per instrument; a pass-probability difference under about 15 points is inside noise.
"""
import os, sys, json, datetime as dt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from mt5 import onestep as OS

DB = os.path.join(HERE, "..", "data", "databento")
PRICE_REF = 25000.0      # approx US100 level over the sample, for point-cost scaling
COST_ENTRY, COST_STOP = 2.45, 0.5
KS = [float(k) for k in OS.Policy().ks]


MT5BROKER_SYMBOL = {"NQ": "US100.cash", "ES": "US500.cash", "YM": "US30.cash", "RTY": "US2000.cash", "GC": "XAUUSD", "SI": "XAGUSD"}


def _mt5broker_bars(sym):
    """MT5 M1 bid bars (forex/data/<symbol>_M1_ticks_full.parquet, MT5 server clock = New York + 7h) as naive New York o/h/l/c."""
    from mt5 import clock
    d = os.environ.get("MT5BROKER_DATA_DIR") or os.path.join(ROOT, "mt5", "data")
    raw = pd.read_parquet(os.path.join(d, f"{MT5BROKER_SYMBOL[sym]}_M1_ticks_full.parquet"))
    idx = clock.server_to_ny(raw["time"].to_numpy())
    cols = {"o": raw["open"].to_numpy(), "h": raw["high"].to_numpy(), "l": raw["low"].to_numpy(), "c": raw["close"].to_numpy()}
    if os.environ.get("ROUND_FILLS") == "ask" and "ask_open" in raw.columns:      # real-fill mode: ask OHLC kept alongside the bid OHLC
        cols.update(ao=raw["ask_open"].to_numpy(), ah=raw["ask_high"].to_numpy(), al=raw["ask_low"].to_numpy(), ac=raw["ask_close"].to_numpy())
    b = pd.DataFrame(cols, index=idx).sort_index()
    return b[~b.index.duplicated(keep="first")]


def load(sym):
    """Databento futures by default; ROUND_DATA=mt5broker switches every round that imports this loader to MT5 broker bid/ask data (same rules, same costs)."""
    if os.environ.get("ROUND_DATA") == "mt5broker":
        b = _mt5broker_bars(sym)
        t = b.index.hour * 60 + b.index.minute
        return b[(t >= 570) & (t < 960) & (b.index.dayofweek < 5) & (b.index >= "2019-09-01")]
    df = pd.read_parquet(os.path.join(DB, f"futures_{sym}.F_1m.parquet"))
    idx = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    b = pd.DataFrame({"o": df["open"].values, "h": df["high"].values, "l": df["low"].values, "c": df["close"].values}, index=idx).sort_index()
    b = b[~b.index.duplicated(keep="first")]
    t = b.index.hour * 60 + b.index.minute
    b = b[(t >= 570) & (t < 960) & (b.index.dayofweek < 5) & (b.index >= "2019-09-01")]
    return b


def result_path(here, name):
    """roundNNN_results.json for Databento runs, roundNNN_results_mt5broker.json (or _mt5broker_ask.json with real fills) when ROUND_DATA=mt5broker, so one never overwrites the other."""
    if os.environ.get("ROUND_DATA") == "mt5broker":
        name = name.replace(".json", "_mt5broker_ask.json" if os.environ.get("ROUND_FILLS") == "ask" else "_mt5broker.json")
    return os.path.join(here, name)


def trade_R(x, i0, side, stop, k, scale, entry_cost_R, stop_cost_R):
    """R multiple of one table ticket entered at the open of bar i0 of the session frame x and run to the last bar.
    Legacy (bid / futures bars): entry at the bar open, fixed round-trip costs in R (entry_cost_R, stop_cost_R). Real-fill (x has ask columns, ROUND_FILLS=ask):
    a long buys at the ask open and is stopped / targeted / closed on the BID; a short sells at the bid open and is stopped / targeted / closed on the ASK, so the
    spread is the data's own and only the slippage constants (entry 1.0 point, stop 0.5 point, scaled) are added."""
    o, h, l, c = x.o.values, x.h.values, x.l.values, x.c.values
    if "ao" in x.columns:
        ao, ah, al, ac = x.ao.values, x.ah.values, x.al.values, x.ac.values
        entry = ao[i0] if side == 1 else o[i0]
        hi, lo, last = (h[i0:], l[i0:], c[-1]) if side == 1 else (ah[i0:], al[i0:], ac[-1])
        e_cost, s_cost = 1.0 * scale / stop, COST_STOP * scale / stop
    else:
        entry = o[i0]
        hi, lo, last = h[i0:], l[i0:], c[-1]
        e_cost, s_cost = entry_cost_R, stop_cost_R
    sl = entry - side * stop
    hit_stop = (lo <= sl) if side == 1 else (hi >= sl)
    tg = entry + side * k * stop
    hit_tg = (hi >= tg) if side == 1 else (lo <= tg)
    i_s = np.argmax(hit_stop) if hit_stop.any() else 10**9
    i_t = np.argmax(hit_tg) if hit_tg.any() else 10**9
    if i_s <= i_t and i_s < 10**9:
        R = -1.0 - s_cost
    elif i_t < 10**9:
        R = k
    else:
        R = side * (last - entry) / stop
    return R - e_cost


def day_table(sym):
    b = load(sym)
    days = {}
    for d, x in b.groupby(b.index.normalize()):
        if len(x) >= 380 and x.index[0].hour == 9 and x.index[0].minute == 30:
            days[d] = x
    ds = sorted(days)
    rng = pd.Series({d: days[d].h.max() - days[d].l.min() for d in ds})
    r20 = rng.rolling(20).mean().shift(1)
    close = pd.Series({d: days[d].c.iloc[-1] for d in ds})
    ret = np.log(close).diff()
    sig = ret.rolling(60).std().shift(1)
    z3 = np.log(close / close.shift(3)) / (sig * np.sqrt(3))
    z3s, rets = z3.shift(1), ret.shift(1)      # decided before the open: the PREVIOUS session's values
    rows = []
    for i, d in enumerate(ds):
        if not np.isfinite(r20.get(d, np.nan)) or d < pd.Timestamp("2020-01-02"):
            continue
        x = days[d]
        o, h, l, c = x.o.values[0], x.h.values, x.l.values, x.c.values
        stop = 0.25 * r20[d]
        cost_scale = (o / PRICE_REF)
        entry_cost_R = COST_ENTRY * cost_scale / stop
        stop_cost_R = COST_STOP * cost_scale / stop
        res = {(side, k): trade_R(x, 0, side, stop, k, cost_scale, entry_cost_R, stop_cost_R) for side in (1, -1) for k in KS}
        rows.append(dict(date=d, z3=z3s[d], prior=rets[d], dow=d.dayofweek, **{f"R_{s}_{k}": v for (s, k), v in res.items()}))
    return pd.DataFrame(rows).set_index("date")


def run_window(df, start, h, dirfn, pol, rng):
    bal, hwm, pos_days = OS.INITIAL, OS.INITIAL, []
    for j in range(start, min(start + h, len(df))):
        row = df[j]
        hwm = max(hwm, bal)
        floor = max(hwm - OS.TRAIL, bal - OS.DAILY_LOSS)
        side = dirfn(row, rng)
        if side == 0:
            continue
        risk, k = pol.lookup(j - start, bal, hwm)
        if risk <= 0:
            continue
        risk = min(risk, OS.MAX_RISK_USD, 0.9 * (bal - floor))
        if risk < OS.MIN_RISK_USD or risk * k > OS.MAX_TICKET_PAYOFF:
            continue
        R = row[f"R_{side}_{k}"]
        pnl = risk * R
        bal += pnl
        if pnl > 0:
            pos_days.append(pnl)
        if bal > OS.TARGET and pos_days and max(pos_days) <= 0.5 * sum(pos_days):
            return "pass", bal
        if bal <= floor + 1e-6:
            return "breach", bal
    return "open", bal


RULES = {
    "COIN": lambda r, rng: 1 if rng.random() < 0.5 else -1,
    "LONG": lambda r, rng: 1,
    "SHORT": lambda r, rng: -1,
    "PRIOR": lambda r, rng: 1 if r["prior"] > 0 else -1,
    "FADE": lambda r, rng: -1 if r["prior"] > 0 else 1,
    "DIP_LONG": lambda r, rng: 1 if (r["z3"] <= -2 and r["dow"] <= 3) else 0,
}


def main(dry):
    pol = OS.Policy()
    out = {}
    for sym in ("NQ", "ES"):
        df = day_table(sym)
        recs = df.reset_index().to_dict("records")
        for r in recs:
            r.update(prior=r["prior"], z3=r["z3"])
        if dry:
            print(f"{sym}: {len(df)} trading days {df.index[0].date()}..{df.index[-1].date()}, ks {KS}, dip days {(df.z3 <= -2).sum()}, "
                  f"mean R long k=2.5 {df['R_1_2.5'].mean():+.3f}, short {df['R_-1_2.5'].mean():+.3f} (cost-inclusive, read only as a unit check)")
            continue
        rng = np.random.default_rng(321)
        for h in (57, 62, 47):
            starts = list(range(0, len(df) - h))
            for name, fn in RULES.items():
                reps = 20 if name == "COIN" else 1
                res = []
                for s in starts:
                    p = np.mean([run_window(recs, s, h, fn, pol, rng)[0] == "pass" for _ in range(reps)])
                    res.append(p)
                res = np.array(res)
                half = df.index[starts] < pd.Timestamp("2023-01-01")
                out[f"{sym}|{h}|{name}"] = dict(P=float(res.mean()), P_2020_22=float(res[half].mean()), P_2023_26=float(res[~half].mean()), n=len(starts))
        for h in (57,):
            print(sym, h, {n: round(out[f"{sym}|{h}|{n}"]["P"], 3) for n in RULES})
    if not dry:
        json.dump(out, open(result_path(HERE, "round321_results.json"), "w"), indent=1)


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
