"""Round 347e -- the trendline-fitting method of github.com/neurotrader888/TrendLineAutomation, turned into a breakout strategy and run through the test rules.  (the trader, 2026-10-06)

WHAT THE REPO IS: MIT-licensed, one file (trendline_automation.py). It FITS trendlines: for a window of candles it finds a support line (below every low) and a resistance line (above every high),
each through one pivot point, with the slope chosen by gradient descent to minimise the squared distance to the data. It has NO entry or exit rules: its __main__ only plots the two slopes.
This module re-implements the fit (in closed form, see fit_lines; validated against a port of the repo's descent in selftest) and adds the simplest breakout rule on top. Every choice below was
FIXED BEFORE ANY RESULT WAS LOOKED AT; nothing is tuned.

STRATEGY (primary spec):
  data      MT5 broker's own 1-minute BID and ASK bars (forex/early_mt5/data/<SYMBOL>_M1_ticks_full.parquet; BTCUSD_M1_ticks247), resampled to H1 and D1 (the two timeframes of the repo's sample data)
  signal    at the close of bar t, fit the support and resistance lines to the L = 30 PREVIOUS bars (the repo's lookback) on log high / low / close, project both to bar t (no bar t data in the fit):
            long if close_t > resistance_t, short if close_t < support_t
  entry     at the first minute of bar t+1: longs at the ask open, shorts at the bid open (the real spread is paid); one position at a time
  exit      stop 1.5 x ATR(14) from the entry price (a stop is filled at the stop price, or at the open of a minute that gapped through it; if stop and target could both be hit the stop wins),
            or at the open of bar t+1+HOLD (HOLD = 12 bars), whichever comes first
  size      the stop distance risks r% of $100K per trade (not compounded); r is swept, never fitted per trade
  costs     the spread (bid / ask bars) + commission as the tester charged on MT5 broker's server: $3 per lot per side on FX, $1 on XAUUSD, none assumed on BTCUSD
Robustness (one parameter at a time, all reported): L in {20, 50}, stop 1.0 / 2.5 x ATR, HOLD 6 / 24 bars.
INSTRUMENTS: BTCUSD (the repo's own market), XAUUSD, EURUSD, GBPUSD, USDJPY; 2022-01 .. 2026-09 (2021-10 is warm-up). BTCUSD trades seven days a week, so its attempts start on every calendar day.

EVALUATION: the daily closed P&L v and the lowest equity of each day m (floating losses at the worst bid / ask of every minute a position is open, the entry minute included) feed the same
replay as firm_compare.py for MT5 1-Step, MT5 2-Step, Broker 1-Step and Broker 2-Step ($100K, from every start date, within 30 / 60 / 86 days). The risk per trade r is the only free
parameter: for each rule set and horizon the best r with breach <= 10% is reported in-sample AND leave-one-year-out. The spec grid has 5 symbols x 2 timeframes x 7 variants = 70 runs: the whole
grid is reported, because the best of 70 flatters.

  python -m mt5broker.ea_batch.trendline_eval --selftest       # closed form vs the repo's descent; accounting vs floating.rebuild
  python -m mt5broker.ea_batch.trendline_eval                  # the full grid -> trendline_eval_results.csv
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.ea_batch.analyze_reports import INITIAL
from mt5broker.ea_batch.firm_compare import FN_1, FN_2, MT5BROKER_1, MT5BROKER_2, attempt

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
YEARS = {2022: ("2022-01-01", "2022-12-31"), 2023: ("2023-01-01", "2023-12-31"), 2024: ("2024-01-01", "2024-12-31"), 2025: ("2025-01-01", "2025-12-31"), 2026: ("2026-01-01", "2026-09-30")}
HORIZONS = (30, 60, 86)
RISKS = (0.10, 0.20, 0.30, 0.40, 0.50, 0.75, 1.0, 1.5, 2.0, 3.0)            # % of $100K risked per trade
RULES = (MT5BROKER_1, MT5BROKER_2, FN_1, FN_2)
RISK_REF = 0.01 * INITIAL                                                   # trades are simulated at 1% and scaled linearly to r
SYMBOLS = {  # file, K = dollars per price unit per lot as f(price), commission $ per lot per side, trading days
    "BTCUSD": ("BTCUSD_M1_ticks247.parquet", lambda p: 1.0, 0.0, "D"),
    "XAUUSD": ("XAUUSD_M1_ticks_full.parquet", lambda p: 100.0, 1.0, "B"),
    "EURUSD": ("EURUSD_M1_ticks_full.parquet", lambda p: 100_000.0, 3.0, "B"),
    "GBPUSD": ("GBPUSD_M1_ticks_full.parquet", lambda p: 100_000.0, 3.0, "B"),
    "USDJPY": ("USDJPY_M1_ticks_full.parquet", lambda p: 100_000.0 / p, 3.0, "B"),
}


# ------------------------------------------------------------------ the trendline fit
def _constrained(Y: np.ndarray, p: np.ndarray, support: bool):
    """Slope and intercept of the line through the pivot (p, Y[p]) that stays on one side of every point (below for support, above for resistance) and minimises the squared distance to them.
    The squared distance is a convex quadratic in the slope, so the optimum is the unconstrained minimiser clipped into the interval the side constraint allows; this is the point the repo's
    step-halving descent converges to."""
    n, L = Y.shape
    x = np.arange(L, dtype=float)
    yp = Y[np.arange(n), p]
    dx = x[None, :] - p[:, None].astype(float)
    dy = Y - yp[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        r = dy / dx
    right, left = dx > 0, dx < 0
    inf = np.inf
    if support:                      # line <= Y: right of the pivot s <= r, left of it s >= r
        s_hi, s_lo = np.where(right, r, inf).min(axis=1), np.where(left, r, -inf).max(axis=1)
    else:                            # line >= Y: right of the pivot s >= r, left of it s <= r
        s_lo, s_hi = np.where(right, r, -inf).max(axis=1), np.where(left, r, inf).min(axis=1)
    sstar = (dy * dx).sum(axis=1) / (dx ** 2).sum(axis=1)
    s = np.clip(sstar, s_lo, s_hi)
    return s, yp - s * p


def fit_lines(high: np.ndarray, low: np.ndarray, close: np.ndarray):
    """Windows of log prices, shape (n, L). Returns ((slope, intercept) of the support, (slope, intercept) of the resistance), each of shape (n,). The pivots are the repo's: the extreme
    deviation of the lows / highs from the least-squares line of the closes."""
    n, L = close.shape
    x = np.arange(L, dtype=float); xm = x.mean()
    cm = close.mean(axis=1)
    s0 = ((close - cm[:, None]) * (x - xm)).sum(axis=1) / ((x - xm) ** 2).sum()
    line = s0[:, None] * x + (cm - s0 * xm)[:, None]
    return _constrained(low, np.argmin(low - line, axis=1), True), _constrained(high, np.argmax(high - line, axis=1), False)


def _descent_port(support: bool, pivot: int, init_slope: float, y: np.ndarray):
    """The repo's step-halving numerical descent, re-written from its description, for validation only."""
    def err(slope):
        line = slope * np.arange(len(y)) + (-slope * pivot + y[pivot]); d = line - y
        if (support and d.max() > 1e-5) or (not support and d.min() < -1e-5):
            return -1.0
        return float((d ** 2).sum())
    unit = (y.max() - y.min()) / len(y)
    step, best, best_err = 1.0, init_slope, err(init_slope)
    need_grad, deriv = True, 0.0
    while step > 1e-4:
        if need_grad:
            e = err(best + unit * 1e-4); deriv = e - best_err
            if e < 0:
                e = err(best - unit * 1e-4); deriv = best_err - e
            need_grad = False
        test = best - unit * step if deriv > 0 else best + unit * step
        e = err(test)
        if e < 0 or e >= best_err:
            step *= 0.5
        else:
            best, best_err, need_grad = test, e, True
    return best, -best * pivot + y[pivot]


