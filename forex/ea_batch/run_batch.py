"""
Round 347 batch runner (the trader's second PC, Windows): compile every EA in forex/ea_batch/manifest.csv with MetaEditor and run it once in the MetaTrader 5 Strategy Tester on
the MT5 broker demo account's own data, then save its closed deals for the analysis (forex/ea_batch/analyze_reports.py, run by Claude).

  1. Close every MetaTrader 5 window (the tester starts its own terminal; a running one makes the command line ignored).
  2. pip install lxml            (once, for reading the reports)
  3. python -m forex.ea_batch.run_batch --limit 3          # a quick check: three EAs
     python -m forex.ea_batch.run_batch                    # all of them; resumable: Ctrl+C and start again, finished EAs are skipped
  4. git add -f forex/ea_batch/results && git commit -m "EA batch results" && git push

SAFETY: tests only (the Strategy Tester never sends orders to the account); the generated config sets AllowLiveTrading=0 and AllowDllImport=0, and the manifest
already excludes every EA with #import or network calls. Each EA runs at most --timeout seconds, then the terminal is closed.
TEST SETTINGS (Round 347, current -- the first screen used model 1 and 2021.10.01 - 2026.09.30; it was misleading for pending-order and grid EAs): the manifest's symbol and
timeframe, 2026.01.01 - 2026.09.30, model 4 (every tick based on real ticks, commission recorded), deposit 100,000 USD, leverage 1:100, the EA's default inputs. Results go to
results_2026/: one deals CSV per EA plus status.csv, which also records the tester's maximal equity and balance drawdown ($, eq_dd / bal_dd) for the scorer's sizing.
MT5's terminal path: MT5BROKER_MT5_TERMINAL or C:\\Program Files\\MetaTrader 5\\terminal64.exe.
TWO STAGES (Round 347): stage 1 is the 2026 screen above. Stage 2 (confirm.py) reruns the stage-1 candidates on 2025 and 2024 at their FROZEN stage-1 size and keeps only the EAs that
hold up there: two of the first three stage-1 leaders lost money in both years. The batch calls confirm.py by itself after every --confirm-every stage-1 EAs and once at the end
(0 = never); confirm.py starts this runner again with --from-date / --to-date / --results for the extra years.
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
# cloud_run.py (the Wine / M1-bar route) reads RESULTS, FROM and TO from this module, so they keep their original values. The second PC's real-tick 2026 screen takes its
# defaults from these instead, applied in main(), so the two routes never share a results folder or a test period.
SCREEN_RESULTS, SCREEN_FROM, SCREEN_TO = "results_2026", "2026.01.01", "2026.09.30"   # 2026 only (user's call); the earlier screens are in results/ (1-minute) and results_ticks/


def data_folder() -> Path:
    """The terminal's data folder (where MQL5\\Experts lives). Read from the folder's origin.txt (the install path of its terminal) so that no terminal window is started;
    falls back to the MetaTrader5 package, which starts the terminal."""
    for origin in (Path(os.getenv("APPDATA", "")) / "MetaQuotes" / "Terminal").glob("*/origin.txt"):
        try:
            if Path(origin.read_bytes().decode("utf-16").lstrip("﻿").strip()).resolve() == TERMINAL.parent.resolve():
                return origin.parent
        except (OSError, UnicodeDecodeError):
            continue
    import MetaTrader5 as mt5
    if not mt5.initialize(path=str(TERMINAL), timeout=90_000):
        raise SystemExit(f"could not start the terminal at {TERMINAL}: {mt5.last_error()}")
    p = Path(mt5.terminal_info().data_path)
    mt5.shutdown()
    return p


def kill_terminal():
    """Kill only the tester's OWN terminal (matched by its exe path), never another MT5 install: a live broker terminal running an EA (e.g. the MT5 broker account) must survive a tester run."""
    path = str(TERMINAL).replace("'", "''")
    ps = f"Get-CimInstance Win32_Process -Filter \"Name='{TERMINAL.name}'\" | Where-Object {{ $_.ExecutablePath -eq '{path}' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)


