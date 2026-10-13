"""Entry SIGNALS of the original EA Exp_JFatl_Digit_System (H4, default inputs) on MT5 broker's FX pairs, per year, for the all-pairs study of the mirrored lead (pre-registered and amended in PREREG_LEAD_ALLPAIRS.md).
   python -m forex.ea_batch.lead_allpairs_run --pairs GBPUSD --years 2023,2024,2025,2022,2026          the validation
   python -m forex.ea_batch.lead_allpairs_run                                                           all 28 pairs x 2022..2026, resumable
Runs on the PORTABLE MT5 broker tester terminal (D:\\finance\\mt5_mt5_tester: own data folder, saved login of account <acct>, Algo Trading off, no charts), symbols <PAIR>+, USD 100,000, leverage 1:100, default inputs, Model 2 (open prices only: the EA decides on closed H4 bars).
MT5 broker's symbols reject the EA's order filling mode ("OrderCheck(): unsupported order filling type"), so the EA never opens a position there. That does not matter: it still raises every signal (BuyPositionOpen() / SellPositionOpen() is called at the signal bar), the tester journal records each call with the simulated time, and the original EA opens a new position at EVERY signal regardless of open positions (lesson 40), so the signal list is the entry list.
Output: forex/ea_batch/leadpairs_mt5/results_<year>/<PAIR>.entries.csv (te, side: +1 original buy / -1 original sell) + .meta.json. The same code with --terminal D:\\finance\\mt5_mt5broker_tester --suffix "" gives MT5 broker signals (there positions open and deals exist)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def _arg(name: str, default: str | None = None) -> str | None:
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


TERM_DIR = Path(_arg("--terminal", r"D:\finance\mt5_mt5_tester"))
SUFFIX = _arg("--suffix", "+")                                   # MT5 broker symbols are <PAIR>+ ; use --suffix "" with the MT5 broker terminal
NOLOGIN = "--no-login" in sys.argv or "mt5_mt5" in str(TERM_DIR)  # the MT5 broker portable copy logs in from its saved account; the MT5 broker demo login in forex/.env must not go into its ini
if os.path.normcase(str(TERM_DIR)) in {os.path.normcase(r"C:\Program Files\MetaTrader 5"), os.path.normcase(r"C:\Program Files\MT5 MT5 Terminal")}:
    raise SystemExit("refusing to run the tester on a LIVE terminal: " + str(TERM_DIR))
os.environ["MT5BROKER_MT5_TERMINAL"] = str(TERM_DIR / "terminal64.exe")
os.environ.setdefault("EA_BATCH_MIN_FREE_GB", "8")

from forex.ea_batch import run_batch as RB  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / ("leadpairs_mt5" if "mt5_mt5" in str(TERM_DIR) else "leadpairs")
PAIRS = ["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD", "CADCHF", "CADJPY", "CHFJPY", "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD", "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD",
         "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
YEARS = {"2022": ("2022.01.01", "2022.12.31"), "2023": ("2023.01.01", "2023.12.31"), "2024": ("2024.01.01", "2024.12.31"), "2025": ("2025.01.01", "2025.12.31"), "2026": ("2026.01.01", "2026.09.30")}
EXPERT = r"ea_batch\15888\Exp_JFatl_Digit_System.ex5"
MODEL = int(_arg("--model", "2"))
SIG = re.compile(r"Core 01\s+(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})\s+(Buy|Sell)PositionOpen\(\)")


def _start_portable(ini: Path):
    exe = str(TERM_DIR / "terminal64.exe")
    if sys.platform == "win32" and os.getenv("EA_BATCH_VISIBLE") != "1":
        try:
            return RB._start_on_hidden_desktop(subprocess.list2cmdline([exe, "/portable", f"/config:{ini}"]))
        except OSError as e:
            print(f"hidden desktop unavailable ({e}); minimised start", flush=True)
    si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW; si.wShowWindow = 7
    return subprocess.Popen([exe, "/portable", f"/config:{ini}"], cwd=str(TERM_DIR), startupinfo=si)


RB.data_folder = lambda: TERM_DIR
RB.start_terminal = _start_portable
if NOLOGIN:
    RB.common_login_lines = lambda: []


def tester_log() -> Path:
    return TERM_DIR / "Tester" / "logs" / f"{datetime.now():%Y%m%d}.log"


def signals_since(lf: Path, pos0: int) -> pd.DataFrame:
    """Signals the EA raised during the run: every BuyPositionOpen() / SellPositionOpen() line appended to the tester journal after byte offset pos0 (UTF-16)."""
    if not lf.exists():
        return pd.DataFrame(columns=["te", "side"])
    b = lf.read_bytes()[pos0 - (pos0 % 2):]
    txt = b.decode("utf-16-le", errors="ignore")
    seen = sorted({(m.group(1), 1 if m.group(2) == "Buy" else -1) for m in SIG.finditer(txt)})
    return pd.DataFrame(seen, columns=["te", "side"]).assign(te=lambda d: pd.to_datetime(d.te, format="%Y.%m.%d %H:%M:%S"))


def deals_with_type(htm: Path) -> pd.DataFrame:
    """Same table as run_batch.parse_report but KEEPING the deal type (buy / sell), which is what gives each entry's direction."""
    import io
    raw = htm.read_bytes()
    txt = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", errors="ignore")
    for t in pd.read_html(io.StringIO(txt)):
        hdr = next((i for i in range(t.shape[0]) if {"deal", "profit", "time"} <= {str(c).strip().lower() for c in t.iloc[i].values}), None)
        if hdr is not None:
            t = t.iloc[hdr + 1:].copy().set_axis([str(c).strip().lower() for c in t.iloc[hdr].values], axis=1)
            t = t[t["type"].astype(str).str.lower().isin(["buy", "sell"])]
            num = lambda c: pd.to_numeric(t[c].astype(str).str.replace(" ", "").str.replace(" ", ""), errors="coerce").fillna(0.0) if c in t else 0.0
            return pd.DataFrame({"time": t["time"].values, "type": t["type"].astype(str).str.lower().values, "direction": t.get("direction", "").values, "volume": num("volume"), "price": num("price"), "profit": num("profit")})
    return pd.DataFrame(columns=["time", "type", "direction", "volume", "price", "profit"])


