"""READ-ONLY pre-London brief for XAUUSD+ from the attached MT5 terminal (local clock; server = local + 2 h). Sends nothing, places nothing.
python london_brief.py    -> state of the terminal (algo trading, open positions / pending orders, spread), Asia range, previous day high / low, EMA12 / ATR on the 1-minute chart, and the minimum stop / target table for the 3.1-lot cap."""
import os
import datetime as dt, numpy as np, pandas as pd, MetaTrader5 as mt5
U = dt.timezone.utc; SYM = "XAUUSD+"
if not mt5.initialize(path=os.getenv("MT5_TERMINAL") or r"C:\Program Files\MetaTrader 5\terminal64.exe", timeout=30000): raise SystemExit("cannot attach: %s" % (mt5.last_error(),))
try:
    mt5.symbol_select(SYM, True); ti, a, tk = mt5.terminal_info(), mt5.account_info(), mt5.symbol_info_tick(SYM)
    now_srv = dt.datetime.fromtimestamp(tk.time, U); now_lis = now_srv - dt.timedelta(hours=2)
    print("local now %s | terminal connected %s | ALGO TRADING %s (must be OFF: manual only) | open positions %d, pending orders %d" % (now_lis.strftime("%a %d %b %H:%M"), ti.connected, "ON" if ti.trade_allowed else "off", len(mt5.positions_get() or ()), len(mt5.orders_get() or ())))
    print("balance %.2f equity %.2f | floor 92,000: %.0f above | spread now %.2f | bid %.2f ask %.2f" % (a.balance, a.equity, a.equity - 92000, tk.ask - tk.bid, tk.bid, tk.ask))
    t1 = now_srv + dt.timedelta(minutes=5); r = mt5.copy_rates_range(SYM, mt5.TIMEFRAME_M1, now_srv - dt.timedelta(days=4), t1)
    d = pd.DataFrame(r); d["lis"] = pd.to_datetime(d.time, unit="s") - pd.Timedelta(hours=2); sp = d.spread / 100.0
    for c in ("open", "high", "low", "close"): d[c] = d[c] + sp / 2
    d["ema"] = d.close.ewm(span=12, adjust=False).mean(); d["atr"] = (d.high - d.low).rolling(14).mean().shift(1)
    day = now_lis.date(); asia = d[(d.lis >= pd.Timestamp(day) + pd.Timedelta(hours=2)) & (d.lis < pd.Timestamp(day) + pd.Timedelta(hours=7))]
    prev = d[(d.lis.dt.date < day)]; pday = prev[prev.lis.dt.date == prev.lis.dt.date.max()]; last = d.iloc[-1]; h4 = d[d.lis > d.lis.iloc[-1] - pd.Timedelta(hours=4)]
    if len(asia): print("Asia 02:00-07:00 (mid): high %.2f low %.2f range %.2f | price vs range: %s" % (asia.high.max(), asia.low.min(), asia.high.max() - asia.low.min(), "above" if last.close > asia.high.max() else "below" if last.close < asia.low.min() else "inside"))
    print("previous trading day (%s): high %.2f low %.2f close %.2f" % (pday.lis.dt.date.iloc[0], pday.high.max(), pday.low.min(), pday.close.iloc[-1]))
    print("last 4 h: move %+.2f (high %.2f low %.2f) | 1-minute EMA12 %.2f, price %.2f (%s) | ATR14 %.2f" % (h4.close.iloc[-1] - h4.close.iloc[0], h4.high.max(), h4.low.min(), last.ema, last.close, "above" if last.close > last.ema else "below", last.atr))
    print("\nminimum stop / target for the 3.1-lot cap (stop measured from the fill price; target at ratio 0.50 / 0.53):")
    for risk in (2000, 1000, 500, 100): m = risk / (100 * 3.1); print("  risk USD %5d: stop >= %.2f | target >= %.2f / %.2f | lots at a 5.00 stop: %.2f" % (risk, m, 0.5 * m, 0.53 * m, np.floor(risk / (100 * 5.0) * 100) / 100))
finally:
    mt5.shutdown()
