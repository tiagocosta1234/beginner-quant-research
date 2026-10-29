"""Macro-release surprise proxies from ALFRED first-release vintages (PREREG_SLOW_INFO.md). Only releases up to 2025-12-31 are fetched (2026 stays sealed).
   python -m forex.self_improving.slow.fetch_alfred
Output data\\data_macro\\alfred\\surprises.csv: kind, release_date, value (the surprise proxy), raw (the first-print change)."""
import io
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("data/data_macro/alfred"); OUT.mkdir(parents=True, exist_ok=True)
URL = "https://alfred.stlouisfed.org/graph/alfredgraph.csv?id={sid}&vintage_date={vd}&cosd={cosd}"
LAST = "2025-12-31"


def vintage(sid, vd):
    f = OUT / f"{sid}_{vd}.csv"
    if f.exists(): return pd.read_csv(f)
    cosd = (pd.Timestamp(vd) - pd.DateOffset(months=8)).strftime("%Y-%m-%d")
    for k in range(3):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(URL.format(sid=sid, vd=vd, cosd=cosd), headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read().decode()
            f.write_text(raw); time.sleep(0.2); return pd.read_csv(io.StringIO(raw))
        except Exception as e: time.sleep(2 * (k + 1)); err = e
    print("failed", sid, vd, err); return None


def series(df): s = pd.to_numeric(df.iloc[:, 1], errors="coerce"); s.index = pd.to_datetime(df.observation_date); return s.dropna()


def main():
    cal = pd.read_csv("data/data_macro/event_calendar.csv"); rows = []
    for d in cal[cal.kind == "NFP"].date:
        if d > LAST: continue
        p, u = vintage("PAYEMS", d), vintage("UNRATE", d)
        if p is not None:
            s = series(p); ch = s.diff().dropna()
            if len(ch) >= 4: rows.append(("NFP", d, float(ch.iloc[-1] - ch.iloc[-4:-1].mean()), float(ch.iloc[-1])))
        if u is not None:
            s = series(u)
            if len(s) >= 2: rows.append(("UNRATE", d, float(s.iloc[-1] - s.iloc[-2]), float(s.iloc[-1])))
    for d in cal[cal.kind == "CPI"].date:
        if d > LAST: continue
        c = vintage("CPIAUCSL", d)
        if c is not None:
            s = series(c); mom = s.pct_change().dropna() * 100
            if len(mom) >= 4: rows.append(("CPI", d, float(mom.iloc[-1] - mom.iloc[-4:-1].mean()), float(mom.iloc[-1])))
    fed = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFEDTARU"); fed.index = pd.to_datetime(fed.observation_date); fed = pd.to_numeric(fed.DFEDTARU, errors="coerce").dropna()
    for d in cal[cal.kind == "FOMC"].date:
        if d > LAST: continue
        a = fed[:pd.Timestamp(d)].iloc[-1]; b = fed[:pd.Timestamp(d) + pd.Timedelta(days=2)].iloc[-1]; rows.append(("FOMC", d, float(b - a), float(b)))
    df = pd.DataFrame(rows, columns=["kind", "release_date", "value", "raw"]); df.to_csv(OUT / "surprises.csv", index=False)
    print(df.groupby("kind").agg(n=("value", "size"), mean=("value", "mean"), sd=("value", "std")).round(3).to_string()); print(df.tail(6).to_string(index=False))


if __name__ == "__main__":
    main()
