"""Round 347m -- CONFIRMATION of the inversion idea on earlier years (pre-registered in forex/intraday_lab/PREREG.md, "Round 347m").

Candidates (fixed from the 2026 screen, ea_invert_results.csv): positive inverted net in BOTH halves of 2026 and inverted t >= 2 -> 9 EAs.
Runs: each candidate on 2025, 2024 and 2023 in the MT5 tester (real ticks, commission, USD 100K, default inputs) via run_batch --only, results in results_inv_<year>/.
Score per EA and year (the same arithmetic as ea_invert_30d.inversion): inverted net per position = -profit - (spread at entry + spread at exit) x volume x K + commission.
CONFIRMED = in EACH of 2025, 2024, 2023: >= 30 positions, inverted net > 0, the ORIGINAL's gross < 0, and the largest single inverted win <= 50% of that year's inverted net;
            AND the pooled inverted t over the three years >= 2.
Usage:  python -m forex.ea_batch.inv_confirm --queue     (waits for the main batch to finish, runs the tester years, scores, restarts the shadow bot)
        python -m forex.ea_batch.inv_confirm --score     (only the scoring, on whatever results exist)"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from forex.ea_batch import floating

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
YEARS = (2025, 2024, 2023)
TOWER_EA_ROOT = "D:/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts/ea_batch"
EA_ROOT = os.environ.get("EA_BATCH_ROOT") or (TOWER_EA_ROOT if Path("D:/MetaQuotes").exists() else "")      # "" = run_batch's default (the terminal's own data folder), as on the second PC
SCRATCH = Path("D:/finance/scratch") if Path("D:/finance/scratch").exists() else ROOT / "mt5broker" / "forward_test" / "log"      # main PC: D:inance\scratch; second PC (no D:): process logs next to the other bot logs
OUT = HERE / "inv_confirm_results.csv"
MARK = SCRATCH / "inv_queue_done.txt"


def candidates() -> list[str]:
    d = pd.read_csv(HERE / "ea_invert_results.csv", dtype={"id": str})
    return d[(d.inv_h1 > 0) & (d.inv_h2 > 0) & (d.inv_t >= 2)].id.tolist()


def batch_running() -> bool:
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'ea_batch.run_batch' -and $_.CommandLine -notmatch 'inv_confirm' }).Count"],
                         capture_output=True, text=True).stdout.strip()
    return out not in ("", "0")


def run_years(ids: list[str]) -> None:
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    if Path(r"D:\finance\tmp").exists():
        env.update(TEMP=r"D:\finance\tmp", TMP=r"D:\finance\tmp")
    for y in YEARS:
        cmd = [sys.executable, "-u", "-m", "forex.ea_batch.run_batch", "--only", ",".join(ids), "--from-date", f"{y}.01.01", "--to-date", f"{y}.12.31", "--results", f"results_inv_{y}", "--confirm-every", "0"]
        rc = subprocess.run(cmd + (["--ea-root", EA_ROOT] if EA_ROOT else []), cwd=str(ROOT), env=env).returncode
        if rc != 0:                                   # a crashed year-run must stop the queue: scoring empty folders gives years_ok 0 and looks like a result
            raise RuntimeError(f"run_batch for {y} exited with code {rc}; nothing was scored")


def inv_year(eid: str, symbol: str, year: int):
    f = HERE / f"results_inv_{year}" / f"{eid}.csv"
    if not f.exists():
        return None
    deals = pd.read_csv(f)
    t0, t1 = pd.Timestamp(f"{year}-01-01"), pd.Timestamp(f"{year}-12-31")
    kp = floating.prior_k(symbol, t0, t1)
    pos, _ = floating.pair_positions(deals, kp)
    if pos is None or len(pos) == 0:
        return dict(id=eid, year=year, positions=0)
    bars, _ = floating.bars_for(symbol, t0, t1)
    if bars is None:
        return dict(id=eid, year=year, positions=len(pos), note="no bars")
    ts = bars.index.values.astype("datetime64[ns]").astype(np.int64)
    sp = bars.ac.values - bars.bc.values
    i0, i1 = floating._bar_idx(ts, pos.te.values), floating._bar_idx(ts, pos.tx.values)
    cost = (sp[i0] + sp[i1]) * pos.v.values * pos.k.values
    comm = deals.commission.values.sum() / len(pos)
    inv = -pos.profit.values - cost + comm
    sd = inv.std()
    return dict(id=eid, year=year, positions=len(pos), inv_net=float(inv.sum()), gross=float(pos.profit.sum()), max_win_share=float(inv.max() / inv.sum()) if inv.sum() > 0 else np.nan,
                inv_sum=float(inv.sum()), inv_sumsq=float((inv ** 2).sum()), inv_n=len(inv), inv_t=float(inv.mean() / sd * np.sqrt(len(inv))) if sd > 0 else np.nan)


def score() -> pd.DataFrame:
    base = pd.read_csv(HERE / "ea_invert_results.csv", dtype={"id": str}).set_index("id")
    rows = []
    for eid in candidates():
        per = [inv_year(eid, str(base.loc[eid, "symbol"]), y) for y in YEARS]
        ok_years = [p for p in per if p and p.get("positions", 0) >= 30 and p.get("inv_net", -1) > 0 and p.get("gross", 1) < 0 and p.get("max_win_share", 1) <= 0.5]
        allp = [p for p in per if p and "inv_n" in p]
        n = sum(p["inv_n"] for p in allp)
        pooled_mean = sum(p["inv_sum"] for p in allp) / n if n else np.nan
        var = (sum(p["inv_sumsq"] for p in allp) / n - pooled_mean ** 2) if n else np.nan
        t = pooled_mean / np.sqrt(var / n) if n and var > 0 else np.nan
        rows.append(dict(id=eid, title=str(base.loc[eid, "title"]), symbol=base.loc[eid, "symbol"], years_ok=len(ok_years), pooled_inv_t=t, confirmed=len(ok_years) == len(YEARS) and t >= 2.0,
                         **{f"inv_net_{p['year']}": p.get("inv_net") for p in per if p}, **{f"pos_{p['year']}": p.get("positions") for p in per if p}, **{f"gross_{p['year']}": p.get("gross") for p in per if p}))
    d = pd.DataFrame(rows); d.to_csv(OUT, index=False)
    return d


def main():
    ids = candidates()
    then = sys.argv[sys.argv.index("--then") + 1] if "--then" in sys.argv else "none"          # after scoring: none | batch (resume the main EA batch here) | signals (start the Telegram loops)
    if "--queue" in sys.argv:
        print(f"candidates {ids}; waiting for the main batch to finish; then: {then}", flush=True)
        while batch_running():
            time.sleep(60)
        try:
            run_years(ids)
        except RuntimeError as e:
            print("QUEUE STOPPED:", e, flush=True); sys.exit(1)
    d = score()
    print(d.round(1).to_string(index=False))
    print("CONFIRMED:", d[d.confirmed].id.tolist(), flush=True)
    if "--queue" in sys.argv:
        MARK.write_text(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
        if then == "signals":
            start_signal_loops()
        elif then == "batch":
            env = dict(os.environ, PYTHONPATH=str(ROOT))
            cmd = [sys.executable, "-u", "-m", "forex.ea_batch.run_batch", "--confirm-every", "0"] + (["--ea-root", EA_ROOT] if EA_ROOT else [])
            print("resuming the main batch:", " ".join(cmd[3:]), flush=True)
            sys.exit(subprocess.run(cmd, cwd=str(ROOT), env=env).returncode)


def user_env() -> dict:
    """Telegram variables from the Windows USER environment (they are not inherited by processes started before they were set)."""
    import winreg
    out = {}
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
        for n in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
            try:
                out[n] = winreg.QueryValueEx(k, n)[0]
            except OSError:
                pass
    return out


def start_signal_loops() -> None:
    """After the tester work: the MT5 broker signal loop (Telegram, 60 s) and the shadow forward-test bot, detached, no window."""
    env = dict(os.environ, PYTHONPATH=str(ROOT), **user_env())
    for mod, log in (("forex.forward_test.mt5_signals", SCRATCH / "mt5_signals.log"), ("forex.forward_test.bot", SCRATCH / "bot_loop.log")):
        subprocess.Popen([sys.executable, "-u", "-m", mod], cwd=str(ROOT), env=env, stdout=open(log, "ab"), stderr=subprocess.STDOUT, creationflags=0x08000000)


if __name__ == "__main__":
    main()
