# Market demo screen (stage 1 = real ticks 2025Q4 + 2026; stage 2 = modelled 2022-2025)

## mkt_ghostscalper_H1: stage 1 fail
net +661 USD, PF 1.47, 1354 trades
- FAIL net > 0 in BOTH windows
- ok   pooled PF 1.47 >= 1.30
- ok   1354 trades >= 60
- ok   net / max equity DD 3.2 >= 2
- FAIL max concurrent 4 <= 3 and lot ratio 1.0 <= 3 (grid / martingale)
- ok   112.8 trades a month >= 5

## mkt_goldbeaver_M15: stage 1 fail
net +87,789 USD, PF 2.66, 106 trades
- ok   net > 0 in BOTH windows
- ok   pooled PF 2.66 >= 1.30
- ok   106 trades >= 60
- ok   net / max equity DD 4.4 >= 2
- FAIL max concurrent 3 <= 3 and lot ratio 162.0 <= 3 (grid / martingale)
- ok   8.8 trades a month >= 5

## mkt_goldenshot_M15: STAGE 1 PASS
net +31,738 USD, PF 3.86, 386 trades
- ok   net > 0 in BOTH windows
- ok   pooled PF 3.86 >= 1.30
- ok   386 trades >= 60
- ok   net / max equity DD 12.9 >= 2
- ok   max concurrent 1 <= 3 and lot ratio 1.5 <= 3 (grid / martingale)
- ok   32.2 trades a month >= 5

stage 2: PF >= 1.0 in 3 of 4 years: 2022 PF 0.80 net -3,352 (195 trades), 2023 PF 1.04 net +503 (195 trades), 2024 PF 1.53 net +8,193 (269 trades), 2025 PF 2.93 net +24,830 (361 trades)
## mkt_goldenshot_H1: STAGE 1 PASS
net +31,738 USD, PF 3.86, 386 trades
- ok   net > 0 in BOTH windows
- ok   pooled PF 3.86 >= 1.30
- ok   386 trades >= 60
- ok   net / max equity DD 12.9 >= 2
- ok   max concurrent 1 <= 3 and lot ratio 1.5 <= 3 (grid / martingale)
- ok   32.2 trades a month >= 5

## mkt_brokergold_M30: STAGE 1 PASS
net +37,014 USD, PF 1.36, 345 trades
- ok   net > 0 in BOTH windows
- ok   pooled PF 1.36 >= 1.30
- ok   345 trades >= 60
- ok   net / max equity DD 2.0 >= 2
- ok   max concurrent 3 <= 3 and lot ratio 1.4 <= 3 (grid / martingale)
- ok   28.8 trades a month >= 5

stage 2: PF >= 1.0 in 4 of 4 years: 2022 PF 1.01 net +1,004 (421 trades), 2023 PF 1.11 net +7,619 (432 trades), 2024 PF 1.44 net +27,095 (405 trades), 2025 PF 1.33 net +26,681 (382 trades)
## mkt_rangebreakout_M15: no deals in 2025Q4
## mkt_rangebreakout_H1: no deals in 2025Q4
## mkt_scrapergold_M15: stage 1 fail
net +24,448 USD, PF 1.66, 338 trades
- FAIL net > 0 in BOTH windows
- ok   pooled PF 1.66 >= 1.30
- ok   338 trades >= 60
- ok   net / max equity DD 4.3 >= 2
- ok   max concurrent 3 <= 3 and lot ratio 1.3 <= 3 (grid / martingale)
- ok   28.2 trades a month >= 5

## mkt_scrapergold_H1: stage 1 fail
net +23,585 USD, PF 1.64, 339 trades
- FAIL net > 0 in BOTH windows
- ok   pooled PF 1.64 >= 1.30
- ok   339 trades >= 60
- ok   net / max equity DD 4.1 >= 2
- ok   max concurrent 3 <= 3 and lot ratio 1.3 <= 3 (grid / martingale)
- ok   28.2 trades a month >= 5

