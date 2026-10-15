# PREREG_ORB11_ENTRY_OOT - out-of-time check of the three walk-forward entry picks (written 2026-10-15 17:37 local clock, before any 2020-21 data is read for this test)
Source: ORB11_ENTRY (commit f76c848e, result in ORB11_ENTRY_OUTPUT.txt). Nothing passed the pre-registered bars (0 of 826 pools, 0 of 5,924 cells). Step 3 of that round chose, on DEV 2022-24 only, the best of the 72 rules for each session x class pool. Three of those picks had enough trades and stayed positive in both 2025 and 2026:
| pick | rule (fixed, chosen on DEV) | DEV / 2025 / 2026 R per trade |
|---|---|---|
| P1 London FX | TOUCH, TREND+WIDE, hold to 17:00 London | +0.058 / +0.086 / +0.055 |
| P2 London indices | HOLD15, SQUEEZE, hold to 17:00 London | +0.202 / +0.103 / +0.231 |
| P3 New York metals | TOUCH, TREND+WIDE, hold to 15:55 NY | +0.243 / +0.121 / +0.068 |
(London metals, +0.003 / +0.330, is left out: its 2025 mean is zero.) They were picked from 10 pools x 72 rules, so they are LEADS only.

## Test (one look)
Period 2020-01-02 .. 2021-11-30 (never used by this family; allowed by the trader's 2020+ rule). HistData 1-minute BID bars via the histdata pip package, EST (UTC-5, no DST) converted to UTC and then to the MT5 broker server clock (Europe/Athens). Ask = bid + MT5 broker's median session spread for 2025-10..2026-10 (today's costs). Exactly the orb11_entry.py code (box, triggers, filters, 22:55-server cap, R >= 2 spreads), only the data loader changes. Daily trend / ATR are built from the HistData series itself, so January 2020 has fewer trades.
Markets: P1 every MT5 broker FX pair in the lab (28; the ones not on disk are downloaded first). P2 SP (SPXUSD), NSDQ (NSXUSD), NIKKEI (JPXJPY), ASX (AUXAUD), DAX (GRXEUR only up to 2020-06-12, see SWAPFREE_DRIFT Amendment 1); DOW has no HistData series and is left out. P3 XAUUSD, XAGUSD.
Gates per pick (Bonferroni over 3): pooled daily mean > 0 with t >= 2.13, and both 2020 and 2021 positive. Also reported: the random-entry null on the same days.
A pick that passes is still not an edge to trade: next would be MT5 broker real ticks (2025-10..2026-10, server clock) and an MT5 broker-rules account simulation.

## Honest prior
The walk-forward picks of the whole entry grid lost on average (DEV +0.230 -> 2025 -0.089 -> 2026 -0.140), and the London-FX breakout family mostly failed its 2020-21 check earlier today except USDJPY (PRESAMPLE2/3). Expected: at most one of the three survives, most likely none.
