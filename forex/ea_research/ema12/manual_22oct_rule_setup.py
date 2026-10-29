"""READ-ONLY: what the frozen rules card ("Cartao de regras: 12 EMA, Londres") produces on 22 Oct on the trader's own TradingView chart (OANDA:XAUUSD 1m), then scored on the MT5 broker feed.
Rules card: market entry 08:00-08:15 local; the setup candle opens one side of the 12 EMA and closes clearly on the other, body larger than its bigger wick and not small;
target an FVG (whole if small, part if big) or a nearby high / low (Amendment 4); stop at twice the target distance (0.5 RR).
HINDSIGHT WARNING: written after the whole day was seen (the trader overslept), so this is an illustration of how the rules read, not evidence of an edge. Nothing is logged or scorable.
OANDA bars below were read from the TradingView chart (data_get_ohlcv, bar k=0 is 07:23 local = 06:23 UTC, one bar a minute). Run: python -B manual_22oct_rule_setup.py"""
import sys, io, numpy as np, pandas as pd
sys.dont_write_bytecode = True
B = """4100.275 4101.055 4097.055 4097.35
4097.36 4099.055 4096.91 4098.62
4098.63 4098.68 4096.99 4097.135
4097.13 4097.205 4094.625 4094.735
4094.66 4095.3 4094.09 4094.555
4094.55 4094.645 4092.345 4092.385
4092.36 4093.175 4091.475 4091.57
4091.545 4093.845 4091.295 4093.435
4093.37 4093.395 4091.75 4092.08
4092.075 4092.375 4090.75 4092.09
4092.105 4093.735 4091.015 4093.295
4093.22 4093.825 4091.755 4091.885
4091.875 4093.68 4091.48 4092.985
4093.22 4095.46 4092.695 4094.655
4094.63 4095.435 4093.64 4093.995
4093.99 4094.705 4091.37 4091.555
4091.48 4092.445 4088.965 4089.165
4089.1 4089.87 4087.465 4087.47
4087.705 4092.425 4087.465 4090.21
4090.305 4091.32 4090.09 4090.745
4090.84 4091.19 4089.96 4091.14
4090.92 4091.81 4089.63 4090.01
4090 4090.54 4089.205 4089.65
4089.675 4093.175 4089.675 4092.835
4092.825 4093.135 4091.475 4092.755
4092.805 4094.305 4091.765 4091.835
4091.785 4093.37 4091.54 4093.33
4093.37 4095.005 4093.27 4093.8
4093.7 4094.255 4093.265 4094.255
4094.425 4094.885 4092.94 4093.695
4093.705 4094.9 4092.34 4092.355
4092.34 4092.975 4091.055 4092.84
4092.845 4095 4092.805 4094.685
4094.72 4095.71 4094.195 4095.395
4095.425 4095.775 4094.14 4094.925
4094.94 4094.94 4093.65 4093.88
4093.83 4094.255 4092.575 4092.665
4092.705 4092.705 4089.065 4091.225
4091.265 4091.995 4090.925 4091.39
4091.4 4093.085 4091.12 4092.54
4092.34 4092.72 4091.035 4091.795
4091.795 4092.535 4091.215 4092.12
4092.105 4093.07 4092.015 4092.955
4092.965 4092.965 4091.475 4091.99
4091.95 4092.625 4089.835 4092.06
4092.07 4098.855 4092.01 4098.18
4098.23 4101.015 4097.945 4098.14
4098.145 4098.145 4095.23 4095.53
4095.58 4096.345 4094.51 4094.835
4094.865 4095.14 4093.235 4095.085
4094.945 4100.715 4094.945 4099.545
4099.51 4099.955 4098.715 4098.965
4099.065 4100.335 4098.28 4099.67
4099.82 4101.13 4099.455 4099.765
4099.715 4100.27 4098.63 4098.875
4098.88 4099.66 4098.56 4099.125
4099.135 4099.215 4097.085 4097.57
4097.475 4098.49 4096.12 4097.19"""
T = pd.read_csv(io.StringIO(B), sep=" ", header=None, names=["o", "h", "l", "c"])
T["lis"] = pd.Timestamp("2026-10-22 07:23") + pd.to_timedelta(np.arange(len(T)), unit="m"); T["hm"] = T.lis.dt.hour * 60 + T.lis.dt.minute
T["ema"] = T.c.ewm(span=12, adjust=False).mean()
tr = np.maximum(T.h - T.l, np.maximum((T.h - T.c.shift()).abs(), (T.l - T.c.shift()).abs())); T["atr"] = tr.rolling(14, min_periods=1).mean()
print("TradingView OANDA:XAUUSD 1m, 22 Oct, local clock; EMA12 of close (seeded 07:23, so it differs a little from the chart's), ATR14; cross = opens one side of the EMA and closes on the other")
print(" time   open     high     low      close    body   upw   lwr   ema12    atr  body/atr  cross  body>wick")
for _, r in T[(T.hm >= 7 * 60 + 55) & (T.hm <= 8 * 60 + 16)].iterrows():
    body = r.c - r.o; upw = r.h - max(r.o, r.c); lwr = min(r.o, r.c) - r.l
    cross = "UP" if (r.o < r.ema < r.c) else "DOWN" if (r.o > r.ema > r.c) else "-"
    print("%s  %.2f  %.2f  %.2f  %.2f  %+.2f  %.2f  %.2f  %.2f  %.2f  %5.2f    %-4s   %s" % (r.lis.strftime("%H:%M"), r.o, r.h, r.l, r.c, body, upw, lwr, r.ema, r.atr, abs(body) / r.atr, cross, "yes" if abs(body) > max(upw, lwr) else "no"))
