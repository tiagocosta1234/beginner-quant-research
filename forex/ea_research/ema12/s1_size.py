"""READ-ONLY S1 position sizer (S1_LIVE_RISK_PLAN.md, adopted by the trader 22 Oct). Places nothing, arms nothing: it only reads the MT5 broker terminal (account_info, ticks, order_calc_margin, closed deals) and prints the numbers the trader types into his own order ticket.
  python s1_size.py --side L --stop 5.65 [--entry 4098.23] [--tgt 2.83] [--sym XAUUSD+] [--k 0.25]
Rule: risk USD = min(2,000, k x (closed balance - 92,000), 108,000 - closed balance), k = 0.25 (0.125 after 3 losses in a row, applied automatically from the closed-deal history);
lots = risk / (stop points x contract size), rounded DOWN to the lot step, never above 3.1 gold lots and never below margin level 110% at entry. S1 order: stop as given, take profit = 1.0 x stop. Notion row: Entry, Stop, and the rules-card level target (--tgt, default stop / 2).
Skips (prints SKIP / STOP): spread above 0.75, a position or pending order already open, a trade already taken today, closed balance at or below 93,000."""
import os, sys, math, argparse, datetime as dt, MetaTrader5 as mt5
ap = argparse.ArgumentParser(); ap.add_argument("--side", required=True, choices=["L", "S"]); ap.add_argument("--stop", type=float, required=True, help="stop distance in points")
ap.add_argument("--entry", type=float); ap.add_argument("--tgt", type=float, help="rules-card level target distance in points (for the Notion row)"); ap.add_argument("--sym", default="XAUUSD+"); ap.add_argument("--k", type=float, default=None)
A = ap.parse_args()
FLOOR, TARGET, DAYCAP, CAPLOTS, SPREAD_MAX, HALT = 92000.0, 108000.0, 2000.0, 3.1, 0.75, 93000.0
TERMINAL = os.getenv("mt5_MT5_TERMINAL") or r"C:\Program Files\MT5 MT5 Terminal\terminal64.exe"; U = dt.timezone.utc
SINCE = dt.datetime(2026, 10, 23, tzinfo=U).timestamp()           # the losing streak counts only trades closed from the first plan day, not the October manual trades before it
if not mt5.initialize(path=TERMINAL, timeout=30000): raise SystemExit("cannot attach to the MT5 broker terminal: %s" % (mt5.last_error(),))
try:
    a, ti = mt5.account_info(), mt5.terminal_info(); mt5.symbol_select(A.sym, True); si, tk = mt5.symbol_info(A.sym), mt5.symbol_info_tick(A.sym)
    pos, pend = len(mt5.positions_get() or ()), len(mt5.orders_get() or ())
    now = dt.datetime.fromtimestamp(tk.time, U); day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(now - dt.timedelta(days=45), now + dt.timedelta(hours=1)) or ()
    closed = {}                                                       # closed positions: net P&L per position id (exit deals only, entry deals carry no profit)
    for d in deals:
        if d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY) and d.type in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL) and d.time >= SINCE:
            c = closed.setdefault(d.position_id, [d.time, 0.0]); c[0] = max(c[0], d.time); c[1] += d.profit + d.commission + d.swap
    ordered = sorted(closed.values()); streak = 0
    for _, pl in reversed(ordered):
        if pl < 0: streak += 1
        else: break
    opened_today = sum(1 for d in deals if d.entry == mt5.DEAL_ENTRY_IN and d.type in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL) and d.volume > 0 and dt.datetime.fromtimestamp(d.time, U) >= day0)   # real entries only
    px = A.entry or (tk.ask if A.side == "L" else tk.bid); m1 = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY if A.side == "L" else mt5.ORDER_TYPE_SELL, A.sym, 1.0, px)     # a calculation, no order
finally:
    mt5.shutdown()
bal, eq, spread = a.balance, a.equity, tk.ask - tk.bid
k = A.k if A.k is not None else (0.125 if streak >= 3 else 0.25)
cushion = bal - FLOOR; risk = max(0.0, min(DAYCAP, k * cushion, TARGET - bal))
cs = si.trade_contract_size; step = si.volume_step
print("S1 sizer | server clock %s | account %s | balance %.2f equity %.2f | cushion above 92,000: %.0f | symbol %s contract %g step %g | spread now %.2f" % (now.strftime("%a %d %b %H:%M"), a.login, bal, eq, cushion, A.sym, cs, step, spread))
stops = []
if bal <= HALT: stops.append("STOP: closed balance %.0f is at or below %.0f - no new entries until the trader decides" % (bal, HALT))
if ti.trade_allowed: stops.append("WARNING: Algo Trading shows ON - the plan is manual only (Ctrl+E turns it off)")
if pos or pend: stops.append("SKIP: %d open position(s) / %d pending order(s) already - one trade at a time" % (pos, pend))
if opened_today: stops.append("SKIP: %d trade(s) already opened today - one trade a day" % opened_today)
if spread > SPREAD_MAX: stops.append("SKIP: spread %.2f is above %.2f" % (spread, SPREAD_MAX))
print("closed trades in the last 45 days: %d | losing streak at the end: %d -> k = %.3f%s" % (len(ordered), streak, k, "  (half size after 3 losses in a row)" if streak >= 3 else ""))
lots_raw = risk / (A.stop * cs)
lots_margin = eq / (1.10 * m1) if m1 else 99.0
lots = math.floor(min(lots_raw, CAPLOTS, lots_margin) / step + 1e-9) * step
usd_risk = lots * A.stop * cs; sgn = 1 if A.side == "L" else -1
print("\nrisk budget USD %.0f (min of %.0f cap, %.0f = %.3f x cushion, %.0f still needed to pass) -> %.3f lots by risk | %.2f lots by the 3.1 cap | %.2f lots by margin level 110%% (margin per lot %.0f)" % (risk, DAYCAP, k * cushion, k, TARGET - bal, lots_raw, CAPLOTS, lots_margin, m1 or 0))
print("ORDER TICKET: %s %.2f lots %s at %.2f | stop %.2f (%.2f pts) | take profit %.2f (1.0 R = %.2f pts)" % ("BUY" if A.side == "L" else "SELL", lots, A.sym, px, px - sgn * A.stop, A.stop, px + sgn * A.stop, A.stop))
print("real risk at the stop USD %.0f | gain at take profit USD %.0f | margin level at entry about %.0f%%" % (usd_risk, usd_risk, 100 * eq / (m1 * lots) if lots and m1 else 0))
tgt = A.tgt if A.tgt else A.stop / 2
print("NOTION ROW (forward log): Direction %s, Entry %.2f, Stop %.2f, Target (rules-card level, %.2f pts) %.2f" % ("Long" if A.side == "L" else "Short", px, px - sgn * A.stop, tgt, px + sgn * tgt))
for s in stops: print(s)
if not stops and lots < step: print("SKIP: size rounds to zero lots")
print("\nnothing was sent: this script only reads the terminal.")
