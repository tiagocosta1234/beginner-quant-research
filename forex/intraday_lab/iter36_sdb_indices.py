"""Iteration 36: the FROZEN SDB rule (config.RULE: pct 1.9, expiry 9, K23 / D3 / S7, bands 9 / 2.0, H1) on the four index CFDs that have both MT5 broker full-tick M1 data and an MT5 broker swap spec, and whose MT5 broker twin exists (US100 = NSDQ, US500 = SP, US30 = DOW, GER40 = DAX).
PRE-REGISTERED 2026-10-07 BEFORE RUNNING (nothing is tuned: same rule, same costs as gold, real bid / ask fills, no commission on MT5 broker indices):
 k = 4 instruments -> two-sided bar t >= 2.5 (Bonferroni 0.0125) on the mean R per trade NET OF MT5 SWAP (swap charged per server-midnight rollover, triple on the spec's triple-swap day, Saturday / Sunday free, short credits kept).
 HIT per index = net-of-swap mean R > 0 with t >= 2.5 AND positive in at least 3 of the calendar years 2022-2026 (2021 and 2026 are partial). Gold is printed only as the in-sample reference (it is NOT a test: the rule was searched on it).
 If any index hits, the MT5 Pro 100K life simulation (firm_sim_swap.life_s, swap and swap-free) is run for it; if none hit, nothing else is run and the idea is closed.
 Prior evidence (LESSONS 31 / 35): no edge on 28 FX pairs, none on seven commodities; the gold edge is feed- and regime-specific. The prior for a hit is low."""
from __future__ import annotations

import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from forex.intraday_lab import sdb

ATH = ZoneInfo("Europe/Athens")
SPEC = json.load(open(Path(__file__).resolve().parents[1] / "specs" / "symbol_specs_20261001.json"))["symbols"]
DAYS = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}


def spec(sym):
    s = SPEC[sym] if isinstance(SPEC, dict) else [r for r in SPEC if r["name"] == sym][0]
    return s


def nights(t0, t1, triple):
    a = pd.Timestamp(t0, unit="s"); b = pd.Timestamp(t1, unit="s")          # stored bar times are already server time
    d = a.normalize() + pd.Timedelta(days=1); n = 0
    while d <= b:
        wd = (d - pd.Timedelta(days=1)).weekday()
        n += 3 if wd == triple else (0 if wd >= 5 else 1)
        d += pd.Timedelta(days=1)
    return n


def run(sym):
    s = spec(sym); point = s["point"]; triple = DAYS.get(s.get("triple_swap_day", "Wednesday"), 2)
    tr = pd.DataFrame(sdb.simulate(sym))
    tr["nights"] = [nights(a, b, triple) for a, b in zip(tr.t_entry, tr.t_exit)]
    per_unit = np.where(tr.side > 0, s["swap_long"], s["swap_short"]) * point        # price units per unit of the instrument per night (negative = cost)
    tr["swap_R"] = per_unit * tr.nights / tr["stop"]                                    # signed: negative costs R, positive credits R
    tr["Rnet"] = tr.R + tr.swap_R
    return tr, s


def tstat(x):
    x = np.asarray(x, float); return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else float("nan")


def main():
    print("symbol | n | hold h med | swap long / short (points) | mean R gross | mean R net swap | t net | long R net | short R net | by year (net R, n)")
    for sym in ("US100.cash", "US500.cash", "US30.cash", "GER40.cash", "XAUUSD"):
        tr, s = run(sym)
        yrs = " ".join(f"{y}:{g.Rnet.mean():+.2f}({len(g)})" for y, g in tr.groupby("year"))
        pos = sum(g.Rnet.mean() > 0 for y, g in tr.groupby("year") if 2022 <= y <= 2026)
        hit = "HIT" if (tr.Rnet.mean() > 0 and tstat(tr.Rnet) >= 2.5 and pos >= 3) else "no"
        tag = "(reference, in-sample)" if sym == "XAUUSD" else hit
        print(f"{sym:10} | {len(tr):3} | {((tr.t_exit - tr.t_entry) / 3600).median():5.1f} | {s['swap_long']:+.2f} / {s['swap_short']:+.2f} | {tr.R.mean():+.3f} | {tr.Rnet.mean():+.3f} | {tstat(tr.Rnet):+.2f} | {tr[tr.side > 0].Rnet.mean():+.3f} | {tr[tr.side < 0].Rnet.mean():+.3f} | {yrs} | years>0 (2022-26): {pos} {tag}")


if __name__ == "__main__":
    main()
