"""READ-ONLY: the frozen rules card applied to TODAY'S London window on the trader's TradingView NAS100 chart (OANDA:NAS100USD 1m, 22 Oct 2026), the same reading used for gold in manual_22oct_rule_setup.py.
HINDSIGHT: written after the day was seen (the trader overslept); an illustration, not evidence. Assumptions (not in the card): 'not small' = body >= 1 ATR14; signal candle labelled 07:59-08:14 (entry candle 08:00-08:15, the recommended window reading);
target = the nearest level at least 1 ATR beyond the entry among the near edges of FVGs and the swing highs / lows of the last 60 minutes (closer ones would not cover the spread); stop = twice the target distance (0.5 RR); S1 = the same stop with a 1.0 R target.
Bars were read from the chart (data_get_ohlcv / bars()): one row per minute, UTC epoch; local = UTC + 1 until 25 Oct."""
import io, numpy as np, pandas as pd
B = """1792648800,29389.4,29390.4,29366,29372.4
1792648860,29372.6,29381.6,29360,29370.6
1792648920,29371.1,29382.1,29366,29366.6
1792648980,29366.3,29372,29357.4,29361.4
1792649040,29361.6,29371,29361,29366.8
1792649100,29366.7,29380,29363.4,29378.4
1792649160,29378.6,29394,29375.2,29388.8
1792649220,29389.4,29401.1,29388.6,29399.4
1792649280,29399.6,29413,29396.6,29408.4
1792649340,29408.3,29410,29395.2,29395.2
1792649400,29394.9,29401,29381.8,29385.4
1792649460,29385.4,29386,29371.7,29375.6
1792649520,29375.8,29385.8,29374.6,29383.8
1792649580,29384,29394,29377.4,29392.4
1792649640,29392.4,29396.4,29386.6,29390.2
1792649700,29390.4,29400.8,29390.4,29398.6
1792649760,29398.6,29400.4,29392.8,29399
1792649820,29398.8,29405.6,29385,29390.3
1792649880,29390.4,29397.4,29384.4,29387.2
1792649940,29387.4,29391,29377.4,29381.2
1792650000,29381,29387.2,29373.2,29375
1792650060,29374.9,29381.2,29370,29378.4
1792650120,29378.6,29380,29371.6,29378.8
1792650180,29378.6,29378.8,29368.4,29370
1792650240,29370,29378.6,29369.2,29376
1792650300,29376.2,29380.4,29374.4,29375.4
1792650360,29375,29380.6,29373,29377.6
1792650420,29378,29378.6,29362.6,29367.2
1792650480,29367.4,29371.8,29360.4,29367.6
1792650540,29367.6,29370,29353.6,29369.2
1792650600,29368.8,29397,29364.4,29393.4
1792650660,29393.2,29395,29384.4,29387.4
1792650720,29387.1,29390,29381.2,29385.4
1792650780,29385.8,29387.4,29371.4,29374.6
1792650840,29374.6,29376.2,29357.4,29357.8
1792650900,29358,29374,29358,29369
1792650960,29368.9,29382.6,29368.4,29379.2
1792651020,29378.8,29384.4,29367.4,29373
1792651080,29372.8,29382.6,29372.2,29377.6
1792651140,29377.7,29380.4,29358.6,29360.4
1792651200,29360.4,29369,29357.8,29366.4
1792651260,29366.4,29378.6,29366,29373.1
1792651320,29373.2,29375.4,29357.4,29361.4
1792651380,29361.6,29372.2,29359.6,29369.7
1792651440,29369.8,29375.4,29362.8,29368.2
1792651500,29368,29370.4,29358,29361.9
1792651560,29361.4,29368.8,29361.4,29367.4
1792651620,29367.6,29369,29360.2,29364.7
1792651680,29364.8,29368.6,29359.4,29364.4
1792651740,29364.6,29370.6,29362.8,29370.4
1792651800,29370.4,29380.4,29368.6,29370.8
1792651860,29371.2,29374.6,29368.2,29370.9
1792651920,29371,29379.3,29366.6,29378.6
1792651980,29378.6,29388.6,29378.2,29387.4
1792652040,29387,29387.4,29377.8,29378.9
1792652100,29378.8,29390,29376.6,29385.8
1792652160,29385.6,29392.6,29385.4,29388.4
1792652220,29388.6,29393.4,29387.2,29388.4
1792652280,29388.2,29388.6,29381.2,29382.6
1792652340,29382.4,29388.8,29381.1,29381.6
1792652400,29381.6,29390.8,29372.6,29387.4
1792652460,29387,29395,29384.4,29387.8
1792652520,29387.7,29395.6,29383.6,29393.6
1792652580,29393.4,29393.6,29368.6,29373.2
1792652640,29372.8,29372.9,29358.8,29366.6
1792652700,29366.6,29377.6,29364.9,29364.9
1792652760,29364.6,29365,29352.4,29357.2
1792652820,29357,29358.6,29341.9,29346
1792652880,29345.8,29345.8,29337.6,29342.4
1792652940,29342.4,29352.6,29331.1,29331.4
1792653000,29331.8,29335.2,29315.4,29327.9
1792653060,29328.6,29343,29327.6,29342.7
1792653120,29342.6,29348,29337.2,29339.4
1792653180,29339.3,29342.6,29335.3,29337
1792653240,29337.4,29347.4,29334.4,29342.2
1792653300,29343,29350.6,29341.6,29348
1792653360,29348.2,29352.4,29342,29346.8
1792653420,29347.2,29347.4,29334,29338.4
1792653480,29338.6,29342.1,29327.8,29341.2"""
T = pd.read_csv(io.StringIO(B), header=None, names=["t", "o", "h", "l", "c"]); T["lis"] = pd.to_datetime(T.t + 3600, unit="s"); T["hm"] = T.lis.dt.hour * 60 + T.lis.dt.minute
T["ema"] = T.c.ewm(span=12, adjust=False).mean()
tr = np.maximum(T.h - T.l, np.maximum((T.h - T.c.shift()).abs(), (T.l - T.c.shift()).abs())); T["atr"] = tr.rolling(14, min_periods=1).mean()
print("TradingView OANDA:NAS100USD 1m, 22 Oct, local clock; EMA12 of close (seeded 07:00), ATR14; cross = opens one side of the EMA and closes on the other")
print(" time   open      high      low       close     body    upw    lwr   ema12     atr   body/atr cross body>wick")
for _, r in T[(T.hm >= 7 * 60 + 52) & (T.hm <= 8 * 60 + 18)].iterrows():
    body = r.c - r.o; upw = r.h - max(r.o, r.c); lwr = min(r.o, r.c) - r.l; cross = "UP" if (r.o < r.ema < r.c) else "DOWN" if (r.o > r.ema > r.c) else "-"
    print("%s  %.1f  %.1f  %.1f  %.1f  %+6.1f  %5.1f  %5.1f  %.1f  %5.1f  %5.2f    %-4s  %s" % (r.lis.strftime("%H:%M"), r.o, r.h, r.l, r.c, body, upw, lwr, r.ema, r.atr, abs(body) / r.atr, cross, "yes" if abs(body) > max(upw, lwr) else "no"))
