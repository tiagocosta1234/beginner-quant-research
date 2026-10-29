"""DESCRIPTIVE ONLY (20 Oct 2026, after the trader: 'its all about where the candle opens and closes, strong body with really small wick near the close price ... if the candle touched the fvg that lowers the chances').
Looks at the signal candle of the 50 FX Replay trades (29 Apr-May 2025 + 21 Jan 2026, MT5 1-minute mid prices) and compares it with every other EMA12 cross candle in the same first 15 minutes after the open.
No results of the trades are used; nothing here is a test, a bar or a rule. Writes MANUAL_CANDLE_PROFILE_OUTPUT.txt when run through the shell."""
import numpy as np, pandas as pd, datetime as dt
from ema12_test import open_min
F = pd.read_csv("FXREPLAY_TRADES_2026-10-20.csv"); F["tm"] = pd.to_datetime(F.chart_entry); F = F[F.side.isin(["Buy", "Sell"])].copy()
d = pd.read_parquet("forex/data_mt5/XAUUSD_M1_rates.parquet").sort_values("t").reset_index(drop=True)
d["lis"] = pd.to_datetime(d.t, unit="s") - pd.Timedelta(hours=2)          # server clock = local + 2 h
M = pd.DataFrame(dict(lis=d.lis, o=(d.bo + d.ao) / 2, h=(d.bh + d.ah) / 2, l=(d.bl + d.al) / 2, c=(d.bc + d.ac) / 2)); M["ema"] = M.c.ewm(span=12, adjust=False).mean()
rng = (M.h - M.l); M["atr"] = rng.rolling(14).mean().shift(1); idx = {t: i for i, t in enumerate(M.lis)}
o, h, l, c, e = (M[k].to_numpy() for k in ("o", "h", "l", "c", "ema"))
def feat(i, side):          # side +1 buy / -1 sell
    body = abs(c[i] - o[i]); up = h[i] - max(o[i], c[i]); lo = min(o[i], c[i]) - l[i]; cw, fw = (up, lo) if side > 0 else (lo, up)
    return dict(cross=bool((o[i] - e[i]) * (c[i] - e[i]) < 0), right_side=bool((c[i] - e[i]) * side > 0), body=body, close_wick=cw, far_wick=fw, cw_ratio=cw / body if body > 0 else np.nan, body_atr=body / M.atr[i] if M.atr[i] > 0 else np.nan, body_gt_wick=bool(body > max(up, lo)))
def touches_target_fvg(i, side, look=120):
    """did the signal candle reach into an UNFILLED fair-value gap lying in the trade direction (buy: bearish gap above, sell: bullish gap below), formed before it?"""
    for k in range(i - 1, max(i - look, 3), -1):
        if side > 0 and h[k] < l[k - 2]:
            lo_, hi_ = h[k], l[k - 2]
            if hi_ > c[i - 1] - 1e-9 and (k + 1 > i - 1 or h[k + 1:i].max() < hi_) and h[i] >= lo_ and lo_ > l[i] - 1e9: return True
        if side < 0 and l[k] > h[k - 2]:
            lo_, hi_ = h[k - 2], l[k]
            if lo_ < c[i - 1] + 1e-9 and (k + 1 > i - 1 or l[k + 1:i].min() > lo_) and l[i] <= hi_: return True
    return False
