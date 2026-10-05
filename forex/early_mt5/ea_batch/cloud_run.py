"""
Round 347 cloud runner: the same batch as run_batch.py, but inside a Claude Code cloud container with MetaTrader 5 under Wine (cloud_setup.sh first).

  bash forex/early_mt5/ea_batch/cloud_setup.sh
  git lfs pull --include="forex/early_mt5/data/*"                 # MT5 broker's own M1 bid bars (2021-09..2026-10), the tester's data here
  python forex/early_mt5/ea_batch/cloud_run.py --limit 3          # check
  python forex/early_mt5/ea_batch/cloud_run.py --workers 4        # all; resumable; results -> forex/early_mt5/ea_batch/results (same format as run_batch.py)

OFFLINE: the cloud container cannot reach MT5 broker's trade server (port 443 passes TLS only; MT5's protocol is not TLS; see README), so the tester runs on
custom symbols <SYMBOL>_MT5BROKER built by ImportMT5BROKER.mq5 from forex/early_mt5/data/<SYMBOL>_M1_ticks_full.parquet: MT5 broker's own ticks, aggregated to M1 bid OHLC with
the per-minute spread. Model 1 (1-minute OHLC) is the pre-registered model, so the tester sees the same bars it would download from MT5. Differences
from the second PC route (disclosed in the round's record): no commission; FX swaps 0 (index and gold swaps are MT5 broker's 2026-10-01 values); margin in USD;
an EA that hard-codes a real symbol name finds no data and makes no deals; EAs on symbols without MT5 M1 data in the repo are skipped (status note).
The tester still needs an account named in its config: the MT5 broker login from the environment (MT5BROKER_MT5_LOGIN / _PASSWORD / _SERVER; the trader agreed on
2026-10-05) is remembered once through a one-off login config that is deleted right after; the password is never printed, logged or committed.
Tests only: AllowLiveTrading=0 and AllowDllImport=0, same settings as run_batch.py.
--workers N runs N terminals at once, each in its own copy of the Wine prefix (EA_CLOUD_ROOT_w1..), on every N-th EA of the fixed shuffle.
"""
from __future__ import annotations

import argparse
import fcntl
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
sys.path.insert(0, str(HERE.parent.parent))
from mt5broker.ea_batch import run_batch as RB  # noqa: E402

ROOT = Path(os.getenv("EA_CLOUD_ROOT", "/root/mt5cloud"))
PREFIX = ROOT / "prefix"
MT = PREFIX / "drive_c" / "Program Files" / "MetaTrader 5"
CFG = PREFIX / "drive_c" / "ea"
ENV = dict(os.environ, WINEPREFIX=str(PREFIX), WINEDEBUG="-all")
DATA = HERE.parent / "data"
STATUS_LOCK = Path(os.getenv("EA_STATUS_LOCK", "/tmp/ea_batch_status.lock"))
# name: digits, point, contract, base, profit currency, calc mode (0 forex, 4 CFD leverage), tick value (USD per point per lot; approximate for non-USD
# profit, the tester converts the actual P&L itself), swap long, swap short (points), triple-swap weekday. Index and gold values: forex/early_mt5/specs/symbol_specs_20261001.json.
SPECS = {
    "EURUSD": (5, 0.00001, 100000, "EUR", "USD", 0, 1.0, 0, 0, 3),
    "GBPUSD": (5, 0.00001, 100000, "GBP", "USD", 0, 1.0, 0, 0, 3),
    "AUDUSD": (5, 0.00001, 100000, "AUD", "USD", 0, 1.0, 0, 0, 3),
    "USDJPY": (3, 0.001, 100000, "USD", "JPY", 0, 0.67, 0, 0, 3),
    "USDCHF": (5, 0.00001, 100000, "USD", "CHF", 0, 1.12, 0, 0, 3),
    "USDCAD": (5, 0.00001, 100000, "USD", "CAD", 0, 0.73, 0, 0, 3),
    "XAUUSD": (2, 0.01, 100, "USD", "USD", 4, 1.0, -87.51, -4.2, 3),
    "US30.cash": (2, 0.01, 1, "USD", "USD", 4, 0.01, -1172.12, 59.17, 5),
    "US100.cash": (2, 0.01, 1, "USD", "USD", 4, 0.01, -692.63, 34.96, 5),
}


def available_symbols() -> set[str]:
    files = {s: DATA / f"{s}_M1_ticks_full.parquet" for s in SPECS}
    return {s for s, f in files.items() if f.exists() and f.stat().st_size > 1000}          # an un-pulled LFS pointer is ~130 bytes


