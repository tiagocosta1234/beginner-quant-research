# XMKT_RESULT - the trader's 50-hypothesis list: triage, D2 refinements and the untested cross-market / daily items (2026-10-15, local clock 19:04)
Pre-registrations PREREG_D2PLUS.md, PREREG_XMKT.md; code d2plus.py, xmkt.py; outputs D2PLUS_OUTPUT.txt, XMKT_OUTPUT.txt. Truncation tests identical (XMKT 112,470 trades).

## Verdict: 0 of 11 new hypotheses pass; none of the 4 D2 refinements improves D2
| item | rule (fixed) | trades 2022-25 | net bp a trade | t | 2022-24 / 2025 / 2026 |
|---|---|---|---|---|---|
| 10 open discovery (reaction against overnight, hold to close; SP / NSDQ / DOW) | 10:00-15:55 NY | 1,170 | +4.25 | 1.41 | -0.5 / +19.1 / -6.6 |
| 11 SP leads NSDQ (5-min z) | 15 min | 157 | -1.90 | -0.82 | -0.8 / -9.5 / -4.5 |
| 12 NSDQ leads SP | 15 min | 207 | +1.56 | 1.00 | +1.8 / +0.7 / +2.8 |
| 13 DAX 03:00-09:25 NY -> SP 09:35-11:30 | daily | 1,015 | +0.30 | 0.19 | +0.1 / +0.9 / -1.9 |
| 14 NIKKEI Tokyo session -> USDJPY London morning | daily | 1,026 | -0.85 | -1.04 | -1.1 / +0.1 / -0.9 |
| 15 WTI 15-min EIA reaction -> USDCAD opposite, +16..+90 min | EIA days | 109 | +1.58 | 1.15 | +2.0 / -0.9 / +0.5 |
| 18 DAX session -> SP afternoon | daily | 980 | -1.13 | -0.50 | -3.1 / +5.0 / -1.7 |
| 19 EURJPY vs EURUSD x USDJPY residual > spread | 5 min | 122,344 | -0.20 (gross 0.00) | -17.97 | the dealer's triangle carries no information |
| 20a SP -1% in 30 min -> short USDJPY 60 min | event | 65 | +1.67 | 0.52 | too few events |
| 20b same -> long gold 60 min | event | 65 | +2.62 | 0.46 | too few events |
| 34 close in the top / bottom 10% of the range -> next day same way (6 markets) | daily | 1,620 | -4.31 | -1.54 | negative; NIKKEI -12.8 bp |
Bar: t >= 2.61 (5% / 11), > 0 in all three periods, >= 100 trades. The nearest, item 12 (NSDQ leads SP), is +1.6 bp a trade at t 1.0 on 207 trades: too small to matter even if real.

D2 refinements (items 41, 42, 43, 47): D2PLUS_RESULT.md, none improves D2 (best: downside-vol weights +2.1 USD a day, t 1.42).

## Triage of all 50 items
- Closed by earlier families (not re-run): 1-9 microstructure / ticks (HF lab 0/48 on real ticks, MICRO_SCALP, BRK_TICKS order flow, EURUSD_OF, TICK_EVENTS); 17 SP-NSDQ spread reversion (STATARB_INTRADAY); 21-30 economic calendar with MT5 consensus (EVENTS 0/18, TICK_EVENTS 0/4, EVENT_MACRO pre-FOMC drift failed its hold-out, NEWS_GAPS; items 22 / 27-29 are sub-cases with tens of events a year: underpowered); 31-33 gaps and overnight (GAP_FADE, WEEKEND_GAP, OVERNIGHT, OVERNIGHT_GRID); 35 multi-day reversal (RSI2_LEG, DIP families); 36 VWAP (Broker-era VWAP-Z, STACKED_VA); 37 trend pullback (TREND_PULLBACK, LEO_EMA_PULLBACK); 38 compression with trend (BRK_SQUEEZE, ORB11_ENTRY SQUEEZE); 39-40 structure and exits (BRK_SWING, BRK_EXITS, ORB11_GRID, ORB11_ICTSTOP); 46 strongest-trend selection (XS_MOM_IDX, failed); 45 is D2's band already; 50 is the standing rule.
- Tested here: 10-15, 18-20, 34 (XMKT) and 41-43, 47 (D2PLUS).
- Not tested: 16 (gold-USDJPY divergence: no rule without a search), 44 (a sizing rule, not a return source), 48 (session rotation does not apply to a weekly book), 49 (needs a definition of divergence).

## Reading for the trader
Your list is well chosen, but the ideas that can be tested quickly have mostly been tested over the last two weeks, and the new ones fail too. The lead-lag ideas are worth at most 1-2 bp a trade against a spread of 0.5-2 bp. Nothing here is faster or better than D2. On the MT5 broker note in your list: the daily profit cap and MT5 broker's warning about reopening positions to get around it are exactly why D2's profit skim (close at +1,800, re-enter the next day) must be confirmed by MT5 broker in writing before it is used (mt5_SUPPORT_MESSAGE_8.md).
