"""
One standard way to test a trading idea (plan of 2026-09-26, "keep testing ideas").

Every idea goes through the same data, exits, costs and report, so results are
comparable and no rule drifts between rounds:

  data      load_mnq_rth()              MNQ RTH 1-min (round120_goal_judge.load_mnq)
            load_days(symbol)           24-hour MNQ/MGC per trading day (18:00 ET start),
                                        one contract per day -- the one with the most RTH
                                        volume -- so rolls never distort levels (as Round 125)
            load_yahoo_hourly(sym)      ~2 years of hourly ES/YM/RTY/NQ/GC/SI/CL futures
                                        (independent data for replication), close-stamped ET
            bars_from_days(days)        those days as one bar frame with a `tday` column
  exits     resolve_trailing(...)       ATR trailing stop, one position, flat at the close
                                        (round120_goal_judge.resolve_mtm)
            resolve_bracket(...)        fixed stop + optional target per signal, one position,
                                        stop wins a tie, flat at the session's last bar or at
                                        `flat_time` (as Round 124)
  costs     commission + 2 ticks slippage per contract round trip
  report    test_idea(...)              one row: trades, win %, R, net and before-cost
                                        expectancy, IS/OOS (split 2025-07-01) bootstrap
                                        P(edge>0), daily Sharpe, and the candidate verdict
  ledger    docs/IDEA_LEDGER.md         every variant tested; its count k sets the bar

The candidate bar (fixed in the plan): rules committed before the run; positive
before AND after costs; IS P(edge>0) >= 0.95; OOS P(edge>0) >= 1 - 0.01/k.
"""
import os, sys, glob, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from round11_fvg_bias import POINT_VALUE, TICK_SIZE, COMMISSION_RT
from round115_extended_hours_data_and_search import _load_one
import round120_goal_judge as J

HERE = os.path.dirname(os.path.abspath(__file__))
EXT_DIRS = {"MNQ": "nasdaq_extended", "MGC": "gold_extended"}
PV = {**POINT_VALUE, "MCL": 100.0}   # micro crude: 100 barrels
TK = {**TICK_SIZE, "MCL": 0.01}
YAHOO_MICRO = {"ES=F": "MES", "YM=F": "MYM", "RTY=F": "M2K", "NQ=F": "MNQ", "GC=F": "MGC", "SI=F": "SIL", "CL=F": "MCL"}
LEDGER = os.path.join(HERE, "..", "docs", "IDEA_LEDGER.md")
RISK = 300.0
MAX_CONTRACTS = 50
T_RTH_OPEN, T_RTH_CLOSE, T_DAY_START = dt.time(9, 30), dt.time(16, 0), dt.time(18, 0)


def cost_per_contract(symbol):
    return COMMISSION_RT + 2 * TK[symbol] * PV[symbol]


# ------------------------------------------------------------------ data ----

def load_mnq_rth():
    df = J.load_mnq()
    return df.assign(tday=df.index.normalize())


def load_days(symbol):
    """Returns a list of dicts per trading day: tday, contract, on (18:00..09:29 ET
    bars), session (09:30..16:00 bars), prev_close (the same contract's previous
    RTH close, or NaN). Days with < 300 overnight or session bars are skipped."""
    frames = []
    for f in sorted(glob.glob(os.path.join(HERE, "..", "data", EXT_DIRS[symbol], "*.Last.txt"))):
        df = _load_one(f)
        df.index = df.index.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
        df["tday"] = (df.index + pd.Timedelta(hours=6)).normalize()  # 18:00 ET starts the next trading day
        df["contract"] = os.path.basename(f)
        frames.append(df)
    allb = pd.concat(frames)
    t = allb.index.time
    rth = (t >= T_RTH_OPEN) & (t <= T_RTH_CLOSE)
    vol = allb[rth].groupby(["tday", "contract"])["vol"].sum()
    best = vol.groupby(level=0).idxmax().map(lambda x: x[1])
    rth_close = allb[rth].groupby(["contract", "tday"])["close"].last()
    days = []
    for tday, contract in best.items():
        d = allb[(allb["tday"] == tday) & (allb["contract"] == contract)]
        tt = d.index.time
        on = d[(tt >= T_DAY_START) | (tt < T_RTH_OPEN)]
        session = d[(tt >= T_RTH_OPEN) & (tt <= T_RTH_CLOSE)]
        if len(on) < 300 or len(session) < 300:
            continue
        prior = rth_close.loc[contract]
        prior = prior[prior.index < tday]
        days.append(dict(tday=tday, contract=contract, on=on, session=session,
                         prev_close=float(prior.iloc[-1]) if len(prior) else np.nan))
    return days


