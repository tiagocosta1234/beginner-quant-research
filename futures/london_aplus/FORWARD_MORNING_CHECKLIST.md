# Morning checklist: London A+ forward log (28 Oct - 18 Dec 2026). Paper account only, never the BROKER eval chart.

1. 07:55 London: open TradingView Paper, 1-minute chart, indicator "claude" on MGC, MNQ, MES, MYM (one at a time, or 4 panes). Do not touch the eval tab.
2. 08:00-08:15 London: the indicator draws a LONG / SHORT box when a candidate passes A+ (2 of 3 confluence, risk in bounds). No box = no trade today for that market.
3. When a box appears, BEFORE anything else add one row to FORWARD_LOG.csv: date, market, side, setup time, entry, stop, target, risk in points, contracts, logged_at (now).
4. Place the paper bracket from the box (entry at market, stop and target as drawn). One trade per market per day. Never move the levels.
5. After the exit (or 16:00 London): fill exit_time, exit_px, exit_reason (TP / SL / 16:00) on the same row.
6. Fridays: run `python score_forward.py` for the running numbers. The bar is only judged on 18 Dec.
7. BROKER keep-alive trade (not part of this log): 1 micro gold, risk USD 15-30, by Fri 30 Oct, then every 7 days.
