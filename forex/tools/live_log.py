"""Live forward log of the MT5 broker account: closed positions per EA (ManualSDB, XAU5, ManualDip) from the running terminal's history, plus ManualDip's
decision lines from the Experts log. Read-only; writes forex/forward_test/live_trades.csv. ManualDip's live signals are its clean out-of-sample
(the backtest rests on 2022-26 data).   python -m forex.tools.live_log [--since 2026-10-01]"""
from __future__ import annotations

import os
import datetime as dt
import re
import sys
from pathlib import Path

import pandas as pd

TERMINAL = os.getenv("MT5_TERMINAL") or r"C:\Program Files\MetaTrader 5\terminal64.exe"
DATA = Path(os.getenv("MT5_DATA_DIR", "."))  # the terminal's data folder (File > Open Data Folder in MT5)
OUT = Path(__file__).resolve().parents[1] / "forward_test" / "live_trades.csv"
NAME = {260931: "ManualSDB", 261011: "ManualDip", 261012: "ManualRSI2"}


def ea(magic: int) -> str: return NAME.get(magic, "XAU5" if magic > 10**9 else f"magic {magic}")


def positions(since: dt.datetime) -> pd.DataFrame:
    import MetaTrader5 as mt5
    if not mt5.initialize(path=TERMINAL): raise SystemExit(f"cannot attach to the MT5 broker terminal: {mt5.last_error()}")
    try:
        deals = mt5.history_deals_get(since, dt.datetime.now() + dt.timedelta(days=2)) or []
        rows = [dict(pos=d.position_id, time=pd.Timestamp(d.time, unit="s"), symbol=d.symbol, type=d.type, entry=d.entry, vol=d.volume, price=d.price,
                     net=d.profit + d.commission + d.swap + d.fee, magic=d.magic) for d in deals if d.type in (0, 1)]
    finally:
        mt5.shutdown()
    D = pd.DataFrame(rows)
    if D.empty: return D
    out = []
    for pid, g in D.groupby("pos"):
        o, c = g[g.entry == 0], g[g.entry == 1]
        if o.empty or c.empty: continue                                      # still open, or opened before the window
        out.append(dict(ea=ea(int(o.magic.iat[0])), symbol=o.symbol.iat[0], side="BUY" if o.type.iat[0] == 0 else "SELL", lots=o.vol.iat[0], opened=o.time.iat[0],
                        closed=c.time.iat[-1], entry_px=o.price.iat[0], exit_px=c.price.iat[-1], net=g.net.sum(), magic=int(o.magic.iat[0]), position=pid))
    return pd.DataFrame(out).sort_values("closed") if out else pd.DataFrame()


def dip_lines() -> list[str]:
    logs = sorted((DATA / "MQL5" / "Logs").glob("*.log"))[-3:]; keep = []
    for f in logs:
        for raw in f.read_bytes().decode("utf-16", errors="ignore").splitlines() if f.read_bytes()[:2] in (b"\xff\xfe", b"\xfe\xff") else f.read_text(errors="ignore").splitlines():
            if re.search(r"ManualDip|z3", raw): keep.append(f"{f.stem} {raw[-170:]}")
    return keep


def main() -> int:
    since = dt.datetime.fromisoformat(sys.argv[sys.argv.index("--since") + 1]) if "--since" in sys.argv else dt.datetime(2026, 10, 1)
    P = positions(since)
    if P.empty: print("no closed positions since", since.date()); return 0
    P.to_csv(OUT, index=False); print(f"{len(P)} closed positions since {since.date()} -> {OUT}\n")
    g = P.groupby("ea").agg(trades=("net", "size"), net=("net", "sum"), win_pct=("net", lambda s: 100 * (s > 0).mean()), avg=("net", "mean"))
    print(g.round(1).to_string()); print(f"\ntotal net {P.net.sum():+,.0f}\n\nlast 8 closed:"); print(P.tail(8)[["ea", "side", "lots", "closed", "net"]].to_string(index=False))
    d = dip_lines(); print(f"\nManualDip log lines found: {len(d)}"); [print("  ", x) for x in d[-6:]]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
