"""Cross-pair screen of the most promising batch EAs on all 28 FX pairs (pre-registered in PREREG_FX_ALLPAIRS_EAS.md).   python -m mt5broker.ea_batch.fx_allpairs [--report]
Stage 1: 11 EAs x 28 pairs, 2026-01-01..2026-09-30. Stage 2 (STAGE-1 passers only, on the pairs where they had an edge): 2025 and 2024.   Resumable: fxall/status.csv (one row per stage x EA x pair), deals in fxall/<stage>_<id>_<pair>.csv.
Runs on the MT5 broker terminal through tester_run.run_test (real ticks, USD 100K, default inputs) exactly like the earlier screens; the live MT5 broker account is never touched. A progress note goes to Telegram every 60 runs and at the end of each stage.
Disk: the tester pauses (never deletes) when the data drive has less than 12 GB free."""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import os
os.environ.setdefault("EA_BATCH_MIN_FREE_GB", "12")

from mt5broker.ea_batch.tester_run import run_test  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "fxall"; OUT.mkdir(exist_ok=True)
STATUS = OUT / "status.csv"
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY", "EURCHF", "EURAUD", "EURCAD", "EURNZD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD",
         "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD", "CADJPY", "CADCHF", "CHFJPY", "NZDJPY", "NZDCAD", "NZDCHF"]
ROSTER = ["13462", "74818", "1294", "11256", "19655", "21759", "17339", "16938", "22909", "77236", "17568"]          # M1 EAs last: they are the slowest
YEARS = {"2026": ("2026.01.01", "2026.09.30"), "2025": ("2025.01.01", "2025.12.31"), "2024": ("2024.01.01", "2024.12.31")}
EDGE1 = dict(trips=30, pf=1.2, top3=0.40); PASS1 = 10
EDGE2 = dict(trips=20, pf=1.1); CONF_SHARE, CONF_MIN = 0.60, 5
GRID_MAXPOS = 20                                                              # amendment 2026-10-08 23:55: an EA that ever holds more than this many positions at once is a grid/basket and is disqualified


def stats(d: pd.DataFrame) -> dict:
    o = d[d.direction == "out"]; n = o.profit + o.commission + o.swap
    if not len(n):
        return dict(trips=0, net=0.0, pf=float("nan"), top3=float("nan"))
    w, l = n[n > 0].sum(), -n[n <= 0].sum()
    return dict(trips=int(len(n)), net=float(n.sum()), pf=float(w / l) if l > 0 else (float("inf") if w > 0 else float("nan")), top3=float(n.sort_values(ascending=False).head(3).sum() / n.sum()) if n.sum() > 0 else float("nan"))


def deal_file(r) -> Path:
    if r.source == "own":
        return HERE / "results_2026" / f"{r.id}.csv"
    if r.source == "multi":
        return HERE / "results_multi" / f"{r.id}_{r.symbol}.csv"
    return OUT / f"{r.stage}_{r.id}_{r.symbol}.csv"


def max_open(d: pd.DataFrame) -> int:
    """Largest number of positions open at the same moment (entries before exits at equal timestamps)."""
    t = pd.to_datetime(d.time).values.astype("datetime64[ns]").astype("int64"); delta = np.where(d.direction == "in", 1, np.where(d.direction == "out", -1, 0))
    return int(np.cumsum(delta[np.lexsort((-delta, t))]).max()) if len(d) else 0


def grid_table(st: pd.DataFrame) -> dict[str, int]:
    """EA id -> largest simultaneous position count over every 2026 cell we hold (only EAs above GRID_MAXPOS are returned)."""
    out: dict[str, int] = {}
    for r in st[st.stage == "2026"].itertuples():
        f = deal_file(r)
        if f.exists():
            out[r.id] = max(out.get(r.id, 0), max_open(pd.read_csv(f)))
    return {i: m for i, m in out.items() if m > GRID_MAXPOS}


def is_edge(r, stage: str) -> bool:
    if stage == "2026":
        return bool(r["trips"] >= EDGE1["trips"] and r["net"] > 0 and r["pf"] >= EDGE1["pf"] and r["top3"] <= EDGE1["top3"])
    return bool(r["trips"] >= EDGE2["trips"] and r["net"] > 0 and r["pf"] >= EDGE2["pf"])


def meta() -> pd.DataFrame:
    s = pd.read_csv(HERE / "results_2026" / "status.csv", dtype={"id": str}).drop_duplicates("id", keep="last").set_index("id")
    m = pd.read_csv(HERE / "manifest.csv", dtype={"id": str}).set_index("id")
    return s.join(m[["main"]], how="left")


