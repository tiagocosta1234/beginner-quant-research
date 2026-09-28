"""
Round 179: the trader asked to add a filter to every "best" strategy from this
session -- one trade a day, New York hours only. Checked what that would
actually require first, and found something serious: EVERY dip-buy-family
result tested this session (Round 166's ensemble, Round 174's confluence,
Round 175's cross-asset combo) is built on `round135_batch_d.market_frame`,
whose "open"/"close" are a Yahoo DAILY bar's own open and close -- which
for CME futures means the PRIOR EVENING's 18:00 ET Globex reopen through
the NEXT DAY's ~16:00-17:00 ET settlement. That is an ~22-hour OVERNIGHT
HOLD, not a New-York-daytime trade. Confirmed directly against real ES=F
data before writing anything further (2026-09-18 bar: open 7637.0 at the
prior evening, close 7657.35 the next afternoon).

This is not a filter to add on top of the ensemble -- it is the exact
artifact this campaign's own history warns about loudest: Rounds 39-119's
the trader TOD+VWAP-Z "edge" and the EMA 9/21 "breakthrough" were BOTH entirely
overnight-hold artifacts that evaporated (to -$3.9/trade and $1.4/trade
respectively) once corrected to flat-at-the-close (Round 120b,
`CURRENT_STATE.md`'s own "Disproven claims" table). Every "best strategy"
number reported this session needs the same check before being trusted.

Rebuilt Connors RSI(2), IBS, and pre-holiday using GENUINE RTH-only daily
bars (open = the real 09:30 ET session open, close = the real 16:00 ET
session close, same calendar day, zero overnight exposure) from the
Databento 1-minute ES and NQ data -- the only two symbols in that dataset
with the depth to build this properly. Month-end rebalancing is DROPPED,
not rebuilt: it needs ZN (Treasury notes) intraday data to compute an
RTH-only stocks-vs-bonds spread, and this repo's only ZN data is the same
overnight-inclusive Yahoo daily series -- honestly excluded rather than
quietly left on the old, contaminated timing. YM and RTY are also dropped
(not in the Databento set); ES+NQ only.

One trade per instrument per day, by construction (each leg already fires
at most once per symbol per day) -- the "one trade a day" half of the trader's
ask was already true of the underlying signals; what needed fixing was the
hours.

4 variants (Connors, IBS, pre-holiday, and the 3-leg RTH-only ensemble),
reported against each leg's ORIGINAL (overnight-inclusive) number for a
direct, honest before/after. Not added to IDEA_LEDGER.md as new candidates
-- this is a correctness check on already-ledgered ideas (rows from Rounds
142/145/135/166), not a new idea; if anything survives this check with real
OOS support, THAT would earn a new row.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import idea_harness as H
import round120_goal_judge as J
from round142_batch_j import connors
from round145_batch_l import ibs_long
from round171_databento_orb_replication import load_days_databento

OOS_START = pd.Timestamp("2025-07-01")


def rth_daily_frame(sym):
    days = load_days_databento(sym)
    rows = [(d["tday"], d["session"]["open"].iloc[0], d["session"]["high"].max(),
            d["session"]["low"].min(), d["session"]["close"].iloc[-1])
            for d in days if not d["session"].empty]
    df = pd.DataFrame(rows, columns=["tday", "open", "high", "low", "close"]).set_index("tday")
    df["r"] = np.log(df["close"] / df["open"])
    df["sd"] = df["r"].shift(1).rolling(20).std()
    df["cost_r"] = H.cost_per_contract(sym) / (df["sd"] * df["open"] * H.PV[sym])
    for c in ("high", "low", "close"):
        df[f"p_{c}"] = df[c].shift(1)
    gap = pd.Series(df.index, index=df.index).diff().dt.days
    df["p_ok"] = gap.notna() & (gap <= 5)
    return df.dropna(subset=["sd"])


def trades_from(d, direction, sym):
    t = d[direction != 0].copy()
    dd = direction[direction != 0]
    gross = dd * t["r"] / t["sd"]
    return pd.DataFrame({"date": t.index, "market": sym, "gross": gross.values, "pnl": (gross - t["cost_r"]).values})


def pre_holiday_flags(idx):
    from round122b_tom_long_history import load_daily
    nyse_idx = load_daily("SPY").index
    nxt = pd.Series(nyse_idx[1:], index=nyse_idx[:-1])
    pre = {day for day, n in nxt.items() if np.busday_count(day.date() + pd.Timedelta(days=1), n.date()) >= 1}
    return pd.Series(np.where(idx.isin(list(pre)), 1, 0), index=idx)


def judge(name, tr):
    st = lambda x: J.edge_stats(x, n_boot=40_000) if len(x) else dict(n=0, exp=np.nan, p_pos=np.nan)
    a, i, o = st(tr), st(tr[tr["date"] < OOS_START]), st(tr[tr["date"] >= OOS_START])
    daily = tr.groupby("date")["pnl"].sum()
    print(f"  {name:<45} n={a['n']:>5} mean {a['exp']:+.3f}R (gross {tr['gross'].mean():+.3f}R) | "
          f"IS(<2025-07) {i['exp']:+.3f}R P {i['p_pos']:.3f} | OOS(>=2025-07) {o['exp']:+.3f}R P {o['p_pos']:.4f} | "
          f"Sharpe/day {daily.mean() / daily.std():+.3f}", flush=True)
    return dict(name=name, n=a["n"], exp=a["exp"], p_is=i["p_pos"], p_oos=o["p_pos"],
                sharpe=float(daily.mean() / daily.std()) if daily.std() > 0 else np.nan)


if __name__ == "__main__":
    frames = {s: rth_daily_frame(s) for s in ("ES", "NQ")}
    for s, f in frames.items():
        print(f"{s} RTH-only daily bars: {f.index.min().date()} -> {f.index.max().date()}, n={len(f)}")
    print()

    legs = {}
    legs["connors"] = pd.concat([trades_from(frames[s], connors(frames[s], 10), s) for s in frames], ignore_index=True)
    legs["ibs"] = pd.concat([trades_from(frames[s], ibs_long(frames[s]).reindex(frames[s].index).fillna(0), s)
                             for s in frames], ignore_index=True)
    legs["pre_holiday"] = pd.concat([trades_from(frames[s], pre_holiday_flags(frames[s].index), s)
                                     for s in frames], ignore_index=True)

    print("RTH-only (New York hours, flat overnight), ES+NQ only -- vs. the ORIGINAL overnight-inclusive number:\n")
    results = {}
    for name, tr in legs.items():
        results[name] = judge(f"RTH-only {name}", tr)
    original = {"connors": "+0.017 Sharpe (2013-26, overnight-inclusive, 4 indices)",
                "ibs": "+0.042 Sharpe (2013-26, overnight-inclusive, 4 indices)",
                "pre_holiday": "part of Round 166's ensemble, not tested standalone before"}
    for name in legs:
        print(f"    {name}: original was {original[name]}")

    print()
    ens = pd.concat(legs.values(), ignore_index=True)
    combined = ens.groupby(["date", "market"], as_index=False)[["gross", "pnl"]].sum()
    r = judge("RTH-only 3-leg ensemble (Connors+IBS+pre-holiday), ES+NQ", combined)
    print(f"\n    original Round 166 ensemble (4 legs incl. month-end, overnight-inclusive, 4 indices): "
          f"Sharpe +0.036 full-calendar")

    with open(os.path.join(H.HERE, "round179_results.json"), "w") as f:
        json.dump({**results, "ensemble": r}, f, indent=1, default=str)