cand = []
for i, r in T.iterrows():
    if not (7 * 60 + 59 <= r.hm <= 8 * 60 + 14): continue
    body = r.c - r.o; upw = r.h - max(r.o, r.c); lwr = min(r.o, r.c) - r.l; up = r.o < r.ema < r.c; dn = r.o > r.ema > r.c
    if (up or dn) and abs(body) > max(upw, lwr) and abs(body) >= r.atr: cand.append((i, "L" if up else "S"))
print("\nqualifying signal candles (cross + body over the bigger wick + body >= 1 ATR) labelled 07:59-08:14: %s" % [(T.lis[i].strftime("%H:%M"), s) for i, s in cand])
if cand:
    i, side = cand[0]; e = T.o[i + 1]; look = T.iloc[max(0, i + 1 - 60):i + 1]
    lv = []
    for k in range(len(look) - 2):                                    # FVG near edges beyond the entry
        a, b2, c = look.iloc[k], look.iloc[k + 1], look.iloc[k + 2]
        if c.l > a.h: lv.append(("bullish FVG edge", a.h if side == "S" else c.l, a.h, c.l))
        if c.h < a.l: lv.append(("bearish FVG edge", c.h if side == "S" else a.l, c.h, a.l))
    for k in range(2, len(look) - 2):                                  # swing pivots (2 bars each side)
        if look.h.iloc[k] > look.h.iloc[k - 2:k + 3].drop(look.index[k]).max(): lv.append(("swing high", look.h.iloc[k], look.h.iloc[k], look.h.iloc[k]))
        if look.l.iloc[k] < look.l.iloc[k - 2:k + 3].drop(look.index[k]).min(): lv.append(("swing low", look.l.iloc[k], look.l.iloc[k], look.l.iloc[k]))
    beyond = [(abs(p - e), n, p) for n, p, _, _ in lv if (p > e if side == "L" else p < e)]; beyond.sort()
    print("signal %s %s (%s) -> market entry at the next open %.1f (%s)" % (T.lis[i].strftime("%H:%M"), side, "UP cross" if side == "L" else "DOWN cross", e, T.lis[i + 1].strftime("%H:%M")))
    print("nearest levels beyond the entry in the trade direction: %s" % [(n, round(p, 1), round(d, 1)) for d, n, p in beyond[:4]])
    atr_s = T.atr[i]; far = [x for x in beyond if x[0] >= atr_s]                      # a level closer than 1 ATR is noise (it would not even cover the spread): ignored
    print("ATR14 at the signal %.1f: levels at least 1 ATR away: %s" % (atr_s, [(n, round(p, 1), round(d, 1)) for d, n, p in far[:4]]))
    d, n, p = far[0]; tgt = d; stop = 2 * d
    sl = e - stop if side == "L" else e + stop; tp = p; tp1 = e + stop if side == "L" else e - stop
    print("RULES CARD: %s at %.1f  target %.1f (%s, %.1f away)  stop %.1f (%.1f away)  | S1: target %.1f (%.1f away)" % ("long" if side == "L" else "short", e, tp, n, tgt, sl, stop, tp1, stop))
    print("entry bar epoch %d (%s local), box end epoch candidates: signal bar %d" % (T.t[i + 1], T.lis[i + 1].strftime("%H:%M"), T.t[i]))