# ------------------------------------------------------------------ data
def load_m1(symbol: str):
    d = pd.read_parquet(DATA / SYMBOLS[symbol][0], columns=["time", "open", "high", "low", "close", "ask_open", "ask_high", "ask_low", "ask_close"])
    d.index = pd.to_datetime(d.pop("time"), unit="s")
    return d.sort_index()


def tf_bars(m1: pd.DataFrame, tf: str):
    """(bars, first-minute index of each bar). Bars follow the server clock the deals and the bars share."""
    key = m1.index.floor("1h" if tf == "H1" else "1D").values
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    ends = np.r_[starts[1:], len(m1)]
    b = pd.DataFrame({"open": m1.open.values[starts], "high": np.maximum.reduceat(m1.high.values, starts), "low": np.minimum.reduceat(m1.low.values, starts), "close": m1.close.values[ends - 1]},
                     index=pd.DatetimeIndex(key[starts]))
    return b, starts


def signals(bars: pd.DataFrame, L: int):
    """For every bar t >= L: (t, long, short) from the lines fitted to bars t-L .. t-1 and projected to t. No data of bar t enters the fit."""
    hi, lo, cl = np.log(bars.high.values), np.log(bars.low.values), np.log(bars.close.values)
    w = np.lib.stride_tricks.sliding_window_view
    (ss, bs), (sr, br) = fit_lines(w(hi, L)[:-1], w(lo, L)[:-1], w(cl, L)[:-1])      # window j ends at bar j+L-1; project to bar j+L
    t = np.arange(L, len(cl))
    return t, cl[L:] > sr * L + br, cl[L:] < ss * L + bs


