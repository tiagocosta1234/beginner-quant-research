# Pre-registration: the US RSI(2) dips as a third leg next to the pair and ManualDip (written 2026-10-12, before the leg was combined)

the trader: "(original wording omitted)". Question: does adding the confirmed daily RSI(2) dip rule (SP, NSDQ, DOW; EV1) to the live system (pair x1.5 + ManualDip 500) raise P(pass)? Same machinery as `final_system_stats.py` / `pass_curve.py`: pass70 rules, +560 counted on 2026-10-12, guard 1,500, CPI news-flat, MIX = 50/50 of the MT5 broker 12-month and FT 2022-26 pools.
Leg construction (as ManualDip in `dip_addon.py`): signals EV1 (Wilder RSI(2) < 10, close > SMA(200), 15:59 New York; exit close > SMA(5) OR RSI(2) > 70 OR 5 days), long only, entry at the 15:59 ask, exit at the bid. Day risk budget 500 USD split across indices that signal the same day, quantity = budget / (3 x sigma60 x price), server-side stop at 3 sigma60 below entry (RSI(2) has no stop in the literature; this mirrors ManualDip and is a risk-control choice), P&L x0.75 as for ManualDip (the real-tick tester showed about that haircut). Daily series (V, B, Hi) from `dip_addon.day_arrays`, added to the live series through `combo_grid.add_dip` (the guard also closes the leg).
Configs: (0) live = pair + ManualDip 500; (1) + RSI(2) leg 500; (2) + RSI(2) leg 1000.

## Acceptance (planning test, config 1 is the proposal)
MIX P(pass) by 22 Dec at least +2.0 points over (0), by 30 Nov not lower, AND breach by 31 Jan not higher by more than 0.3 points. Reported: also 31 Jan, the leg's own stats and its daily correlation with the pair V and with the ManualDip leg.
Caveat fixed in advance: the leg's rule was confirmed on MT5 broker data (2022-26 incl. hold-out), the same history the pools are drawn from; this is a sizing/planning test, not out-of-sample evidence. Nothing goes live from this round; the MT5 broker tester run and build come next if it passes.

## Honest prior
Low impact: about 20 entry days a year and 52% of them coincide with a ManualDip day, so it mostly doubles up on days ManualDip already trades. ManualDip itself added only +2 to +2.5 points. Expect +1 or less.
