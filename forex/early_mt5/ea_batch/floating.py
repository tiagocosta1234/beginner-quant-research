"""Round 347d -- FLOATING-LOSS AWARENESS for the batch scorer (written 2026-10-06 at the trader's request, after the XAUUSD EA's closed-deal odds turned out to be about twice the real ones).

WHY: the scorer replays each EA's CLOSED daily P&L. MT5 broker and Broker test the account's EQUITY at any moment, so an EA that sits on a deep floating loss and closes it later looks safe in
that replay and is not (XAUUSD 5 minute: 38% / 43% closed-deal odds by Dec 31 became about 22% / 21% with floating losses counted; at 0.10 lot, 2022 would have crossed the 10% limit).
WHAT THIS MODULE DOES for one EA run (deals CSV + symbol): rebuild its intraday equity from MT5 broker's own 1-minute bid/ask bars (forex/early_mt5/data/<SYMBOL>_M1_ticks_full.parquet) and return, per day,
  v  the day's realized P&L (profit + commission + swap, as analyze_reports.daily_pnl)
  m  the lowest equity of the day relative to the day's OPENING balance, at the tested lot (m <= v; scale both linearly for another lot)
so a replay can test the daily-loss and maximum-loss floors against equity, the way the firms do.
HOW: (1) pair every 'out' deal with the open 'in' deal it closes. The deal list has no ticket and no side, so the pairing is by profit: profit = side * (exit - entry) * volume * K, where K
(P&L in dollars per price unit per lot: contract size times the quote-to-USD rate) is NOT assumed but calibrated from the EA's own trades (a rolling median, so JPY / CHF quotes that move with the
rate are followed). Pass 1 pairs first-in-first-out to estimate K; pass 2 re-pairs choosing, among the open positions of the same volume, the one whose implied K matches best. The side is the sign
of profit * (exit - entry). A position whose side cannot be read (a zero-profit exit) is marked at the worse of its two possible sides, never the better. (2) For each minute a position is open
its floating P&L is marked at the bar's WORST price: bid low for a buy, ask high for a sell (a hedged book cannot hit both extremes in one minute, so this errs on the safe side); the entry bar is
marked at the close (so the spread cost shows) and the exit bar carries only the realized result. (3) VALIDATION, always: the rebuilt maximal peak-to-trough equity drawdown must land within
[RATIO_LO, RATIO_HI] of the tester's own "Equity Drawdown Maximal" (status.csv eq_dd). XAUUSD 5 minute: 0.98-1.02 in all five years. Outside the band the rebuild is NOT trusted (status "mismatch").
SYMBOLS: the symbol's own M1 file; FX crosses without one (GBPJPY, EURJPY, ...) are built from their two dollar legs (bid = bid / ask, extremes taken pessimistically, which can only overstate
floating losses); a symbol with no price data gets status "no_prices" and keeps its closed-deal numbers, flagged. Results are cached per (EA, year, file content) in floating_cache/.

STATUS: "ok" verified | "no_prices" | "multi_symbol" (its entry prices are not the chart symbol's: a multi-currency EA) | "mismatch" | "no_dd" (the tester reported no equity drawdown) | "no_k" (cannot calibrate) | "few_trades".

  python -m mt5broker.ea_batch.floating                     # survey: every EA in results_2026/, status counts and the drawdown ratio
  python -m mt5broker.ea_batch.floating --id 15581          # one EA in detail
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = Path(os.getenv("MT5BROKER_DATA_DIR") or HERE.parent.parent / "mt5broker" / "data")
CACHE = Path(os.getenv("EA_BATCH_FLOAT_CACHE") or HERE / "floating_cache")
RATIO_LO, RATIO_HI = 0.85, 1.30        # rebuilt max equity drawdown / the tester's own: inside this band the rebuild is trusted
MIN_POSITIONS = 8
ALGO = "4"                              # bump when the rebuild logic changes: it is part of the cache key
_BAR_COLS = ["time", "low", "high", "close", "ask_low", "ask_high", "ask_close"]
_memo: dict = {}


@dataclass
class Floating:
    status: str
    ratio: float = float("nan")
    dd_rebuilt: float = float("nan")
    dd_tester: float = float("nan")
    v: pd.Series | None = None          # realized P&L per day at the tested lot
    m: pd.Series | None = None          # lowest equity of the day relative to the day's opening balance, at the tested lot
    diag: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "ok"


# ------------------------------------------------------------------ price bars
def _direct(sym: str, t0, t1):
    key = (sym, str(t0), str(t1))
    if key in _memo:
        return _memo[key]
    f = DATA / f"{sym}_M1_ticks_full.parquet"
    out = None
    if f.exists():
        a, b = int(pd.Timestamp(t0).timestamp()), int(pd.Timestamp(t1).timestamp())
        d = pd.read_parquet(f, columns=_BAR_COLS, filters=[("time", ">=", a), ("time", "<=", b)])
        d.index = pd.to_datetime(d.pop("time"), unit="s")
        d.columns = ["bl", "bh", "bc", "al", "ah", "ac"]                # bid low / high / close, ask low / high / close
        out = d.sort_index()
    _memo[key] = out
    return out


def _leg(ccy: str, t0, t1):
    """One unit of `ccy` in USD as bid / ask bars (None if that leg has no data)."""
    if ccy in ("EUR", "GBP", "AUD", "NZD"):
        return _direct(ccy + "USD", t0, t1)
    if ccy in ("JPY", "CHF", "CAD"):
        d = _direct("USD" + ccy, t0, t1)
        if d is None:
            return None
        return pd.DataFrame(dict(bl=1 / d.ah, bh=1 / d.al, bc=1 / d.ac, al=1 / d.bh, ah=1 / d.bl, ac=1 / d.bc))
    return None


def bars_for(symbol: str, t0, t1):
    """(bars, how) for the symbol, or (None, reason). `how` = "direct" or "synthetic cross"."""
    d = _direct(symbol, t0, t1)
    if d is not None:
        return d, "direct"
    s = str(symbol)
    if len(s) == 6 and s[:3] != "USD" and s[3:] != "USD":
        a, b = _leg(s[:3], t0, t1), _leg(s[3:], t0, t1)
        if a is not None and b is not None:
            j = a.join(b, how="inner", lsuffix="_a", rsuffix="_b")
            x = pd.DataFrame(index=j.index)
            x["bl"] = j.bl_a / j.ah_b; x["bh"] = j.bh_a / j.al_b; x["bc"] = j.bc_a / j.ac_b       # value of a in b: bid = bid(a) / ask(b), extremes pessimistic
            x["al"] = j.al_a / j.bh_b; x["ah"] = j.ah_a / j.bl_b; x["ac"] = j.ac_a / j.bc_b
            return x, "synthetic cross"
    return None, "no price file for " + s



def prior_k(symbol: str, t0, t1):
    """Dollars per price unit per lot as a function of time (ns epoch), when the contract is standard: FX pairs 100,000 x the quote currency's USD value at that time, XAUUSD 100.
    None when it must be calibrated from the trades instead (indices, crypto, NZD quotes)."""
    s = str(symbol)
    if s == "XAUUSD":
        return lambda x: 100.0
    if len(s) == 6 and s[:3].isalpha() and s[3:].isalpha():
        q = s[3:]
        if q == "USD":
            return lambda x: 100_000.0
        if q in ("JPY", "CHF", "CAD"):
            d = _direct("USD" + q, t0, t1)
            if d is None:
                return None
            tk, px = d.index.values.astype("datetime64[ns]").astype(np.int64), 1.0 / d.bc.values
        elif q in ("EUR", "GBP", "AUD"):
            d = _direct(q + "USD", t0, t1)
            if d is None:
                return None
            tk, px = d.index.values.astype("datetime64[ns]").astype(np.int64), d.bc.values
        else:
            return None
        return lambda x: 100_000.0 * float(np.interp(np.int64(x), tk, px))
    return None

# ------------------------------------------------------------------ pairing
def _khat_fn(te_ts, ks):
    """Time -> K from the positions matched so far (rolling median of the implied K, interpolated); None if there is too little to calibrate."""
    ks = np.asarray(ks, float); te_ts = np.asarray(te_ts, np.int64)
    ok = np.isfinite(ks) & (ks > 0)
    if ok.sum() < 3:
        return None
    t, k = te_ts[ok], ks[ok]
    o = np.argsort(t); t, k = t[o], k[o]
    med = pd.Series(k).rolling(21, center=True, min_periods=3).median().bfill().ffill().values
    return lambda x: float(np.interp(np.int64(x), t, med))


def _match(t, direction, vol, price, profit, khat):
    """One pass of pairing: FIFO among same-volume opens when khat is None, else the open position whose implied K matches best. Rows: (i_in, i_out, entry, exit, volume, profit)."""
    open_, rows = [], []
    for i in range(len(t)):
        if direction[i] == "in":
            open_.append([i, price[i], vol[i]])
            continue
        vo, po, pr = vol[i], price[i], profit[i]
        cands = [j for j, o in enumerate(open_) if abs(o[2] - vo) < 1e-9]
        partial = False
        if not cands:
            cands = [j for j, o in enumerate(open_) if o[2] > vo + 1e-9]; partial = True
        if not cands:
            continue
        j = cands[0]
        if khat is not None and len(cands) > 1:
            kt, best = khat(t[i]), None
            for c in cands:
                d = po - open_[c][1]
                if abs(pr) < 0.005 or d == 0:
                    sc = 0.0 if (abs(pr) < 0.005 and d == 0) else 5.0
                else:
                    sc = abs(np.log(abs(pr) / (abs(d) * vo) / kt))
                if best is None or sc < best[0] - 1e-12:
                    best = (sc, c)
            j = best[1]
        o = open_[j]
        if partial:
            o[2] -= vo
        else:
            open_.pop(j)
        rows.append((o[0], i, o[1], po, vo, pr))
    return rows


def pair_positions(deals: pd.DataFrame, kprior=None):
    """Positions with side and K: DataFrame(te, tx, pe, px, v, profit, side, k) and a diagnostics dict, or (None, diag) if K cannot be calibrated."""
    tt = pd.to_datetime(deals.time.astype(str).str.replace(".", "-", regex=False))
    t = tt.values.astype("datetime64[ns]").astype(np.int64)
    direction, vol = deals.direction.values, deals.volume.values.astype(float)
    price, profit = deals.price.values.astype(float), deals.profit.values.astype(float)

    def implied(rows):
        k = []
        for (_, _, pe, px, v, pr) in rows:
            d = abs(px - pe) * v
            k.append(abs(pr) / d if (d > 0 and abs(pr) >= 0.5) else np.nan)
        return np.array(k)

    if kprior is not None:
        kh = kprior                                                          # standard contract: no calibration needed
    else:
        rows = _match(t, direction, vol, price, profit, None)
        if not rows:
            return None, dict(positions=0, reason="no closed positions")
        kh = _khat_fn([t[r[0]] for r in rows], implied(rows))
        if kh is None:
            return None, dict(positions=len(rows), reason="cannot calibrate K")
    rows = _match(t, direction, vol, price, profit, kh)                       # K-guided pairing
    if not rows:
        return None, dict(positions=0, reason="no closed positions")
    k_imp = implied(rows)
    kh2 = kprior if kprior is not None else _khat_fn([t[r[0]] for r in rows], k_imp)
    pos = pd.DataFrame(rows, columns=["i0", "i1", "pe", "px", "v", "profit"])
    pos["te"] = t[pos.i0.values]; pos["tx"] = t[pos.i1.values]
    d = pos.px - pos.pe
    sig = (pos.profit.abs() >= 0.005) & (d != 0)
    pos["side"] = np.where(sig, np.sign(pos.profit) * np.sign(d), 0).astype(int)
    pos["k"] = [kh2(x) if kh2 else np.nan for x in pos.te.values]
    fin = np.isfinite(k_imp) & (k_imp > 0)
    rel = np.abs(np.log(k_imp[fin] / np.array([kh2(x) for x in pos.tx.values[fin]]))) if fin.any() else np.array([np.nan])
    diag = dict(positions=len(pos), unmatched_out=int((direction == "out").sum() - len(pos)), ambiguous=int((pos.side == 0).sum()),
                k_median=float(np.nanmedian(k_imp)), k_misfit_median=float(np.nanmedian(rel)), k_misfit_p90=float(np.nanpercentile(rel, 90)) if len(rel) else float("nan"))
    return pos, diag



def _bar_idx(ts, t):
    """Index of the minute bar that CONTAINS time t (bar start <= t < next bar start), clipped to the file."""
    return np.clip(np.searchsorted(ts, t, side="right") - 1, 0, len(ts) - 1)

# ------------------------------------------------------------------ equity rebuild
def rebuild(deals: pd.DataFrame, bars: pd.DataFrame, kprior=None):
    """(frames, drawdowns, diagnostics): frames = {"mid": DataFrame(v, m), "hi": DataFrame(v, m)} per bar-day at the tested lot; drawdowns = maximal peak-to-trough equity drawdown of the
    rebuilt curve under three markings: "lo" every open minute at the bar CLOSE; "mid" worst price on the minutes strictly between entry and exit, close on the entry bar, nothing on the exit bar
    (what the XAUUSD EA validated at 0.99); "hi" worst price on EVERY minute the position was open, entry and exit bars included (before its exit the position is taken at the bar's extreme).
    The tester's own figure, computed on ticks, lies between lo and hi."""
    pos, diag = pair_positions(deals, kprior)
    if pos is None:
        return None, None, diag
    ts = bars.index.values.astype("datetime64[ns]").astype(np.int64)
    n = len(ts)
    bl, bh, bc, al, ah, ac = (bars[c].values for c in ("bl", "bh", "bc", "al", "ah", "ac"))
    d = deals.copy()
    d["t"] = pd.to_datetime(d.time.astype(str).str.replace(".", "-", regex=False))
    net = (d.profit + d.commission + d.swap).values
    real = np.zeros(n)
    np.add.at(real, _bar_idx(ts, d.t.values.astype("datetime64[ns]").astype(np.int64)), net)
    R = np.cumsum(real)
    Fc, Fm, Fh, Sh = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    for p in pos.itertuples():
        i0 = int(_bar_idx(ts, p.te)); i1 = int(_bar_idx(ts, p.tx))
        if not np.isfinite(p.k):
            continue
        kv = p.v * p.k
        if p.side == 1:
            wl, cl = (bl - p.pe) * kv, (bc - p.pe) * kv
        elif p.side == -1:
            wl, cl = (p.pe - ah) * kv, (p.pe - ac) * kv
        else:                                                                    # side unreadable: the worse of the two
            wl, cl = np.minimum(bl - p.pe, p.pe - ah) * kv, np.minimum(bc - p.pe, p.pe - ac) * kv
        if i1 > i0:
            Fc[i0:i1] += cl[i0:i1]
            Fm[i0] += cl[i0]; Fm[i0 + 1:i1] += wl[i0 + 1:i1]
            Fh[i0:i1] += wl[i0:i1]
        Sh[i1] += min(wl[i1] - net[p.i1], 0.0)                                   # hi only: the minute of the exit, taken just before it
    day = bars.index.values.astype("datetime64[D]")
    start = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    days = pd.DatetimeIndex(day[start])
    before = np.where(start > 0, R[np.maximum(start - 1, 0)], 0.0)                # realized strictly before each bar-day
    v = pd.Series(net, index=d.t.dt.normalize()).groupby(level=0).sum().reindex(days).fillna(0.0).values
    e_lo, e_mid, e_hi = R + Fc, R + Fm, R + Fh + Sh

    def maxdd(eq):
        e = np.concatenate([[0.0], eq])
        return float((np.maximum.accumulate(e) - e).max())

    def frame(eq):
        return pd.DataFrame({"v": v, "m": np.minimum(np.minimum.reduceat(eq, start) - before, v)}, index=days)
    diag["net"] = float(net.sum())
    return {"mid": frame(e_mid), "hi": frame(e_hi)}, {"lo": maxdd(e_lo), "mid": maxdd(e_mid), "hi": maxdd(e_hi)}, diag


def _inside_share(deals: pd.DataFrame, bars: pd.DataFrame) -> float:
    """Share of entry prices that lie inside the [bid low, ask high] of their own minute: ~99% when the price file is the EA's symbol (XAUUSD: 99.7%); far lower for a multi-symbol EA."""
    ins = deals[deals.direction == "in"]
    if ins.empty:
        return float("nan")
    t = pd.to_datetime(ins.time.astype(str).str.replace(".", "-", regex=False)).values.astype("datetime64[ns]").astype(np.int64)
    ts = bars.index.values.astype("datetime64[ns]").astype(np.int64)
    i = _bar_idx(ts, t)
    p = ins.price.values.astype(float)
    return float(((p >= bars.bl.values[i] - 1e-9) & (p <= bars.ah.values[i] + 1e-9)).mean())


def compute(deals: pd.DataFrame, symbol: str, tester_dd: float, start: str, end: str) -> Floating:
    if not (tester_dd > 0):
        return Floating("no_dd")
    t0, t1 = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
    bars, how = bars_for(symbol, t0, t1)
    if bars is None or bars.empty:
        return Floating("no_prices", diag=dict(reason=how))
    inside = _inside_share(deals, bars)
    if not inside >= 0.90:
        return Floating("multi_symbol", diag=dict(bars=how, price_inside=inside))
    frames, dds, diag = rebuild(deals, bars, prior_k(symbol, t0, t1))
    diag["bars"] = how; diag["price_inside"] = inside
    if frames is None:
        return Floating("no_k", diag=diag)
    if diag["positions"] < MIN_POSITIONS:
        return Floating("few_trades", diag=diag)
    diag.update(ratio_lo=dds["lo"] / tester_dd, ratio_mid=dds["mid"] / tester_dd, ratio_hi=dds["hi"] / tester_dd)
    for basis in ("mid", "hi"):
        r = dds[basis] / tester_dd
        if RATIO_LO <= r <= RATIO_HI:
            diag["basis"] = basis
            return Floating("ok", ratio=r, dd_rebuilt=dds[basis], dd_tester=tester_dd, v=frames[basis].v, m=frames[basis].m, diag=diag)
    return Floating("mismatch", ratio=dds["mid"] / tester_dd, dd_rebuilt=dds["mid"], dd_tester=tester_dd, diag=diag)


def get(eid: str, year: int, csv: Path, symbol: str, tester_dd: float, start: str, end: str) -> Floating:
    """compute() with a cache keyed by the deals file's content (the batch rewrites a file only when it re-runs the EA)."""
    csv = Path(csv)
    h = hashlib.md5(csv.read_bytes() + f"{ALGO}|{symbol}|{tester_dd}|{start}|{end}".encode()).hexdigest()[:12]
    cf = CACHE / str(year) / f"{eid}_{h}.json"
    if cf.exists():
        try:
            j = json.loads(cf.read_text())
            idx = pd.DatetimeIndex(j["days"]) if j.get("days") else None
            return Floating(j["status"], j["ratio"], j["dd_rebuilt"], j["dd_tester"], pd.Series(j["v"], index=idx) if idx is not None else None,
                            pd.Series(j["m"], index=idx) if idx is not None else None, j.get("diag", {}))
        except Exception:
            pass
    f = compute(pd.read_csv(csv), symbol, tester_dd, start, end)
    try:
        cf.parent.mkdir(parents=True, exist_ok=True)
        cf.write_text(json.dumps(dict(status=f.status, ratio=f.ratio, dd_rebuilt=f.dd_rebuilt, dd_tester=f.dd_tester, diag={k: (v if not isinstance(v, (np.floating, np.integer)) else float(v)) for k, v in f.diag.items()},
                                      days=[str(x.date()) for x in f.m.index] if f.m is not None else None, v=list(map(float, f.v.values)) if f.v is not None else None,
                                      m=list(map(float, f.m.values)) if f.m is not None else None)))
    except Exception:
        pass
    return f


# ------------------------------------------------------------------ equity-aware replays (MT5 broker rules, $100K) -- the same logic as analyze_2026.replay_1step / replay_2step
INITIAL = 100_000.0


def replay_1step_eq(pnl: dict, mm, days):
    """(outcome, calendar days from the first day to the outcome day) of one MT5 1-Step attempt over `days` (+10%, 3% daily loss, 10% floor trailing the highest end-of-day balance, best day
    <= 50% of the positive days' profit). The floors are tested on the day's worst EQUITY, mm[day] = lowest equity of the day relative to its opening balance; mm = None tests closed P&L only
    and is identical to analyze_2026.replay_1step."""
    bal = hwm = INITIAL; pos = best = 0.0
    for d in days:
        v = pnl.get(d, 0.0)
        m = v if mm is None else min(mm.get(d, 0.0), v)
        hwm = max(hwm, bal)
        if m < -3_000:
            return "breach", (d - days[0]).days + 1
        if bal + m <= hwm - 10_000:
            return "breach", (d - days[0]).days + 1
        bal += v
        if v > 0:
            pos += v; best = max(best, v)
        if bal > 110_000 and best <= 0.5 * pos:
            return "pass", (d - days[0]).days + 1
    return "open", None


def replay_2step_eq(pnl: dict, mm, ent: set, days) -> str:
    """MT5 2-Step, both phases (+10% then +5%, 5% daily loss, static $90K floor, 4 trading days each, Phase 2 two weekdays after Phase 1), floors on the day's worst equity (mm = None: closed P&L,
    identical to analyze_2026.replay_2step)."""
    def phase(i, target):
        bal, tds = INITIAL, set()
        while i < len(days):
            d = days[i]; v = pnl.get(d, 0.0)
            m = v if mm is None else min(mm.get(d, 0.0), v)
            if d in ent:
                tds.add(d)
            if m < -5_000 or bal + m < 90_000:
                return "breach", i + 1
            bal += v
            if bal > target and len(tds) >= 4:
                return "pass", i + 1
            i += 1
        return "open", i
    o1, i = phase(0, 110_000.0)
    return o1 if o1 != "pass" else phase(i + 2, 105_000.0)[0]


def chances_eq(raw: pd.Series, m: pd.Series, ent: set, lam: float, windows: dict) -> dict:
    """analyze_2026.chances with the floors tested on equity: p1_H / b1_H (1-Step pass / breach), p2_H / b2_H (2-Step both phases), ret30 / ret60 (closed returns), days30 / days60 (calendar days to pass)."""
    pnl = (raw * lam).to_dict(); mm = (m * lam).to_dict(); out = {}
    for H, day_lists in windows.items():
        r1 = [replay_1step_eq(pnl, mm, dl) for dl in day_lists]; r2 = [replay_2step_eq(pnl, mm, ent, dl) for dl in day_lists]
        out.update({f"p1_{H}": float(np.mean([x[0] == "pass" for x in r1])), f"b1_{H}": float(np.mean([x[0] == "breach" for x in r1])),
                    f"p2_{H}": float(np.mean([x == "pass" for x in r2])), f"b2_{H}": float(np.mean([x == "breach" for x in r2]))})
        if H in (30, 60):
            ret = np.array([sum(pnl.get(d, 0.0) for d in dl) for dl in day_lists]) / INITIAL * 100
            dp = [x[1] for x in r1 if x[0] == "pass"]
            out.update({f"ret{H}_mean": float(ret.mean()), f"ret{H}_best": float(ret.max()), f"days{H}_med": float(np.median(dp)) if dp else float("nan"),
                        f"days{H}_mean": float(np.mean(dp)) if dp else float("nan")})
    return out


# ------------------------------------------------------------------ survey / CLI
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(HERE / "results_2026")); ap.add_argument("--id", default=""); ap.add_argument("--start", default="2026-01-01"); ap.add_argument("--end", default="2026-09-30")
    a = ap.parse_args(argv)
    res = Path(a.results)
    st = pd.read_csv(res / "status.csv", dtype={"id": str}).drop_duplicates("id", keep="last")
    st = st[st.deals > 0]
    if a.id:
        st = st[st.id == a.id]
    rows = []
    for r in st.itertuples():
        f = get(r.id, 0, res / f"{r.id}.csv", r.symbol, float(r.eq_dd) if pd.notna(r.eq_dd) else float("nan"), a.start, a.end)
        rows.append(dict(id=r.id, title=str(r.title)[:30], symbol=r.symbol, status=f.status, ratio=f.ratio, positions=f.diag.get("positions"), ambiguous=f.diag.get("ambiguous"),
                         k_misfit_p90=f.diag.get("k_misfit_p90"), bars=f.diag.get("bars", "")))
    out = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    if a.id:
        print(out.to_string(index=False)); return out
    print(out.status.value_counts().to_string())
    ok = out[out.status.isin(["ok", "mismatch"])]
    print("\nrebuilt / tester equity drawdown (EAs with price data): " + ok.ratio.describe(percentiles=[.05, .25, .5, .75, .95]).round(2).to_string().replace("\n", " | "))
    print("\nby symbol:"); print(out.groupby(["symbol", "status"]).size().unstack(fill_value=0).to_string())
    out.to_csv(HERE / "floating_survey.csv", index=False)
    return out


if __name__ == "__main__":
    main()