# ------------------------------------------------------------------ simulation
@dataclass
class Spec:
    L: int = 30
    stop_atr: float = 1.5
    hold: int = 12

    def tag(self) -> str:
        return f"L{self.L}-stop{self.stop_atr:g}-hold{self.hold}"


def simulate(symbol: str, tf: str, spec: Spec, m1: pd.DataFrame, start: str = "2022-01-01", end: str = "2026-09-30", rng=None, invert: bool = False):
    """Trades as a DataFrame (entry / exit minute, side, entry, exit, lots, K at entry, gross, commission) at 1% risk. rng != None is the NULL benchmark: the same breakout events and rules,
    but the direction of every trade is a coin flip, so whatever it earns is the test rules plus luck, not information in the signal."""
    _, kf, comm, _ = SYMBOLS[symbol]
    bars, bstart = tf_bars(m1, tf)
    nb, n = len(bars), len(m1)
    bo, bl, bh = m1.open.values, m1.low.values, m1.high.values
    ao, al, ah = m1.ask_open.values, m1.ask_low.values, m1.ask_high.values
    tr = np.maximum.reduce([bars.high.values - bars.low.values, np.abs(bars.high.values - np.r_[np.nan, bars.close.values[:-1]]), np.abs(bars.low.values - np.r_[np.nan, bars.close.values[:-1]])])
    atr = pd.Series(tr).rolling(14).mean().values
    t, lg, sh = signals(bars, spec.L)
    t0 = np.searchsorted(bars.index.values, np.datetime64(start)); t1 = np.searchsorted(bars.index.values, np.datetime64(end) + np.timedelta64(1, "D"))
    rows, free = [], 0
    for k in range(len(t)):
        b = int(t[k])
        if b < t0 or b >= t1 - 1 or b < free or not np.isfinite(atr[b]) or atr[b] <= 0 or lg[k] == sh[k]:
            continue
        side = 1 if lg[k] else -1
        if rng is not None:
            side = 1 if rng.random() < 0.5 else -1
        if invert:                                                                  # fade the breakout instead of following it
            side = -side
        eb = b + 1; ie = int(bstart[eb])
        pe = ao[ie] if side == 1 else bo[ie]
        d = spec.stop_atr * atr[b]
        stop = pe - side * d
        xb = min(eb + spec.hold, nb - 1); ix = int(bstart[xb]) if eb + spec.hold < nb else n - 1
        seg = slice(ie, max(ix, ie + 1))
        hit = (bl[seg] <= stop) if side == 1 else (ah[seg] >= stop)
        if hit.any():
            j = ie + int(np.argmax(hit))
            px = min(stop, bo[j]) if side == 1 else max(stop, ao[j])                  # a gap through the stop fills at the open
            xi = j
        else:
            xi = ix; px = bo[ix] if side == 1 else ao[ix]                              # time exit: longs sell at the bid, shorts buy at the ask
        lots = RISK_REF / (d * kf(pe))
        gross = side * (px - pe) * lots * kf(px)
        rows.append((ie, xi, side, pe, px, lots, kf(pe), gross, comm * lots, 0.5 * ((ao[ie] - bo[ie]) + (ao[xi] - bo[xi])) * lots * kf(pe)))
        free = int(np.searchsorted(bstart, xi, side="right") - 1)                      # the bar in which the exit happened: a new signal needs a close after the exit
        free = max(free, b + 1)
    return pd.DataFrame(rows, columns=["i0", "i1", "side", "pe", "px", "lots", "k", "gross", "comm", "spread"])