_DESKTOP: dict = {}


class _HiddenProcess:
    """The slice of subprocess.Popen that main() uses: wait(timeout), raising TimeoutExpired."""

    def __init__(self, handle, kernel32):
        self._h, self._k = handle, kernel32

    def wait(self, timeout=None):
        r = self._k.WaitForSingleObject(self._h, 0xFFFFFFFF if timeout is None else int(timeout * 1000))
        if r == 0x102:                                   # WAIT_TIMEOUT
            raise subprocess.TimeoutExpired("terminal64", timeout)
        self._k.CloseHandle(self._h)
        return 0


def _start_on_hidden_desktop(cmdline: str) -> _HiddenProcess:
    import ctypes
    from ctypes import wintypes

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR), ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                    ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD), ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                    ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD), ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD), ("lpReserved2", ctypes.c_void_p),
                    ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE), ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]

    user32, kernel32 = ctypes.WinDLL("user32", use_last_error=True), ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]; kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CreateProcessW.restype = wintypes.BOOL
    kernel32.CreateProcessW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p,
                                        wintypes.LPCWSTR, ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]
    if "h" not in _DESKTOP:
        user32.CreateDesktopW.restype = wintypes.HANDLE
        user32.CreateDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
        h = user32.CreateDesktopW("ea_batch_hidden", None, None, 0, 0x10000000, None)       # GENERIC_ALL
        if not h:
            raise OSError(ctypes.get_last_error(), "CreateDesktop failed")
        _DESKTOP["h"] = h                                # kept open for the life of this process: a desktop object dies with its last handle
    si = STARTUPINFOW(); si.cb = ctypes.sizeof(si); si.lpDesktop = "winsta0\\ea_batch_hidden"
    pi = PROCESS_INFORMATION()
    if not kernel32.CreateProcessW(None, ctypes.create_unicode_buffer(cmdline), None, None, False, 0, None, str(TERMINAL.parent), ctypes.byref(si), ctypes.byref(pi)):
        raise OSError(ctypes.get_last_error(), "CreateProcess failed")
    kernel32.CloseHandle(pi.hThread)
    return _HiddenProcess(pi.hProcess, kernel32)


def start_terminal(ini: Path):
    """Start the terminal for one tester run without a window on any of the user's desktops.
    Default (Windows): the process is created on a private desktop OBJECT (CreateDesktop; not a virtual desktop, never displayed), so nothing pops up on Desktop 1 or 2
    and no focus is stolen. EA_BATCH_VISIBLE=1 starts it normally (minimised, no focus); any failure of the hidden start falls back to that."""
    if sys.platform == "win32" and os.getenv("EA_BATCH_VISIBLE") != "1":
        try:
            return _start_on_hidden_desktop(subprocess.list2cmdline([str(TERMINAL), f"/config:{ini}"]))
        except OSError as e:
            print(f"hidden desktop unavailable ({e}); starting the terminal minimised instead", flush=True)
    kw = {}
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW; si.wShowWindow = 7        # SW_SHOWMINNOACTIVE
        kw["startupinfo"] = si
    return subprocess.Popen([str(TERMINAL), f"/config:{ini}"], **kw)


def compile_ea(editor: Path, src: Path) -> tuple[bool, str]:
    log = src.with_suffix(".log")
    subprocess.run([str(editor), f"/compile:{src}", f"/log:{log}"], capture_output=True, timeout=300)
    ok = src.with_suffix(".ex5").exists()
    txt = log.read_text(encoding="utf-16", errors="ignore") if log.exists() else ""
    return ok, txt[-400:].replace("\n", " ")


