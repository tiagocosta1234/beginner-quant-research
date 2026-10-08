"""Inverted entries with REALISED exits (the trader 2026-10-08: "realise the profit and then open the position again").   python -m mt5broker.ea_batch.inv_realize
LESSON 40 showed the CONFIRMED inversions were a stop-out artifact (all positions closed on one day). Here every ORIGINAL entry of the two EAs (16081 Exp_CandlesticksBW EURUSD, 15888 Exp_JFatl_Digit_System GBPUSD; entry times and directions from the second PC's year-runs 2023 / 2024 / 2025, only while the original was alive) is mirrored (opposite direction, 0.10 lot, entry at the open of that minute on the MT5 broker tick-built M1 bid / ask bars) and closed by its OWN exit: take profit TP pips or stop loss SL pips (stop first when both fall in one minute), or at market after 60 days. Costs: real bid / ask plus USD 6 a 100K lot round turn. Each exit is a separate trade on its own day.
PRE-REGISTERED 2026-10-08 BEFORE RUNNING. Grid: TP in {10, 20, 40, 80} pips x SL in {20, 40, 80, 160} pips = 16 variants per EA, 32 cells (k = 32). A cell is a HIT if net P&L > 0 in EACH of the three years AND the pooled per-trade t >= 3.1 (Bonferroni 0.05 / 32) AND no more than 50% of the profit comes from trades closing on one calendar day AND at most 20 positions are open at once.
Reported for every cell: trades, net USD at 0.10 lot, win rate, t, worst day, max closed drawdown, max concurrent positions. Nothing else is tuned; if no cell hits the idea is closed."""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from mt5broker.ea_batch import floating
from mt5broker.intraday_lab import sdb

HERE = __import__("pathlib").Path(__file__).resolve().parent
EAS = (("16081", "EURUSD"), ("15888", "GBPUSD"))
YEARS = (2023, 2024, 2025)
PIP, UNITS, COMM = 1e-4, 10_000.0, 0.6                    # 0.10 lot = 10,000 units: USD 1 a pip on a USD-quoted pair; USD 6 a 100K lot round turn = 0.6
TPS, SLS, MAXH = (10, 20, 40, 80), (20, 40, 80, 160), 60 * 1440


def entries(eid, sym, year):
    d = pd.read_csv(HERE / f"results_inv_{year}" / f"{eid}.csv")
    pos, _ = floating.pair_positions(d, floating.prior_k(sym, pd.Timestamp(f"{year}-01-01"), pd.Timestamp(f"{year}-12-31")))
    pos = pos.copy(); pos["te"] = pd.to_datetime(pos.te)
    return pos.sort_values("te")[["te", "side"]].reset_index(drop=True)


def simulate(m, ent, tp, sl):
    t = m["t"]; out = []
    for te, side in zip(ent.te.values.astype("datetime64[s]").astype("int64"), ent.side.values):
        a = int(np.searchsorted(t, te)); d = -int(side)                       # mirrored direction
        if a >= len(t) - 2: continue
        b = min(len(t), a + MAXH)
        if d > 0:
            e = m["ao"][a]; hit_tp = m["bh"][a:b] >= e + tp * PIP; hit_sl = m["bl"][a:b] <= e - sl * PIP
        else:
            e = m["bo"][a]; hit_tp = m["al"][a:b] <= e - tp * PIP; hit_sl = m["ah"][a:b] >= e + sl * PIP
        i_tp = int(np.argmax(hit_tp)) if hit_tp.any() else 10 ** 9; i_sl = int(np.argmax(hit_sl)) if hit_sl.any() else 10 ** 9
        if i_sl <= i_tp and i_sl < 10 ** 9: j, px = i_sl, (e - sl * PIP if d > 0 else e + sl * PIP)
        elif i_tp < 10 ** 9: j, px = i_tp, (e + tp * PIP if d > 0 else e - tp * PIP)
        else: j = b - a - 1; px = m["bc"][a + j] if d > 0 else m["ac"][a + j]
        out.append((int(t[a]), int(t[min(a + j, len(t) - 1)]), (px - e) * d * UNITS - COMM))
    return pd.DataFrame(out, columns=["t0", "t1", "pnl"])


def stats(tr):
    if len(tr) < 5: return None
    p = tr.pnl.values; day = pd.to_datetime(tr.t1, unit="s").dt.date
    dp = tr.groupby(day).pnl.sum(); big = dp.max() / p.sum() if p.sum() > 0 else np.nan
    ev = np.r_[np.ones(len(tr)), -np.ones(len(tr))]; ts = np.r_[tr.t0.values, tr.t1.values]
    conc = int(np.cumsum(ev[np.argsort(ts, kind="stable")]).max())
    eq = np.cumsum(tr.sort_values("t1").pnl.values); dd = (eq - np.maximum.accumulate(np.r_[0.0, eq])[1:]).min()
    return dict(n=len(p), net=p.sum(), win=(p > 0).mean(), t=p.mean() / p.std(ddof=1) * np.sqrt(len(p)) if p.std() > 0 else np.nan, worst_day=dp.min(), top_day_share=big, dd=dd, conc=conc)


def main():
    for eid, sym in EAS:
        m = sdb.load_m1(sym); ents = {y: entries(eid, sym, y) for y in YEARS}
        print(f"\n===== {eid} {sym}: entries per year {[len(e) for e in ents.values()]} =====")
        print("TP/SL pips | net 2023 / 2024 / 2025 (USD, 0.10 lot) | trades | win% | pooled t | worst day | max DD | max open | top-day share | HIT")
        for tp, sl in itertools.product(TPS, SLS):
            per = {y: simulate(m, ents[y], tp, sl) for y in YEARS}
            sy = {y: stats(per[y]) for y in YEARS}; allt = pd.concat(per.values()); sa = stats(allt)
            nets = [sy[y]["net"] if sy[y] else float("nan") for y in YEARS]
            hit = all(n > 0 for n in nets) and sa["t"] >= 3.1 and max(s["top_day_share"] for s in sy.values() if s) <= 0.5 and max(s["conc"] for s in sy.values() if s) <= 20
            print(f"{tp:>3}/{sl:<3} | {nets[0]:8,.0f} / {nets[1]:8,.0f} / {nets[2]:8,.0f} | {sa['n']:4} | {sa['win']:4.0%} | {sa['t']:+5.2f} | {sa['worst_day']:7,.0f} | {sa['dd']:8,.0f} | {max(s['conc'] for s in sy.values() if s):3} | {max(s['top_day_share'] for s in sy.values() if s):4.0%} | {'HIT' if hit else 'no'}", flush=True)


if __name__ == "__main__":
    main()