def day_frames(tr: pd.DataFrame, m1: pd.DataFrame):
    """(v, m, entry days): per-day realized P&L at 1% risk, the lowest equity of each day relative to its opening balance (worst bid / ask of every minute a position is open, the entry minute included),
    and the days a position was opened."""
    n = len(m1)
    bl, ah = m1.low.values, m1.ask_high.values
    real, F = np.zeros(n), np.zeros(n)
    for p in tr.itertuples():
        kv = p.lots * p.k
        wl = (bl[p.i0:p.i1 + 1] - p.pe) * kv if p.side == 1 else (p.pe - ah[p.i0:p.i1 + 1]) * kv
        real[p.i0] -= p.comm
        real[p.i1] += p.gross - p.comm
        if p.i1 > p.i0:
            F[p.i0:p.i1] += wl[:-1]
    R = np.cumsum(real)
    eq = R + F                                                                     # an exit is at the stop price or at an open, so nothing is added for the exit minute itself
    day = m1.index.values.astype("datetime64[D]")
    start = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    days = pd.DatetimeIndex(day[start])
    before = np.where(start > 0, R[np.maximum(start - 1, 0)], 0.0)
    v = np.add.reduceat(real, start)
    m = np.minimum(np.minimum.reduceat(eq, start) - before, v)
    ent = set(pd.DatetimeIndex(m1.index.values[tr.i0.values]).normalize()) if len(tr) else set()
    return pd.Series(v, index=days), pd.Series(m, index=days), ent


# ------------------------------------------------------------------ evaluation under the rules
def windows(freq: str):
    mk = pd.bdate_range if freq == "B" else pd.date_range
    return {(y, H): [list(mk(s, s + pd.Timedelta(days=H))) for s in mk(a, b) if s + pd.Timedelta(days=H) <= pd.Timestamp(b)] for y, (a, b) in YEARS.items() for H in HORIZONS}