def bars_from_days(days, part="all"):
    """part: 'session', 'on', or 'all' (overnight then session)."""
    keys = ["on", "session"] if part == "all" else [part]
    return pd.concat([d[k] for d in days for k in keys]).sort_index()


def load_yahoo_hourly(yahoo_symbol):
    """~2 years of hourly futures bars from Yahoo's chart API (front month), cached
    raw in data/hourly/. Yahoo stamps bars at their START; they are re-stamped at
    their close (+1h) to match every other loader here, in New York time. Bars with
    no data (the 17:00-18:00 ET break, Yahoo gaps) and off-hour stamps are dropped,
    as is the last bar of the download (possibly incomplete). Adds `tday`."""
    import json, urllib.request
    path = os.path.join(HERE, "..", "data", "hourly", f"{yahoo_symbol}_yahoo_60m.csv")
    if not os.path.exists(path):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?interval=60m&range=730d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        res = json.load(urllib.request.urlopen(req, timeout=60))["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        raw = pd.DataFrame({"start_utc": res["timestamp"], "open": q["open"], "high": q["high"],
                            "low": q["low"], "close": q["close"], "volume": q["volume"]})
        os.makedirs(os.path.dirname(path), exist_ok=True)
        raw.iloc[:-1].to_csv(path, index=False)
    raw = pd.read_csv(path)
    idx = (pd.to_datetime(raw["start_utc"], unit="s", utc=True).dt.tz_convert("America/New_York")
           .dt.tz_localize(None) + pd.Timedelta(hours=1))
    df = raw.drop(columns="start_utc").set_index(pd.DatetimeIndex(idx, name="ts"))
    df = df[df["close"].notna() & (df.index.minute == 0)].sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df.assign(tday=(df.index + pd.Timedelta(hours=6)).normalize())


# ----------------------------------------------------------------- exits ----

def resolve_trailing(sig, bars, symbol, risk=RISK, trail_mult=1.5, max_contracts=MAX_CONTRACTS):
    """sig: ts, direction, entry, stop. RTH bars only (flat at each date's last bar)."""
    return J.resolve_mtm(sig, bars, symbol, risk, trail_mult, 1e9, max_contracts)[1]


def _session_minute(idx):
    m = idx.hour * 60 + idx.minute
    return (m - (T_DAY_START.hour * 60 + T_DAY_START.minute)) % 1440