def tg(text: str) -> None:
    try:
        from mt5broker.forward_test import telegram
        telegram.send(text)
    except Exception:
        pass


def seeds(M: pd.DataFrame) -> pd.DataFrame:
    """Rows we already have from identical settings: the EA's own 2026 batch run and the old multi-symbol screen (same period, real ticks, default inputs)."""
    rows = []
    for i in ROSTER:
        own = str(M.loc[i, "symbol"]); f = HERE / "results_2026" / f"{i}.csv"
        if own in PAIRS and f.exists():
            rows.append(dict(stage="2026", id=i, symbol=own, source="own", seconds=0, note="", **stats(pd.read_csv(f))))
        for sym in PAIRS:
            g = HERE / "results_multi" / f"{i}_{sym}.csv"
            if g.exists() and sym != own:
                rows.append(dict(stage="2026", id=i, symbol=sym, source="multi", seconds=0, note="", **stats(pd.read_csv(g))))
    return pd.DataFrame(rows)


def load_status() -> pd.DataFrame:
    return pd.read_csv(STATUS, dtype={"id": str, "stage": str, "symbol": str}).drop_duplicates(["stage", "id", "symbol"], keep="last") if STATUS.exists() else pd.DataFrame(columns=["stage", "id", "symbol", "source", "seconds", "note", "trips", "net", "pf", "top3"])


def run_cell(M, stage: str, i: str, pair: str) -> dict:
    frm, to = YEARS[stage]; r = M.loc[i]; rel = f"ea_batch\\{i}\\{Path(str(r.main)).with_suffix('.ex5').name}"
    try:
        res = run_test(f"fx_{stage}_{i}_{pair}", rel, pair, str(r.period), frm, to, None, timeout=2400)
    except Exception as e:                                              # one unreadable report or a hung run must not stop the screen
        res = dict(note=f"error {type(e).__name__}: {str(e)[:80]}", seconds=0, deals=None)
    row = dict(stage=stage, id=i, symbol=pair, source="run", seconds=res.get("seconds", 0), note=res.get("note", ""), trips=0, net=float("nan"), pf=float("nan"), top3=float("nan"))
    if res.get("deals") is not None and len(res["deals"]):
        res["deals"].to_csv(OUT / f"{stage}_{i}_{pair}.csv", index=False); row.update(stats(res["deals"]))
    pd.DataFrame([row]).to_csv(STATUS, mode="a", header=not STATUS.exists(), index=False)
    return row


def run_stage(M, stage: str, cells: list[tuple[str, str]]) -> None:
    done = load_status(); seen = {(r.stage, r.id, r.symbol) for r in done.itertuples()}
    todo = [(i, p) for i, p in cells if (stage, i, p) not in seen]; t0 = time.time(); n = 0
    print(f"=== stage {stage}: {len(cells)} cells, {len(todo)} to run", flush=True)
    if stage == "2026" and todo:
        tg(f"FX all-pairs screen started: stage 1 has {len(todo)} runs to do (11 EAs x 28 pairs, 2026, MT5 broker real ticks). Progress notes every 60 runs.")
    grid = grid_table(done) if stage == "2026" else {}                            # a grid EA needs no more stage-1 runs
    for i, pair in todo:
        if i in grid:
            print(f"{datetime.now():%H:%M:%S} [{stage}] {i} {pair}: skipped, GRID EA (up to {grid[i]} positions open at once)", flush=True); continue
        row = run_cell(M, stage, i, pair); n += 1
        if stage == "2026":
            grid = grid_table(load_status())
        print(f"{datetime.now():%H:%M:%S} [{stage}] {i} {str(M.loc[i, 'title'])[:34]:<34} {pair}: trips {row['trips']} net {row['net']:,.0f} pf {row['pf']:.2f} top3 {row['top3']:.2f} ({row['seconds']}s) {row['note']}", flush=True)
        if n % 60 == 0:
            el = (time.time() - t0) / 60; tg(f"FX all-pairs screen [{stage}]: {n}/{len(todo)} runs done in {el:.0f} min, about {el / n * (len(todo) - n):.0f} min left.")


def edge_table(st: pd.DataFrame, stage: str) -> pd.DataFrame:
    s = st[st.stage == stage].copy()
    s["edge"] = s.apply(lambda r: is_edge(r, stage), axis=1) if len(s) else False
    return s


def passers(st: pd.DataFrame) -> dict[str, list[str]]:
    s = edge_table(st, "2026"); out = {}; grid = grid_table(st)
    for i, g in s.groupby("id"):
        e = g[g.edge].symbol.tolist()
        if len(e) >= PASS1 and i not in grid:
            out[i] = e
    return out


