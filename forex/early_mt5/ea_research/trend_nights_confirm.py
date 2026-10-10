"""One-look 2026 confirmation of trend-filtered index nights (PREREG_TREND_NIGHTS_CONFIRM.md).   python -m mt5broker.ea_research.trend_nights_confirm"""
import datetime as dt
import numpy as np, pandas as pd
from mt5broker.ea_research import overnight_grid as N, event_macro as V
from mt5broker.ea_research import pass70 as P
def series(m, filt):
    F = N.frame(m, "T5", "2026-09-30"); ok = N.filters(F)[filt].fillna(False); return F.net.where(ok, 0.0), F
def st(x):
    x = x[(x.index >= "2026-01-01") & (x.index <= "2026-09-30")]; n = len(x)
    return n, float(x.mean()), float(x.mean() / (x.std(ddof=1) / np.sqrt(n))), int((x != 0).sum()), float(x.min())
out = {}
for m, filt, role in (("US-EW", "trend200", "PRIMARY"), ("NSDQ", "trend200", "report"), ("SP", "trend200", "report"), ("US-EW", "none", "no filter")):
    s, F = series(m, filt); n, mu, t, act, worst = st(s); out[(m, filt)] = s
    print(f"{role:9s} {m:6s} {filt:8s} 2026: nights {n} (active {act}) | mean {mu:+.2f} bp/night | t {t:+.2f} | worst {worst:+.1f} bp")
    with open(V.LEDGER, "a", encoding="utf-8") as f: f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M},trend_nights_confirm,{m}|{filt},HOLD,{n},{act},,{mu:.4f},,{t:.2f},,{role}\n")
n, mu, t, act, worst = st(out[("US-EW", "trend200")]); passed = mu > 0 and t >= 1.65
print(f"PRIMARY pass (mean > 0 and t >= 1.65): {passed}")
s = out[("US-EW", "trend200")]; hist = s[s.index < "2026-01-01"]; w = -min(hist.min(), s.min())
notional = 1000.0 / (w / 1e4); print(f"size for worst night <= 1,000 USD: about {notional:,.0f} USD notional -> 2026 mean {mu * notional / 1e4:+.1f} USD per night")
pr = P.series_nh("MT5", 1.2); pv = pd.Series(pr["V"], index=pd.to_datetime(pr["days"] * 86400, unit="s"))
j = pd.concat([pv, s * notional / 1e4], axis=1, join="inner").loc["2026-01-01":"2026-09-30"]; print(f"daily correlation with the gold pair in 2026: {j.corr().iloc[0, 1]:+.2f} ({len(j)} days)")
