"""EURUSD-LAB2 exactly as in PREREG_EURUSD_LAB2.md.  python -m forex.ea_research.eurusd_lab2 [--dry] [--hold]"""
import sys, numpy as np, pandas as pd

HOLD = "--hold" in sys.argv
DRY = "--dry" in sys.argv
END = pd.Timestamp("2026-10-01" if HOLD else "2026-01-01")
SLIP = 0.1
DATA = "forex/data_mt5/"


class Px:
    def __init__(self, m):
        d = pd.read_parquet(DATA + f"{m}_M1_rates.parquet", columns=["t", "bo", "bh", "bl", "ao", "bc", "ac"]).sort_values("t")
        d = d[(d.t < END.timestamp()) & (d.bo > 0) & (d.ao >= d.bo)].drop_duplicates("t")
        self.d = d
        self.ix = pd.Index(d.t.to_numpy())
        self.bo, self.ao = d.bo.to_numpy(), d.ao.to_numpy()
        self.mid = (d.bo + d.ao).to_numpy() / 2

    def idx(self, t):
        return self.ix.get_indexer(np.atleast_1d(t))

    def m(self, t):
        i = self.idx(t)
        return np.where(i >= 0, self.mid[np.maximum(i, 0)], np.nan)


EU = Px("EURUSD")