def wine(args, timeout):
    try:
        return subprocess.run(["xvfb-run", "-a", "-n", os.getenv("EA_XVFB_NUM", "99"), "wine", *args], cwd=MT, env=ENV, capture_output=True, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        subprocess.run(["wineserver", "-k"], env=ENV); return -1


def stop():
    subprocess.run(["wineserver", "-k"], env=ENV, capture_output=True); time.sleep(1)


def close_terminal():
    """Graceful close first so the terminal flushes its journal and saves state, then kill whatever is left in this prefix."""
    subprocess.run(["wine", "taskkill", "/IM", "terminal64.exe"], cwd=MT, env=ENV, capture_output=True)
    time.sleep(15)
    stop()


def start_terminal(cfg: str) -> subprocess.Popen:
    return subprocess.Popen(["xvfb-run", "-a", "-n", os.getenv("EA_XVFB_NUM", "99"), "wine", "terminal64.exe", "/portable", f"/config:C:\\ea\\{cfg}"],
                            cwd=MT, env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def terminal_log_tail(n=6) -> str:
    logs = sorted((MT / "logs").glob("[0-9]*.log"))           # the terminal's dated journal, not metaeditor.log (which sorts last)
    return "" if not logs else " | ".join(logs[-1].read_bytes().decode("utf-16", errors="ignore").strip().splitlines()[-n:])


def login_once():
    """Start the terminal once with the account so it is remembered (accounts.dat); the password file is deleted right after.
    Authorization is not required: the offline tester only needs the account named in its config."""
    login, pw, server = (os.getenv(k) for k in ("MT5BROKER_MT5_LOGIN", "MT5BROKER_MT5_PASSWORD", "MT5BROKER_MT5_SERVER"))
    if not (login and pw and server):
        raise SystemExit("set MT5BROKER_MT5_LOGIN, MT5BROKER_MT5_PASSWORD and MT5BROKER_MT5_SERVER in the environment settings")
    marker = CFG / "account.done"
    if marker.exists():
        return login, server
    f = CFG / "login.ini"
    try:
        f.write_text(f"[Common]\r\nLogin={login}\r\nPassword={pw}\r\nServer={server}\r\nKeepPrivate=0\r\n[StartUp]\r\nSymbol=EURUSD\r\nPeriod=H1\r\n", encoding="utf-8")
        start_terminal("login.ini")
        for _ in range(20):
            time.sleep(3)
            if re.search(r"authorized on|connection to .* lost", terminal_log_tail(20)):
                break
        time.sleep(10)
    finally:
        f.unlink(missing_ok=True)
    close_terminal()
    tail = terminal_log_tail(20)
    print("login:", "authorized" if re.search(r"authorized on", tail) else "not authorized (expected in the cloud; the tester runs offline)", flush=True)
    marker.write_text("account remembered\n")
    return login, server


def prepare_symbols(syms):
    """Build <SYMBOL>_MT5BROKER custom symbols from the parquet bars (once per prefix)."""
    hist = MT / "Bases" / "Custom" / "history"
    need = sorted(s for s in syms if not (hist / f"{s}_MT5BROKER").exists())
    if not need:
        return
    files = MT / "MQL5" / "Files"; files.mkdir(parents=True, exist_ok=True)
    rows = []
    for s in need:
        d = pd.read_parquet(DATA / f"{s}_M1_ticks_full.parquet", columns=["time", "open", "high", "low", "close", "tick_volume", "spread"])
        d.to_csv(files / f"BARS_{s}_MT5BROKER.csv", index=False, header=False)
        dg, pt, ct, base, prof, calc, tv, swl, sws, r3 = SPECS[s]
        rows.append(f"{s}_MT5BROKER,{dg},{pt:.5f},{ct},{base},{prof},{calc},{tv},{swl},{sws},{r3}")
    (files / "bars_specs.csv").write_text("\r\n".join(rows) + "\r\n")
    shutil.copy(HERE / "ImportMT5BROKER.mq5", MT / "MQL5" / "Scripts" / "ImportMT5BROKER.mq5")
    wine(["MetaEditor64.exe", "/portable", "/compile:MQL5\\Scripts\\ImportMT5BROKER.mq5", "/log:MQL5\\Scripts\\ImportMT5BROKER.log"], 180)
    (CFG / "import.ini").write_text("[StartUp]\r\nScript=ImportMT5BROKER\r\n")
    log = files / "import_log.txt"; log.unlink(missing_ok=True)
    start_terminal("import.ini")
    for _ in range(300):
        time.sleep(3)
        if log.exists() and "IMPORT_DONE" in log.read_text(errors="ignore"):
            break
    close_terminal()
    print("import:", " | ".join(l for l in (log.read_text(errors="ignore").splitlines() if log.exists() else ["no import log"]) if "bars" in l or "no " in l), flush=True)
    for s in need:
        (files / f"BARS_{s}_MT5BROKER.csv").unlink(missing_ok=True)
    missing = [s for s in need if not (hist / f"{s}_MT5BROKER").exists()]
    if missing:
        raise SystemExit(f"custom symbols not built: {missing}")


def ini(path: Path, login, server, expert_rel, symbol, period, report_rel):
    path.write_text("\r\n".join([
        "[Common]", f"Login={login}", f"Server={server}",
        "[Experts]", "AllowLiveTrading=0", "AllowDllImport=0", "Enabled=1",
        "[Tester]", f"Login={login}", f"Expert={expert_rel}", f"Symbol={symbol}", f"Period={period}", "Model=1", "Optimization=0", f"FromDate={RB.FROM}",
        f"ToDate={RB.TO}", "ForwardMode=0", "Deposit=100000", "Currency=USD", "Leverage=100", "ExecutionMode=0", "Visual=0", f"Report={report_rel}",
        "ReplaceReport=1", "ShutdownTerminal=1", ""]), encoding="utf-8")


def place_indicators(eid: str, files: dict[str, bytes]) -> int:
    """Compile the EA's own indicators into MQL5\\Indicators, where iCustom looks for them (539 of the 1,220 EAs ship one); a folder named in the
    EA's iCustom string (e.g. "Custom\\\\X") is kept. The EA's .mqh files go next to each indicator for its quoted #includes."""
    src = " ".join(b.decode("utf-8", errors="ignore") + b.decode("utf-16", errors="ignore") for b in files.values())
    n = 0
    for nm, b in files.items():
        if not nm.lower().endswith(".mq5") or (b"OnCalculate" not in b and "OnCalculate".encode("utf-16-le") not in b):
            continue
        stem = Path(nm).stem
        m = re.search(r'"((?:[\w .\-]+\\\\)*)' + re.escape(stem) + r'(?:\.ex5)?"', src)
        sub = m.group(1).replace("\\\\", "/") if m else ""
        tdir = MT / "MQL5" / "Indicators" / sub; tdir.mkdir(parents=True, exist_ok=True)
        (tdir / Path(nm).name).write_bytes(b)
        for h, hb in files.items():
            if h.lower().endswith(".mqh"):
                (tdir / Path(h).name).write_bytes(hb)
        rel = ("MQL5/Indicators/" + sub + Path(nm).name).replace("/", "\\")
        wine(["MetaEditor64.exe", "/portable", f"/compile:{rel}", f"/log:MQL5\\Experts\\ea_batch\\{eid}\\ind.log"], 180)
        n += (tdir / Path(nm).with_suffix(".ex5").name).exists()
    return n


def append_status(status_f: Path, rec: dict):
    with open(STATUS_LOCK, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        pd.DataFrame([rec]).to_csv(status_f, mode="a", header=not status_f.exists(), index=False)


def run_workers(a):
    """Prepare the main prefix, clone it per worker, run one shard per worker, wait for all."""
    login_once(); prepare_symbols(available_symbols()); stop()
    for f in (ROOT / "mt5setup.exe", ROOT / "mt5broker5setup.exe"):
        f.unlink(missing_ok=True)
    procs = []
    for i in range(a.workers):
        root = ROOT if i == 0 else Path(f"{ROOT}_w{i}")
        if not root.exists():
            subprocess.run(["cp", "-a", str(ROOT), str(root)], check=True)
        env = dict(os.environ, EA_CLOUD_ROOT=str(root), EA_XVFB_NUM=str(99 + 10 * i))
        procs.append(subprocess.Popen([sys.executable, __file__, "--shard", str(i), "--of", str(a.workers), "--timeout", str(a.timeout),
                                       "--limit", str(a.limit)], env=env))
    for p in procs:
        p.wait()
    print("done (all workers)")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--timeout", type=int, default=900); ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=1); ap.add_argument("--shard", type=int, default=0); ap.add_argument("--of", type=int, default=1)
    a = ap.parse_args(argv)
    if not (MT / "terminal64.exe").exists():
        raise SystemExit("run bash forex/early_mt5/ea_batch/cloud_setup.sh first")
    if a.workers > 1:
        return run_workers(a)
    syms = available_symbols()
    if not syms:
        raise SystemExit('no MT5 M1 bars: git lfs pull --include="forex/early_mt5/data/*"')
    login, server = login_once()
    prepare_symbols(syms)
    man = pd.read_csv(HERE / "manifest.csv", dtype={"id": str})
    man = man[man.keep].sample(frac=1.0, random_state=347)
    if "precompiled_ok" in man:
        man = man[man.precompiled_ok.astype(str).str.lower() == "true"]
    if a.only:
        man = man[man.id.isin(a.only.split(","))]
    man = man.iloc[a.shard::a.of]
    RB.RESULTS.mkdir(exist_ok=True)
    status_f = RB.RESULTS / "status.csv"
    done = set(pd.read_csv(status_f, dtype={"id": str}).id) if status_f.exists() else set()
    exp_root, rep_root, inc_root = MT / "MQL5" / "Experts" / "ea_batch", MT / "ea_batch_reports", MT / "MQL5" / "Include"
    exp_root.mkdir(parents=True, exist_ok=True); rep_root.mkdir(exist_ok=True)
    z = zipfile.ZipFile(HERE / "sources.zip")
    n = 0
    for _, r in man.iterrows():
        if r.id in done:
            continue
        if r.symbol not in syms:
            append_status(status_f, dict(id=r.id, title=r.title, symbol=r.symbol, period=r.period, compiled="", deals=0, net=0.0, seconds=0.0,
                                         note="skipped: no MT5 M1 data for this symbol"))
            continue
        if a.limit and n >= a.limit:
            break
        n += 1; t0 = time.time()
        d = exp_root / r.id; d.mkdir(exist_ok=True)
        files = {nm.split("/", 1)[1]: z.read(nm) for nm in z.namelist() if nm.startswith(f"{r.id}/")}
        for nm, b in files.items():
            (d / nm).write_bytes(b)
        for b in files.values():
            for inc in re.findall(r"#include\s*<([^>]+)>", b.decode("utf-8", errors="ignore") + b.decode("utf-16", errors="ignore")):
                base = inc.replace("\\", "/").split("/")[-1]
                if base in files:
                    t = inc_root / inc.replace("\\", "/"); t.parent.mkdir(parents=True, exist_ok=True); t.write_bytes(files[base])
        place_indicators(r.id, {nm: b for nm, b in files.items() if nm != r.main})
        wine(["MetaEditor64.exe", "/portable", f"/compile:MQL5\\Experts\\ea_batch\\{r.id}\\{r.main}", f"/log:MQL5\\Experts\\ea_batch\\{r.id}\\c.log"], 180)
        compiled = (d / Path(r.main).with_suffix(".ex5").name).exists()
        rec = dict(id=r.id, title=r.title, symbol=r.symbol, period=r.period, compiled=compiled, deals=0, net=0.0, seconds=0.0, note="" if compiled else "compile failed")
        if compiled:
            for old in rep_root.glob(f"{r.id}.*"):
                old.unlink()
            ini(CFG / "test.ini", login, server, f"ea_batch\\{r.id}\\{Path(r.main).with_suffix('.ex5').name}", f"{r.symbol}_MT5BROKER", r.period, f"ea_batch_reports\\{r.id}")
            rc = wine(["terminal64.exe", "/portable", r"/config:C:\ea\test.ini"], a.timeout)
            if rc == -1:
                rec["note"] = f"timeout {a.timeout}s"
            htm = next(iter(rep_root.glob(f"{r.id}*.htm*")), None)
            if htm is not None:
                deals = RB.parse_report(htm)
                deals.to_csv(RB.RESULTS / f"{r.id}.csv", index=False)
                rec.update(deals=len(deals), net=float((deals.profit + deals.commission + deals.swap).sum()))
                for f in rep_root.glob(f"{r.id}*"):
                    f.unlink()
            elif not rec["note"]:
                rec["note"] = "no report: " + re.sub(r"\d{6,}", "<login>", terminal_log_tail(3))[-200:]
        stop()
        for f in [*MT.glob("Tester/Agent-*/logs/*.log"), *MT.glob("Tester/logs/*.log")]:   # busy EAs write GBs of journal (agent and terminal side)
            if f.stat().st_size > 50e6:                                                     # into each prefix; the session's disk is limited
                f.unlink()
        rec["seconds"] = round(time.time() - t0, 1)
        append_status(status_f, rec)
        print(f"[w{a.shard} {n}] {r.id} {r.title[:45]!r} {r.symbol} {r.period}: compiled={compiled} deals={rec['deals']} net={rec['net']:,.0f} {rec['note']} ({rec['seconds']}s)", flush=True)
    print(f"done (worker {a.shard})")


if __name__ == "__main__":
    main()