## mkt_smartgoldhunter_M15: stage 1 fail
net +162 USD, PF 1.60, 136 trades
- FAIL net > 0 in BOTH windows
- ok   pooled PF 1.60 >= 1.30
- ok   136 trades >= 60
- ok   net / max equity DD 3.6 >= 2
- ok   max concurrent 1 <= 3 and lot ratio 1.0 <= 3 (grid / martingale)
- ok   11.3 trades a month >= 5

## mkt_smartgoldhunter_H1: stage 1 fail
net +162 USD, PF 1.60, 136 trades
- FAIL net > 0 in BOTH windows
- ok   pooled PF 1.60 >= 1.30
- ok   136 trades >= 60
- ok   net / max equity DD 3.6 >= 2
- ok   max concurrent 1 <= 3 and lot ratio 1.0 <= 3 (grid / martingale)
- ok   11.3 trades a month >= 5

## mkt_titanforge_H1: stage 1 fail
net -1,063 USD, PF 0.00, 2 trades
- FAIL net > 0 in BOTH windows
- FAIL pooled PF 0.00 >= 1.30
- FAIL 2 trades >= 60
- FAIL net / max equity DD -1.9 >= 2
- ok   max concurrent 1 <= 3 and lot ratio 1.0 <= 3 (grid / martingale)
- FAIL 0.2 trades a month >= 5


---
# Reading (2026-10-09 23:36 local) - written after the runs, numbers are from the tester on MT5 broker data
Registered screen (PREREG_MARKET_DEMOS.md, 22:12): 8 demos found (Lizard did not reach the tester folder; Range Breakout EA with Range Filters opened no trades in the tester, probably because it needs its own symbol list / settings). Ledger rows appear twice (the report ran twice); the figures are identical.
| EA (author, product) | Stage 1 (real ticks 2025Q4 + 2026, default inputs, 100,000) | Stage 2 (modelled ticks 2022-2025) | Verdict |
|---|---|---|---|
| GoldenShot (Adam Hrncir, 185207; same result on M15 and H1) | PASS: +31.7% / 12 months, PF 3.86, 386 trades (32 a month), max equity DD 2.5%, worst day -1.7%, 12 of 12 months positive, win rate 95.6%, one position at a time | PF 0.80 / 1.04 / 1.53 / 2.93 (2022 -3.4%, 2023 +0.5%, 2024 +8.2%, 2025 +24.8%): 3 of 4 years >= 1.0 | CANDIDATE (regime dependent) |
| Broker Gold EA (Jimmy Peter Eriksson, 153540, M30) | PASS but thin: +37%, PF 1.36, 345 trades, max DD about 18%, worst day -2.55%, net / DD 2.0 | PF 1.01 / 1.11 / 1.44 / 1.33 (4 of 4) with DD 7-14% a year | candidate on paper, useless at MT5 broker risk (adds little, raises breach, see PFG_COMBO_OUTPUT.txt) |
| Gold Beaver (177869, M15) | fails the lot-ratio rule (first trade 0.01 then 1.0-1.6 lots: percent-risk sizing, not a martingale as far as the lots show) but +88%, PF 2.66, 106 trades, worst day -7.9%, DD 15-20%, one trade = 26% of the profit | not run | too aggressive and fragile |
| Scraper Gold (90 USD, M15 / H1) | PF 1.65, +24%, but 2025Q4 was -4% (net > 0 in both windows fails) | not run | fail |
| Ghost Scalper (Thomas Christoph Lipka, 189922, H1) | 1,354 trades, PF 1.47 but 2025Q4 negative and 4 concurrent positions | not run | fail |
| Smart Gold Hunter (170050) | 136 trades, tiny lot (0.01): +162 USD, 2025Q4 slightly negative | not run | fail |
| TitanForge (196963, H1) | 2 trades in 12 months (-1,063 USD) | not run | fail |
| Range Breakout EA with Range Filters (122237), Lizard | no trades / not downloaded | - | not tested |