def resolve_bracket(sig, bars, symbol, risk=RISK, max_contracts=MAX_CONTRACTS, flat_time=None):
    """sig: ts, direction, entry, sl, tp (tp NaN = no target). Entry at the signal
    bar's close (the signal ts must be a bar in `bars`), active from the next bar of
    the same trading day, only when flat. Stop checked before target on each bar.
    Forced flat at the trading day's last bar, or at the first bar at/after
    flat_time (a time of day on the 18:00 ET session clock); no entries from then on."""
    pv, cpc = PV[symbol], cost_per_contract(symbol)
    ts, hi, lo, cl = bars.index.values, bars["high"].values, bars["low"].values, bars["close"].values
    day = bars["tday"].values
    last_of_day = np.r_[day[1:] != day[:-1], True]
    past_flat = np.zeros(len(bars), bool)
    if flat_time is not None:
        sm = _session_minute(bars.index)
        cut = ((flat_time.hour * 60 + flat_time.minute) - (T_DAY_START.hour * 60 + T_DAY_START.minute)) % 1440
        past_flat = sm >= cut
    sig = sig.sort_values("ts", kind="stable").reset_index(drop=True)
    act = np.searchsorted(ts, sig["ts"].values.astype(ts.dtype), side="right")
    by_bar = {}
    for j, p in enumerate(act):
        if 0 < p < len(ts) and day[p] == day[p - 1] and ts[p - 1] == sig["ts"].values[j] and not past_flat[p - 1]:
            by_bar.setdefault(int(p), j)  # first signal per bar
    trades, pos = [], None
    for i in range(len(ts)):
        j = by_bar.get(i)
        if pos is None and j is not None and not past_flat[i - 1]:
            r = sig.iloc[j]
            dist = abs(r["entry"] - r["sl"])
            if dist > 0:
                c = min(max(1, int(risk // (dist * pv))), max_contracts)
                pos = dict(d=int(r["direction"]), e=r["entry"], sl=r["sl"], tp=r["tp"], c=c, i0=i - 1, dist=dist)
        if pos is None:
            continue
        d, px = pos["d"], None
        if (d == 1 and lo[i] <= pos["sl"]) or (d == -1 and hi[i] >= pos["sl"]):
            px = pos["sl"]
        elif not np.isnan(pos["tp"]) and ((d == 1 and hi[i] >= pos["tp"]) or (d == -1 and lo[i] <= pos["tp"])):
            px = pos["tp"]
        elif last_of_day[i] or past_flat[i]:
            px = cl[i]
        if px is not None:
            gross = d * (px - pos["e"]) * pv * pos["c"]
            trades.append((ts[pos["i0"]], ts[i], d, pos["c"], gross - pos["c"] * cpc, d * (px - pos["e"]) / pos["dist"]))
            pos = None
    return pd.DataFrame(trades, columns=["entry_ts", "exit_ts", "direction", "contracts", "pnl", "r"])


# ---------------------------------------------------------------- report ----

def ledger_count():
    if not os.path.exists(LEDGER):
        return 0
    return sum(1 for line in open(LEDGER, encoding="utf-8") if line.startswith("| ") and line[2:3].isdigit())


def oos_bar(k):
    return 1.0 - 0.01 / max(k, 1)


def test_idea(name, trades, all_days, symbol, k, risk=RISK, n_boot=4_000):
    """Prints and returns the standard row. k = ledger count including this variant."""
    e = pd.to_datetime(trades["entry_ts"])
    # a mixed-instrument portfolio carries its own per-trade "cost" column
    gross = trades["pnl"] + (trades["cost"] if "cost" in trades else trades["contracts"] * cost_per_contract(symbol))
    st_is = J.edge_stats(trades[e < J.OOS_START], n_boot=n_boot)
    st_oos = J.edge_stats(trades[e >= J.OOS_START], n_boot=n_boot)
    if st_oos["p_pos"] >= 0.99:  # resolve the tail finely enough to compare with the bar
        st_oos = J.edge_stats(trades[e >= J.OOS_START], n_boot=40_000)
    daily = trades.groupby(pd.to_datetime(trades["exit_ts"]).dt.normalize())["pnl"].sum()
    daily = daily.reindex(pd.DatetimeIndex(sorted(set(all_days))), fill_value=0.0)
    row = dict(name=name, n=len(trades), win=float((trades["pnl"] > 0).mean()) if len(trades) else np.nan,
               r_net=float(trades["pnl"].mean() / risk) if len(trades) else np.nan,
               exp=float(trades["pnl"].mean()) if len(trades) else np.nan,
               exp_gross=float(gross.mean()) if len(trades) else np.nan,
               n_is=st_is["n"], exp_is=st_is["exp"], p_is=st_is["p_pos"],
               n_oos=st_oos["n"], exp_oos=st_oos["exp"], p_oos=st_oos["p_pos"],
               sharpe=float(daily.mean() / daily.std()) if daily.std() > 0 else np.nan, k=k, bar=oos_bar(k))
    row["candidate"] = bool(row["exp"] > 0 and row["exp_gross"] > 0 and row["p_is"] >= 0.95 and row["p_oos"] >= row["bar"])
    print(f"  {name:<58} n={row['n']:>5} win {row['win']:.0%} {row['r_net']:+.2f}R net ${row['exp']:+7.1f} "
          f"(gross ${row['exp_gross']:+7.1f}) | IS ${row['exp_is']:+7.1f} P {row['p_is']:.2f} | "
          f"OOS ${row['exp_oos']:+7.1f} P {row['p_oos']:.4f} (bar {row['bar']:.4f}) | "
          f"Sharpe/day {row['sharpe']:+.3f} | {'CANDIDATE' if row['candidate'] else 'no'}", flush=True)
    return row


def ledger_rows(rows, source, commit, date="2026-09-26"):
    """Markdown rows for docs/IDEA_LEDGER.md, numbered from the current count."""
    k0 = ledger_count()
    out = []
    for n, r in enumerate(rows, start=k0 + 1):
        verdict = "CANDIDATE" if r["candidate"] else "no edge"
        out.append(f"| {n} | {date} | {r['name']} | {source} | {commit} | {r['n']} | {r['exp']:+.1f} | {r['exp_gross']:+.1f} "
                   f"| {r['p_is']:.2f} / {r['p_oos']:.3f} | {verdict} |")
    return out


# ------------------------------------------------------------- self-test ----

def _judas_signals(days, window_end=dt.time(11, 0), target="2R", min_stop_ticks=8):
    """Round 125's entry logic as signals (first valid setup per day)."""
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
            dist = abs(cl[i] - stop)
            if dist < min_stop_ticks * tick:
                continue
            tp = cl[i] + dd * 2 * dist if target == "2R" else (on_lo if dd == -1 else on_hi)
            if dd * (tp - cl[i]) <= 0:
                continue
            out.append((s.index[i], dd, cl[i], stop, tp))
            break
    return pd.DataFrame(out, columns=["ts", "direction", "entry", "sl", "tp"])


def selftest():
    import round124_codetrading_scalper as R124
    from round19_random_entry import causal_atr15_lookup
    from round117_gap_and_trend_search import build_ema_cross_signals
    ok = True

    def check(label, got_n, got_exp, want_n, want_exp):
        nonlocal ok
        good = got_n == want_n and abs(got_exp - want_exp) < 0.05
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {label}: n={got_n} exp ${got_exp:.2f} (want n={want_n}, ${want_exp})")

    mnq = load_mnq_rth()
    s = R124.signals(mnq, 1.1, 1.5)
    s = s.assign(sl=s["entry"] - s["direction"] * s["dist"], tp=s["entry"] + s["direction"] * 1.5 * s["dist"])
    tr = resolve_bracket(s, mnq, "MNQ")
    check("Round 124 (SL 1.1 x ATR7, BB 1.5)", len(tr), tr["pnl"].mean(), 3922, -21.83)

    ema = build_ema_cross_signals(mnq, causal_atr15_lookup(mnq), 9, 21, 1.5)
    tr = resolve_trailing(ema, mnq.drop(columns="tday"), "MNQ", risk=450.0)
    check("Round 120b EMA 9/21 flat at close", len(tr), tr["pnl"].mean(), 2090, 1.44)

    days = load_days("MNQ")
    tr = resolve_bracket(_judas_signals(days), bars_from_days(days, "session"), "MNQ")
    check("Round 125 Judas swing (to 11:00, 2R)", len(tr), tr["pnl"].mean(), 704, -26.0)
    print("\nharness self-test:", "ALL PASS" if ok else "FAILURES")
    return ok


if __name__ == "__main__":
    selftest()
