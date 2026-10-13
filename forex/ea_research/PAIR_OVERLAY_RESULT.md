# Regime overlay on the pair's size: result (2026-10-09 ~10:35 local)

Pre-registration `PREREG_PAIR_OVERLAY.md` (written 10:32, before the run), code `pair_overlay.py`, full output `PAIR_OVERLAY_OUTPUT.txt`, ledger rows O1 / O2 (37 of 40 registered trials). MT5 broker-based 2022-26 series, both daily caps with carry-over (minute-level), test starts every business day, MT5 broker Pro rules.

## Verdict: neither overlay meets the acceptance test; the idea is closed
| sizing | ALL 2022-26 pass / breach / median bd / <= 42 / <= 62 bd | PRE-BOOM 2022-24 pass / breach / median / <= 62 bd |
|---|---|---|
| constant 1.0 (locked) | 93% / 50 (4%) / 69 / 26% / 41% | 89% / 50 (6%) / 134 / 22% |
| constant 1.2 | 93% / 63 (5%) / 47 / 41% / 59% | 89% / 57 (7%) / 59 / 46% |
| O1 gold above its 100-day average -> 1.2, else 0.6 | 92% / 63 (5%) / 66 / 27% / 44% | 89% / 57 (7%) / 105 / 28% |
| O2 pair equity above its 20-day average -> 1.2, else 0.6 | 92% / 79 (6%) / 58 / 33% / 49% | 86% / 73 (9%) / 80 / 33% |
Registered bar: versus constant 1.0 an overlay needs +10 points on P(pass within 62 bd) in BOTH pools with no more breaches; versus constant 1.2 fewer breaches with at most 5 points less speed. O1 gains 3 / 6 points and has MORE breaches than 1.0 (63 vs 50, 57 vs 50), exactly the breaches of constant 1.2; O2 gains 8 / 11 points but has the most breaches (79, 73).
## Reading
The breach episodes (June 2022, April-May 2023) happen while the filters read "good" (gold above its 100-day average; the pair's own curve above its 20-day average): the slide to the 8% floor comes from a trend that fails after it was in place, which neither filter can see in advance. What does move the numbers is plain size: from 1.0 to 1.2 the median pass falls from 69 to 47 business days and the share passing within 62 rises from 41% to 59% at the price of 13 more breached starts (5% vs 4%); the five-year and the tick-level 12-month windows both put the breach cost of 1.2x at about 1-4 percentage points.
