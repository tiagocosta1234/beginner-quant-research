"""GOLD-FIX exactly as in PREREG_GOLD_FIX.md.  python -m forex.ea_research.gold_fix [--dry] [--hold]"""
import sys
import numpy as np
import pandas as pd

HOLD = "--hold" in sys.argv
DRY = "--dry" in sys.argv
END = pd.Timestamp("2026-10-01" if HOLD else "2026-01-01")
SLIP = 0.1
d = pd.read_parquet("forex/data_mt5/XAUUSD_M1_rates.parquet", columns=["t", "bo", "ao"]).sort_values("t").drop_duplicates("t")
d = d[(d.t < END.timestamp()) & (d.bo > 0) & (d.ao >= d.bo)]
IX = pd.Index(d.t.to_numpy())
BO, AO = d.bo.to_numpy(), d.ao.to_numpy()
MID = (BO + AO) / 2
days = pd.bdate_range("2022-01-03", END - pd.Timedelta(days=1))


def srv_epoch(day, hh, mm, off_min):
    """London local time (day, hh:mm + off minutes) -> server-clock naive epoch seconds."""
    lon = (pd.DatetimeIndex(day) + pd.Timedelta(hours=hh, minutes=mm + off_min)).tz_localize("Europe/London", ambiguous="NaT", nonexistent="NaT")
    s = lon.tz_convert("Europe/Athens").tz_localize(None)
    return np.where(s.isna(), -1, s.values.astype("datetime64[s]").astype("int64"))


def at(ep):
    i = IX.get_indexer(ep)
    return i


def trades(hh, mm):
    """the three cells for an auction at London hh:mm; returns dict cell -> DataFrame(day, net_bp)."""
    pts = {k: at(srv_epoch(days, hh, mm, k)) for k in (-60, -30, -15, 0, 5, 65)}
    ok_all = np.all(np.stack([v >= 0 for v in pts.values()]), axis=0)
    out = {}

    def leg(side, i_in, i_out):
        lg = (BO[i_out] / AO[i_in] - 1) * 1e4 - 2 * SLIP
        sh = (BO[i_in] / AO[i_out] - 1) * 1e4 - 2 * SLIP
        return np.where(side > 0, lg, sh)

    k = ok_all
    i60, i30, i15, i0, i5, i65 = (pts[x][k] for x in (-60, -30, -15, 0, 5, 65))
    dd = days[k]
    s_pre = np.sign(MID[i15] / MID[i60] - 1)
    out["PRE"] = pd.DataFrame({"day": dd, "bp": np.where(s_pre != 0, leg(s_pre, i15, i0), np.nan)}).dropna()
    s_post = -np.sign(MID[i5] / MID[i30] - 1)
    out["POST"] = pd.DataFrame({"day": dd, "bp": np.where(s_post != 0, leg(s_post, i5, i65), np.nan)}).dropna()
    out["DRIFT"] = pd.DataFrame({"day": dd, "bp": leg(np.full(len(dd), -1.0), i30, i5)})
    return out


def tt(x):
    x = np.asarray(x)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else 0.0


def per(df, a, b):
    return df[(df.day >= a) & (df.day <= b)].bp.to_numpy()


REAL = {"AM": (10, 30), "PM": (15, 0)}
FAKE = {"F0845": (8, 45), "F1230": (12, 30), "F1630": (16, 30), "F1730": (17, 30), "F1830": (18, 30), "F1930": (19, 30)}
if DRY:
    T = trades(15, 0)
    for c, df in T.items():
        print(c, len(df), df.day.min().date(), df.day.max().date())
    e = srv_epoch(pd.DatetimeIndex(["2024-07-10", "2024-12-10"]), 15, 0, 0)
    print("hand check: London 15:00 ->", [str(pd.Timestamp(x, unit="s")) for x in e], "(server = London + 2h)")
    sys.exit()
rows = []
for name, (hh, mm) in {**REAL, **FAKE}.items():
    for c, df in trades(hh, mm).items():
        a, v = per(df, "2022-01-03", "2024-12-31"), per(df, "2025-01-01", "2025-12-31")
        yrs = [per(df, f"{y}-01-01", f"{y}-12-31").mean() for y in (2022, 2023, 2024, 2025)]
        rows.append(dict(auction=name, cell=c, nD=len(a), mD=a.mean(), tD=tt(a), nV=len(v), mV=v.mean(), tV=tt(v), y22=yrs[0], y23=yrs[1], y24=yrs[2], y25=yrs[3], real=name in REAL))
R = pd.DataFrame(rows)
plc = R[~R.real]
ceil = np.percentile(np.abs(plc.tD), 95)
pd.set_option("display.width", 200)
print(R.round(2).to_string(index=False))
print(f"\nplacebo (fake auction times, 18 cells): max |DEV t| {np.abs(plc.tD).max():.2f}, 95th pct {ceil:.2f}")
for _, r in R[R.real].iterrows():
    sgn = np.sign(r.tD)
    ok = abs(r.tD) >= 2.64 and abs(r.mD) >= 1.0 and np.sign(r.tV) == sgn and abs(r.tV) >= 1.65 and sum(np.sign([r.y22, r.y23, r.y24, r.y25]) == sgn) >= 3 and abs(r.tD) > ceil
    print(f"{r.auction} {r.cell}: DEV {r.mD:+.2f} bp t {r.tD:+.2f} | VAL {r.mV:+.2f} t {r.tV:+.2f} | years {r.y22:+.1f}/{r.y23:+.1f}/{r.y24:+.1f}/{r.y25:+.1f} | PASS {ok}")
