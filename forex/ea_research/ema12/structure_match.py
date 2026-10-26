"""the trader 26 Oct 2026: "but order blocks, fvgs, highs/lows, etc. could all have been at different prices". On every blind day (Jan + batch 2),
06:00-08:15 local, compare the 1-minute structure of MT5 broker spot (mid) and GC futures with the basis removed (basis = median futures - spot that window):
- candle-by-candle: |difference| of open/high/low/close after the basis, and the correlation of 1-minute moves;
- FVGs (3-candle gaps of >= 0.5 pt): same minute and direction on both?
- swing highs / lows (5-candle fractals): same minute on both, and the price gap between them;
- order blocks (last opposite candle before a 3-candle displacement of >= 1.5 x the median range): same minute on both?
Usage (from ema12): python structure_match.py"""
import numpy as np, pandas as pd
import blind_png as B


def spot(day, cutoff):
    r = pd.read_parquet(B.SRC); t = pd.to_datetime(r.t, unit="s")
    m = (t >= day) & (t < pd.Timestamp(day) + pd.Timedelta(days=1)); r, t = r[m], t[m]
    idx = t.pipe(lambda x: x - pd.Timedelta(hours=7)).dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("Europe/London").dt.tz_localize(None)
    d = pd.DataFrame({k: ((r["b" + k[0]] + r["a" + k[0]]) / 2).to_numpy() for k in ("open", "high", "low", "close")}, index=idx.to_numpy())
    d = d[~d.index.isna()]; d = d[~d.index.duplicated()].sort_index()
    return d[(d.index >= pd.Timestamp(day + " 06:00")) & (d.index <= cutoff)]


def fvgs(d, mn=0.5):
    H, L, out = d.high.to_numpy(), d.low.to_numpy(), set()
    for i in range(2, len(d)):
        if L[i] - H[i - 2] >= mn: out.add((d.index[i - 1], "bull"))
        if L[i - 2] - H[i] >= mn: out.add((d.index[i - 1], "bear"))
    return out


def swings(d, k=2):
    H, L, out = d.high.to_numpy(), d.low.to_numpy(), {}
    for i in range(k, len(d) - k):
        if H[i] == H[i - k:i + k + 1].max(): out[(d.index[i], "H")] = H[i]
        if L[i] == L[i - k:i + k + 1].min(): out[(d.index[i], "L")] = L[i]
    return out


def obs(d):
    O, C, H, L = (d[c].to_numpy() for c in ("open", "close", "high", "low")); rng = np.median(H - L); out = set()
    for i in range(1, len(d) - 3):
        up = C[i + 3] - O[i + 1] >= 1.5 * 3 * rng / 3 * 1.5 if False else (C[i + 3] - O[i + 1]) >= 1.5 * rng * 1.5
        dn = (O[i + 1] - C[i + 3]) >= 1.5 * rng * 1.5
        if up and C[i] < O[i]: out.add((d.index[i], "bull"))
        if dn and C[i] > O[i]: out.add((d.index[i], "bear"))
    return out


def main():
    days = pd.concat([pd.read_csv(f).date for f in ("BLIND_LOG_JAN2026_FXR.csv", "BLIND_LOG_BATCH2_FXR.csv")]).unique()
    agg = dict(cand=[], corr=[], fvg_s=0, fvg_both=0, fvg_f=0, sw_s=0, sw_both=0, sw_gap=[], ob_s=0, ob_both=0, ob_f=0, n=0)
    for day in sorted(days):
        cut = pd.Timestamp(day + " 08:15")
        s = spot(day, cut); g = B.load_fut(day, cut); g = g[g.index >= pd.Timestamp(day + " 06:00")]
        j = s.index.intersection(g.index)
        if len(j) < 100: continue
        s, g = s.loc[j], g.loc[j]; basis = float(np.median(g.close - s.close)); g = g - basis
        agg["n"] += 1
        agg["cand"] += list(np.abs((g - s)[["open", "high", "low", "close"]]).to_numpy().ravel())
        agg["corr"].append(np.corrcoef(s.close.diff().dropna(), g.close.diff().dropna())[0, 1])
        fs, ff = fvgs(s), fvgs(g); agg["fvg_s"] += len(fs); agg["fvg_f"] += len(ff); agg["fvg_both"] += len(fs & ff)
        ss, sf = swings(s), swings(g); agg["sw_s"] += len(ss)
        for key, px in ss.items():
            if key in sf: agg["sw_both"] += 1; agg["sw_gap"].append(abs(sf[key] - px))
        os_, of = obs(s), obs(g); agg["ob_s"] += len(os_); agg["ob_f"] += len(of); agg["ob_both"] += len(os_ & of)
    c = np.array(agg["cand"]); gap = np.array(agg["sw_gap"])
    print("days compared: %d (06:00-08:15 local, futures minus the day's basis)" % agg["n"])
    print("1-minute moves: correlation %.3f (median day)" % np.median(agg["corr"]))
    print("candle prices (open/high/low/close) after the basis: median diff %.2f, 90%% within %.2f, 99%% within %.2f points" % (
        np.median(c), np.percentile(c, 90), np.percentile(c, 99)))
    print("FVGs >= 0.5 pt: spot %d, futures %d, same minute and direction %d (%.0f%% of spot's)" % (
        agg["fvg_s"], agg["fvg_f"], agg["fvg_both"], 100 * agg["fvg_both"] / max(agg["fvg_s"], 1)))
    print("swing highs/lows (5-candle): spot %d, same minute on futures %d (%.0f%%), price gap median %.2f, 90%% within %.2f points" % (
        agg["sw_s"], agg["sw_both"], 100 * agg["sw_both"] / max(agg["sw_s"], 1), np.median(gap), np.percentile(gap, 90)))
    print("order blocks (last opposite candle before a 3-candle displacement): spot %d, futures %d, same minute and direction %d (%.0f%% of spot's)" % (
        agg["ob_s"], agg["ob_f"], agg["ob_both"], 100 * agg["ob_both"] / max(agg["ob_s"], 1)))


if __name__ == "__main__":
    main()
