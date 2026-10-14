"""FX3-OPEN, exactly as registered in PREREG_FX3_OPEN.md.   python -m forex.ea_research.fx3_open [--dry] [--hold]
Default: DEV+VAL table and the permutation calibration. --hold opens 2026 ONCE for the cells that passed acceptance 1-3."""
from __future__ import annotations

import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data_mt5"
SLIP_BP = 0.1  # per side
DRIVERS = {"NIKKEI": ("Asia/Tokyo", (9, 5), (11, 0)), "DAX": ("Europe/Berlin", (9, 5), (11, 0)), "SP": ("America/New_York", (9, 35), (10, 30))}
CELLS = [("USDJPY", "NIKKEI"), ("USDJPY", "DAX"), ("USDJPY", "SP"), ("EURUSD", "DAX"), ("EURUSD", "SP"), ("GBPUSD", "DAX"), ("GBPUSD", "SP")]
HOLDS = (2, 4)
PER = {"DEV": ("2022-01-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}


def load(m: str) -> dict:
    d = pd.read_parquet(DATA / f"{m}_M1_rates.parquet", columns=["t", "bo", "ao", "bc", "ac"]).sort_values("t")
    d = d[(d.bo > 0) & (d.ao >= d.bo) & (d.bc > 0) & (d.ac >= d.bc)]
    naive = pd.to_datetime(d.t.to_numpy(), unit="s")
    loc = pd.DatetimeIndex(naive).tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="shift_forward")
    ok = ~loc.isna()
    utc = (loc[ok].tz_convert("UTC").tz_localize(None).astype("datetime64[s]").astype("int64")).to_numpy()
    d = d[ok.to_numpy() if hasattr(ok, "to_numpy") else ok]
    o = np.argsort(utc, kind="stable")
    return {"u": utc[o], "bo": d.bo.to_numpy()[o], "ao": d.ao.to_numpy()[o], "bc": d.bc.to_numpy()[o], "ac": d.ac.to_numpy()[o],
            "sh": ((d.t.to_numpy() // 3600) % 24)[o]}


def at(M: dict, u: int):
    i = np.searchsorted(M["u"], u)
    return i if i < len(M["u"]) and M["u"][i] == u else None


def local_utc(day: pd.Timestamp, tz: str, hm: tuple) -> int:
    z = pd.Timestamp(year=day.year, month=day.month, day=day.day, hour=hm[0], minute=hm[1]).tz_localize(ZoneInfo(tz), ambiguous="NaT", nonexistent="NaT")
    return None if z is pd.NaT else int(z.tz_convert("UTC").timestamp())


def trades(tgt: dict, drv: dict, dname: str, H: int, dates) -> pd.DataFrame:
    tz, s, e = DRIVERS[dname]; rows = []
    for day in dates:
        if day.dayofweek >= 5: continue
        u0, u1 = local_utc(day, tz, s), local_utc(day, tz, e)
        if u0 is None or u1 is None: continue
        i0, i1 = np.searchsorted(drv["u"], u0), np.searchsorted(drv["u"], u1)  # bars [u0, u1)
        n = i1 - i0; need = (u1 - u0) / 60
        if n < 0.8 * need: continue
        D = (drv["bc"][i1 - 1] + drv["ac"][i1 - 1]) / (drv["bo"][i0] + drv["ao"][i0]) - 1.0
        if D == 0: continue
        ue, ux = u1 + 300, u1 + 300 + H * 3600
        ie, ix = at(tgt, ue), at(tgt, ux)
        if ie is None or ix is None: continue
        if tgt["sh"][ie] in (23, 0) or tgt["sh"][ix] in (23, 0): continue
        mid_e = (tgt["bo"][ie] + tgt["ao"][ie]) / 2
        long_bp = (tgt["bo"][ix] / tgt["ao"][ie] - 1) * 1e4 - 2 * SLIP_BP
        short_bp = (tgt["bo"][ie] / tgt["ao"][ix] - 1) * 1e4 - 2 * SLIP_BP
        rows.append((pd.Timestamp(ue, unit="s"), np.sign(D), long_bp, short_bp))
    return pd.DataFrame(rows, columns=["T", "s", "long", "short"])


def tstat(x: np.ndarray) -> float:
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))) if len(x) > 2 and x.std() > 0 else 0.0


def net(df: pd.DataFrame) -> np.ndarray:
    return np.where(df.s.to_numpy() > 0, df.long.to_numpy(), df.short.to_numpy())


def win(df: pd.DataFrame, per: str) -> pd.DataFrame:
    a, b = PER[per]; return df[(df["T"] >= a) & (df["T"] < pd.Timestamp(b) + pd.Timedelta(days=1))]


def main():
    hold = "--hold" in sys.argv; dry = "--dry" in sys.argv
    mk = {m: load(m) for m in {"EURUSD", "GBPUSD", "USDJPY", "NIKKEI", "DAX", "SP"}}
    dates = pd.date_range("2022-01-03", "2026-09-30", freq="D")
    T = {}
    for tg, dr in CELLS:
        for H in HOLDS: T[(tg, dr, H)] = trades(mk[tg], mk[dr], dr, H, dates)
    if dry:
        for k, v in T.items():
            print(k, "trades", len(v), "first", v["T"].min().date(), "last", v["T"].max().date(), "share long", round((v.s > 0).mean(), 2))
        # hand check one trade: SP driver, USDJPY
        v = T[("USDJPY", "SP", 2)]; r = v.iloc[100]; print("hand-check row", r.to_dict())
        return
    print(f"{'cell':26s}{'nDEV':>6s}{'netDEV':>8s}{'tDEV':>7s}{'revDEV':>8s}{'nVAL':>6s}{'netVAL':>8s}{'tVAL':>7s}  yearly net 22/23/24/25   pass")
    ps = []; passed = []
    for k, v in T.items():
        d, a = win(v, "DEV"), win(v, "VAL"); nd, na = net(d), net(a)
        rev = np.where(d.s.to_numpy() > 0, d.short.to_numpy(), d.long.to_numpy())
        yrs = [net(v[v["T"].dt.year == y]).mean() if (v["T"].dt.year == y).any() else np.nan for y in (2022, 2023, 2024, 2025)]
        td, ta = tstat(nd), tstat(na)
        ok = nd.mean() > 0 and td >= 2.9 and na.mean() > 0 and ta >= 1.65 and nd.mean() >= 0.3 and na.mean() >= 0.3 and sum(y > 0 for y in yrs) >= 3
        if ok: passed.append(k)
        print(f"{str(k):26s}{len(nd):6d}{nd.mean():8.2f}{td:7.2f}{rev.mean():8.2f}{len(na):6d}{na.mean():8.2f}{ta:7.2f}  " + "/".join(f"{y:+.1f}" for y in yrs) + f"   {ok}")
    rng = np.random.default_rng(5); mx = []
    DV = {k: win(v, "DEV") for k, v in T.items()}
    for _ in range(200):
        m = 0.0
        for k, d in DV.items():
            s = rng.permutation(d.s.to_numpy()); x = np.where(s > 0, d.long.to_numpy(), d.short.to_numpy()); m = max(m, abs(tstat(x)))
        mx.append(m)
    print("permutation max |t| over 14 cells (DEV): median %.2f, 95th pct %.2f, share >= 2.9: %.3f" % (np.median(mx), np.percentile(mx, 95), np.mean(np.array(mx) >= 2.9)))
    print("PASSED acceptance 1-3:", passed)
    if hold:
        for k in passed:
            h = win(T[k], "HOLD"); x = net(h); print("HOLD", k, len(x), round(x.mean(), 2), round(tstat(x), 2))


if __name__ == "__main__":
    main()
