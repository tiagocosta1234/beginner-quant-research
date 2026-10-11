# Fastest-pass configuration after MT5 broker's reply (2026-10-11; planning simulation)

Script `fastest_config2.py`, output `FASTEST_CONFIG2_OUTPUT.txt`; rules and start as `FASTEST_CONFIG_RESULT.md`. MT5 broker's written reply
(`forex/early_mt5/mt5_SUPPORT_REPLY_4.md`): opposite positions inside one account are not prohibited; no strict 1%-per-trade rule.

| config | 30 Oct | 30 Nov | 22 Dec | 31 Jan | breach by 31 Jan | median pass |
|---|---|---|---|---|---|---|
| x1.2, no-hedge ON (live) | 5.3% | 35.7% | 54.3% | 72.5% | 0.7% | 48 bd |
| x1.2, no-hedge OFF | 6.3% | 39.4% | 57.8% | 75.4% | 0.6% | 45 bd |
| x1.5, no-hedge ON | 9.1% | 41.3% | 57.7% | 73.8% | 3.5% | 44 bd |
| **x1.5, no-hedge OFF** | **10.3%** | **44.1%** | **61.2%** | **77.3%** | **3.0%** | **41 bd (~7 Dec)** |
| x1.5, OFF, XAU5 flat on weekends | 9.0% | 41.0% | 57.5% | 73.9% | 2.8% | 44 bd |
| x1.8, no-hedge OFF | 13.5% | 46.8% | 60.9% | 73.4% | 11.4% | 39 bd |

## Recommendation: x1.5 with the no-hedge guard OFF
Fastest configuration with a small breach: +8 points by 30 Nov and +7 by 22 Dec over the live setup, breach 3.0%. Turning the no-hedge
rule off also LOWERS breach (opposite positions offset each other). x1.8 gains 2.7 points by 30 Nov for almost 4x the breach and is
not better by 22 Dec. Flattening XAU5 on weekends costs about 3 points for 0.2 points less breach in the history (the -77 USD/oz worst gap
is inside the sample); keep weekends as they are unless a major weekend event is scheduled.
Inputs the trader changes by hand on BOTH PCs: ManualSDB InpLots 0.14 -> 0.18 and InpGuardNoHedge true -> false; XAU5 Entry_Amount 0.05 -> 0.06.
Everything else (day loss stop 2.0%, floor 6.5%, counted pass lock) stays.

## Addendum 2026-10-11: no day may lose more than 2,000 (the trader)
`daystop_under_2000.py` (outputs `DAYSTOP_UNDER_2000_OUTPUT.txt`, `DAYSTOP_NEWS_OUTPUT.txt`), x1.5, no-hedge off, M1-close guard model:
| guard day stop | worst day MT5 broker 12m / 2022-26 | days below -2,000 | MIX 30 Nov / 22 Dec | breach |
|---|---|---|---|---|
| 2.0% (2,000) | -2,306 / -2,215 | 12 / 21 | 44.9% / 61.7% | 2.1% |
| 1.7% (1,700) | -2,112 / -1,942 | 1 / 0 | 43.0% / 60.0% | 2.0% |
| 1.5% (1,500) | -2,112 / -1,760 | 1 / 0 | 41.2% / 57.7% | 1.9% |
| 1.7% + flat 2 min before CPI / NFP / FOMC | -1,813 / -1,937 | 0 / 0 | 38.2% / 55.5% | 1.5% |
The one remaining day (2026-07-14, -2,112) is the CPI release: gold jumped 44 USD in one minute at 08:30 NY; no day stop can catch it.
The guard overshoots 2,000 because it closes after the move (fills a minute late in this model; a per-tick guard does better but gaps and
news spikes can still jump it). No setting can GUARANTEE a day above -2,000 (a weekend gap larger than history would jump any stop).
Weekend flattening does not help this target (the worst days are not gaps) and costs 3-10 points.

## Addendum 2: losses must be cut at 1,900 (the trader 2026-10-11), output `DAYSTOP_1900_OUTPUT.txt`
| setting | worst day MT5 broker 12m / 2022-26 | days below -1,900 | MIX 30 Nov / 22 Dec | breach |
|---|---|---|---|---|
| trigger at 1.9% | -2,112 / -2,215 | 13 / 24 | 44.1% / 61.0% | 2.0% |
| trigger at 1.5% | -2,112 / -1,760 | 1 / 0 | 41.1% / 57.4% | 1.9% |
| trigger at 1.4% | -2,112 / -1,730 | 1 / 0 | 40.2% / 57.0% | 1.7% |
| trigger 1.5% + flat before CPI/NFP/FOMC | -1,813 / -1,654 | 0 / 0 | 37.6% / 54.3% | 1.2% |
A trigger AT 1,900 does not keep losses at 1,900 (fills overshoot by 100-300). To finish days at or above -1,900, the trigger has to be 1.5%.
