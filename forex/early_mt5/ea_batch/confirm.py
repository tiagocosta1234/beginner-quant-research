"""Round 347 stage 2 -- CONFIRMATION of the stage-1 leaders on earlier years (written 2026-10-05 at the trader's request, after two of the first three stage-1 leaders failed on 2024-2025).

WHY: stage 1 screens about 1,200 EAs on one 9-month stretch (2026), picks the best and sizes each at the largest lot its two caps allow (analyze_2026.py). With that many EAs the top of
the list is mostly luck: Exp_ColorSchaffMFITrendCycle and e-News-Lucky made money in 2026 and lost in both 2025 and 2024; Exp_XFisher_org_v1 won in 2025 and was flat in 2024.
CANDIDATES (fixed now): the EAs analyze_2026.py ranks (testable, sizable, not martingale-like) that earned at least MIN_RET30 = +1.0% on average per 30 days at their safe size, the best
MAX_CAND = 40 by that return.
RUNS: each candidate on 2025.01.01-2025.12.31 and 2024.01.01-2024.12.31, the same tester settings as stage 1 (real ticks, commission, $100K, the EA's default inputs); results in
results_2025/ and results_2024/ (run_batch.py with --from-date / --to-date / --results; finished EAs are skipped, so this is resumable).
FROZEN SIZE: the stage-1 lot multiple lam_max is applied unchanged to 2025 and 2024 (nothing is re-fitted on the new years). Symbols that are not 6-letter FX pairs (gold, indices, crypto)
are rescaled by (2026 median deal price / that year's median deal price), so the same lot is the same dollar risk as today.
CONFIRMED (fixed now), in BOTH 2025 and 2024: (a) net P&L at the default lot > 0 after costs; (b) the tester's maximal equity drawdown at the frozen size <= MAX_EQDD_PCT = 10% of the $100K
(MT5 broker's trailing limit; stage 1 allowed 8%); (c) the 1-Step breach rate within 86 days (6 Oct -> 31 Dec) <= MAX_BREACH86 = 10% (closed-deal replay, every weekday start of that year).
RANKING of confirmed EAs: the mean over 2026, 2025 and 2024 of p1_30 (1-Step pass within 30 calendar days), then of p1_60, then of p1_86. An EA that crashed, flooded the journal or produced
no report in an extra year FAILS; one not run yet is PENDING.
STAGE 3 (portfolio.py) runs at the end of this stage on the confirmed EAs.
POWER: one EA, two extra years, about 8 independent months each. This removes the EAs that only worked in 2026; it does not prove the survivors have an edge.

  python -m mt5broker.ea_batch.confirm      # stage 2 on the current stage-1 results (the batch calls it by itself); writes forex/early_mt5/ea_batch/confirmed_summary.csv
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from mt5broker.ea_batch.analyze_2026 import replay_1step, replay_2step
from mt5broker.ea_batch.analyze_reports import INITIAL, daily_pnl

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
YEARS = (2025, 2024)
MIN_RET30, MAX_CAND = 1.0, 40
MAX_EQDD_PCT, MAX_BREACH86 = 10.0, 0.10
OUT = HERE / "confirmed_summary.csv"
CCY = {"USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "SEK", "NOK", "DKK", "PLN", "MXN", "ZAR", "SGD", "HKD", "CNH", "TRY", "HUF", "CZK"}


def is_fx(symbol: str) -> bool:
    """A currency pair (dollar P&L per lot does not move with the price level); XAUUSD / XAGUSD / crypto / indices are not."""
    s = str(symbol)
    return len(s) == 6 and s[:3] in CCY and s[3:] in CCY


def stage1() -> pd.DataFrame:
    with tempfile.TemporaryDirectory() as tmp:
        env = {k: v for k, v in os.environ.items() if k not in ("EA_BATCH_RESULTS", "EA_BATCH_OUT")}
        subprocess.run([sys.executable, "-m", "mt5broker.ea_batch.analyze_2026"], env=dict(env, EA_BATCH_OUT=tmp), cwd=str(ROOT), check=True, capture_output=True)
        return pd.read_csv(Path(tmp) / "results_summary.csv", dtype={"id": str})


def candidates(s1: pd.DataFrame) -> pd.DataFrame:
    ok = s1[(s1.rankable == True) & (s1.ret30_mean >= MIN_RET30)]
    return ok.sort_values("ret30_mean", ascending=False).head(MAX_CAND)


def done_ids(year: int) -> set:
    f = HERE / f"results_{year}" / "status.csv"
    return set(pd.read_csv(f, dtype={"id": str}).id) if f.exists() else set()


def run_year(year: int, ids: list) -> None:
    subprocess.run([sys.executable, "-u", "-m", "mt5broker.ea_batch.run_batch", "--from-date", f"{year}.01.01", "--to-date", f"{year}.12.31", "--results", f"results_{year}",
                    "--only", ",".join(ids), "--timeout", "1800", "--confirm-every", "0"], cwd=str(ROOT))


def level(csv: Path) -> float:
    return float(pd.read_csv(csv, usecols=["price"]).price.median())


def windows(year: int) -> tuple:
    end = pd.Timestamp("2026-09-30") if year == 2026 else pd.Timestamp(f"{year}-12-31")
    idx = pd.bdate_range(f"{year}-01-01", end)
    return idx, {H: [list(pd.bdate_range(s, s + pd.Timedelta(days=H))) for s in idx if s + pd.Timedelta(days=H) <= end] for H in (30, 60, 86)}


_W = {y: windows(y) for y in (2026,) + YEARS}


def load_year(r, year: int, base_dir: Path | None = None):
    """The EA's results for `year` at its frozen stage-1 size (2026 = the stage-1 run itself). Returns ("ok", dict(pnl = daily $ P&L on that year's weekdays, ent = entry days,
    eq_dd = the tester's max equity drawdown in $ at that size, net = net P&L at the default lot, sharpe = annualised daily Sharpe)), ("pending", None) if not run yet,
    or (f"fail {year}: ...", None) if it produced nothing usable."""
    d = base_dir or HERE
    rd = d / f"results_{year}"; f = rd / f"{r.id}.csv"
    stf = rd / "status.csv"
    if not stf.exists():
        return "pending", None
    st = pd.read_csv(stf, dtype={"id": str}).drop_duplicates("id", keep="last").set_index("id")
    if r.id not in st.index:
        return "pending", None
    row = st.loc[r.id]
    note = "" if pd.isna(row.get("note")) else str(row.get("note"))
    if not f.exists() or not row.get("eq_dd", float("nan")) > 0:
        return f"fail {year}: no usable result ({note or 'no report'})", None
    raw = daily_pnl(f)
    if raw.empty:
        return f"fail {year}: no trades", None
    fac = 1.0 if (year == 2026 or is_fx(r.symbol)) else level(d / "results_2026" / f"{r.id}.csv") / level(f)
    lam = float(r.lam_max) * fac
    pnl = raw.reindex(_W[year][0]).fillna(0.0) * lam
    deals = pd.read_csv(f, usecols=["time", "direction"])
    ent = set(pd.to_datetime(deals.time[deals.direction == "in"].astype(str).str.replace(".", "-", regex=False)).dt.normalize())
    sd = float(pnl.std())
    return "ok", dict(pnl=pnl, ent=ent, eq_dd=float(row.eq_dd) * lam, net=float(row.net), sharpe=float(pnl.mean() / sd * np.sqrt(252)) if sd > 0 else float("nan"))


def score_year(r, year: int, base_dir: Path | None = None):
    """Metrics of one EA in one extra year at its frozen stage-1 size; ("pending", None) if not run yet, ("fail: ...", None) if it produced nothing usable."""
    status, dat = load_year(r, year, base_dir)
    if dat is None:
        return status, None
    pnl = dat["pnl"].to_dict(); ent = dat["ent"]; wins = _W[year][1]
    m = dict(net=dat["net"], eqdd_pct=dat["eq_dd"] / INITIAL * 100, sharpe=dat["sharpe"])
    for H, dls in wins.items():
        r1 = [replay_1step(pnl, dl)[0] for dl in dls]
        m[f"p1_{H}"] = float(np.mean([x == "pass" for x in r1])); m[f"b1_{H}"] = float(np.mean([x == "breach" for x in r1]))
    m["p2_86"] = float(np.mean([replay_2step(pnl, ent, dl) == "pass" for dl in wins[86]]))
    m["ret30"] = float(np.mean([sum(pnl.get(x, 0.0) for x in dl) for dl in wins[30]]) / INITIAL * 100)
    why = [t for t, bad in (("net<=0", m["net"] <= 0), (f"eqDD {m['eqdd_pct']:.0f}%>10%", m["eqdd_pct"] > MAX_EQDD_PCT), (f"breach {m['b1_86']:.0%}>10%", m["b1_86"] > MAX_BREACH86)) if bad]
    return ("ok" if not why else f"fail {year}: " + ", ".join(why)), m


def score(r, base_dir: Path | None = None) -> dict:
    out = dict(id=r.id, title=r.title, symbol=r.symbol, period=r.period, lam_max=r.lam_max, ret30_2026=r.ret30_mean, p1_30_2026=r.p1_30, p1_60_2026=r.p1_60, p1_86_2026=r.p1_86,
               sharpe_2026=r.get("sharpe_2026", float("nan")))
    verdicts, ms = [], {}
    for y in YEARS:
        v, m = score_year(r, y, base_dir)
        verdicts.append(v)
        if m:
            ms[y] = m
            out.update({f"{k}_{y}": val for k, val in m.items()})
    fails = [v for v in verdicts if v.startswith("fail")]
    out["verdict"] = "CONFIRMED" if all(v == "ok" for v in verdicts) else ("; ".join(fails) if fails else "pending")
    if out["verdict"] == "CONFIRMED":
        for k in ("p1_30", "p1_60", "p1_86"):
            out[f"avg_{k}"] = float(np.mean([out[f"{k}_2026"]] + [ms[y][k] for y in YEARS]))
        out["avg_sharpe"] = float(np.nanmean([out["sharpe_2026"]] + [ms[y]["sharpe"] for y in YEARS]))
    return out


def main() -> None:
    s1 = stage1()
    c = candidates(s1)
    print(f"stage 2: {len(c)} candidates (of {int((s1.rankable == True).sum())} ranked EAs; at least +{MIN_RET30}% per 30 days at the safe size)", flush=True)
    for y in YEARS:
        todo = [i for i in c.id if i not in done_ids(y)]
        if todo:
            print(f"  {y}: running {len(todo)} EAs", flush=True)
            run_year(y, todo)
    if c.empty:
        print("no candidates yet"); return
    res = pd.DataFrame([score(r) for _, r in c.iterrows()])
    res["_rank"] = (res.verdict == "CONFIRMED").astype(int) * 2 + (res.verdict == "pending").astype(int)
    res = res.sort_values(["_rank", "avg_p1_30", "avg_p1_60", "avg_p1_86"], ascending=False, na_position="last").drop(columns="_rank") if "avg_p1_30" in res else res
    res.to_csv(OUT, index=False)
    n_ok = int((res.verdict == "CONFIRMED").sum()); n_pend = int((res.verdict == "pending").sum())
    print(f"stage 2 result: {n_ok} confirmed, {len(res) - n_ok - n_pend} failed, {n_pend} pending -> {OUT.name}", flush=True)
    for _, r in res[res.verdict == "CONFIRMED"].head(10).iterrows():
        print(f"  CONFIRMED {str(r.title)[:34]} {r.symbol} {r.period}: 1-Step in 30 days avg {r.avg_p1_30:.0%}, 60 days {r.avg_p1_60:.0%}, by Dec 31 {r.avg_p1_86:.0%}, Sharpe {r.avg_sharpe:.1f} (2026/2025/2024)", flush=True)
    for _, r in res[~res.verdict.isin(["CONFIRMED", "pending"])].head(8).iterrows():
        print(f"  failed    {str(r.title)[:34]} {r.symbol}: {r.verdict}", flush=True)
    try:                                                    # stage 3: the portfolio of the confirmed EAs (portfolio.py)
        from mt5broker.ea_batch import portfolio
        portfolio.main([])
    except Exception as e:
        print(f"stage 3 failed: {e}", flush=True)


if __name__ == "__main__":
    main()