def report(M) -> str:
    st = load_status(); s1 = edge_table(st, "2026"); P = passers(st); G = grid_table(st); lines = [f"# FX all-pairs screen of the best-looking batch EAs (generated {datetime.now():%Y-%m-%d %H:%M})", "", "Pre-registration: PREREG_FX_ALLPAIRS_EAS.md. MT5 broker real ticks, default inputs, USD 100K.", ""]
    lines += ["## Stage 1 (2026-01-01..09-30): pairs with an edge (>= 30 trips, net > 0, PF >= 1.2, top-3 <= 40%) out of the 28", "", "| EA | native | pairs tested | edge on | share | PASS (>= 10) | profitable pairs (net > 0) | median PF of tested |", "|---|---|---|---|---|---|---|---|"]
    for i in ROSTER:
        g = s1[s1.id == i]
        if not len(g): continue
        e = int(g.edge.sum()); pos = int((g.net > 0).sum())
        lines.append(f"| {i} {str(M.loc[i, 'title'])[:34]} | {M.loc[i, 'symbol']} {M.loc[i, 'period']} | {len(g)} | {e} | {100 * e / len(g):.0f}% | {'PASS' if i in P else (f'GRID (up to {G[i]} open at once), disqualified' if i in G else '-')} | {pos} | {g.pf.replace([np.inf], np.nan).median():.2f} |")
    done = st[st.stage != "2026"]
    if len(done):
        lines += ["", "## Stage 2 (passers, on their edge pairs): 2025 and 2024 (EDGE2: >= 20 trips, net > 0, PF >= 1.1)", "", "| EA | pairs | 2025 EDGE2 | 2024 EDGE2 | CONFIRMED |", "|---|---|---|---|---|"]
        for i, pairs in P.items():
            r = {y: edge_table(st[(st.stage == y) & (st.id == i)], y) for y in ("2025", "2024")}
            ok = {y: int(r[y].edge.sum()) if len(r[y]) else 0 for y in r}; tested = {y: len(r[y]) for y in r}
            conf = all(tested[y] >= len(pairs) and ok[y] >= max(CONF_MIN, np.ceil(CONF_SHARE * len(pairs))) for y in ok)
            lines.append(f"| {i} {str(M.loc[i, 'title'])[:34]} | {len(pairs)} | {ok['2025']}/{tested['2025']} | {ok['2024']}/{tested['2024']} | {'CONFIRMED' if conf else 'no'} |")
    best = s1[s1.edge & ~s1.id.isin(list(G))].sort_values("pf", ascending=False).head(25)
    lines += ["", "## The 25 best stage-1 edge cells (by profit factor; grid EAs excluded)", "", "| EA | pair | trips | net | PF | top-3 |", "|---|---|---|---|---|---|"] + [f"| {r.id} {str(M.loc[r.id, 'title'])[:28]} | {r.symbol} | {r.trips} | {r.net:,.0f} | {r.pf:.2f} | {r.top3:.2f} |" for r in best.itertuples()]
    txt = "\n".join(lines) + "\n"; (HERE / "FXALL_RESULT.md").write_text(txt, encoding="utf-8"); return txt


def main() -> int:
    M = meta().loc[ROSTER]
    if "--report" in sys.argv:
        print(report(M)); return 0
    sd = seeds(M); st = load_status()
    if len(sd):                                                               # add the seeds once
        new = sd[~sd.set_index(["stage", "id", "symbol"]).index.isin(st.set_index(["stage", "id", "symbol"]).index)] if len(st) else sd
        if len(new): new.to_csv(STATUS, mode="a", header=not STATUS.exists(), index=False)
    run_stage(M, "2026", [(i, p) for i in ROSTER for p in PAIRS])
    st = load_status(); P = passers(st); txt = report(M)
    tg(f"FX all-pairs screen: STAGE 1 DONE. EAs with an edge on >= 10 of 28 pairs: {', '.join(f'{i} ({len(v)} pairs)' for i, v in P.items()) or 'NONE'}. Report: forex/early_mt5/ea_batch/FXALL_RESULT.md")
    for y in ("2025", "2024"):
        run_stage(M, y, [(i, p) for i, ps in P.items() for p in ps])
    st = load_status(); txt = report(M)
    conf = [l.split("|")[1].strip() for l in txt.splitlines() if "CONFIRMED" in l and l.startswith("| ") and "EA" not in l]
    tg(f"FX all-pairs screen: ALL STAGES DONE. CONFIRMED in 2025 and 2024: {', '.join(conf) or 'none'}. Report: forex/early_mt5/ea_batch/FXALL_RESULT.md")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
