"""READ-ONLY look at the attached MT5 terminal (account <acct>): leverage, margin per lot for gold and Nasdaq, lot limits, spread at today's opens, commission in recent deals.
Sends nothing: only account_info / symbol_info / order_calc_margin (a calculation) / ticks / history. python margin_check.py"""
import os, datetime as dt, numpy as np, MetaTrader5 as mt5
TERMINAL = os.getenv("MT5_TERMINAL") or r"C:\Program Files\MetaTrader 5\terminal64.exe"
U = dt.timezone.utc
if not mt5.initialize(path=TERMINAL, timeout=30000): raise SystemExit("cannot attach: %s" % (mt5.last_error(),))
try:
    ti, a = mt5.terminal_info(), mt5.account_info()
    print("terminal %s | connected %s | algo trading allowed %s" % (ti.path, ti.connected, ti.trade_allowed))
    print("account %s on %s | %s | LEVERAGE 1:%s | balance %.2f equity %.2f | margin used %.2f free %.2f | positions open %d, pending orders %d | stop-out mode %s call %s stop-out %s" % (
        a.login, a.server, a.currency, a.leverage, a.balance, a.equity, a.margin, a.margin_free, len(mt5.positions_get() or ()), len(mt5.orders_get() or ()), a.margin_so_mode, a.margin_so_call, a.margin_so_so))
    for sym in ("XAUUSD+", "NSDQ+"):
        si, tk = mt5.symbol_info(sym), mt5.symbol_info_tick(sym)
        if si is None or tk is None: print(sym, "not available (add it to Market Watch)"); continue
        print("\n%s: contract %g | volume min %g step %g MAX %g | calc mode %s | margin_initial %g maintenance %g hedged %g | spread now %.2f (%s points) | last tick %s server" % (
            sym, si.trade_contract_size, si.volume_min, si.volume_step, si.volume_max, si.trade_calc_mode, si.margin_initial, si.margin_maintenance, si.margin_hedged, tk.ask - tk.bid, si.spread, dt.datetime.fromtimestamp(tk.time, U).strftime("%H:%M:%S")))
        per = {}
        for lots in (0.01, 1.0, 3.0, 4.0):
            mb = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, sym, lots, tk.ask); ms = mt5.order_calc_margin(mt5.ORDER_TYPE_SELL, sym, lots, tk.bid); per[lots] = mb
            print("   %.2f lot: margin BUY %s SELL %s %s" % (lots, "%.2f" % mb if mb else mb, "%.2f" % ms if ms else ms, a.currency))
        if per[1.0]: print("   margin per 1.00 lot %.0f | implied leverage %.1f | max lots by free margin %.2f | max lots by equity %.2f" % (per[1.0], si.trade_contract_size * tk.ask / per[1.0], a.margin_free / per[1.0], a.equity / per[1.0]))
        # spread at today's opens (server clock: London 10:00-10:15, NY 16:30-16:45) and in the last 30 minutes
        day = dt.datetime.fromtimestamp(tk.time, U).replace(hour=0, minute=0, second=0, microsecond=0)
        for lab, h0, m0, h1, m1 in (("London open 10:00-10:15", 10, 0, 10, 15), ("NY open 16:30-16:45", 16, 30, 16, 45)):
            t0, t1 = day.replace(hour=h0, minute=m0), day.replace(hour=h1, minute=m1)
            if t0.timestamp() > tk.time: continue
            tt = mt5.copy_ticks_range(sym, t0, t1, mt5.COPY_TICKS_ALL)
            if tt is None or len(tt) == 0: print("   %s: no ticks" % lab); continue
            sp = tt["ask"] - tt["bid"]; sp = sp[(tt["bid"] > 0) & (tt["ask"] > 0)]
            print("   spread %s today (%d ticks): median %.2f | 90th %.2f | max %.2f | share within +-0.02 of the median %.0f%% | share above 0.75: %.1f%%" % (lab, len(sp), np.median(sp), np.quantile(sp, .9), sp.max(), 100 * np.mean(np.abs(sp - np.median(sp)) <= .02 * (1 if si.digits <= 2 else 1)), 100 * np.mean(sp > .75)))
        tt = mt5.copy_ticks_range(sym, dt.datetime.fromtimestamp(tk.time - 1800, U), dt.datetime.fromtimestamp(tk.time, U), mt5.COPY_TICKS_ALL)
        if tt is not None and len(tt): sp = (tt["ask"] - tt["bid"])[(tt["bid"] > 0) & (tt["ask"] > 0)]; print("   spread last 30 min (%d ticks): median %.2f | 90th %.2f | max %.2f" % (len(sp), np.median(sp), np.quantile(sp, .9), sp.max()))
    deals = mt5.history_deals_get(dt.datetime(2026, 10, 1, tzinfo=U), dt.datetime.fromtimestamp(mt5.symbol_info_tick("XAUUSD+").time + 86400, U))
    rows = [d for d in (deals or ()) if d.type in (0, 1)]
    print("\ndeals since 1 Oct (buy/sell only): %d" % len(rows))
    for sym in ("XAUUSD+", "NSDQ+"):
        r = [d for d in rows if d.symbol == sym]
        if r: print("   %s: %d deals, %.2f lots, commission %.2f (%.2f per lot per deal), fee %.2f, swap %.2f" % (sym, len(r), sum(d.volume for d in r), sum(d.commission for d in r), sum(d.commission for d in r) / max(sum(d.volume for d in r), 1e-9), sum(d.fee for d in r), sum(d.swap for d in r)))
    for d in rows[-8:]: print("   %s %-8s type %d entry %d vol %.2f price %.2f commission %.2f fee %.2f swap %.2f profit %.2f" % (dt.datetime.fromtimestamp(d.time, U).strftime("%m-%d %H:%M"), d.symbol, d.type, d.entry, d.volume, d.price, d.commission, d.fee, d.swap, d.profit))
finally:
    mt5.shutdown()
