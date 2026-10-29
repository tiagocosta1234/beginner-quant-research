"""Bug hunt for the PRESAMPLE L1 pass (diagnostic, not a test): run the same L1 engine on HistData USDJPY 2022-2024 and compare it,
year by year and day by day, with the MT5-data session breakout of round 1 (BRK_EXITS X4, USDJPY). Same MT5 broker spread floor.
   python -m forex.ea_research.presample_xcheck"""
import io
import zipfile

import numpy as np
import pandas as pd

import forex.ea_research.presample as ps


def histdata(years):
    frames = []
    for yr in years:
        z = zipfile.ZipFile(f"data/data_histdata/DAT_ASCII_USDJPY_M1_{yr}.zip")
        name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
        frames.append(pd.read_csv(io.BytesIO(z.read(name)), sep=";", header=None, names=["dt", "bo", "bh", "bl", "bc", "v"]))
    d = pd.concat(frames)
    d["t_utc"] = (pd.to_datetime(d.dt, format="%Y%m%d %H%M%S") + pd.Timedelta(hours=5)).astype("datetime64[s]").astype("int64")
    for a, b in (("ao", "bo"), ("ah", "bh"), ("al", "bl"), ("ac", "bc")):
        d[a] = d[b]
    return d.sort_values("t_utc").drop_duplicates("t_utc")


def main():
    fj = ps.mt5_floor("USDJPY", "Europe/London", 8, 17)
    d = histdata((2022, 2023, 2024))
    d.to_parquet("data/data_histdata/USDJPY_2022_24.parquet")
    orig = pd.read_parquet
    pd.read_parquet = lambda f, *a, **k: d if f.endswith("USDJPY.parquet") else orig(f, *a, **k)
    import forex.ea_research.presample as ps2
    J = ps2.load_duka.__wrapped__("USDJPY", "Europe/London", fj) if hasattr(ps2.load_duka, "__wrapped__") else None
    pd.read_parquet = orig
    # load_duka filters to the 2020-21 window, so rebuild the dict here with the same logic and no window
    D = {k: d[k].to_numpy(float) for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")}
    sp = np.maximum(D["ao"] - D["bo"], fj)
    for a, b in (("ao", "bo"), ("ah", "bh"), ("al", "bl"), ("ac", "bc")):
        D[a] = np.maximum(D[a], D[b] + sp)
    D["t"] = d.t_utc.to_numpy(np.int64)
    loc = pd.to_datetime(D["t"], unit="s").tz_localize("UTC").tz_convert("Europe/London").tz_localize(None)
    D["lc"] = loc.values.astype("datetime64[s]").astype(np.int64)
    h = ps.l1_usdjpy(D, np.random.default_rng(2020))
    e = pd.read_parquet("data/si_ledgers/BRK_EXITS.parquet")
    e = e[(e.mkt == "USDJPY") & (e.kind == "BRK") & (e.day < "2025-01-01")][["day", "side", "X4_noTP"]]
    print("HistData engine vs MT5 broker data, USDJPY London session breakout held to 17:00 (mean R):")
    for y in (2022, 2023, 2024):
        a, b = h[h.day.dt.year == y], e[e.day.dt.year == y]
        print(f"  {y}: HistData n{len(a)} {a.R.mean():+.3f} | MT5 broker n{len(b)} {b.X4_noTP.mean():+.3f}")
    m = h.merge(e, on="day", suffixes=("_h", "_e"))
    same = (m.side_h == m.side_e).mean()
    print(f"  common days {len(m)}: same side {same:.1%}; correlation of R {np.corrcoef(m.R, m.X4_noTP)[0, 1]:+.3f}; mean R on common days HistData {m.R.mean():+.3f} vs MT5 {m.X4_noTP.mean():+.3f}")


if __name__ == "__main__":
    main()