def srv_hour(t):
    return (t // 3600) % 24


def trade(te, side, hold_min):
    """net bp of a trade entered at the open of server-clock minute te and exited hold_min later, or None."""
    tx = te + hold_min * 60
    if srv_hour(te) in (23, 0) or srv_hour(tx) in (23, 0):
        return None
    i, j = EU.idx(te)[0], EU.idx(tx)[0]
    if i < 0 or j < 0:
        return None
    if side > 0:
        return (EU.bo[j] / EU.ao[i] - 1) * 1e4 - 2 * SLIP
    return (EU.bo[i] / EU.ao[j] - 1) * 1e4 - 2 * SLIP


def epoch_srv(utc_ts):
    s = pd.DatetimeIndex(utc_ts).tz_localize("UTC").tz_convert("Europe/Athens").tz_localize(None)
    return s.astype("datetime64[s]").astype("int64").to_numpy()


OBS = {}  # base cell -> list of (T, sig, bpL, bpS)


def add(base, te, sig, hold):
    l, s = trade(te, 1, hold), trade(te, -1, hold)
    if l is not None and s is not None:
        OBS.setdefault(base, []).append((pd.Timestamp(te, unit="s"), int(sig), l, s))


# ------------------------------------------------------------------ C: calendar timing
cal = pd.read_csv("data/data_macro/mt5_calendar.csv", encoding="latin-1")
cal = cal[(cal.importance == 3) & cal.currency.isin(["USD", "EUR"])]
cal["utc"] = pd.to_datetime(cal.time, format="%Y.%m.%d %H:%M:%S")
cal = cal[(cal.utc >= "2022-03-01") & (cal.utc < END)]
for cur in ("USD", "EUR"):
    ev = np.unique(epoch_srv(cal[cal.currency == cur].utc.drop_duplicates().sort_values()))
    a, b = EU.m(ev - 60), EU.m(ev + 600)
    mv = (b / a - 1) * 1e4
    for te0, v in zip(ev, mv):
        if v == v and abs(v) >= 4.0:
            for hold in (60, 240, 1380):
                add(f"C-{cur}-{hold}", te0 + 600, np.sign(v), hold)
# ------------------------------------------------------------------ slots for X, V, P
slots = [(hh, int((day + pd.Timedelta(hours=hh, minutes=5)).timestamp()))
         for day in pd.date_range("2022-03-01", END - pd.Timedelta(days=1), freq="D") if day.dayofweek <= 3 for hh in (10, 16)]
others = {m: Px(m) for m in ("GBPUSD", "AUDUSD", "NZDUSD")}
hist = {(hh, L): [] for hh in (10, 16) for L in (6, 24)}
for hh, t in slots:
    for L in (6, 24):
        r = []
        for P in [EU] + list(others.values()):
            x0, x1 = P.m(t - L * 3600)[0], P.m(t)[0]
            r.append(x1 / x0 - 1 if x0 == x0 and x1 == x1 else np.nan)
        if np.isnan(r).any():
            continue
        s = (r[0] - np.mean(r[1:])) * 1e4
        h = hist[(hh, L)]
        if len(h) >= 50:
            z = s / np.std(h[-250:], ddof=1)
            if abs(z) >= 1.0:
                add(f"X-{hh}-{L}", t, np.sign(s), 240)
        h.append(s)
# V: tick volume
vol = pd.read_parquet("data/ticks_vol/EURUSD.parquet").set_index("time").tick_volume
vol = vol[vol.index < END.timestamp()]
VT, VC = vol.index.to_numpy(), np.r_[0, np.cumsum(vol.to_numpy().astype(float))]


def vsum(t0, t1):
    return VC[np.searchsorted(VT, t1)] - VC[np.searchsorted(VT, t0)]


for hh, t in slots:
    for L in (3, 6):
        cur = vsum(t - L * 3600, t)
        base = []
        k = 1
        while len(base) < 20 and k < 40:
            tk = t - k * 86400
            if pd.Timestamp(tk, unit="s").dayofweek < 5:
                base.append(vsum(tk - L * 3600, tk))
            k += 1
        if len(base) < 20 or np.median(base) <= 0:
            continue
        x0, x1 = EU.m(t - L * 3600)[0], EU.m(t)[0]
        if cur / np.median(base) >= 1.25 and x0 == x0 and x1 == x1 and x1 != x0:
            add(f"V-{hh}-{L}", t, np.sign(x1 - x0), 240)
# P: pivots (previous server day)
d = EU.d.copy()
d.index = pd.to_datetime(d.t, unit="s")
spr = (d.ao - d.bo) / 2
Dd = pd.DataFrame({"h": (d.bh + spr).resample("1D").max(), "l": (d.bl + spr).resample("1D").min(), "c": ((d.bc + d.ac) / 2).resample("1D").last()}).dropna()
Dd = Dd[Dd.index.dayofweek < 5]
Dd["atr"] = (Dd.h - Dd.l).rolling(14).mean()
for hh, t in slots:
    if hh != 10:
        continue
    day = pd.Timestamp(t, unit="s").normalize()
    pv = Dd[Dd.index < day]
    if len(pv) < 20:
        continue
    q = pv.iloc[-1]
    P = (q.h + q.l + q.c) / 3
    R1, S1 = 2 * P - q.l, 2 * P - q.h
    p = EU.m(t - 60)[0]
    if p != p:
        continue
    band = 0.25 * q.atr
    sig_rs = 1 if abs(p - R1) < band and abs(p - R1) <= abs(p - S1) else -1 if abs(p - S1) < band else 0
    sig_p0 = int(np.sign(q.c - P)) if abs(p - P) < band else 0
    for hold in (240, 1380):
        if sig_rs:
            add(f"P-RS-{hold}", t, sig_rs, hold)
        if sig_p0:
            add(f"P-P0-{hold}", t, sig_p0, hold)
O = {k: pd.DataFrame(v, columns=["T", "sig", "L", "S"]) for k, v in OBS.items()}
print("entries per base cell:", {k: len(v) for k, v in sorted(O.items())})
if DRY:
    for k in ("C-USD-60", "X-10-6", "V-10-3", "P-RS-240"):
        if k in O:
            print(k, O[k].head(2).round(2).to_string(header=False))
    sys.exit()


def tt(v):
    return v.mean() / (v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 2 and v.std() > 0 else 0.0


per = {"DEV": ("2022-03-01", "2024-12-31"), "VAL": ("2025-01-01", "2025-12-31"), "HOLD": ("2026-01-01", "2026-09-30")}


def win(df, p):
    return df[(df["T"] >= per[p][0]) & (df["T"] < pd.Timestamp(per[p][1]) + pd.Timedelta(days=1))]


def cell(df, direction):
    sg = df.sig.to_numpy() * (1 if direction == "cont" else -1)
    return np.where(sg > 0, df.L, df.S)


cells = [(b, dr) for b in sorted(O) for dr in ("cont", "fade")]
print(len(cells), "cells")
print(f"{'cell':20s}{'nDEV':>5s}{'netbp':>7s}{'tDEV':>6s}{'hit':>4s} | {'nVAL':>4s}{'netbp':>7s}{'tVAL':>6s} | yearly bp 22/23/24/25 | pass")
res = {}
for b, dr in cells:
    df = O[b]
    a, v = cell(win(df, "DEV"), dr), cell(win(df, "VAL"), dr)
    ys = []
    for y in (2022, 2023, 2024, 2025):
        x = cell(df[df["T"].dt.year == y], dr)
        ys.append(x.mean() if len(x) > 5 else np.nan)
    ok = len(a) >= 100 and a.mean() > 1.0 and tt(a) >= 3.4 and len(v) >= 40 and v.mean() > 0 and tt(v) >= 1.65 and sum(np.nan_to_num(ys) > 0) >= 3
    res[(b, dr)] = (tt(a), ok)
    print(f"{b + ' ' + dr:20s}{len(a):5d}{a.mean():7.2f}{tt(a):6.2f}{(a > 0).mean() * 100:4.0f} | {len(v):4d}{v.mean():7.2f}{tt(v):6.2f} | " + "/".join(f"{y:+.1f}" for y in ys) + f" | {ok}")
rng = np.random.default_rng(21)
mx = []
DV = {b: win(O[b], "DEV") for b in O}
for _ in range(500):
    mm = 0.0
    for b, dr in cells:
        x = DV[b]
        if len(x) < 3:
            continue
        sg = rng.permutation(x.sig.to_numpy()) * (1 if dr == "cont" else -1)
        mm = max(mm, abs(tt(np.where(sg > 0, x.L, x.S))))
    mx.append(mm)
ceil = np.percentile(mx, 95)
print("placebo max |t| over %d cells (DEV): median %.2f, 95th %.2f; real best t %.2f" % (len(cells), np.median(mx), ceil, max(v[0] for v in res.values())))
passed = [c for c, v in res.items() if v[1] and v[0] >= ceil]
print("PASSED all gates:", passed)
if HOLD:
    for b, dr in passed:
        h = cell(win(O[b], "HOLD"), dr)
        print("HOLD", b, dr, len(h), round(h.mean(), 2), round(tt(h), 2))