# ---- MT5 broker check on NSDQ+ (read-only MT5): same distances from the MT5 broker fill, short at the bid, stop / target on the ask ----
import sys, datetime as dt
sys.path.insert(0, r"mt5\ea_research\ema12"); sys.dont_write_bytecode = True
import MetaTrader5 as mt5, forward_score as F
if not mt5.initialize(path=F.TERMINAL, timeout=30000): raise SystemExit("cannot attach to the MT5 broker terminal: %s" % (mt5.last_error(),))
try:
    U = dt.timezone.utc; r = mt5.copy_rates_range("NSDQ+", mt5.TIMEFRAME_M1, dt.datetime(2026, 10, 21, 22, 0, tzinfo=U), dt.datetime(2026, 10, 23, 0, 0, tzinfo=U)); pt = mt5.symbol_info("NSDQ+").point
finally:
    mt5.shutdown()
Z = pd.DataFrame(r); Z["dt"] = pd.to_datetime(Z.time, unit="s"); Z["lis"] = Z.dt - pd.Timedelta(hours=2); Z["hm"] = Z.lis.dt.hour * 60 + Z.lis.dt.minute
Z["sp"] = Z.spread * pt; Z["ah"] = Z.high + Z.sp; Z["al"] = Z.low + Z.sp
i0 = Z.index[Z.hm == 8 * 60 + 4][0]; fill = Z.open[i0]
print("\nMT5 broker NSDQ+ 08:04 minute: bid open %.1f, spread %.1f; the 08:03 signal candle on MT5: open %.1f close %.1f" % (fill, Z.sp[i0], Z.open[i0 - 1], Z.close[i0 - 1]))
for lab, tgt_d in (("rules card (target 13.4)", 13.4), ("S1 (target 26.8)", 26.8)):
    st, tp, res = fill + 26.8, fill - tgt_d, None
    for j in range(i0, len(Z)):
        if Z.hm[j] > 17 * 60: break
        if Z.ah[j] >= st: res = ("STOP", Z.lis[j].strftime("%H:%M"), -1.0); break
        if Z.al[j] <= tp: res = ("TARGET", Z.lis[j].strftime("%H:%M"), tgt_d / 26.8); break
    print("MT5 %-26s: fill %.1f stop %.1f target %.1f -> %s" % (lab, fill, st, tp, res if res else "still open (day not finished)"))
