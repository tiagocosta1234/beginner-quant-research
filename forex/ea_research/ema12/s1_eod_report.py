"""READ-ONLY end-of-day report, opened automatically by the 17:05 scheduled task (no command needed): the account now, today's closed trades, the S1 live record since 23 Oct, and the chance to still pass by 30 Nov / 22 Dec (the output of s1_pass_tracker.py).
Places nothing, arms nothing."""
import os, sys, subprocess, datetime as dt, MetaTrader5 as mt5
TERMINAL = os.getenv("mt5_MT5_TERMINAL") or r"C:\Program Files\MT5 MT5 Terminal\terminal64.exe"; U = dt.timezone.utc; SINCE = dt.datetime(2026, 10, 23, tzinfo=U).timestamp()
if not mt5.initialize(path=TERMINAL, timeout=30000): raise SystemExit("cannot attach to the MT5 broker terminal: %s" % (mt5.last_error(),))
try:
    a = mt5.account_info(); tk = mt5.symbol_info_tick("XAUUSD+"); now = dt.datetime.fromtimestamp(tk.time, U); day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    pos = mt5.positions_get() or (); deals = mt5.history_deals_get(now - dt.timedelta(days=45), now + dt.timedelta(hours=1)) or ()
finally:
    mt5.shutdown()
lis = lambda t: (dt.datetime.fromtimestamp(t, U) - dt.timedelta(hours=2)).strftime("%d %b %H:%M")
print("S1 DAY REPORT  |  local %s  |  closed balance %.2f  equity %.2f  |  floor 92,000: %.0f above  |  to pass 108,000: %.0f" % ((now - dt.timedelta(hours=2)).strftime("%a %d %b %H:%M"), a.balance, a.equity, a.equity - 92000, 108000 - a.balance))
for p in pos: print("STILL OPEN: %s %.2f lots %s from %.2f, SL %.2f TP %.2f, floating %+.0f  <- check that nothing should be left open" % ("BUY" if p.type == 0 else "SELL", p.volume, p.symbol, p.price_open, p.sl, p.tp, p.profit))
closed = {}
for d in deals:
    if d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY) and d.type in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL):
        c = closed.setdefault(d.position_id, [d.time, 0.0, d.symbol]); c[0] = max(c[0], d.time); c[1] += d.profit + d.commission + d.swap
today = [(t, pl, s) for t, pl, s in closed.values() if t >= day0.timestamp()]
print("\ntrades closed today: %d%s" % (len(today), "".join("\n   %s  %s  %+.0f USD" % (lis(t), s, pl) for t, pl, s in sorted(today))))
live = sorted((t, pl) for t, pl, s in closed.values() if t >= SINCE); w = sum(1 for _, pl in live if pl > 0)
print("S1 live record since 23 Oct: %d closed trades, %d wins, %d losses, total %+.0f USD" % (len(live), w, len(live) - w, sum(pl for _, pl in live)) + ("" if len(live) < 10 else "  <- 10 trades reached: do the plan's review"))
print("\n---- chance to still pass (s1_pass_tracker.py) ----")
r = subprocess.run([sys.executable, "-B", os.path.join(os.path.dirname(os.path.abspath(__file__)), "s1_pass_tracker.py"), "--balance", "%.2f" % a.balance], capture_output=True, text=True, timeout=600)
print(r.stdout.strip() or r.stderr.strip())
