"""Screen of MQL5 Market gold EAs (free DEMO versions) on MT5 broker data in the portable MT5 TESTER terminal, exactly as registered in PREREG_MARKET_DEMOS.md.
   python -m forex.ea_batch.market_demo_run --list                 show the demo .ex5 files found in the tester's MQL5\\Experts\\Market and the jobs they imply
   python -m forex.ea_batch.market_demo_run --run1 [--only key]    stage 1: 2025Q4 and 2026 (100% real ticks) for every demo found
   python -m forex.ea_batch.market_demo_run --run2                 stage 2: 2022..2025 (modelled ticks) for the stage-1 passers
   python -m forex.ea_batch.market_demo_run --report               verdict table + MARKET_DEMO_RESULT.md + ledger rows
Never touches a live terminal (mt5data_run refuses them and the tester kills only its own terminal). EA inputs are the defaults; symbol XAUUSD+, Model 4, USD 100,000."""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_batch import mt5data_run as ER

HERE = Path(__file__).resolve().parent
CAND = pd.concat([pd.read_csv(HERE / "market_candidates.csv", dtype=str), pd.read_csv(HERE / "market_candidates_nongold.csv", dtype=str)], ignore_index=True).fillna("")   # 2026-10-11: non-gold list, own symbol column
MARKET = ER.TERM_DIR / "MQL5" / "Experts" / "Market"
SKIP = {"xauusd5minute"}                                              # the live pair's second leg, already tested
STAGE1, STAGE2 = ("2025Q4", "2026"), ("2022", "2023", "2024", "2025")
LEDGER = HERE.parent / "ea_research" / "LEDGER.csv"


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def found() -> list[dict]:
    out = []
    for f in sorted(MARKET.glob("*.ex5")) if MARKET.exists() else []:
        n = norm(f.stem)
        if n in SKIP:
            continue
        row = next((r for _, r in CAND.iterrows() if norm(r["name"]) == n or norm(r["name"]) in n or n in norm(r["name"])), None)
        key = row["key"] if row is not None else n[:20]; tfs = (row["timeframes"].split("|") if row is not None and row["timeframes"] else ["M15", "H1"])
        out.append(dict(file=f.name, key=key, name=row["name"] if row is not None else f.stem, tfs=tfs, symbol=(row["symbol"] if row is not None and row.get("symbol", "") else "XAUUSD+")))
    return out


def jobs_for(e: dict) -> list[str]:
    ids = []
    for tf in e["tfs"]:
        eid = f"mkt_{e['key']}_{tf}"; ER.EAS[eid] = (rf"Market\{e['file']}", tf, f"{e['name']} (Market demo) {tf}"); SYM[eid] = e.get("symbol", "XAUUSD+"); ids.append(eid)
    return ids


def deals(eid: str, year: str):
    f = ER.OUT / f"results_{year}" / f"{eid}.csv"; m = ER.OUT / f"results_{year}" / f"{eid}.meta.json"
    return (pd.read_csv(f) if f.exists() else None), (json.loads(m.read_text()) if m.exists() else None)


def metrics(d: pd.DataFrame, meta: dict, months: float) -> dict:
    d = d.copy(); d["time"] = pd.to_datetime(d["time"], format="%Y.%m.%d %H:%M:%S", errors="coerce"); d = d.sort_values("time"); net = d.profit + d.commission + d.swap
    out = d[d.direction == "out"]; o = net[d.direction == "out"]; w, l_ = o[o > 0].sum(), -o[o <= 0].sum()
    step = np.where(d.direction == "in", 1, -1); conc = int(np.cumsum(step).max()) if len(d) else 0; vin = d.volume[d.direction == "in"]; vr = float(vin.max() / vin.min()) if len(vin) and vin.min() > 0 else float("nan")
    eq_dd = float(meta.get("eq_dd", float("nan")))
    return dict(trades=len(out), net=float(o.sum()), pf=float(w / l_) if l_ > 0 else float("inf"), win=float((o > 0).mean()) if len(o) else float("nan"), per_month=len(out) / months, conc=conc, lot_ratio=vr, eq_dd=eq_dd, net_dd=float(o.sum() / eq_dd) if eq_dd and eq_dd > 0 else float("nan"))


