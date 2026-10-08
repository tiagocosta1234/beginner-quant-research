"""The mirrored-lead study on all 28 FX pairs with MT5 broker's own data (PREREG_LEAD_ALLPAIRS.md): the original EA's MT5 broker entries (lead_allpairs_run.py, Model 2) are mirrored with TP / SL exits on MT5 broker's M1 bars (mt5data_m1_export.py).
   python -m mt5broker.ea_batch.lead_allpairs_study            writes forex/early_mt5/ea_batch/leadpairs_mt5/study_trades.csv and prints the report
Mirror rules (as inv_realize.py): opposite direction at the next minute's ask (long) / bid (short); TP / SL in pips on the bid (long) or ask (short) high / low; a minute that touches both counts as the SL; 60-day time stop at the close; round-trip commission 0.6 pip.
The first-hit minute for every TP and SL is read from running max / min arrays, one pass per trade, so all 16 cells of the grid come from the same trade list."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
RES = HERE / "leadpairs_mt5" / "m2"
PAIRS = ["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD",
         "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
YEARS = ["2022", "2023", "2024", "2025", "2026"]
TPS, SLS, MAXH, COMM = (10, 20, 40, 80), (20, 40, 80, 160), 60 * 1440, 0.6
DISC, HOLD = ["2023", "2024", "2025"], ["2022", "2026"]
T_BAR = 3.7                                            # one-sided Bonferroni 5% for k = 28 x 16 = 448 cells


def pip_of(pair: str) -> float:
    return 0.01 if pair.endswith("JPY") else 1e-4


def mirror_pair(pair: str) -> pd.DataFrame:
    f = DATA / f"{pair}_M1_rates.parquet"
    if not f.exists():
        return pd.DataFrame()
    m = pd.read_parquet(f); t = m["t"].to_numpy(); bo, bh, bl, bc, ao, ah, al, ac = (m[c].to_numpy() for c in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")); pip = pip_of(pair); out = []
    for y in YEARS:
        ef = RES / f"results_{y}" / f"{pair}.entries.csv"
        if not ef.exists():
            continue
        ent = pd.read_csv(ef, parse_dates=["te"])
        for te, side in zip(ent.te.values.astype("datetime64[s]").astype("int64"), ent.side.values):
            a = int(np.searchsorted(t, te)); d = -int(side)                           # mirrored direction
            if a >= len(t) - 2:
                continue
            b = min(len(t), a + MAXH)
            if d > 0:
                e = ao[a]; rmax = np.maximum.accumulate(bh[a:b]); rmin = np.minimum.accumulate(bl[a:b]); close = bc[a:b][-1]
            else:
                e = bo[a]; rmin = np.minimum.accumulate(al[a:b]); rmax = np.maximum.accumulate(ah[a:b]); close = ac[a:b][-1]
            n = b - a
            for tp in TPS:
                i_tp = int(np.searchsorted(rmax if d > 0 else -rmin, (e + tp * pip) if d > 0 else -(e - tp * pip), side="left"))
                for sl in SLS:
                    i_sl = int(np.searchsorted(-rmin if d > 0 else rmax, -(e - sl * pip) if d > 0 else (e + sl * pip), side="left"))
                    if i_sl < n and i_sl <= i_tp: j, pnl = i_sl, -sl
                    elif i_tp < n: j, pnl = i_tp, tp
                    else: j, pnl = n - 1, ((close - e) * d) / pip
                    out.append((pair, y, int(t[a]), int(t[a + j]), tp, sl, d, pnl - COMM))
    return pd.DataFrame(out, columns=["pair", "year", "t0", "t1", "tp", "sl", "d", "pips"])


def cell_stats(g: pd.DataFrame) -> dict:
    p = g.pips.values; day = pd.to_datetime(g.t1, unit="s").dt.date; dp = g.groupby(day).pips.sum()
    ev = np.r_[np.ones(len(g)), -np.ones(len(g))]; ts = np.r_[g.t0.values, g.t1.values]; conc = int(np.cumsum(ev[np.argsort(ts, kind="stable")]).max())
    return dict(n=len(p), net=p.sum(), win=(p > 0).mean(), t=p.mean() / p.std(ddof=1) * np.sqrt(len(p)) if len(p) > 4 and p.std() > 0 else np.nan, top_day=(dp.max() / p.sum()) if p.sum() > 0 else np.nan, conc=conc)


def main() -> int:
    outf = HERE / "leadpairs_mt5" / "study_trades.csv"
    pairs = [p for p in PAIRS if (DATA / f"{p}_M1_rates.parquet").exists()]
    print(f"pairs with M1 bars exported: {len(pairs)} of 28; with entries in all five years: {sum(all((RES / f'results_{y}' / f'{p}.entries.csv').exists() for y in YEARS) for p in pairs)}", flush=True)
    T = pd.concat([mirror_pair(p) for p in pairs], ignore_index=True); T.to_csv(outf, index=False); print(f"{len(T):,} mirrored trade-cells -> {outf.name}", flush=True)
    rows = []
    for (pair, tp, sl), g in T.groupby(["pair", "tp", "sl"]):
        yr = g.groupby("year").pips.sum().reindex(YEARS).fillna(0.0); s = cell_stats(g[g.year.isin(DISC)]); h = g[g.year.isin(HOLD)]
        pf_h = h.pips[h.pips > 0].sum() / abs(h.pips[h.pips < 0].sum()) if (h.pips < 0).any() else np.inf
        disc = bool((yr[DISC] > 0).all() and s["t"] >= T_BAR and s["top_day"] <= 0.5 and s["conc"] <= 20)
        conf = bool(disc and (yr[HOLD] > 0).all() and pf_h >= 1.10)
        rows.append(dict(pair=pair, tp=tp, sl=sl, **{f"y{y}": round(yr[y]) for y in YEARS}, disc_t=s["t"], disc_n=s["n"], win=s["win"], top_day=s["top_day"], conc=s["conc"], pf_hold=pf_h, DISCOVERY=disc, CONFIRMED=conf))
    R = pd.DataFrame(rows); R.to_csv(HERE / "leadpairs_mt5" / "study_cells.csv", index=False)
    print(f"\n=== {len(R)} cells ({R.pair.nunique()} pairs x 16). DISCOVERIES (net pips > 0 in 2023, 2024 and 2025, pooled t >= {T_BAR}, top-day share <= 50%, <= 20 open): {int(R.DISCOVERY.sum())} | CONFIRMED in both hold-outs (2022 and 2026 net > 0, PF >= 1.10): {int(R.CONFIRMED.sum())}")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print("\nDiscoveries (sorted by discovery t):"); print(R[R.DISCOVERY].sort_values("disc_t", ascending=False).head(30).round(2).to_string(index=False) if R.DISCOVERY.any() else "  none")
    g = R[(R.pair == "GBPUSD")]; print("\nGBPUSD+ (the lead found on MT5 broker data), all 16 cells, net pips per year (MT5 broker entries, MT5 broker bars):"); print(g.sort_values(["tp", "sl"])[["tp", "sl", *[f"y{y}" for y in YEARS], "disc_t", "win", "DISCOVERY", "CONFIRMED"]].round(2).to_string(index=False))
    pos = R.assign(d3=lambda d: d[[f"y{y}" for y in DISC]].gt(0).all(axis=1)); print(f"\ncells positive in all three discovery years: {int(pos.d3.sum())} of {len(R)} | of these, positive in BOTH hold-outs: {int((pos.d3 & (R.y2022 > 0) & (R.y2026 > 0)).sum())}")
    allc = R.assign(disc_pips=R[[f'y{y}' for y in DISC]].sum(axis=1), hold_pips=R.y2022 + R.y2026)
    print(f"correlation across all {len(allc)} cells between discovery-years pips and hold-out pips: {np.corrcoef(allc.disc_pips, allc.hold_pips)[0, 1]:+.2f} (a real lead would show a clearly positive value)")
    top = allc.sort_values("disc_pips", ascending=False).head(40); print(f"the 40 cells with the highest discovery pips: mean discovery pips {top.disc_pips.mean():,.0f}, mean hold-out pips {top.hold_pips.mean():,.0f}; share with positive hold-out pips {100 * (top.hold_pips > 0).mean():.0f}%")
    side = {y: [] for y in YEARS}
    for p in pairs:
        for y in YEARS:
            ef = RES / f"results_{y}" / f"{p}.entries.csv"
            if ef.exists():
                e = pd.read_csv(ef); n = max(len(e), 1); side[y].append(max((e.side > 0).sum(), (e.side < 0).sum()) / n)
    print("average share of the EA's entries that go the same way within a pair-year (1.0 = always one direction): " + ", ".join(f"{y} {np.mean(v):.2f}" for y, v in side.items() if v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
