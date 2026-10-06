"""Round 347k -- six PRE-REGISTERED stock strategies from the published literature on MT5 broker stock CFDs (the trader: "generate a really good strategy for stocks trading").

HONEST FRAME. Nobody can design a strategy that is known to work by thinking about it; this module writes down the best-documented candidates BEFORE any result, runs each once with real costs, and reports
all of them. 6 candidates x the available stocks is a small multiple-testing family: a candidate counts only if its net R per trade has t >= 2.5 AND it beats a coin-flip-side null AND it survives a
split of the sample in halves. Data: MT5 broker tick-built 1-minute bid / ask bars (MSFT, NVDA 2021-10..2026-10; AMD, INTC 2026-01..2026-10), NY time = server - 7 h, quotes ~09:35..15:59.

CANDIDATES (all long-AND-short unless stated; one position at a time; costs = real bid / ask + commission 0.004% of the notional per side; held overnight pays the CFD swap 5.4% a year long / 4.2% short):
  S1 ORB-5       Zarattini-Barbon-Aziz (2024) opening-range breakout: range = first 5 minutes of quotes; first break of the range high (long) or low (short) before 15:00; stop at the opposite side of the range; exit 15:55.
  S2 ORB-30      the same with the 09:30-10:00 range, entries until 15:00.
  S3 ORB-5 + RV  S1 only on days whose first-5-minute tick count is >= 1.5x its 14-day average ("stocks in play", the paper's key filter; relative tick volume stands in for share volume).
  S4 GAP-GO      gap = open vs previous 15:59 close; if |gap| >= 1.0% trade in the gap's direction from 10:00 (ask / bid), stop 1.0 x the opening range away, exit 15:55 (the "gap and go" continuation).
  S5 OVERNIGHT   long from 15:55 to the next 09:40 (the documented stock overnight drift); pays the long swap for each night.
  S6 TREND       Moskowitz-Ooi-Pedersen style time-series momentum: long when the 15:55 price is above its 100-day mean of daily closes, short when below, rebalanced daily at 15:55 (a flip costs a spread); pays swap.
SIZE  trades are scored in R (the stop distance = 1R) for S1-S4; S5 / S6 have no stop: 1R = 1% of the price (a fixed convention, only for the t-stat). Pass rates use the equity-aware MT5 / Broker replay from
      ote_stdv_stocks.py (leverage cap 3.3x, risk r swept).
NULL  coin-flip side at the same entry minutes and exits;  BENCHMARK  the same stock bought and held (for S5 / S6).

  python -m mt5broker.ea_batch.stock_candidates
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from mt5broker.ea_batch import ote_stdv_stocks as OS
from mt5broker.ea_batch import trendline_eval as T

SYMS = ("MSFT", "NVDA", "AMD", "INTC")
SWAP_LONG, SWAP_SHORT = 0.054 / 365, 0.042 / 365


class Day:
    pass


def load(sym):
    m1 = T.load_m1(sym)
    tv = pd.read_parquet(T.DATA / T.SYMBOLS[sym][0], columns=["time", "tick_volume"])
    m1["tick_volume"] = tv.tick_volume.values[np.argsort(tv.time.values, kind="stable")] if len(tv) == len(m1) else np.nan
    nym = m1.index.values.astype("datetime64[m]").astype(np.int64) - 420
    d = nym // 1440
    st = np.flatnonzero(np.r_[True, d[1:] != d[:-1]]); en = np.r_[st[1:], len(d)]
    return m1, nym, d[st], st, en


def row(i0, i1, side, pe, px, dist, nights, m1):
    lots = T.RISK_REF / dist
    ao, bo = m1.ask_open.values, m1.open.values
    spr = 0.5 * ((ao[i0] - bo[i0]) + (ao[i1] - bo[i1])) * lots
    swap = abs(pe) * lots * (SWAP_LONG if side == 1 else SWAP_SHORT) * nights
    return dict(i0=i0, i1=i1, side=side, pe=pe, px=px, lots=lots, k=1.0, gross=side * (px - pe) * lots - swap, comm=0.0, spread=spr, dist=dist, c=i1, day=0, swap=swap)


def intraday(sym, kind, m1, nym, days, st, en, rng=None):
    """S1-S4. Returns the trades of one stock."""
    bo, bh, bl = m1.open.values, m1.high.values, m1.low.values
    ao, ah, al = m1.ask_open.values, m1.ask_high.values, m1.ask_low.values
    mh, ml = (bh + ah) / 2, (bl + al) / 2
    rows, hist, prev_close = [], [], None
    for k, d in enumerate(days):
        a, b = st[k], en[k]
        t = nym[a:b] - d * 1440                                                       # minute of the NY day
        sel = np.flatnonzero((t >= 570) & (t <= 955)) + a
        if len(sel) < 200:
            continue
        first = sel[0]
        close_prev = prev_close
        prev_close = bo[sel[-1]]
        # exit minute: first minute >= 15:55
        ex = sel[np.searchsorted(nym[sel] - d * 1440, 955)] if (nym[sel] - d * 1440).max() >= 955 else sel[-1]
        if kind in ("S1", "S3", "S4"):
            rend = 575                                                                  # first 5 minutes of quotes: up to 09:40 (quotes begin ~09:35)
            rend = (nym[first] - d * 1440) + 5
        else:
            rend = 600
        rsel = sel[(nym[sel] - d * 1440) < rend]
        if len(rsel) < 3:
            continue
        H, L = mh[rsel].max(), ml[rsel].min()
        after = sel[(nym[sel] - d * 1440 >= rend) & (nym[sel] - d * 1440 <= 900)]
        if kind == "S3":
            tv = len(rsel)                                                              # minute bars in the window cannot proxy volume; use the mean tick volume per minute
            tvol = m1["tick_volume"].values[rsel].sum() if "tick_volume" in m1.columns else np.nan
            hist.append(tvol)
            if len(hist) < 15 or not np.isfinite(tvol) or tvol < 1.5 * np.mean(hist[-15:-1]):
                continue
        if H - L <= 0 or (H - L) / ((H + L) / 2) < 0.0005:
            continue
        if kind == "S4":
            if close_prev is None:
                continue
            gap = (bo[first] - close_prev) / close_prev
            if abs(gap) < 0.01:
                continue
            side = 1 if gap > 0 else -1
            ent = sel[(nym[sel] - d * 1440) >= 600][:1]
            if not len(ent):
                continue
            i0 = int(ent[0]); pe = ao[i0] if side == 1 else bo[i0]
            dist = max(H - L, 0.0005 * pe); stop = pe - side * dist
        else:
            # first break
            up = after[ah[after] >= H]; dn = after[bl[after] <= L]
            iu = int(up[0]) if len(up) else None; idn = int(dn[0]) if len(dn) else None
            if iu is None and idn is None:
                continue
            if iu is not None and idn is not None and iu == idn:
                continue
            if idn is None or (iu is not None and iu < idn):
                side, i0 = 1, iu; pe = max(H, ao[i0]); stop = L
            else:
                side, i0 = -1, idn; pe = min(L, bo[i0]); stop = H
            dist = max(abs(pe - stop), 0.0005 * pe)
            stop = pe - side * dist
        if rng is not None:
            side = 1 if rng.random() < 0.5 else -1
            pe = ao[i0] if side == 1 else bo[i0]; stop = pe - side * dist
        seg = np.arange(i0, ex + 1)
        seg = seg[nym[seg] - d * 1440 <= 955] if len(seg) else seg
        if side == 1:
            hit = np.flatnonzero(bl[seg] <= stop)
        else:
            hit = np.flatnonzero(ah[seg] >= stop)
        if len(hit):
            j = int(seg[hit[0]]); px = min(stop, bo[j]) if side == 1 else max(stop, ao[j]); i1 = j
        else:
            i1 = int(seg[-1]); px = bo[i1] if side == 1 else ao[i1]
        rows.append(row(i0, i1, side, pe if side == 1 else -pe if False else pe, px, dist, 0, m1))
        rows[-1]["day"] = int(d)
    return pd.DataFrame(rows)


def daily_series(m1, nym, days, st, en):
    """Per day: minute index of the 15:55 bar, the 09:40 bar of the day, and the bid / ask there."""
    i1555, i940 = {}, {}
    for k, d in enumerate(days):
        a, b = st[k], en[k]
        t = nym[a:b] - d * 1440
        s = np.flatnonzero(t >= 955)
        if len(s): i1555[int(d)] = a + int(s[0])
        s = np.flatnonzero(t >= 580)
        if len(s): i940[int(d)] = a + int(s[0])
    return i1555, i940


def overnight(m1, nym, days, st, en):
    bo, ao = m1.open.values, m1.ask_open.values
    i1555, i940 = daily_series(m1, nym, days, st, en)
    ds = sorted(i1555); rows = []
    for k in range(len(ds) - 1):
        d0, d1 = ds[k], ds[k + 1]
        if d1 not in i940 or d1 - d0 > 4:
            continue
        i0, i1 = i1555[d0], i940[d1]
        pe, px = ao[i0], bo[i1]
        r = row(i0, i1, 1, pe, px, 0.01 * pe, d1 - d0, m1); r["day"] = int(d0); rows.append(r)
    return pd.DataFrame(rows)


def trend(m1, nym, days, st, en, N=100):
    bo, ao = m1.open.values, m1.ask_open.values
    i1555, _ = daily_series(m1, nym, days, st, en)
    ds = sorted(i1555); closes = np.array([bo[i1555[d]] for d in ds]); rows = []
    pos, entry, ei = 0, None, None
    for k in range(N, len(ds)):
        sig = 1 if closes[k] > closes[k - N + 1:k + 1].mean() else -1
        d = ds[k]; i = i1555[d]
        if pos != 0 and sig != pos:
            px = bo[i] if pos == 1 else ao[i]
            nights = d - ds_entry
            r = row(ei, i, pos, entry, px, 0.01 * entry, nights, m1); r["day"] = int(ds_entry); rows.append(r); pos = 0
        if pos == 0:
            pos, ei, ds_entry = sig, i, d; entry = ao[i] if sig == 1 else bo[i]
    return pd.DataFrame(rows)


def main():
    W = T.windows("B")
    out = []
    for kind in ("S1", "S2", "S3", "S4", "S5", "S6"):
        parts, allR, allN, nullR, bhR = [], [], 0, [], []
        for sym in SYMS:
            if sym not in T.SYMBOLS or not (T.DATA / T.SYMBOLS[sym][0]).exists():
                continue
            m1, nym, days, st, en = load(sym)
            tr = (intraday(sym, kind, m1, nym, days, st, en) if kind in ("S1", "S2", "S3", "S4") else overnight(m1, nym, days, st, en) if kind == "S5" else trend(m1, nym, days, st, en))
            tr = tr[tr.day.map(lambda x: pd.Timestamp(int(x) * 86400, unit="s") >= pd.Timestamp("2022-01-01"))] if len(tr) else tr
            if len(tr) < 15:
                print(f"{kind} {sym}: {len(tr)} trades -- skipped", flush=True); continue
            R = (tr.side.values * (tr.px.values - tr.pe.values) - 2 * OS.COMM * np.abs(tr.pe.values) - tr.swap.values / tr.lots.values) / tr.dist.values
            half = pd.to_datetime(tr.day.values * 86400, unit="s") < pd.Timestamp("2024-07-01")
            print(f"{kind} {sym}: {len(tr)} trades ({len(tr) / 4.75:.0f}/yr, long {np.mean(tr.side == 1):.0%}) win {np.mean(R > 0):.0%} meanR {R.mean():+.3f} (t {R.mean() / (R.std() / np.sqrt(len(R))):+.1f}) halves {R[half].mean():+.3f} / {R[~half].mean():+.3f}", flush=True)
            allR.append(R); parts.append((sym, m1, tr, nym, days, st, en))
        if not allR:
            continue
        R = np.concatenate(allR)
        print(f"  == {kind} pooled: {len(R)} trades, mean R {R.mean():+.3f}, t {R.mean() / (R.std() / np.sqrt(len(R))):+.1f}", flush=True)
        # coin-flip null for the intraday kinds
        if kind in ("S1", "S2", "S3", "S4"):
            rs = []
            for sd in range(10):
                rr = []
                for sym, m1, tr, nym, days, st, en in parts:
                    nt = intraday(sym, kind, m1, nym, days, st, en, rng=np.random.default_rng(sd))
                    nt = nt[nt.day.map(lambda x: pd.Timestamp(int(x) * 86400, unit="s") >= pd.Timestamp("2022-01-01"))]
                    rr.append((nt.side.values * (nt.px.values - nt.pe.values) - 2 * OS.COMM * np.abs(nt.pe.values)) / nt.dist.values)
                rs.append(np.concatenate(rr).mean())
            print(f"  == {kind} coin-flip-side null mean R {np.mean(rs):+.3f} (min..max {min(rs):+.3f}..{max(rs):+.3f}); real {R.mean():+.3f}", flush=True)
        # equity-aware evaluation as one account
        class D_:                                                                       # minimal stand-in: day_frames needs only .m1
            pass
        pl = []
        for sym, m1, tr, *_ in parts:
            d_ = D_(); d_.m1 = m1; pl.append((d_, tr))
        ev = OS.evaluate_capped(pl, W, OS.LEV / 4 if len(pl) > 1 else OS.LEV)
        OS.fmt(ev, f"{kind} ONE ACCOUNT")
        ev["cand"] = kind; out.append(ev)
    pd.concat(out).to_csv(OS.HERE / "stock_candidates_results.csv", index=False)


if __name__ == "__main__":
    main()