def verdict1(eid: str):
    parts = {}; reasons = []
    for y, months in (("2025Q4", 3.0), ("2026", 9.0)):
        d, m = deals(eid, y)
        if d is None or not len(d):
            return None, ["no deals in " + y], {}
        parts[y] = metrics(d, m, months)
    q, y26 = parts["2025Q4"], parts["2026"]; pooled_net = q["net"] + y26["net"]; pooled_trades = q["trades"] + y26["trades"]
    pf = (lambda a: a)  # pooled PF from the two windows' gross numbers
    gw = sum(((deals(eid, y)[0].profit + deals(eid, y)[0].commission + deals(eid, y)[0].swap)[deals(eid, y)[0].direction == "out"].clip(lower=0)).sum() for y in parts)
    gl = sum(-((deals(eid, y)[0].profit + deals(eid, y)[0].commission + deals(eid, y)[0].swap)[deals(eid, y)[0].direction == "out"].clip(upper=0)).sum() for y in parts)
    ppf = gw / gl if gl > 0 else float("inf"); worst_dd = max(q["eq_dd"], y26["eq_dd"]); netdd = pooled_net / worst_dd if worst_dd > 0 else float("nan")
    conc, lr, pm = max(q["conc"], y26["conc"]), max(q["lot_ratio"], y26["lot_ratio"]), pooled_trades / 12.0
    checks = [(q["net"] > 0 and y26["net"] > 0, "net > 0 in BOTH windows"), (ppf >= 1.30, f"pooled PF {ppf:.2f} >= 1.30"), (pooled_trades >= 60, f"{pooled_trades} trades >= 60"), (netdd >= 2, f"net / max equity DD {netdd:.1f} >= 2"),
              (conc <= 3 and lr <= 3, f"max concurrent {conc} <= 3 and lot ratio {lr:.1f} <= 3 (grid / martingale)"), (pm >= 5, f"{pm:.1f} trades a month >= 5")]
    reasons = [("ok  " if ok else "FAIL") + " " + t for ok, t in checks]
    return all(ok for ok, _ in checks), reasons, dict(pooled_net=pooled_net, pooled_trades=pooled_trades, ppf=ppf, netdd=netdd, conc=conc, lr=lr, per_month=pm, q=q, y26=y26)


SYM: dict[str, str] = {}


def run_stage(ids: list[str], years) -> None:
    for eid in ids:
        ER.SYMBOL = SYM.get(eid, "XAUUSD+")                                   # non-gold candidates run on their own symbol (run_job reads the module global)
        for y in years:
            ER.run_job(eid, y)
    ER.SYMBOL = "XAUUSD+"


def ledger(eid: str, window: str, trades, avg, pf, netdd, win, note: str) -> None:
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},market_demos,{eid},{window},,{trades},,{avg:.4f},{pf:.3f},{netdd:.2f},{win:.3f},{note}\n")


def report() -> None:
    lines = ["# Market demo screen (stage 1 = real ticks 2025Q4 + 2026; stage 2 = modelled 2022-2025)", ""]
    for e in found():
        for eid in jobs_for(e):
            ok, reasons, s = verdict1(eid)
            if ok is None:
                lines.append(f"## {eid}: {reasons[0]}"); print(f"{eid}: {reasons[0]}"); continue
            tag = "STAGE 1 PASS" if ok else "stage 1 fail"; print(f"\n{eid}: {tag} | net {s['pooled_net']:+,.0f} USD at the default lot, PF {s['ppf']:.2f}, {s['pooled_trades']} trades ({s['per_month']:.1f}/month), max concurrent {s['conc']}, lot ratio {s['lr']:.1f}, net/maxDD {s['netdd']:.1f}")
            lines += [f"## {eid}: {tag}", f"net {s['pooled_net']:+,.0f} USD, PF {s['ppf']:.2f}, {s['pooled_trades']} trades", *["- " + r for r in reasons], ""]
            for r in reasons: print("   ", r)
            ledger(eid, "STAGE1", s["pooled_trades"], s["pooled_net"] / max(s["pooled_trades"], 1), s["ppf"], s["netdd"], s["q"]["win"], f"{tag}; conc {s['conc']} lot ratio {s['lr']:.1f}")
            if ok:
                py = []
                for y in STAGE2:
                    d, m = deals(eid, y)
                    if d is not None and len(d):
                        mm = metrics(d, m, 12.0); py.append((y, mm["pf"], mm["net"], mm["trades"]))
                if py:
                    n_ok = sum(1 for _, pf, _, _ in py if pf >= 1.0); lines.append(f"stage 2: PF >= 1.0 in {n_ok} of {len(py)} years: " + ", ".join(f"{y} PF {pf:.2f} net {nt:+,.0f} ({tr} trades)" for y, pf, nt, tr in py)); print("    stage 2:", lines[-1])
    (HERE.parent / "ea_research" / "MARKET_DEMO_RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    a = sys.argv[1:]
    if "--list" in a:
        for e in found():
            print(e["file"], "->", e["key"], e["tfs"], jobs_for(e))
        print("Market folder:", MARKET, "| demos found:", len(found())); return 0
    only = a[a.index("--only") + 1] if "--only" in a else None; es = [e for e in found() if only in (None, e["key"])]
    if "--run1" in a:
        for e in es:
            run_stage(jobs_for(e), STAGE1)
    if "--run2" in a:
        for e in es:
            for eid in jobs_for(e):
                ok, _, _ = verdict1(eid)
                if ok:
                    run_stage([eid], STAGE2)
    if "--report" in a or "--run1" in a or "--run2" in a:
        report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