def evaluate(v: pd.Series, m: pd.Series, ent: set, W, max_breach: float = 0.10):
    """Pass / breach per rule set, horizon and risk, pooled over 2022-2026, and the best risk (in-sample and leave-one-year-out)."""
    res = {}
    for r in RISKS:
        k = r / 1.0                                                                  # trades were simulated at 1% risk
        pnl = (v * k).to_dict(); mm = (m * k).to_dict()
        for y in YEARS:
            for R in RULES:
                for H in HORIZONS:
                    n = p = b = 0
                    for days in W[(y, H)]:
                        o, _ = attempt(days, pnl, mm, ent, R)
                        n += 1; p += o == "pass"; b += o == "breach"
                    res[(R.name, H, r, y)] = (n, p, b)
    out = []
    for R in RULES:
        for H in HORIZONS:
            def pick(years):
                best = None
                for r in RISKS:
                    n = sum(res[(R.name, H, r, y)][0] for y in years); p = sum(res[(R.name, H, r, y)][1] for y in years); b = sum(res[(R.name, H, r, y)][2] for y in years)
                    if n and b / n <= max_breach and (best is None or (p / n, -r) > best[0]):
                        best = ((p / n, -r), r)
                return None if best is None else best[1]
            ys = tuple(YEARS)
            r = pick(ys)
            row = dict(rule=R.name, horizon=H, best_risk_pct=r)
            if r is not None:
                n = sum(res[(R.name, H, r, y)][0] for y in ys)
                row.update(pass_pct=100 * sum(res[(R.name, H, r, y)][1] for y in ys) / n, breach_pct=100 * sum(res[(R.name, H, r, y)][2] for y in ys) / n,
                           **{f"pass_{y}": 100 * res[(R.name, H, r, y)][1] / res[(R.name, H, r, y)][0] for y in YEARS})
            n = p = b = 0
            for hy in YEARS:
                r2 = pick(tuple(y for y in YEARS if y != hy))
                if r2 is not None:
                    a = res[(R.name, H, r2, hy)]; n += a[0]; p += a[1]; b += a[2]
            row.update(loyo_pass_pct=100 * p / n if n else float("nan"), loyo_breach_pct=100 * b / n if n else float("nan"))
            out.append(row)
    return pd.DataFrame(out)


def trade_stats(tr: pd.DataFrame, v: pd.Series):
    if tr.empty:
        return dict(trades=0)
    net = tr.gross - 2 * tr.comm
    R = net / RISK_REF
    wins, losses = net[net > 0].sum(), -net[net <= 0].sum()
    vv = v.reindex(pd.date_range(v.index.min(), v.index.max(), freq="D")).fillna(0.0)
    pre = (tr.gross + tr.spread) / RISK_REF                                           # the same trades at mid prices, before commission
    return dict(trades=len(tr), per_year=len(tr) / 4.75, mean_R_before_costs=float(pre.mean()), cost_R=float(((tr.spread + 2 * tr.comm) / RISK_REF).mean()), win_pct=100 * (net > 0).mean(), mean_R=float(R.mean()), t_stat=float(R.mean() / (R.std() / np.sqrt(len(R)))) if R.std() > 0 else float("nan"),
                profit_factor=float(wins / losses) if losses > 0 else float("nan"), net_at_1pct=float(net.sum()), sharpe=float(vv.mean() / vv.std() * np.sqrt(365)) if vv.std() > 0 else float("nan"))


