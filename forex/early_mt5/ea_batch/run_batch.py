"""
Round 347 batch runner (the trader's second PC, Windows): compile every EA in forex/early_mt5/ea_batch/manifest.csv with MetaEditor and run it once in the MetaTrader 5 Strategy Tester on
the MT5 broker demo account's own data, then save its closed deals for the analysis (forex/early_mt5/ea_batch/analyze_reports.py, run by Claude).

  1. Close every MetaTrader 5 window (the tester starts its own terminal; a running one makes the command line ignored).
  2. pip install lxml            (once, for reading the reports)
  3. python -m mt5broker.ea_batch.run_batch --limit 3          # a quick check: three EAs
     python -m mt5broker.ea_batch.run_batch                    # all of them; resumable: Ctrl+C and start again, finished EAs are skipped
  4. git add -f forex/early_mt5/ea_batch/results && git commit -m "EA batch results" && git push

SAFETY: tests only (the Strategy Tester never sends orders to the account); the generated config sets AllowLiveTrading=0 and AllowDllImport=0, and the manifest
already excludes every EA with #import or network calls. Each EA runs at most --timeout seconds, then the terminal is closed.
TEST SETTINGS (Round 347, fixed): the manifest's symbol and timeframe, 2021.10.01 - 2026.09.30, model 1 (1-minute OHLC: fast; real ticks would take weeks for 1,000
EAs), deposit 100,000 USD, leverage 1:100, the EA's default inputs. MT5's terminal path: MT5BROKER_MT5_TERMINAL or C:\\Program Files\\MetaTrader 5\\terminal64.exe.
"""
from __future__ import annotations

import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
TERMINAL = Path(os.getenv("MT5BROKER_MT5_TERMINAL") or r"C:\Program Files\MetaTrader 5\terminal64.exe")
FROM, TO = "2021.10.01", "2026.09.30"


def data_folder() -> Path:
    """The terminal's data folder (where MQL5\\Experts lives), from the MetaTrader5 package."""
    import MetaTrader5 as mt5
    if not mt5.initialize(path=str(TERMINAL), timeout=90_000):
        raise SystemExit(f"could not start the terminal at {TERMINAL}: {mt5.last_error()}")
    p = Path(mt5.terminal_info().data_path)
    mt5.shutdown()
    return p


def kill_terminal():
    subprocess.run(["taskkill", "/F", "/IM", TERMINAL.name], capture_output=True)


def compile_ea(editor: Path, src: Path) -> tuple[bool, str]:
    log = src.with_suffix(".log")
    subprocess.run([str(editor), f"/compile:{src}", f"/log:{log}"], capture_output=True, timeout=300)
    ok = src.with_suffix(".ex5").exists()
    txt = log.read_text(encoding="utf-16", errors="ignore") if log.exists() else ""
    return ok, txt[-400:].replace("\n", " ")


def write_ini(path: Path, expert_rel: str, symbol: str, period: str, report_rel: str):
    path.write_text("\n".join([
        "[Experts]", "AllowLiveTrading=0", "AllowDllImport=0", "Enabled=1",
        "[Tester]", f"Expert={expert_rel}", f"Symbol={symbol}", f"Period={period}", "Model=1", "Optimization=0", f"FromDate={FROM}", f"ToDate={TO}",
        "ForwardMode=0", "Deposit=100000", "Currency=USD", "Leverage=100", "ExecutionMode=0", "Visual=0", f"Report={report_rel}", "ReplaceReport=1",
        "ShutdownTerminal=1", ""]), encoding="utf-8")


