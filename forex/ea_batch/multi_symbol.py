"""Multi-symbol edge screen (the trader, 2026-10-06: "we should be only for strategies with edges across multiple symbols").  PRE-REGISTERED before any result.

CANDIDATES  every EA of the 2026 real-tick screen (results_2026/status.csv) with net > 0 and >= 30 deals on its own symbol, default inputs (149 EAs at the time of writing), ordered by tester equity drawdown (smallest first).
BASKET      EURUSD, GBPUSD, USDJPY, AUDUSD, XAUUSD, US100.cash: each EA is also run on every basket symbol it was not screened on, same period (timeframe), default inputs, real ticks, $100K, 2026-01-01..2026-09-30
            (MT5 broker bid / ask data, MT5 broker commission and swap from the symbol spec, as in the batch).
EDGE ON A SYMBOL  >= 30 round trips, net > 0 after commission and swap, and profit factor >= 1.2.
PASS (multi-symbol edge)  the EA has an edge on its own symbol AND on at least 3 of the other basket symbols (counting its own symbol if it is in the basket, so at least 4 symbols in all out of at most 6).
NEXT STAGE (only for passers)  the same test on 2025 and 2024; a passer must repeat the pass on both before it counts as confirmed; then the combined replay with the pair.
Resumable: results_multi/status.csv (one row per EA x symbol), deals in results_multi/<id>_<symbol>.csv.  STOP THE EA BATCH FIRST (shared terminal).   python -m forex.ea_batch.multi_symbol
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from forex.ea_batch.tester_run import run_test

HERE = Path(__file__).resolve().parent
OUT = HERE / "results_multi"; OUT.mkdir(exist_ok=True)
BASKET = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD", "US100.cash")
FROM, TO = "2026.01.01", "2026.09.30"


def candidates() -> pd.DataFrame:
    s = pd.read_csv(HERE / "results_2026" / "status.csv", dtype={"id": str}).drop_duplicates("id", keep="last")
    s["net"] = pd.to_numeric(s.net, errors="coerce"); s["deals"] = pd.to_numeric(s.deals, errors="coerce"); s["eq_dd"] = pd.to_numeric(s.eq_dd, errors="coerce")
    c = s[(s.net > 0) & (s.deals >= 60)].sort_values("eq_dd")                      # deals counts in and out rows: >= 60 deals = >= 30 round trips
    m = pd.read_csv(HERE / "manifest.csv", dtype={"id": str}).set_index("id")
    c = c[c.id.isin(m.index)].copy(); c["main"] = c.id.map(m.main)
    return c


def stats(d: pd.DataFrame) -> dict:
    o = d[d.direction == "out"]; net = o.profit + o.commission + o.swap
    w = net[net > 0].sum(); l = -net[net <= 0].sum()
    return dict(trips=len(o), net=float(net.sum()), pf=float(w / l) if l > 0 else float("inf") if w > 0 else float("nan"))


def main(argv=None):
    done_f = OUT / "status.csv"
    done = pd.read_csv(done_f, dtype={"id": str}) if done_f.exists() else pd.DataFrame(columns=["id", "symbol"])
    seen = set(zip(done.id, done.symbol))
    for r in candidates().itertuples():
        for sym in BASKET:
            if sym == r.symbol or (r.id, sym) in seen:
                continue
            rel = f"ea_batch\\{r.id}\\{Path(r.main).with_suffix('.ex5').name}"
            try:
                res = run_test(f"ms_{r.id}_{sym.replace('.', '')}", rel, sym, r.period, FROM, TO, None, timeout=1500)
            except Exception as e:                                          # an unreadable / empty tester report must not stop the screen (13:54 crash, lxml "no text parsed")
                res = dict(note=f"error {type(e).__name__}: {str(e)[:80]}", seconds=0, deals=None)
            row = dict(id=r.id, symbol=sym, own=r.symbol, period=r.period, note=res["note"], seconds=res["seconds"], trips=0, net=float("nan"), pf=float("nan"))
            if res["deals"] is not None and len(res["deals"]):
                res["deals"].to_csv(OUT / f"{r.id}_{sym.replace('.', '')}.csv", index=False); row.update(stats(res["deals"]))
            pd.DataFrame([row]).to_csv(done_f, mode="a", header=not done_f.exists(), index=False)
            print(f"{r.id} {r.title[:40]:<40} {r.symbol}->{sym} {r.period}: trips {row['trips']} net {row['net']:,.0f} pf {row['pf']:.2f} ({res['seconds']}s) {res['note']}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
