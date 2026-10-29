"""READ-ONLY: the trader's TradingView short drawn after the fact on 22 Oct (id nRy9vU on OANDA:XAUUSD 1m: entry 4092.665 at the 07:59 local candle, stop +5.290, target -5.301 = ratio 1.002)
against the MT5 XAUUSD+ M1 feed. A hindsight drawing (he overslept the London window): not logged, not scorable, an anecdote like the 21 Oct boxes.
Same conventions as MANUAL_21OCT_DRAWN_TRADE_OUTPUT.txt: local clock = MT5 server clock - 2 h until 25 Oct, mid prices, EMA12 of mid close, ATR14 of mid true range;
short fills at the bid, the stop is hit when the ask reaches it, the target when the ask reaches it, stop first inside one bar.
Run from the repo: python -B forex/ea_research/ema12/manual_22oct_drawn_check.py > forex/ea_research/ema12/MANUAL_22OCT_DRAWN_TRADE_OUTPUT.txt"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, r"mt5\ea_research\ema12"); sys.dont_write_bytecode = True
import forward_score as F
D = F.load_days_mt5("2026-10-22", "2026-10-22")
Z = D[pd.Timestamp("2026-10-22").date()].copy()
Z["lis"] = Z.dt - pd.Timedelta(hours=2)
Z["o"] = (Z.bo + Z.ao) / 2; Z["h"] = (Z.bh + Z.ah) / 2; Z["l"] = (Z.bl + Z.al) / 2; Z["c"] = (Z.bc + Z.ac) / 2
Z["ema"] = Z.c.ewm(span=12, adjust=False).mean()
tr = np.maximum(Z.h - Z.l, np.maximum((Z.h - Z.c.shift()).abs(), (Z.l - Z.c.shift()).abs())); Z["atr"] = tr.rolling(14).mean()
Z["hm2"] = Z.lis.dt.hour * 60 + Z.lis.dt.minute
print("MT5 XAUUSD+ 22 Oct, local clock, mid prices; body = close-open, up wick / low wick, EMA12 of mid close")
print(" time   open     high     low      close    body   upw   lwr   ema12   atr   spr")
for _, r in Z[(Z.hm2 >= 7 * 60 + 45) & (Z.hm2 <= 8 * 60 + 30)].iterrows():
    body = r.c - r.o; upw = r.h - max(r.o, r.c); lwr = min(r.o, r.c) - r.l
    print("%s  %.2f  %.2f  %.2f  %.2f  %+.2f  %.2f  %.2f  %.2f  %.2f %.2f" % (r.lis.strftime("%H:%M"), r.o, r.h, r.l, r.c, body, upw, lwr, r.ema, r.atr, r.sp))
c = Z[Z.hm2 == 7 * 60 + 59].iloc[0]
print("\nsignal candle 07:59: body %.2f = %.2f ATR, close-side wick (low) %.2f = %.0f%% of the body, other wick %.2f; closes %.2f below EMA12 (opened %.2f above it)" % (c.c - c.o, abs(c.c - c.o) / c.atr, c.c - c.l, 100 * (c.c - c.l) / abs(c.c - c.o), c.h - c.o, c.ema - c.c, c.o - c.ema))
a, b = Z[Z.hm2 == 7 * 60 + 58].iloc[0], Z[Z.hm2 == 8 * 60].iloc[0]
print("bearish 3-candle gap 07:58 / 07:59 / 08:00: 07:58 low %.2f against 08:00 high %.2f = %.2f points (his entry 4092.665 sits inside it on the OANDA chart)" % (a.l, b.h, a.l - b.h))
STOP, TGT = 5.290, 5.301
print("\ndrawn short: stop %.3f / target %.3f above / below the entry (ratio %.3f); TradingView (OANDA) entry 4092.665" % (STOP, TGT, TGT / STOP))
def run(i0, label, stop=STOP, tgt=TGT):
    r0 = Z.iloc[i0]; fill = r0.bo; st = fill + stop; tp = fill - tgt; res = None
    path = Z.iloc[i0:]
    for _, b_ in path.iterrows():
        if b_.ah >= st: res = ("STOP", b_.lis.strftime("%H:%M"), -1.0); break
        if b_.al <= tp: res = ("TARGET", b_.lis.strftime("%H:%M"), tgt / stop); break
    w60 = Z.iloc[i0:i0 + 60]; adv = w60.ah.max() - fill; fav = fill - w60.al.min()
    day = path[path.hm2 <= 17 * 60]; mfe_day = fill - day.al.min()
    print("%s: fill(bid open) %.2f stop %.2f target %.2f -> %s | 60-min worst adverse %.2f (%.2f R), best favourable %.2f (%.2f R) | best favourable to 17:00 %.2f (%.2f R)" % (label, fill, st, tp, res if res else "no exit by the feed's end", adv, adv / stop, fav, fav / stop, mfe_day, mfe_day / stop))
for hm, lab in ((7 * 60 + 59, "entry at the 07:59 open (box anchor)"), (8 * 60, "entry at the 08:00 open (signal candle 07:59)"), (8 * 60 + 1, "entry at the 08:01 open (signal candle 08:00)")):
    i = Z.index[Z.hm2 == hm]
    if len(i): run(Z.index.get_loc(i[0]), lab)
print("\nsame entry (08:00 open) and the same stop, other targets (post-hoc, looking at the outcome):")
i0 = Z.index.get_loc(Z.index[Z.hm2 == 8 * 60][0])
for k in (0.53, 0.75, 1.0, 1.5, 2.0):
    run(i0, "target/stop %.2f" % k, STOP, STOP * k)