def common_login_lines() -> list[str]:
    """[Common] login lines for the tester ini, read from forex/.env (MT5BROKER_MT5_LOGIN / PASSWORD / SERVER). The batch kills and restarts the terminal before every EA; a terminal whose
    saved login has no stored password starts unauthorised and the tester then waits about 9 minutes for the trade server (2026-10-07). Empty if the three values are not all set."""
    try:
        from dotenv import dotenv_values
        v = dotenv_values(HERE.parent / ".env")
        if all(v.get(k) for k in ("MT5BROKER_MT5_LOGIN", "MT5BROKER_MT5_PASSWORD", "MT5BROKER_MT5_SERVER")):
            return ["[Common]", f"Login={v['MT5BROKER_MT5_LOGIN']}", f"Password={v['MT5BROKER_MT5_PASSWORD']}", f"Server={v['MT5BROKER_MT5_SERVER']}"]
    except Exception:
        pass
    return []


def write_ini(path: Path, expert_rel: str, symbol: str, period: str, report_rel: str, model: int = 4):
    path.write_text("\n".join(common_login_lines() + [
        "[Experts]", "AllowLiveTrading=0", "AllowDllImport=0", "Enabled=1",
        "[Tester]", f"Expert={expert_rel}", f"Symbol={symbol}", f"Period={period}", f"Model={model}", "Optimization=0", f"FromDate={FROM}", f"ToDate={TO}",
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


FLOOD_MB = 100          # stop an EA whose run grows the tester journal by more than this
MIN_FREE_GB = float(os.environ.get("EA_BATCH_MIN_FREE_GB", 10))      # pause while the data drive has less free space than this (the second PC sets a high value to cap what a night can use)
TRIM_JOURNAL_MB = float(os.environ.get("EA_BATCH_TRIM_JOURNAL_MB", 0))   # 0 = never touch the logs (default). > 0: after each EA, empty any tester journal file bigger than this (they only hold the EA's own chatter)


def journal_bytes(data: Path) -> int:
    """Total size of the tester's journal files (Tester\\logs): a blown-up EA can write tens of GB there, and the journal is one file per day."""
    return sum(f.stat().st_size for f in (data / "Tester" / "logs").glob("*.log") if f.exists())


def wait_for_disk(data: Path) -> None:
    """Block until the data drive has MIN_FREE_GB free. The runner never deletes logs itself: clear Tester\\logs by hand and the batch carries on."""
    warned = False
    while shutil.disk_usage(str(data)).free < MIN_FREE_GB * (1 << 30):          # MIN_FREE_GB may be a float (EA_BATCH_MIN_FREE_GB): shifting a float crashed the batch on the second PC
        if not warned:
            print(f"PAUSED: less than {MIN_FREE_GB} GB free on the data drive. Delete the big files in {data / 'Tester' / 'logs'} and the batch resumes by itself.", flush=True)
            warned = True
        time.sleep(60)


def trim_journal(data: Path) -> int:
    """Opt-in (EA_BATCH_TRIM_JOURNAL_MB > 0): empty the tester journals that grew past the limit, in the terminal's Tester\\logs and in the tester agent folders. Called only after an EA's run has ended
    (the terminal is closed), so nothing is writing to them. Returns the MB freed. Reports and results are never touched."""
    if TRIM_JOURNAL_MB <= 0:
        return 0
    roots = [data / "Tester" / "logs"]
    appdata = os.environ.get("APPDATA")
    if appdata:
        roots += list((Path(appdata) / "MetaQuotes" / "Tester" / data.name).glob("Agent-*/logs"))
    freed = 0
    for root in roots:
        for f in root.glob("*.log"):
            try:
                size = f.stat().st_size
                if size > TRIM_JOURNAL_MB * (1 << 20):
                    with open(f, "r+b") as fh:
                        fh.truncate(0)
                    freed += size >> 20
            except OSError:
                pass
    if freed:
        print(f"trimmed tester journals: {freed} MB freed", flush=True)
    return freed


def parse_drawdowns(htm: Path) -> tuple[float, float]:
    """The tester's own maximal equity and balance drawdowns in $ (the equity one includes floating losses, which closed deals hide: grid / martingale EAs)."""
    raw = htm.read_bytes()
    txt = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", errors="ignore")
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", txt))
    out = []
    for key in ("Equity Drawdown Maximal", "Balance Drawdown Maximal"):
        m = re.search(re.escape(key) + r"\s*:?\s*([\d ]+(?:\.\d+)?)\s*\(", txt)
        out.append(float(m.group(1).replace(" ", "")) if m else float("nan"))
    return out[0], out[1]


def upgrade_status(status_f: Path, rep_root: Path) -> None:
    """Older status.csv files lack eq_dd / bal_dd: fill them from the reports still on disk (only reports of this FROM-TO period), then rewrite the file."""
    if not status_f.exists():
        return
    st = pd.read_csv(status_f, dtype={"id": str})
    if "eq_dd" in st.columns:
        return
    eq, bal = [], []
    for i in st.id:
        htm = next(iter(rep_root.glob(f"{i}*.htm*")), None)
        e = b = float("nan")
        if htm is not None:
            raw = htm.read_bytes()
            txt = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", errors="ignore")
            m = re.search(r"Period:\s*\S+\s*\(([\d.]+)\s*-\s*([\d.]+)\)", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", txt)))
            if m and (m.group(1), m.group(2)) == (FROM, TO):
                e, b = parse_drawdowns(htm)
        eq.append(e); bal.append(b)
    st["eq_dd"], st["bal_dd"] = eq, bal
    st.to_csv(status_f, index=False)


def run_confirmation() -> None:
    """Stage 2 (confirm.py) on the current stage-1 candidates; a failure there must not stop the batch."""
    try:
        subprocess.run([sys.executable, "-u", "-m", "forex.ea_batch.confirm"], cwd=str(HERE.parent.parent))
    except Exception as e:
        print(f"confirmation stage failed: {e}", flush=True)


def stage_sources(d: Path, files: dict, tries: int = 5) -> bool:
    """Create the EA's folder and write its sources. A folder deleted a moment ago can still look present (pending delete / the D: junction), and the first such error ended a 1,075-EA run at EA 2, so retry; False = give up on this EA for now."""
    for k in range(tries):
        try:
            d.mkdir(exist_ok=True)
            for nm, b in files.items():
                (d / nm).write_bytes(b)
            return True
        except OSError as e:
            print(f"  folder setup for {d.name} failed ({type(e).__name__}: {e}); retry {k + 1}/{tries}", flush=True)
            time.sleep(3)
    return False


def main(argv=None):
    global RESULTS, FROM, TO
    for _s in (sys.stdout, sys.stderr):                                           # EA titles can hold any script; a redirected log must not crash the run on one
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--timeout", type=int, default=900); ap.add_argument("--only", default="")
    ap.add_argument("--from-date", default="", help="test period start, e.g. 2025.01.01 (default: the 2026 screen's)"); ap.add_argument("--to-date", default="")
    ap.add_argument("--results", default="", help="results folder name under forex/ea_batch (default results_2026) or an absolute path")
    ap.add_argument("--confirm-every", type=int, default=100, help="run the confirmation stage after this many stage-1 EAs (0 = never)")
    ap.add_argument("--ea-root", default="", help="path to folder where EAs are staged (default: MetaTrader data\\MQL5\\Experts\\ea_batch); use for D: direct access if junction mkdir fails")
    ap.add_argument("--model", type=int, default=4, help="tester model: 4 = every tick based on real ticks (default, the 2026 screen), 1 = 1-minute OHLC (the first Round 347 batch)")
    a = ap.parse_args(argv)
    FROM = a.from_date or SCREEN_FROM
    TO = a.to_date or SCREEN_TO
    RESULTS = Path(a.results) if a.results and Path(a.results).is_absolute() else HERE / (a.results or SCREEN_RESULTS)
    stage1 =bool(a.confirm_every) and not a.only and RESULTS.name == "results_2026"
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
    if a.ea_root:
        exp_root = Path(a.ea_root)
    else:
        exp_root = data / "MQL5" / "Experts" / "ea_batch"
    rep_root = data / "ea_batch_reports"
    inc_root = (exp_root.parents[1] / "Include") if a.ea_root else data / "MQL5" / "Include"      # same junction workaround as --ea-root: use the real D: path
    exp_root.mkdir(parents=True, exist_ok=True); rep_root.mkdir(exist_ok=True)
    upgrade_status(status_f, rep_root)
    z = zipfile.ZipFile(HERE / "sources.zip")
    n = 0
    for _, r in man.iterrows():
        if r.id in done:
            continue
        if a.limit and n >= a.limit:
            break
        n += 1; t0 = time.time()
        d = exp_root / r.id
        files = {name.split("/", 1)[1]: z.read(name) for name in z.namelist() if name.startswith(f"{r.id}/")}
        if not stage_sources(d, files):                # not recorded in status.csv, so the next run tries this EA again
            print(f"[{n}] {r.id}: skipped, could not set up its folder", flush=True)
            continue
        for b in files.values():                       # #include <dir/x.mqh> resolves under MQL5\Include: place the EA's own copy there
            for inc in re.findall(r"#include\s*<([^>]+)>", b.decode("utf-8", errors="ignore") + b.decode("utf-16", errors="ignore")):
                base = inc.replace("\\", "/").split("/")[-1]
                if base in files:
                    tgt = inc_root / inc.replace("\\", "/"); tgt.parent.mkdir(parents=True, exist_ok=True); tgt.write_bytes(files[base])
        ok, log = compile_ea(editor, d / r.main)
        rec = dict(id=r.id, title=r.title, symbol=r.symbol, period=r.period, compiled=ok, deals=0, net=0.0, seconds=0.0, note="" if ok else f"compile: {log}", eq_dd=float("nan"), bal_dd=float("nan"))
        if ok:
            ini = d / "tester.ini"; rep = rep_root / r.id
            for old in rep_root.glob(f"{r.id}.*"):
                old.unlink()
            write_ini(ini, f"ea_batch\\{r.id}\\{Path(r.main).with_suffix('.ex5').name}", r.symbol, r.period, f"ea_batch_reports\\{r.id}", a.model)
            kill_terminal()
            wait_for_disk(data)
            j0, t_run = journal_bytes(data), time.time()
            p = start_terminal(ini)
            while True:
                try:
                    p.wait(timeout=5)
                    break
                except subprocess.TimeoutExpired:
                    grown = journal_bytes(data) - j0
                    if grown > FLOOD_MB << 20:             # an EA that blew its account keeps sending orders that fail ("No money"): one run wrote GBs of journal
                        kill_terminal(); rec["note"] = f"journal flood: +{grown >> 20} MB in {int(time.time() - t_run)}s (account exhausted?); stopped"
                        break
                    if time.time() - t_run > a.timeout:
                        kill_terminal(); rec["note"] = f"timeout {a.timeout}s"
                        break
            trim_journal(data)
            htm = next(iter(rep_root.glob(f"{r.id}*.htm*")), None)
            if htm is not None:
                try:
                    deals = parse_report(htm)
                except Exception as e:                     # one unparseable report must not stop the whole batch
                    deals = None; rec["note"] = f"report parse error: {type(e).__name__}"
                if deals is not None:
                    deals.to_csv(RESULTS / f"{r.id}.csv", index=False)
                    rec.update(deals=len(deals), net=float((deals.profit + deals.commission + deals.swap).sum()))
                    rec["eq_dd"], rec["bal_dd"] = parse_drawdowns(htm)
            elif not rec["note"]:
                rec["note"] = "no report"
        rec["seconds"] = round(time.time() - t0, 1)
        pd.DataFrame([rec]).to_csv(status_f, mode="a", header=not status_f.exists(), index=False)
        print(f"[{n}] {r.id} {r.title[:50]!r} {r.symbol} {r.period}: compiled={ok} deals={rec['deals']} net={rec['net']:,.0f} {rec['note']} ({rec['seconds']}s)", flush=True)
        if stage1 and n % a.confirm_every == 0:
            run_confirmation()
    kill_terminal()
    if stage1 and not a.limit:
        run_confirmation()
    print("done; commit forex/ea_batch/results")


if __name__ == "__main__":
    main()