# MT5 broker bars for scoring
sys.path.insert(0, r"mt5\ea_research\ema12")
import forward_score as F
Z = F.load_days_mt5("2026-10-22", "2026-10-22")[pd.Timestamp("2026-10-22").date()].copy()
Z["lis"] = Z.dt - pd.Timedelta(hours=2); Z["hm2"] = Z.lis.dt.hour * 60 + Z.lis.dt.minute
def score(i0, side, stop, tgt, label):
    fill = Z.ao.iloc[i0] if side == "L" else Z.bo.iloc[i0]; st = fill - stop if side == "L" else fill + stop; tp = fill + tgt if side == "L" else fill - tgt; res = None
    for _, b in Z.iloc[i0:].iterrows():
        if b.hm2 > 17 * 60: break
        hs = (b.bl <= st) if side == "L" else (b.ah >= st); ht = (b.bh >= tp) if side == "L" else (b.al <= tp)
        if hs: res = ("STOP", b.lis.strftime("%H:%M"), -1.0); break
        if ht: res = ("TARGET", b.lis.strftime("%H:%M"), tgt / stop); break
    print("%s: fill %.2f stop %.2f target %.2f -> %s" % (label, fill, st, tp, res if res else "still open at 17:00 local"))
print()
# rule reading, long after the 08:08 candle (OANDA: opens 4092.07 below the EMA, closes 4098.18 far above it, body 6.11 vs 0.68 wick)
ent = T[T.hm == 8 * 60 + 9].iloc[0].o; hi = T[T.hm < 8 * 60 + 9].h.max(); tgt = hi - ent; stop = 2 * tgt
print("rule reading: market long at the 08:09 open (OANDA %.3f); no bearish FVG above it, so the target is the nearest prior high above, the session high %.3f (07:23) = %.3f away; stop at twice that = %.3f below = %.3f (the 08:07 high / gap bottom is 4092.625)" % (ent, hi, tgt, stop, ent - stop))
i0 = Z.index.get_loc(Z.index[Z.hm2 == 8 * 60 + 9][0])
score(i0, "L", stop, tgt, "MT5, long at the 08:09 open (ask), distances as above")
print("for comparison, the drawn short (his bracket 5.290 / 5.301) at the 08:00 open:")
score(Z.index.get_loc(Z.index[Z.hm2 == 8 * 60][0]), "S", 5.290, 5.301, "MT5, short at the 08:00 open (bid)")
