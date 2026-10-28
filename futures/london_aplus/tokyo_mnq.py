import numpy as np
import pandas as pd

PATH = r"D:\finance\beginner-quant-research\futures\data\databento\futures_NQ.F_1m.parquet"
COST = 0.86
MIN_S = 8.0
TEST_START = pd.Timestamp("2023-01-01", tz="UTC").date()

d = pd.read_parquet(PATH, columns=["ts", "open", "high", "low", "close"])
d = d[d.ts.dt.hour < 6].copy()
d["date"] = d.ts.dt.date
d["m"] = d.ts.dt.hour * 60 + d.ts.dt.minute


def sim(side, entry, stop, tgt, hi, lo, cl):
    s = abs(entry - stop)
    last = entry
    for i in range(len(hi)):
        if np.isnan(hi[i]):
            continue
        last = cl[i]
        if side > 0:
            if lo[i] <= stop:
                return -1.0
            if hi[i] >= tgt:
                return 1.0
        else:
            if hi[i] >= stop:
                return -1.0
            if lo[i] <= tgt:
                return 1.0
    return side * (last - entry) / s


rows = []
for date, g in d.groupby("date"):
    o = np.full(360, np.nan); h = o.copy(); l = o.copy(); c = o.copy()
    m = g.m.values
    o[m] = g.open.values; h[m] = g.high.values; l[m] = g.low.values; c[m] = g.close.values
    if np.isnan(o[0]) or np.isnan(o[15]) or np.isnan(c[14]):
        continue
    ch, cl_ = np.nanmax(h[0:15]), np.nanmin(l[0:15])
    co, cc = o[0], c[14]
    entry = o[15]
    rec = {"date": date, "RL": np.nan, "RS": np.nan, "up": np.nan, "H3": np.nan}
    if cc != co:
        rec["up"] = 1.0 if cc > co else -1.0
        sL = entry - cl_
        if sL >= MIN_S:
            rec["RL"] = sim(1, entry, cl_, entry + sL, h[15:], l[15:], c[15:]) - COST / sL
        sS = ch - entry
        if sS >= MIN_S:
            rec["RS"] = sim(-1, entry, ch, entry - sS, h[15:], l[15:], c[15:]) - COST / sS
    # H3: 30m range breakout
    rh, rl = np.nanmax(h[0:30]), np.nanmin(l[0:30])
    S3 = rh - rl
    if S3 >= MIN_S:
        for i in range(30, 360):
            if np.isnan(c[i]):
                continue
            if c[i] > rh or c[i] < rl:
                side = 1 if c[i] > rh else -1
                stop = rl if side > 0 else rh
                s = abs(c[i] - stop)
                if s >= MIN_S:
                    tgt = c[i] + side * s
                    rec["H3"] = sim(side, c[i], stop, tgt, h[i + 1:], l[i + 1:], c[i + 1:]) - COST / s
                break
    rows.append(rec)

df = pd.DataFrame(rows)
df["date"] = pd.to_datetime(df["date"])
df["h1"] = np.where(df.up > 0, df.RL, df.RS)
df["h2"] = np.where(df.up > 0, df.RS, df.RL)
rng = np.random.default_rng(20261027)


def boot_p(x):
    x = x[~np.isnan(x)]
    if len(x) < 2:
        return np.nan
    m = rng.choice(x, size=(5000, len(x)), replace=True).mean(axis=1)
    return (m <= 0).mean()


def rand_side_p(sub, col):
    ok = sub.dropna(subset=["RL", "RS", col])
    if len(ok) < 2:
        return np.nan
    obs = ok[col].mean()
    flips = rng.random((5000, len(ok))) < 0.5
    sim_m = np.where(flips, ok.RL.values, ok.RS.values).mean(axis=1)
    return (sim_m >= obs).mean()


def report(name, sub, col, side_test):
    x = sub[col].dropna().values
    if len(x) == 0:
        print(f"{name}: no trades"); return
    yrs = sub.dropna(subset=[col]).groupby(sub.date.dt.year)[col].mean()
    print(f"{name}: n {len(x)}  win {np.mean(x > 0):.1%}  mean net R {x.mean():+.3f}  "
          f"boot P(mean<=0) {boot_p(x):.4f}  "
          + (f"random-side P {rand_side_p(sub, col):.3f}  " if side_test else "")
          + f"years+ {int((yrs > 0).sum())}/{len(yrs)}")


dev = df[df.date.dt.date < TEST_START]
test = df[df.date.dt.date >= TEST_START]
print(f"days: DEV {len(dev)}  TEST {len(test)}  (range {df.date.min().date()} .. {df.date.max().date()})")
for label, sub in (("DEV (descriptive)", dev), ("TEST (single look)", test)):
    print(f"--- {label}")
    report("H1 follow  ", sub, "h1", True)
    report("H2 fade    ", sub, "h2", True)
    report("H3 breakout", sub, "H3", False)
df.to_csv(r"D:\finance\beginner-quant-research\london_aplus\TOKYO_MNQ_DAYS.csv", index=False)
