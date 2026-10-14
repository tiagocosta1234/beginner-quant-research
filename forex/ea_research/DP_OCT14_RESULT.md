# Dynamic sizing from the live state, 2026-10-14 (the trader: "we have to pass the account this month"; chose "maximise the 30 Oct chance")
Scripts `dp_oct14.py` (all multipliers), `dp_oct14_capped.py` (<= x2.5), outputs `DP_OCT14_OUTPUT.txt`, `DP_OCT14_CAPPED_OUTPUT.txt`; card `forex/mt5_SIZING_CARD_OCT.md`. State from `live_state.py` (read-only): balance 99,625.70, equity 99,843 (open XAU5 short 0.08, floating +218, not counted), counted profit -374.30; 12 trading days to Fri 30 Oct, then x1.2 to 22 Dec (49 days).
| policy | pass by 30 Oct (12M / 2022-26) | breach by 30 Oct | pass / breach by 22 Dec |
|---|---|---|---|
| constant x1.2 | 1.3% (2.5 / 0.2) | 0.0% | 47.8% / 0.7% |
| constant x1.8 | 4.7% (7.2 / 2.2) | 3.0% | 52.1% / 11.6% |
| constant x2.5 | 6.5% (8.9 / 4.2) | 7.0% | 47.2% / 24.5% |
| constant x3.5 / x5.0 | 5.6% / 5.6% | 14.2% / 26.1% | 29.5% / 21.0% |
| DP, all multipliers, lambda 0.3 / 1.0 | 6.8% (9.1 / 4.4) / 6.0% | 3.3% / 1.4% | 44.2% / 4.7% ; 45.9% / 2.5% |
| DP capped at x2.5, lambda 0.3 (the card) | 6.1% (8.4 / 3.9) | 2.7% | 45.2% / 4.0% |
| DP capped at x2.5, lambda 1.0 | 5.4% (7.9 / 2.9) | 1.2% | 46.8% / 2.2% |
Findings: (1) from today's state the October chance is about 5-7% for any legitimate sizing, down from 13% ceiling on 12 Oct because counted profit is -374 and three days are gone; (2) the best dynamic table adds only about 1-2 points over constant x1.8-2.5 but cuts breach to about 2.7% (constant x2.5: 7.0%); (3) x3.5 / x5.0 do not help (the 2,000-a-day counted cap and the guard), and the unconstrained DP's x5 on the last day carries weekend-gap risk, so the card is capped at x2.5; (4) the December path stays about 45%.
Acceptance rule from the plan: the card does not beat constant x2.0 (about 5.5%) by a full point on pass chance (+0.6) but halves its breach (2.7% vs about 4.5%); accepted on that basis, stated openly.
No new strategy was added: every EURUSD / FX / multi-asset test this week found no edge.
