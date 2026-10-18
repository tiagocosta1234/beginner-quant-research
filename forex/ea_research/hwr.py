"""HWR: high-win-rate / small-daily-win index trials on the validated dip edge (DIP6, DIP6-TP, CONNORS-RSI2), judged on MT5 broker cycles.
Pre-registration: forex/ea_research/PREREG_HWR.md.   python -m forex.ea_research.hwr"""
import numpy as np, pandas as pd
from forex.ea_research.brk_patterns import load
from forex.ea_research.orbx import ct

MK = {"SP": ("America/New_York", 1549), "NSDQ": ("America/New_York", 1549), "DOW": ("America/New_York", 1549),
      "DAX": ("Europe/Berlin", 1719), "NIKKEI": ("Asia/Tokyo", 1449), "ASX": ("Australia/Sydney", 1549)}
SLIP, KSTOP = 1e-5, 3.0
DEV, VAL, HOLD = ("2022-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01"), ("2026-01-01", "2026-10-17")
START, FLOOR, TARGET, DAY_LOSS, DAY_CAP, LIVE = 100_000.0, 92_000.0, 108_000.0, -2_500.0, 2_000.0, 95_472.14


def daily(m):
    D = load(m); tz, hm = MK[m]; t = D["t"]
    loc = pd.to_datetime(t, unit="s").tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").tz_convert(tz)
    h = (loc.hour * 100 + loc.minute).to_numpy(); date = loc.tz_localize(None).normalize()
    idx = np.flatnonzero(h == hm)
    ok = idx[(idx + 1 < len(t))]
    ok = ok[(t[ok + 1] - t[ok]) <= 120]
    dd = pd.DataFrame({"date": date[ok], "i": ok}).dropna().drop_duplicates("date").set_index("date")
    dd["px"] = (D["bc"][dd.i.to_numpy()] + D["ac"][dd.i.to_numpy()]) / 2
    r = dd.px.pct_change(); dd["sd"] = r.rolling(60, min_periods=40).std()
    dd["z3"] = np.log(dd.px / dd.px.shift(3)) / (dd.sd * np.sqrt(3))
    d_ = dd.px.diff(); up = d_.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-d_.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    dd["rsi2"] = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    dd["sma200"] = dd.px.rolling(200, min_periods=200).mean(); dd["sma5"] = dd.px.rolling(5).mean()
    return D, dd


def sim(D, dd, m, trial):
    t = D["t"]; out = []; busy_until = -1; dates = dd.index; n = len(dd)
    for j in range(n - 1):
        r = dd.iloc[j]
        if j <= busy_until or not np.isfinite(r.sd) or r.sd <= 0:
            continue
        if trial in ("DIP6", "DIP6-TP"):
            if not (np.isfinite(r.z3) and r.z3 <= -2):
                continue
        elif not (np.isfinite(r.sma200) and r.px > r.sma200 and np.isfinite(r.rsi2) and r.rsi2 < 10):
            continue
        f = int(r.i) + 1; e = D["ao"][f] * (1 + SLIP); stop = e * (1 - KSTOP * r.sd)
        tgt = e * (1 + r.sd) if trial == "DIP6-TP" else np.inf
        if trial == "DIP6":
            xj = j + 1
        elif trial == "DIP6-TP":
            xj = min(j + 3, n - 1)
        else:
            xj = min(j + 10, n - 1)
            for q in range(j + 1, min(j + 10, n - 1) + 1):
                if dd.px.iloc[q] > dd.sma5.iloc[q]:
                    xj = q; break
        if xj <= j:
            continue
        xf = int(dd.i.iloc[xj]) + 1
        seg_l, seg_h = D["bl"][f:xf + 1], D["bh"][f:xf + 1]
        hs = np.flatnonzero(seg_l <= stop); ht = np.flatnonzero(seg_h >= tgt); ht = ht[ht > 0]
        k_s = hs[0] if len(hs) else 1 << 40; k_t = ht[0] if len(ht) else 1 << 40
        if k_s <= k_t and k_s < 1 << 40:
            k = f + k_s; ex = stop if k_s == 0 else min(stop, D["bo"][k])
        elif k_t < 1 << 40:
            k = f + k_t; ex = max(tgt, D["bo"][k])
        else:
            k = xf; ex = D["bo"][xf]
        risk = e - stop
        mae = (min(seg_l[:k - f + 1].min(), ex) - e) / risk
        out.append(dict(mkt=m, day=dates[j], t_in=int(t[f]), t_out=int(t[k]), R=(ex - e) / risk, mae=min(mae, 0.0)))
        exit_date = pd.Timestamp(int(t[k]), unit="s").normalize()
        busy_until = max(j, int(np.searchsorted(dates.values, np.datetime64(exit_date), side="right")) - 1)
    return out


