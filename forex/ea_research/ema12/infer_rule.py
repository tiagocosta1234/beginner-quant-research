"""Infer what the trader's 12 EMA entries look like on MT5 XAUUSD M1 (server clock), using the 30 dated trades (replay_mt5.csv)."""
import numpy as np, pandas as pd
O = pd.read_csv("replay_mt5.csv")
raw = pd.read_parquet("forex/data_mt5/XAUUSD_M1_rates.parquet")
raw["dt"] = pd.to_datetime(raw.t, unit="s"); raw = raw.sort_values("dt").reset_index(drop=True)
raw["mid"] = (raw.bc + raw.ac) / 2; raw["mh"] = (raw.bh + raw.ah) / 2; raw["ml"] = (raw.bl + raw.al) / 2
raw["ema"] = raw.mid.ewm(span=12, adjust=False).mean()
raw["rng"] = raw.mh - raw.ml; raw["atr"] = raw.rng.rolling(14).mean()
raw["day"] = raw.dt.dt.date; raw["hm"] = raw.dt.dt.hour * 60 + raw.dt.dt.minute
idx = {(d, h): i for i, (d, h) in enumerate(zip(raw.day, raw.hm))}
rows = []
for _, r in O.iterrows():
    i = idx[(pd.Timestamp(r.day).date(), int(r.hm))]
    open_hm = 600 if r.ses == "London" else 990
    sgn = 1 if r.side == "L" else -1
    prev = raw.iloc[i - 1]
    dist_ema = sgn * (prev.mid - prev.ema)                       # >0: price on the trade side of the EMA
    # minutes since close crossed the EMA (in the trade direction)
    k = 0
    while k < 60 and sgn * (raw.mid[i - 1 - k] - raw.ema[i - 1 - k]) > 0: k += 1
    win = raw.iloc[i - 30:i]
    ext30 = (r.risk if False else 0)
    lo5, hi5 = raw.ml[i-5:i].min(), raw.mh[i-5:i].max(); lo10, hi10 = raw.ml[i-10:i].min(), raw.mh[i-10:i].max()
    lo15, hi15 = raw.ml[i-15:i].min(), raw.mh[i-15:i].max()
    e = raw.ao[i] if sgn == 1 else raw.bo[i]
    sw5 = (e - lo5) if sgn == 1 else (hi5 - e); sw10 = (e - lo10) if sgn == 1 else (hi10 - e); sw15 = (e - lo15) if sgn == 1 else (hi15 - e)
    since_open = raw.iloc[i - (int(r.hm) - open_hm):i] if r.hm > open_hm else raw.iloc[i-1:i]
    sess_rng = since_open.mh.max() - since_open.ml.min()
    rows.append(dict(k=r.k, ses=r.ses, side=r.side, off=int(r.hm) - open_hm, dist_ema=dist_ema, bars_on_side=k, atr14=raw.atr[i-1], risk=r.risk, rew=r.rew,
                     risk_atr=r.risk / raw.atr[i-1], sw5=sw5, sw10=sw10, sw15=sw15, sess_rng=sess_rng, risk_over_ema=r.risk / max(abs(dist_ema), 0.05)))
F = pd.DataFrame(rows); pd.set_option("display.width", 220)
print(F.round(2).to_string(index=False))
print("\nside of EMA at entry: trade-side share %.0f%%; median minutes since price crossed to that side: %.0f (IQR %.0f-%.0f)" % (100*(F.dist_ema > 0).mean(), F.bars_on_side.median(), F.bars_on_side.quantile(.25), F.bars_on_side.quantile(.75)))
print("entry offset from session open (min): median %.0f, IQR %.0f-%.0f, max %.0f" % (F.off.median(), F.off.quantile(.25), F.off.quantile(.75), F.off.max()))
for c in ("atr14", "sw5", "sw10", "sw15", "sess_rng", "dist_ema"):
    ok = F[[c, "risk"]].dropna(); print("corr(risk, %-8s) = %.2f | median risk/%s = %.2f (IQR %.2f-%.2f)" % (c, np.corrcoef(ok[c], ok.risk)[0, 1], c, (ok.risk/ok[c].abs().clip(lower=0.05)).median(), (ok.risk/ok[c].abs().clip(lower=0.05)).quantile(.25), (ok.risk/ok[c].abs().clip(lower=0.05)).quantile(.75)))
