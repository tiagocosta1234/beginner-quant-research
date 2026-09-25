"""
Round 124: CodeTrading's "Trading with Python: Simple Scalping Strategy"
(youtube.com/watch?v=C3bh6Y4LpGs, 2024-01-11) -- claimed 200%+ in a 3-month
EUR/USD 5-minute backtest.

Rules as stated in the video description: 5-minute bars; a fast and a slow
moving average define the trend; in an uptrend, buy when price reaches the
lower Bollinger band, in a downtrend sell at the upper band; stop and target
from ATR with a fixed target/stop ratio. Exact numbers were not available (the
author's code link could not be fetched here); these are as recalled from the
video, with a small fixed grid around the two most uncertain ones, all reported:
  trend: EMA30 above/below EMA50 on each of the last 7 bars
  entry: close <= lower BB(15, std) in uptrend / close >= upper BB in downtrend
  stop:  SL_MULT x ATR(7) on 5-min bars; target 1.5 x the stop distance
  grid:  SL_MULT in {1.1, 1.2}, BB std in {1.5, 2.0}

Tested on MNQ RTH 2022-12..2026-09 with this campaign's standard: entry at the
signal bar's close, one position, exits checked on 1-minute bars (a bar that
touches both stop and target counts as the stop), flat at the session's last
bar, commission + 2 ticks slippage per round trip, $300 risk per trade.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from round11_fvg_bias import resample_causal, POINT_VALUE, TICK_SIZE, COMMISSION_RT
import round120_goal_judge as J

RISK = 300.0
TP_RATIO = 1.5


def signals(df1m, sl_mult, bb_std, fast=30, slow=50, trend_bars=7, bb_len=15, atr_len=7):
    b = resample_causal(df1m, "5min")
    ef = b["close"].ewm(span=fast, adjust=False).mean()
    es = b["close"].ewm(span=slow, adjust=False).mean()
    up = (ef > es).astype(int).rolling(trend_bars).min() == 1
    dn = (ef < es).astype(int).rolling(trend_bars).min() == 1
    mid = b["close"].rolling(bb_len).mean()
    sd = b["close"].rolling(bb_len).std(ddof=0)
    tr = pd.concat([b["high"] - b["low"], (b["high"] - b["close"].shift()).abs(),
                    (b["low"] - b["close"].shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / atr_len, adjust=False).mean()
    long_ = up & (b["close"] <= mid - bb_std * sd)
    short_ = dn & (b["close"] >= mid + bb_std * sd)
    s = pd.DataFrame({"ts": b.index, "direction": np.where(long_, 1, np.where(short_, -1, 0)),
                      "entry": b["close"].values, "dist": (sl_mult * atr).values})
    return s[(s["direction"] != 0) & (s["dist"] > 0)].reset_index(drop=True)


def resolve_bracket(sig, df1m, symbol="MNQ", risk=RISK, max_contracts=50):
    pv, tick = POINT_VALUE[symbol], TICK_SIZE[symbol]
    ts, hi, lo, cl = df1m.index.values, df1m["high"].values, df1m["low"].values, df1m["close"].values
    day = df1m.index.normalize().values
    last_of_day = np.r_[day[1:] != day[:-1], True]
    act = np.searchsorted(ts, sig["ts"].values.astype(ts.dtype), side="right")
    by_bar = {}
    for j, p in enumerate(act):
        if 0 < p < len(ts) and day[p] == day[p - 1] and ts[p - 1] == sig["ts"].values[j]:
            by_bar.setdefault(int(p), j)  # first signal per bar; signal ts must be a real 1-min bar
    trades, pos = [], None
    for i in range(len(ts)):
        j = by_bar.get(i)
        if pos is None and j is not None:
            d, e, dist = int(sig["direction"].iat[j]), sig["entry"].iat[j], sig["dist"].iat[j]
            c = min(max(1, int(risk // (dist * pv))), max_contracts)
            pos = dict(d=d, e=e, sl=e - d * dist, tp=e + d * TP_RATIO * dist, c=c, i0=i - 1,
                       cost=c * (COMMISSION_RT + 2 * tick * pv))
        if pos is None:
            continue
        exit_px = None
        if pos["d"] == 1:
            if lo[i] <= pos["sl"]:
                exit_px = pos["sl"]
            elif hi[i] >= pos["tp"]:
                exit_px = pos["tp"]
        else:
            if hi[i] >= pos["sl"]:
                exit_px = pos["sl"]
            elif lo[i] <= pos["tp"]:
                exit_px = pos["tp"]
        if exit_px is None and last_of_day[i]:
            exit_px = cl[i]
        if exit_px is not None:
            pnl = pos["d"] * (exit_px - pos["e"]) * pv * pos["c"] - pos["cost"]
            trades.append((ts[pos["i0"]], ts[i], pos["d"], pos["c"], pnl))
            pos = None
    return pd.DataFrame(trades, columns=["entry_ts", "exit_ts", "direction", "contracts", "pnl"])


if __name__ == "__main__":
    mnq = J.load_mnq()
    print(f"MNQ RTH {mnq.index[0].date()}..{mnq.index[-1].date()}, ${RISK:.0f} risk/trade, target {TP_RATIO}x stop\n")
    for sl_mult in [1.1, 1.2]:
        for bb_std in [1.5, 2.0]:
            tr = resolve_bracket(signals(mnq, sl_mult, bb_std), mnq)
            e = pd.to_datetime(tr["entry_ts"])
            daily = tr.groupby(pd.to_datetime(tr["exit_ts"]).dt.normalize())["pnl"].sum()
            daily = daily.reindex(pd.DatetimeIndex(sorted(mnq.index.normalize().unique())), fill_value=0.0)
            st_i, st_o = J.edge_stats(tr[e < J.OOS_START]), J.edge_stats(tr[e >= J.OOS_START])
            win = (tr["pnl"] > 0).mean()
            print(f"SL {sl_mult} x ATR7, BB std {bb_std}: n={len(tr)} win {win:.0%} exp ${tr['pnl'].mean():+.1f} "
                  f"total ${tr['pnl'].sum():+,.0f} | IS n={st_i['n']} ${st_i['exp']:+.1f} P(>0) {st_i['p_pos']:.2f} | "
                  f"OOS n={st_o['n']} ${st_o['exp']:+.1f} P(>0) {st_o['p_pos']:.2f} | "
                  f"daily Sharpe {daily.mean() / daily.std():+.3f}", flush=True)
