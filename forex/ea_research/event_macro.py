"""Family V (scheduled US macro events), exactly as registered in PREREG_EVENT_MACRO.md.
   python -m forex.ea_research.event_macro --dry-run | --trials | --holdout"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data_mt5"
LEDGER = HERE / "LEDGER.csv"
STATE = HERE / "EVENT_MACRO_STATE.json"
CAL = Path("data/data_macro/event_calendar.csv")
PERIODS = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}
SLIP = 1e-5
V1_MKTS = ("SP", "NSDQ", "DOW")
V2_MKTS = ("XAUUSD", "EURUSD", "USDJPY", "NSDQ")
_cache: dict = {}


def mkt(m: str) -> pd.DataFrame:
    if m not in _cache:
        d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "ao"]).sort_values("t").drop_duplicates("t")
        _cache[m] = d[(d.bo > 0) & (d.ao >= d.bo)].set_index("t")
    return _cache[m]


def server_s(day: str, hh: int, mm: int) -> int:
    """Seconds of the MT5 broker server clock (Europe/Athens wall time stored as epoch) for hh:mm New York time on 'day'."""
    ts = pd.Timestamp(f"{day} {hh:02d}:{mm:02d}").tz_localize("America/New_York").tz_convert("Europe/Athens").tz_localize(None)
    return int((ts - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1))


def quote(m: str, t: int):
    d = mkt(m)
    if t not in d.index: return None
    r = d.loc[t]; return float(r.bo), float(r.ao)


def prev_bday(day: str) -> str:
    return str(np.busday_offset(np.datetime64(day), -1, roll="backward"))


def v1_events(cal: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for D in cal[cal.kind == "FOMC"].date:
        ti, tx = server_s(prev_bday(D), 14, 2), server_s(D, 13, 55); legs = []
        for m in V1_MKTS:
            qi, qx = quote(m, ti), quote(m, tx)
            if qi is None or qx is None: continue
            net = (qx[0] / qi[1] - 1.0) * 1e4 - 2 * SLIP * 1e4; gross = ((qx[0] + qx[1]) / (qi[0] + qi[1]) - 1.0) * 1e4; legs.append((m, net, gross))
        if legs: rows.append(dict(date=pd.Timestamp(D), n=len(legs), net=np.mean([x[1] for x in legs]), gross=np.mean([x[2] for x in legs]), **{f"net_{m}": v for m, v, _ in legs}))
    return pd.DataFrame(rows)


def v2_events(cal: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in cal[cal.kind.isin(["NFP", "CPI"])].iterrows():
        D = r.date; t0, t15, te, tx = server_s(D, 8, 29), server_s(D, 8, 45), server_s(D, 8, 47), server_s(D, 11, 30); legs = []
        for m in V2_MKTS:
            q0, q15, qe, qx = quote(m, t0), quote(m, t15), quote(m, te), quote(m, tx)
            if None in (q0, q15, qe, qx): continue
            s = np.sign((q15[0] + q15[1]) - (q0[0] + q0[1]))
            if s == 0: continue
            net = ((qx[0] / qe[1] - 1.0) if s > 0 else (qe[0] / qx[1] - 1.0)) * 1e4 - 2 * SLIP * 1e4; gross = s * ((qx[0] + qx[1]) / (qe[0] + qe[1]) - 1.0) * 1e4
            legs.append((m, net, gross))
        if legs: rows.append(dict(date=pd.Timestamp(D), kind=r.kind, n=len(legs), net=np.mean([x[1] for x in legs]), gross=np.mean([x[2] for x in legs]), **{f"net_{m}": v for m, v, _ in legs}))
    return pd.DataFrame(rows)


def stat(E: pd.DataFrame, per: str) -> dict:
    a, b = PERIODS[per]; X = E[(E.date >= a) & (E.date <= b)]; n = len(X)
    if n < 3: return dict(events=n, net=float("nan"), gross=float("nan"), t=float("nan"), win=float("nan"))
    return dict(events=n, net=float(X.net.mean()), gross=float(X.gross.mean()), t=float(X.net.mean() / (X.net.std(ddof=1) / np.sqrt(n))), win=float((X.net > 0).mean()))


def ledger(trial, per, s, note=""):
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},event_macro,{trial},{per},{s['events']},{s['events']},,{s['net']:.4f},,{s['t']:.2f},{s['win']:.3f},{note}\n")


def dry_run():
    cal = pd.read_csv(CAL); print("calendar:", cal.kind.value_counts().to_dict())
    for D in ("2024-09-18", "2025-03-19"):
        print(f"V1 {D}: entry server {pd.to_datetime(server_s(prev_bday(D), 14, 2), unit='s')} (= 14:02 ET {prev_bday(D)}), exit server {pd.to_datetime(server_s(D, 13, 55), unit='s')} (= 13:55 ET)")
    for D in ("2024-03-08", "2024-11-01"):
        print(f"V2 {D}: 08:29 ET = server {pd.to_datetime(server_s(D, 8, 29), unit='s')}, entry 08:47 ET = {pd.to_datetime(server_s(D, 8, 47), unit='s')}, exit 11:30 ET = {pd.to_datetime(server_s(D, 11, 30), unit='s')}")
    av1 = sum(all(quote(m, server_s(prev_bday(D), 14, 2)) is not None and quote(m, server_s(D, 13, 55)) is not None for m in V1_MKTS) for D in cal[cal.kind == "FOMC"].date)
    av2 = {m: sum(all(quote(m, server_s(D, h, mi)) is not None for h, mi in ((8, 29), (8, 45), (8, 47), (11, 30))) for D in cal[cal.kind.isin(["NFP", "CPI"])].date) for m in V2_MKTS}
    print(f"V1 events with all three indices quoted: {av1} of {int((cal.kind == 'FOMC').sum())} | V2 release days with all four minutes quoted, per market: {av2} of {int(cal.kind.isin(['NFP', 'CPI']).sum())}")
    q = quote("XAUUSD", server_s("2024-03-08", 8, 29)); print("hand check XAUUSD 2024-03-08 08:29 ET bid/ask", q, "| no P&L computed")


def run(holdout=False):
    cal = pd.read_csv(CAL); res = {}
    for trial, E in (("V1", v1_events(cal)), ("V2", v2_events(cal))):
        print(f"\n=== {trial}: {len(E)} events ===")
        st = {}
        for per in ("DEV", "VAL") + (("HOLD",) if holdout else ()):
            if per == "HOLD" and not res.get(trial, {}).get("passed"): continue
            s = stat(E, per); st[per] = s
            print(f"{trial} {per}: events {s['events']:3d} | net {s['net']:+7.2f} bp/event (gross {s['gross']:+7.2f}) | t {s['t']:+5.2f} | win {100*s['win']:4.1f}%")
            ledger(trial, per, s, f"net {s['net']:+.2f} bp/event; gross {s['gross']:+.2f}")
        for y in range(2022, 2027 if holdout else 2026):
            X = E[E.date.dt.year == y]
            if len(X): print(f"   {y}: events {len(X):3d} net {X.net.mean():+7.2f} bp gross {X.gross.mean():+7.2f}")
        print("   per market (DEV+VAL, net bp):", {c[4:]: round(float(E[(E.date <= '2025-12-31')][c].mean()), 2) for c in E.columns if c.startswith("net_")})
        if trial == "V2": print("   by kind (DEV+VAL):", E[E.date <= "2025-12-31"].groupby("kind").net.agg(["size", "mean"]).round(2).to_dict("index"))
        a1 = st["DEV"]["net"] > 0 and st["DEV"]["t"] >= 2.0; a2 = st["VAL"]["net"] > 0; res[trial] = dict(a1=bool(a1), a2=bool(a2), passed=bool(a1 and a2))
        print(f"   acceptance 1 (DEV mean > 0, t >= 2.0): {a1} | 2 (VAL > 0): {a2} => {'hold-out may be opened' if a1 and a2 else 'closed'}")
    if not holdout: STATE.write_text(json.dumps(res), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--trials", action="store_true"); ap.add_argument("--holdout", action="store_true"); x = ap.parse_args()
    if x.dry_run: dry_run()
    if x.trials: run(False)
    if x.holdout:
        st = json.loads(STATE.read_text()) if STATE.exists() else {}
        live = [k for k, v in st.items() if v.get("passed")]
        if not live: print("No trial passed acceptance 1-2: the 2026 hold-out stays CLOSED (registered rule).")
        cal = pd.read_csv(CAL)
        for trial in live:                                                       # ONE look at 2026 for the trials that passed DEV and VAL
            E = v1_events(cal) if trial == "V1" else v2_events(cal); s = stat(E, "HOLD"); X = E[(E.date >= "2026-01-01") & (E.date <= "2026-09-30")]
            print(f"{trial} HOLD 2026: events {s['events']} | net {s['net']:+.2f} bp/event (gross {s['gross']:+.2f}) | t {s['t']:+.2f} | win {100*s['win']:.0f}% | acceptance 3 (mean > 0): {s['net'] > 0}")
            print("   per event:", [(str(d.date()), round(float(v), 1)) for d, v in zip(X.date, X.net)])
            ledger(trial, "HOLD", s, f"net {s['net']:+.2f} bp/event; passed {s['net'] > 0}")


if __name__ == "__main__":
    main()