def day_series(X, risk, days):
    """per server day: realised $ and the worst floating $ of positions open that day (conservative: each open position at its
    whole-hold MAE on every day it is open)"""
    real = pd.Series(0.0, index=days); flo = pd.Series(0.0, index=days)
    for r in X.itertuples():
        d_in = pd.Timestamp(r.t_in // 86400 * 86400, unit="s"); d_out = pd.Timestamp(r.t_out // 86400 * 86400, unit="s")
        if d_out in real.index:
            real[d_out] += r.R * risk
        span = real.index[(real.index >= d_in) & (real.index <= d_out)]
        flo[span] += r.mae * risk
    return real.to_numpy(), flo.to_numpy()


def evaluate(real, flo, start=START):
    res = []; bal = None; nd = 0
    for p, fl in zip(real, flo):
        if bal is None:
            bal, nd = start, 0
        nd += 1
        if p + min(fl, 0) <= DAY_LOSS or bal + min(fl, 0) <= FLOOR or bal + p <= FLOOR:
            res.append(("breach", nd)); bal = None; continue
        bal += min(p, DAY_CAP)
        if bal >= TARGET:
            res.append(("pass", nd)); bal = None
    if bal is not None:
        res.append(("open", nd))
    return res


def main():
    trials = ("DIP6", "DIP6-TP", "CONNORS-RSI2"); TR = {k: [] for k in trials}
    for m in MK:
        D, dd = daily(m)
        for tr in trials:
            TR[tr] += sim(D, dd, m, tr)
    T = {k: pd.DataFrame(v) for k, v in TR.items()}
    for k, x in T.items():
        x.to_parquet(f"C:/work/scratch/hwr_{k}.parquet")
    print("Trials (net R a trade; DEV 2022-24 / VAL 2025; HOLD only for DEV + VAL passers)")
    passers = []
    for k, x in T.items():
        per = lambda p: x[(x.day >= p[0]) & (x.day < p[1])]
        d, v = per(DEV), per(VAL); md, td = ct(d); mv, tv = ct(v); yrs = d.groupby(d.day.dt.year).R.mean()
        ok = len(d) >= 100 and md > 0 and td >= 2.4 and (yrs > 0).sum() >= 2
        okv = ok and mv > 0 and tv >= 1.65
        line = (f"  {k:13s} DEV n {len(d)} {md:+.3f} R (t {td:+.2f}) win {(d.R > 0).mean():.0%} avg win {d.R[d.R > 0].mean():+.2f} avg loss {d.R[d.R <= 0].mean():+.2f}"
                f" yrs {'/'.join(f'{q:+.2f}' for q in yrs)} -> {'PASS' if ok else 'FAIL'} | VAL n {len(v)} {mv:+.3f} (t {tv:+.2f}) win {(v.R > 0).mean():.0%}")
        if okv:
            h = per(HOLD); mh, th = ct(h)
            line += f" | HOLD n {len(h)} {mh:+.3f} (t {th:+.2f}) win {(h.R > 0).mean():.0%} -> {'PASS' if mh > 0 and th >= 1.65 else 'FAIL'}"
            if mh > 0 and th >= 1.65:
                passers.append(k)
        print(line)
    print("\nMT5 broker fit, 2022-25: win rate, winning days, days > $2,000 realised; back-to-back fresh MT5 Pro evaluations; from the live balance")
    days = pd.bdate_range("2022-01-03", "2025-12-31"); rng = np.random.default_rng(1626)
    for k, x in T.items():
        x = x[x.day < "2026-01-01"]
        print(f"\n  {k}: {len(x)} trades ({len(x)/4:.0f} a year), win {(x.R > 0).mean():.0%}, mean {x.R.mean():+.3f} R")
        for risk in (250, 500, 1000):
            real, flo = day_series(x, risk, days); act = real != 0
            c = evaluate(real, flo); P = [d for o, d in c if o == "pass"]; B = sum(o == "breach" for o, _ in c)
            Hh = 180; nb = Hh // 5 + 2
            s = rng.integers(0, len(real) - 5, size=(4000, nb)); bi = (s[:, :, None] + np.arange(5)).reshape(4000, -1)[:, :Hh]
            out = np.array([evaluate(real[b], flo[b], LIVE)[0][0] for b in bi])
            print(f"    ${risk:5d}: winning days {np.mean(real[act] > 0):.0%} of {act.sum()} exit days, days > $2,000: {np.mean(real[act] > 2000):.1%};"
                  f" fresh evaluations 2022-25: {len(P)} pass / {B} breach (avg {np.mean(P) if P else float('nan'):.0f} days to pass);"
                  f" from 95,472 by 30 Jun 27: pass {100*np.mean(out == 'pass'):.1f}% / breach {100*np.mean(out == 'breach'):.1f}%")
    print("\nfull passers:", passers or "none")


if __name__ == "__main__":
    main()