rows = []
for _, r in F.iterrows():
    side = 1 if r.side == "Buy" else -1; T = r.tm; sig = T.floor("min")      # the order is placed in the last visible candle (about 5 s before it closes): that candle is the signal candle
    i = idx[sig]; f = feat(i, side); f.update(group=r.group, when=str(sig), side=r.side, mins_before_order=int((T.floor("min") - sig).total_seconds() // 60), price_gap=round(abs(c[i] - r.entry), 2), prev_cross=bool((o[i - 1] - e[i - 1]) * (c[i - 1] - e[i - 1]) < 0), touches_fvg=touches_target_fvg(i, side)); rows.append(f)
S = pd.DataFrame(rows); pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)
print("signal candle = the candle the order sits in; price gap between its close and his entry: median %.2f USD, 90%% within %.2f" % (S.price_gap.median(), S.price_gap.quantile(.9)))
print("\nHIS 50 SIGNAL CANDLES (MT5 1-minute mid):")
print("  open and close on opposite sides of the EMA12 (a cross candle): %d of %d (%.0f%%)" % (S.cross.sum(), len(S), 100 * S.cross.mean()))
print("  the PREVIOUS candle was the cross candle (he entered on the candle after the cross): %d of %d" % (S.prev_cross.sum(), len(S)))
print("  closes on the trade side of the EMA: %d of %d | body > both wicks: %d of %d" % (S.right_side.sum(), len(S), S.body_gt_wick.sum(), len(S)))
print("  close-side wick / body: median %.2f, 25%% %.2f, 75%% %.2f, share <= 0.15: %.0f%%, share <= 0.25: %.0f%%" % (S.cw_ratio.median(), S.cw_ratio.quantile(.25), S.cw_ratio.quantile(.75), 100 * (S.cw_ratio <= .15).mean(), 100 * (S.cw_ratio <= .25).mean()))
print("  body / mean range of the prior 14 candles: median %.2f, 25%% %.2f, 75%% %.2f" % (S.body_atr.median(), S.body_atr.quantile(.25), S.body_atr.quantile(.75)))
print("  the signal candle reached into an unfilled fair-value gap lying in the trade direction: %d of %d" % (S.touches_fvg.sum(), len(S)))
# baseline: every cross candle (either side) in the first 15 minutes after the open on the same days / sessions
base = []
for _, r in F.iterrows():
    day = r.tm.date(); ses = "London" if r.tm.hour < 12 else "NY"; om = open_min(day, ses) - 120; start = pd.Timestamp(day) + pd.Timedelta(minutes=om)
    for k in range(0, 16):
        tt = start + pd.Timedelta(minutes=k)
        if tt not in idx: continue
        i = idx[tt]
        if not ((o[i] - e[i]) * (c[i] - e[i]) < 0): continue
        sd = 1 if c[i] > e[i] else -1; f = feat(i, sd); f.update(touches_fvg=touches_target_fvg(i, sd), day=str(day), ses=ses, minute=k); base.append(f)
B = pd.DataFrame(base).drop_duplicates(subset=["day", "ses", "minute"])
print("\nBASELINE: all %d cross candles in the first 15 minutes after the open on his %d trading days / sessions:" % (len(B), F.tm.dt.date.nunique()))
print("  body > both wicks %.0f%% | close-side wick / body median %.2f (25%% %.2f, 75%% %.2f), share <= 0.15: %.0f%%, <= 0.25: %.0f%% | body / ATR median %.2f | reached into an unfilled gap in its direction: %.0f%%" % (100 * B.body_gt_wick.mean(), B.cw_ratio.median(), B.cw_ratio.quantile(.25), B.cw_ratio.quantile(.75), 100 * (B.cw_ratio <= .15).mean(), 100 * (B.cw_ratio <= .25).mean(), B.body_atr.median(), 100 * B.touches_fvg.mean()))
cross_only = S[S.cross]; print("\nHIS signal candles that are themselves cross candles (n %d): close-side wick / body median %.2f, share <= 0.15 %.0f%%, <= 0.25 %.0f%% | body / ATR median %.2f | reached into a gap %.0f%%" % (len(cross_only), cross_only.cw_ratio.median(), 100 * (cross_only.cw_ratio <= .15).mean(), 100 * (cross_only.cw_ratio <= .25).mean(), cross_only.body_atr.median(), 100 * cross_only.touches_fvg.mean()))
print("by period (his signal candles): "); print(S.groupby("group").agg(n=("cross", "size"), cross=("cross", "mean"), prev_cross=("prev_cross", "mean"), cw_median=("cw_ratio", "median"), body_atr=("body_atr", "median"), fvg_touch=("touches_fvg", "mean")).round(2).to_string())
