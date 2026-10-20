"""DESCRIPTIVE ONLY (20 Oct 2026, after the trader's answers on his entry filter). Codes the parts of his checklist that can be coded and counts, on the 50 FX Replay trades (29 Apr-May 2025 + 21 Jan 2026, MT5 1-minute mid prices, signal candle = the candle the order sits in) and the sessions they come from, how many candles pass it and where his entry sits among them. No results of any trade are used; nothing here is a test, a bar or a rule.
His words: (1) a cross candle whose close-side wick is not small is only accepted if the NEXT candle closes strong; CISD optional; (2) strong body = good displacement and body bigger than the SUM of the wicks, the rest is discretion; (3) a gap should be 'in favor of the candle you're coming from', HTF bias optional; (4) the 14:34 short was 'not big enough', closed inside a 1-minute rejection block and did not follow the trend.
Coded: TYPE A = cross candle with body > sum of wicks and close-side wick <= CW x body (CW 0.15; 0.25 shown as a check), enter on its close. TYPE B = the previous candle was a cross candle in the trade direction that is NOT type A, and this candle has body > sum of wicks, closes on the trade side of the EMA and beyond the previous close. TREND = sign(close - close 30 candles earlier) equals the trade side. DISP = body >= 1.0 x mean range of the prior 14 candles. Not coded: HTF bias, CISD, 1-minute rejection blocks, the gap rule (its direction is not settled)."""
import numpy as np, pandas as pd
from ema12_test import open_min
F = pd.read_csv("FXREPLAY_TRADES_2026-10-20.csv"); F["tm"] = pd.to_datetime(F.chart_entry); F = F[F.side.isin(["Buy", "Sell"])].copy()
d = pd.read_parquet("D:/finance/beginner-quant-research/forex/data_mt5/XAUUSD_M1_rates.parquet").sort_values("t").reset_index(drop=True)
M = pd.DataFrame(dict(lis=pd.to_datetime(d.t, unit="s") - pd.Timedelta(hours=2), o=(d.bo + d.ao) / 2, h=(d.bh + d.ah) / 2, l=(d.bl + d.al) / 2, c=(d.bc + d.ac) / 2)); M["ema"] = M.c.ewm(span=12, adjust=False).mean()
M["atr"] = (M.h - M.l).rolling(14).mean().shift(1); idx = {t: i for i, t in enumerate(M.lis)}; o, h, l, c, e, atr = (M[k].to_numpy() for k in ("o", "h", "l", "c", "ema", "atr"))
def cross(i): return (o[i] - e[i]) * (c[i] - e[i]) < 0
def shape(i, s):
    body = abs(c[i] - o[i]); up = h[i] - max(o[i], c[i]); lo = min(o[i], c[i]) - l[i]; cw = up if s > 0 else lo; return body, cw, up + lo
def classify(i, s, CW=0.15):
    """returns dict(A, B, bsw, trend, disp) for candle i read as a signal in direction s"""
    body, cw, wsum = shape(i, s); bsw = body > wsum; trend = (np.sign(c[i] - c[i - 30]) == s); disp = bool(atr[i] > 0 and body >= atr[i])
    A = bool(cross(i) and (c[i] - e[i]) * s > 0 and bsw and body > 0 and cw <= CW * body)
    pb, pcw, pws = shape(i - 1, s); prevA = bool(cross(i - 1) and (c[i - 1] - e[i - 1]) * s > 0 and pb > pws and pb > 0 and pcw <= CW * pb)
    B = bool(cross(i - 1) and (c[i - 1] - e[i - 1]) * s > 0 and not prevA and bsw and (c[i] - e[i]) * s > 0 and (c[i] - c[i - 1]) * s > 0)
    return dict(A=A, B=B, bsw=bool(bsw), trend=bool(trend), disp=disp)
rows = []; sess = []
for _, r in F.iterrows():
    s = 1 if r.side == "Buy" else -1; sig = r.tm.floor("min"); i = idx[sig]; day = r.tm.date(); ses = "London" if r.tm.hour < 12 else "NY"
    k = classify(i, s); k025 = classify(i, s, 0.25); rows.append(dict(group=r.group, when=str(sig), side=r.side, **k, A25=k025["A"], B25=k025["B"]))
    st = pd.Timestamp(day) + pd.Timedelta(minutes=open_min(day, ses) - 120); cand = []
    for m in range(0, 16):
        t = st + pd.Timedelta(minutes=m)
        if t not in idx: continue
        j = idx[t]
        for sd in (1, -1):
            kk = classify(j, sd)
            if (kk["A"] or kk["B"]) and kk["trend"]: cand.append((t, sd, kk["disp"]))
    cand_all = [x for x in cand]; cand_disp = [x for x in cand if x[2]]
    sess.append(dict(when=str(sig), side=s, n_pass=len(cand_all), n_pass_disp=len(cand_disp), his_in=any(x[0] == sig and x[1] == s for x in cand_all), his_in_disp=any(x[0] == sig and x[1] == s for x in cand_disp), before_his=sum(1 for x in cand_all if x[0] < sig), after_his=sum(1 for x in cand_all if x[0] > sig)))
S = pd.DataFrame(rows); Q = pd.DataFrame(sess); n = len(S)
print("HIS 50 SIGNAL CANDLES against the coded checklist (MT5 1-minute mid):")
print("  body > sum of the wicks: %d of %d | follows the 30-candle trend: %d of %d | displacement (body >= mean range of the prior 14): %d of %d" % (S.bsw.sum(), n, S.trend.sum(), n, S.disp.sum(), n))
print("  TYPE A (cross candle, small close-side wick <= 0.15 of the body): %d | TYPE B (the candle after a cross that was not type A): %d | neither: %d" % (S.A.sum(), S.B.sum(), (~(S.A | S.B)).sum()))
print("  with a looser 'small wick' (<= 0.25): A %d, B %d" % (S.A25.sum(), S.B25.sum()))
ok = (S.A | S.B) & S.trend; print("  type A or B AND trend-aligned: %d of %d | and with displacement as well: %d" % (ok.sum(), n, (ok & S.disp).sum()))
print("  by period (A or B and trend):"); print(S.assign(ok=ok).groupby("group").agg(n=("ok", "size"), ok=("ok", "sum"), A=("A", "sum"), B=("B", "sum"), trend=("trend", "mean")).round(2).to_string())
print("\nTHE SAME CHECKLIST ON THE WHOLE SESSION (first 15 minutes after the open, either direction, A or B and trend-aligned):")
print("  candidates per session: median %.0f, mean %.1f, max %d | sessions with exactly 1: %d of %d | with 0: %d" % (Q.n_pass.median(), Q.n_pass.mean(), Q.n_pass.max(), (Q.n_pass == 1).sum(), n, (Q.n_pass == 0).sum()))
print("  his entry is one of the candidates: %d of %d | when it is, candidates BEFORE his entry that he skipped: median %.0f, mean %.1f; AFTER his entry: median %.0f" % (Q.his_in.sum(), n, Q[Q.his_in].before_his.median(), Q[Q.his_in].before_his.mean(), Q[Q.his_in].after_his.median()))
print("  with the displacement rule added: candidates per session median %.0f, mean %.1f | his entry among them: %d of %d" % (Q.n_pass_disp.median(), Q.n_pass_disp.mean(), Q.his_in_disp.sum(), n))
print("  his entry is the FIRST candidate of its session: %d of %d" % (((Q.his_in) & (Q.before_his == 0)).sum(), Q.his_in.sum()))
