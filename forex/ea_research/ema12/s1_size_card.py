"""READ-ONLY S1 size card, opened automatically by the scheduled tasks (07:35 inside the morning brief and 07:56 on its own), so nobody has to type a command.
It reads the MT5 broker terminal (balance, spread, open positions, today's deals, the losing streak since 23 Oct, the margin of one lot) and prints a table: for each stop distance in points, the lots to enter, the real risk in USD, the gain at the 1.0 R take profit and the margin level at entry,
using the S1 plan rule: risk USD = min(2,000, k x (closed balance - 92,000), 108,000 - closed balance), k = 0.25 (0.125 after 3 losses in a row), lots rounded down to 0.01, never above 3.1 lots and never below margin level 110%.
Places nothing, arms nothing. (s1_size.py does the same for one stop given on the command line, for Claude.)"""
import os, math, datetime as dt, MetaTrader5 as mt5
FLOOR, TARGET, DAYCAP, CAPLOTS, SPREAD_MAX, HALT, SYM = 92000.0, 108000.0, 2000.0, 3.1, 0.75, 93000.0, "XAUUSD+"
TERMINAL = os.getenv("MT5_TERMINAL") or r"C:\Program Files\MetaTrader 5\terminal64.exe"; U = dt.timezone.utc; SINCE = dt.datetime(2026, 10, 23, tzinfo=U).timestamp()
if not mt5.initialize(path=TERMINAL, timeout=30000): raise SystemExit("cannot attach to the MT5 broker terminal: %s" % (mt5.last_error(),))
try:
    a, ti = mt5.account_info(), mt5.terminal_info(); mt5.symbol_select(SYM, True); si, tk = mt5.symbol_info(SYM), mt5.symbol_info_tick(SYM)
    pos = mt5.positions_get() or (); pend = len(mt5.orders_get() or ()); now = dt.datetime.fromtimestamp(tk.time, U); day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(now - dt.timedelta(days=45), now + dt.timedelta(hours=1)) or (); closed = {}
    for d in deals:
        if d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY) and d.type in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL) and d.time >= SINCE:
            c = closed.setdefault(d.position_id, [d.time, 0.0]); c[0] = max(c[0], d.time); c[1] += d.profit + d.commission + d.swap
    streak = 0
    for _, pl in reversed(sorted(closed.values())):
        if pl < 0: streak += 1
        else: break
    opened_today = sum(1 for d in deals if d.entry == mt5.DEAL_ENTRY_IN and d.type in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL) and d.volume > 0 and dt.datetime.fromtimestamp(d.time, U) >= day0)   # real entries only (a 0-lot balance deal is not a trade)
    m1 = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, SYM, 1.0, tk.ask)                       # a calculation, no order
finally:
    mt5.shutdown()
bal, eq, spread, step, cs = a.balance, a.equity, tk.ask - tk.bid, si.volume_step, si.trade_contract_size
k = 0.125 if streak >= 3 else 0.25; cushion = bal - FLOOR; risk = max(0.0, min(DAYCAP, k * cushion, TARGET - bal)); lis = now - dt.timedelta(hours=2)
print("S1 SIZE CARD  |  local %s  |  closed balance %.2f  equity %.2f  |  cushion above 92,000: %.0f  |  spread now %.2f" % (lis.strftime("%a %d %b %H:%M"), bal, eq, cushion, spread))
print("risk budget USD %.0f  (= min of 2,000, %.3f x cushion = %.0f, %.0f still needed to pass)  |  losing streak since 23 Oct: %d%s" % (risk, k, k * cushion, TARGET - bal, streak, "  -> HALF SIZE" if streak >= 3 else ""))
flags = []
if bal <= HALT: flags.append("STOP: closed balance at or below %.0f - no new entries until the trader decides" % HALT)
if bal >= TARGET: flags.append("PASS LOCK: closed balance is at or above %.0f - no new entries, nothing left open, screenshot the MT5 broker dashboard" % TARGET)
if ti.trade_allowed: flags.append("WARNING: Algo Trading shows ON - manual only (Ctrl+E turns it off)")
if pos or pend: flags.append("SKIP: %d open position(s) / %d pending order(s) - one trade at a time" % (len(pos), pend))
if opened_today: flags.append("SKIP: %d trade(s) already opened today - one trade a day" % opened_today)
if spread > SPREAD_MAX: flags.append("SKIP: spread %.2f is above %.2f" % (spread, SPREAD_MAX))
for p in pos: flags.append("   open now: %s %.2f lots %s from %.2f, SL %.2f TP %.2f, floating %+.0f" % ("BUY" if p.type == 0 else "SELL", p.volume, p.symbol, p.price_open, p.sl, p.tp, p.profit))
print("\n".join(flags) if flags else "no flags: no open position, no trade yet today, spread fine")
print("\n stop (pts)   lots    real risk USD   gain at TP USD   margin level at entry")
mlots = eq / (1.10 * m1) if m1 else 99.0
for s in [x / 2 for x in range(4, 25)] + [13, 14, 15, 16, 18, 20]:
    lots = math.floor(min(risk / (s * cs), CAPLOTS, mlots) / step + 1e-9) * step; usd = lots * s * cs
    print("   %5.1f     %5.2f      %8.0f         %8.0f            %5.0f%%" % (s, lots, usd, usd, 100 * eq / (m1 * lots) if lots and m1 else 0))
print("\nOrder: lots from this table for your stop distance; SL = entry -/+ stop, TP = entry +/- the same distance (1.0 R), both attached when you send the order. Create the Notion forward-log row BEFORE entering.")
print("One trade a day, window 08:00-08:15 local, no re-entry, never move SL or TP. Nothing here sends anything.")