# ------------------------------------------------------------------ self-test and main
def selftest():
    m1 = load_m1("BTCUSD"); bars, _ = tf_bars(m1, "D1")
    hi, lo, cl = np.log(bars.high.values), np.log(bars.low.values), np.log(bars.close.values)
    L = 30; w = np.lib.stride_tricks.sliding_window_view
    Hw, Lw, Cw = w(hi, L)[::37], w(lo, L)[::37], w(cl, L)[::37]
    (ss, bs), (sr, br) = fit_lines(Hw, Lw, Cw)
    worst, n = 0.0, len(Hw)
    for i in range(n):
        x = np.arange(L); c0 = np.polyfit(x, Cw[i], 1)
        for sup, p, y, s_cf in ((True, int(np.argmin(Lw[i] - (c0[0] * x + c0[1]))), Lw[i], ss[i]), (False, int(np.argmax(Hw[i] - (c0[0] * x + c0[1]))), Hw[i], sr[i])):
            s_d, _ = _descent_port(sup, p, c0[0], y)
            unit = (y.max() - y.min()) / L
            worst = max(worst, abs(s_d - s_cf) / unit)
    print(f"closed form vs the repo's descent on {n} real BTC daily windows x 2 lines: worst slope difference {worst:.2e} of the slope unit (the descent stops at 1e-4)")
    # accounting: the day frames must reproduce the trades' net P&L, and no day's lowest equity may exceed its realized P&L
    tr = simulate("EURUSD", "H1", Spec(), load_m1("EURUSD"))
    v, m, ent = day_frames(tr, load_m1("EURUSD"))
    print(f"EURUSD H1 primary: {len(tr)} trades; sum of daily v {v.sum():.2f} vs trades' net {(tr.gross - 2 * tr.comm).sum():.2f}; days with m > v: {int((m > v + 1e-9).sum())}")
    return worst


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--selftest", action="store_true"); ap.add_argument("--symbols", default=",".join(SYMBOLS)); ap.add_argument("--tfs", default="H1,D1")
    ap.add_argument("--quick", action="store_true", help="primary spec only"); ap.add_argument("--null", type=int, default=0, help="null benchmark: N random-direction runs of the primary spec per symbol and timeframe")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest(); return
    if a.null:
        rows = []
        for sym in a.symbols.split(","):
            m1 = load_m1(sym); W = windows(SYMBOLS[sym][3])
            for tf in a.tfs.split(","):
                evs = []
                for seed in range(a.null):
                    tr = simulate(sym, tf, Spec(), m1, rng=np.random.default_rng(seed)); v, m, ent = day_frames(tr, m1)
                    e = evaluate(v, m, ent, W); e["seed"] = seed; evs.append(e)
                e = pd.concat(evs); e86 = e[e.horizon == 86].groupby("rule")[["pass_pct", "loyo_pass_pct"]].mean()
                print(f"NULL {sym} {tf} (mean of {a.null} random-direction runs) Dec31 pass in-sample / leave-1-yr-out: " + ", ".join(f"{r} {e86.loc[r, 'pass_pct']:.0f}/{e86.loc[r, 'loyo_pass_pct']:.0f}%" for r in e86.index), flush=True)
                e.insert(0, "tf", tf); e.insert(0, "symbol", sym); rows.append(e)
        pd.concat(rows).to_csv(HERE / "trendline_eval_null.csv", index=False)
        return
    variants = [Spec()] + ([] if a.quick else [Spec(L=20), Spec(L=50), Spec(stop_atr=1.0), Spec(stop_atr=2.5), Spec(hold=6), Spec(hold=24)])
    rows, stats = [], []
    for sym in a.symbols.split(","):
        m1 = load_m1(sym); W = windows(SYMBOLS[sym][3])
        for tf in a.tfs.split(","):
            for spec in variants:
                tr = simulate(sym, tf, spec, m1)
                v, m, ent = day_frames(tr, m1)
                ts = trade_stats(tr, v); ts.update(symbol=sym, tf=tf, spec=spec.tag()); stats.append(ts)
                ev = evaluate(v, m, ent, W); ev.insert(0, "spec", spec.tag()); ev.insert(0, "tf", tf); ev.insert(0, "symbol", sym)
                rows.append(ev)
                e86 = ev[ev.horizon == 86].set_index("rule")
                print(f"{sym} {tf} {spec.tag():<22} trades {ts['trades']:>5} ({ts.get('per_year', 0):.0f}/yr) win {ts.get('win_pct', 0):.0f}% meanR {ts.get('mean_R', 0):+.3f} (t {ts.get('t_stat', 0):+.1f}, pre-cost {ts.get('mean_R_before_costs', 0):+.3f}) PF {ts.get('profit_factor', 0):.2f}"
                      f" | Dec31 pass in-sample / leave-1-yr-out: MT5 1-Step {e86.loc['MT5 1-Step', 'pass_pct']:.0f}/{e86.loc['MT5 1-Step', 'loyo_pass_pct']:.0f}%, MT5 2-Step {e86.loc['MT5 2-Step', 'pass_pct']:.0f}/{e86.loc['MT5 2-Step', 'loyo_pass_pct']:.0f}%,"
                      f" Broker 2-Step {e86.loc['Broker 2-Step', 'pass_pct']:.0f}/{e86.loc['Broker 2-Step', 'loyo_pass_pct']:.0f}%", flush=True)
    pd.concat(rows).to_csv(HERE / "trendline_eval_results.csv", index=False)
    pd.DataFrame(stats).to_csv(HERE / "trendline_eval_trades.csv", index=False)


if __name__ == "__main__":
    main()