def quality(htm: Path | None) -> dict:
    if htm is None:
        return {}
    b = htm.read_bytes()
    t = b.decode("utf-16", errors="ignore") if b[:2] in (b"\xff\xfe", b"\xfe\xff") else b.decode("cp1252", errors="ignore")
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))
    m = re.search(r"History Quality:\s*(\S+(?: \w+)?)", txt)
    return dict(history_quality=m.group(1) if m else None)


def run_job(pair: str, year: str) -> dict | None:
    rd = OUT / f"m{MODEL}" / f"results_{year}"; rd.mkdir(parents=True, exist_ok=True)
    meta_f = rd / f"{pair}.meta.json"
    if meta_f.exists():
        return json.loads(meta_f.read_text())
    frm, to = YEARS[year]; RB.FROM, RB.TO = frm, to
    name = f"lead_{pair}_{year}_m{MODEL}"; rep_root = TERM_DIR / "ea_batch_reports"; rep_root.mkdir(exist_ok=True)
    ini = Path(r"D:\finance\tmp") / f"{name}.ini"; ini.parent.mkdir(parents=True, exist_ok=True)
    RB.write_ini(ini, EXPERT, pair + SUFFIX, "H4", f"ea_batch_reports\\{name}", model=MODEL)
    for old in rep_root.glob(f"{name}.*"):
        old.unlink()
    RB.kill_terminal(); lf = tester_log(); pos0 = lf.stat().st_size if lf.exists() else 0
    t0 = time.time(); p = RB.start_terminal(ini); note = ""
    while True:
        try:
            p.wait(timeout=5); break
        except subprocess.TimeoutExpired:
            if time.time() - t0 > 1800:
                RB.kill_terminal(); note = "timeout 1800s"; break
    htm = next(iter(rep_root.glob(f"{name}*.htm*")), None)
    sig = signals_since(tester_log(), pos0)                                          # fallback only: signals that the broker REFUSED (journal lines); empty when the orders go through
    ent = pd.DataFrame(columns=["te", "side"]); nd = 0
    if htm is not None:
        d = deals_with_type(htm); nd = len(d)
        if nd:
            d.to_csv(rd / f"{pair}.deals.csv", index=False)
            i = d[d.direction.astype(str).str.lower() == "in"]
            ent = pd.DataFrame({"te": pd.to_datetime(i.time, format="%Y.%m.%d %H:%M:%S"), "side": np.where(i.type.str.lower() == "buy", 1, -1)})
    if not len(ent) and len(sig):
        ent = sig
    ent = ent[(ent.te >= pd.Timestamp(frm.replace(".", "-"))) & (ent.te <= pd.Timestamp(to.replace(".", "-") + " 23:59:59"))]
    ent.to_csv(rd / f"{pair}.entries.csv", index=False)
    q = quality(htm)
    meta = dict(pair=pair, year=year, model=MODEL, entries=int(len(ent)), buys=int((ent.side > 0).sum()), sells=int((ent.side < 0).sum()), deals=nd, refused_signals=int(len(sig)), seconds=int(time.time() - t0), note=note,
                symbol=pair + SUFFIX, finished_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), **q)
    meta_f.write_text(json.dumps(meta))
    print(f"{datetime.now():%H:%M:%S} {pair}{SUFFIX} {year} model {MODEL}: {len(ent)} entries ({meta['buys']} buy / {meta['sells']} sell), deals {nd}, refused {len(sig)}, quality {q.get('history_quality')} in {meta['seconds']}s {note}", flush=True)
    return meta


def main() -> int:
    pairs = _arg("--pairs").split(",") if _arg("--pairs") else PAIRS
    years = _arg("--years").split(",") if _arg("--years") else list(YEARS)
    for y in years:
        for pr in pairs:
            run_job(pr, y)
    return 0


if __name__ == "__main__":
    sys.exit(main())