## GoldenShot in detail (the only EA that is both frequent and clean)
Default sizing is 1% risk per trade (fixed 200-pip stop, lot about 0.5 on 100,000); median holding time 6 minutes, 73% longs, 2 trades a day (max 15); the 17 losers lost 11-21 USD/oz, the winners gained a median 1.8 USD/oz: average win +116 USD vs average loss -653 USD (payoff 0.18, break-even win rate 84.9%). Cost stress (extra USD/oz per round trip on top of MT5 broker's spread): +0.3 -> PF 2.56, +0.6 -> PF 1.91 (+20% a year), +1.0 -> PF 1.43, +1.5 -> PF 1.09. Win-rate stress: at 92% the expectation per trade is +55 USD (PF 2.0), at 88% +24 USD (PF 1.3).
Daily correlation with the live pair +0.12 (2 of its 11 losing days coincide with a pair loss). Aligned block bootstrap (forex/early_mt5/ea_research/gs_combo.py, GS_COMBO_OUTPUT.txt; baseline = the pair alone in the same 12-month pool: 50.5% by 30 Nov, 74.2% by 22 Dec): pair + GoldenShot at its default 1% risk, full edge: 79% / 95%, breach 0.1%; half the edge: 64% / 86%; NO edge: 49% / 71% with breach 0.5% (so the downside is bounded in this sample).
Why the numbers must not be taken at face value: (1) the edge is a volatility-regime edge: year by year it grows from -3% (2022) to +25% (2025) and +32% (last 12 months), the same period in which gold's M15 ATR went from 2.1 to 11 USD; (2) the modelled-tick years are unreliable for a 6-minute scalp; (3) the EA was published in 2026 (manual v1.40, 28 Aug 2026), so the last 12 months are very likely inside the author's own optimisation window; the seller's own page asks "is it real or over-fitted?"; (4) tester fills are ideal, a 95% win rate with 1.8 USD winners lives or dies on execution quality; (5) a purchase is required to run it live (249-399 USD; the trader: no payment) and it would then need a forward test on the MT5 broker trial account before touching the test.

---
# ADDENDUM (2026-10-09 23:39): the author's OWN live signal and the reviews overturn the tester numbers for GoldenShot
Read through Comet / the manual / the product page (public): GoldenShot v1.45 (updated 2026-10-05, published 2026-08-28), 10 activations, 2,138 demo downloads, rating 4.42, 33 reviews. Strategy: two market-order strategies, 1) pullback with 200-pip stop / 40-pip target and a trailing stop from 12 pips, 2) momentum with 250 / 50 pips; one position at a time; no Friday entries; entry windows; high-impact USD news pause of 60 minutes before and after (the tester cannot reproduce it); 1% risk per trade by default.
The author's live signal "GoldenShot High Risk" (Vantage live, 0.01 lot, started 2026-08-19, 7 weeks): 31 trades, 27 winners (87.1%), average profit +1.75 USD, average loss -11.63 USD, gross profit 47.20 vs gross loss 46.53, PROFIT FACTOR 1.01, expected payoff +0.02 USD a trade, maximum balance drawdown 11%, 3 trades a week (the tester takes 8 a week). Tester on MT5 broker data over 2025Q4-2026: win rate 95.6%, PF 3.86. If the tester's loss rate (4.4%) were true, 4 or more losers in 31 trades would happen with probability about 4% (small sample, but the direction is clear).
Public reviews (Sep 2026): "few small wins and then ONE big stop loss", "yesterday it hit the stop loss and wiped out last month's profits", "one loss erases the profit of more than 20 orders; I removed it from my real account"; the seller attributes the 29 Sep loss to war news and promises a spike protection.
Reading: the tester shows the same payoff shape (average win 116 USD vs average loss 653 USD at 1% risk) and a higher win rate than the live record; the live record is flat. The tester is the best case, the live signal the reality check. DOWNGRADED from "candidate" to "do not buy"; watch the signal for 12 more weeks (need >= 100 live trades and live PF >= 1.5 before any money).
HFT rule check (MT5 broker: no more than 50% of trades under one minute): 12% of the tester's trades are held under 60 s.