def parse_report(htm: Path) -> pd.DataFrame:
    raw = htm.read_bytes()
    txt = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", errors="ignore")
    for t in pd.read_html(io.StringIO(txt)):
        # the Deals header sits mid-table, below the Orders section, in MT5's report
        hdr = next((i for i in range(t.shape[0]) if {"deal", "profit", "time"} <= {str(c).strip().lower() for c in t.iloc[i].values}), None)
        if hdr is not None:
            cols = [str(c).strip().lower() for c in t.iloc[hdr].values]
            t = t.iloc[hdr + 1:].copy(); t.columns = cols
            t = t[t["type"].astype(str).str.lower().isin(["buy", "sell"])]
            num = lambda c: pd.to_numeric(t[c].astype(str).str.replace(" ", "").str.replace("\xa0", ""), errors="coerce").fillna(0.0) if c in t else 0.0
            return pd.DataFrame({"time": t["time"].values, "direction": t.get("direction", "").values,
                                 "volume": num("volume"), "price": num("price"), "commission": num("commission"), "swap": num("swap"), "profit": num("profit")})
    return pd.DataFrame(columns=["time", "direction", "volume", "price", "commission", "swap", "profit"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--timeout", type=int, default=900); ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    man = pd.read_csv(HERE / "manifest.csv", dtype={"id": str})
    man = man[man.keep].sample(frac=1.0, random_state=347)        # fixed random order: any partial run is an unbiased sample
    if "precompiled_ok" in man:                                    # skip the EAs that did not compile in the offline MetaEditor check (Wine, build 6238)
        man = man[man.precompiled_ok.astype(str).str.lower() == "true"]
    if a.only:
        man = man[man.id.isin(a.only.split(","))]
    RESULTS.mkdir(exist_ok=True)
    status_f = RESULTS / "status.csv"
    done = set(pd.read_csv(status_f, dtype={"id": str}).id) if status_f.exists() else set()
    data = data_folder(); editor = TERMINAL.with_name("metaeditor64.exe")
    exp_root = data / "MQL5" / "Experts" / "ea_batch"; rep_root = data / "ea_batch_reports"
    exp_root.mkdir(parents=True, exist_ok=True); rep_root.mkdir(exist_ok=True)
    z = zipfile.ZipFile(HERE / "sources.zip")
    n = 0
    for _, r in man.iterrows():
        if r.id in done:
            continue
        if a.limit and n >= a.limit:
            break
        n += 1; t0 = time.time()
        d = exp_root / r.id; d.mkdir(exist_ok=True)
        files = {name.split("/", 1)[1]: z.read(name) for name in z.namelist() if name.startswith(f"{r.id}/")}
        for nm, b in files.items():
            (d / nm).write_bytes(b)
        for b in files.values():                       # #include <dir/x.mqh> resolves under MQL5\Include: place the EA's own copy there
            for inc in re.findall(r"#include\s*<([^>]+)>", b.decode("utf-8", errors="ignore") + b.decode("utf-16", errors="ignore")):
                base = inc.replace("\\", "/").split("/")[-1]
                if base in files:
                    tgt = data / "MQL5" / "Include" / inc.replace("\\", "/"); tgt.parent.mkdir(parents=True, exist_ok=True); tgt.write_bytes(files[base])
        ok, log = compile_ea(editor, d / r.main)
        rec = dict(id=r.id, title=r.title, symbol=r.symbol, period=r.period, compiled=ok, deals=0, net=0.0, seconds=0.0, note="" if ok else f"compile: {log}")
        if ok:
            ini = d / "tester.ini"; rep = rep_root / r.id
            for old in rep_root.glob(f"{r.id}.*"):
                old.unlink()
            write_ini(ini, f"ea_batch\\{r.id}\\{Path(r.main).with_suffix('.ex5').name}", r.symbol, r.period, f"ea_batch_reports\\{r.id}")
            kill_terminal()
            p = subprocess.Popen([str(TERMINAL), f"/config:{ini}"])
            try:
                p.wait(timeout=a.timeout)
            except subprocess.TimeoutExpired:
                kill_terminal(); rec["note"] = f"timeout {a.timeout}s"
            htm = next(iter(rep_root.glob(f"{r.id}*.htm*")), None)
            if htm is not None:
                deals = parse_report(htm)
                deals.to_csv(RESULTS / f"{r.id}.csv", index=False)
                rec.update(deals=len(deals), net=float((deals.profit + deals.commission + deals.swap).sum()))
            elif not rec["note"]:
                rec["note"] = "no report"
        rec["seconds"] = round(time.time() - t0, 1)
        pd.DataFrame([rec]).to_csv(status_f, mode="a", header=not status_f.exists(), index=False)
        print(f"[{n}] {r.id} {r.title[:50]!r} {r.symbol} {r.period}: compiled={ok} deals={rec['deals']} net={rec['net']:,.0f} {rec['note']} ({rec['seconds']}s)", flush=True)
    kill_terminal()
    print("done; commit forex/early_mt5/ea_batch/results")


if __name__ == "__main__":
    main()
