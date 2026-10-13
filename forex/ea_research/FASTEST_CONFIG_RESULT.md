# Fastest-pass configuration for the live MT5 broker account (2026-10-11; planning simulation, not an edge trial)

Script `fastest_config.py`, output `FASTEST_CONFIG_OUTPUT.txt`. pass70 rules (guard 2,000 a day, counted cap 2,000, breach at -2,500 in a
day or equity 92,000, counted pass lock 8,100, no-hedge), start counted +560 on Mon 2026-10-12, pools MT5 broker (last 12 months, real ticks)
and FT (2022-26), MIX = 50/50. DA2 = index dip add-on (DIP_ADDON_RESULT.md), 1% risk per signal day, intraday lows summed (conservative).

| config | 30 Oct | 30 Nov | 22 Dec | 31 Jan | breach by 31 Jan | median pass |
|---|---|---|---|---|---|---|
| x1.2 (live) | 5.0% | 35.6% | 53.8% | 72.2% | 0.8% | 49 bd (~17 Dec) |
| x1.2 + DA2 | 6.1% | 37.9% | 56.4% | 74.5% | 0.8% | 46 bd |
| **x1.5** | 9.1% | **41.6%** | **58.1%** | 74.1% | **3.4%** | **44 bd (~10 Dec)** |
| x1.5 + DA2 | 10.5% | 42.3% | 57.0% | 70.8% | 11.1% | 44 bd |
| x1.8 | 11.9% | 42.5% | 56.3% | 69.5% | 12.8% | 44 bd |
| x1.8 + DA2 | 13.1% | 41.6% | 53.5% | 63.7% | 23.7% | 47 bd |

## Recommendation: x1.5, guard unchanged, no add-on
x1.5 is the fastest configuration that keeps the breach small: +6 points by 30 Nov and +4 by 22 Dec over x1.2 for +2.6 points of breach.
x1.8 buys 1 more point by 30 Nov for 4x the breach and is worse by 22 Dec. DA2 on top of x1.5 or x1.8 pushes days past the 2,500 line
(breach 11-24%); DA2 only belongs next to x1.2. Lots: ManualSDB InpLots 0.14 -> 0.18, XAU5 Entry_Amount 0.05 -> 0.06; every guard input stays.
Risks stated: SDB risk per trade goes from about 1.14% to about 1.4% of the account (above MT5 broker's "1% per trade idea" guideline);
the worst historical weekend gap (-77 USD/oz) on a full long stack at x1.5 (0.18 + 3 x 0.06 = 36 oz) is about -2,770 USD, above the
2,500 line: close the XAU5 positions by hand on Friday evening while at x1.5 (do not reopen them: close-and-reopen is an MT5 broker red flag).
Preset files for x1.5 were NOT written: the permission classifier blocks changes to live trading configuration; the trader changes the two inputs by hand.
