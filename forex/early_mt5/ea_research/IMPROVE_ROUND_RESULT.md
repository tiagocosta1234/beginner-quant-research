# Improvement round (2026-10-12): all legs together, performance throttle

Pre-registration: PREREG_IMPROVE.md. Planning simulations on the installed system, fresh account.

## IM1 all small legs together (MIX, pass within 22 / 44 / 60 business days | breach by 60)
| Configuration | 22 | 44 | 60 | breach | vs A at 44 bd |
|---|---|---|---|---|---|
| A installed | 17.4% | 47.5% | 61.6% | 2.2% | – |
| B + RSI(2) leg | 17.9% | 48.8% | 63.2% | 2.0% | +1.3 |
| C + strategy 3 (0.2 NQ, 2 pt slippage) | 19.5% | 49.5% | 63.3% | 3.5% | +2.0 |
| D + RSI(2) + strategy 3 | 19.0% | 48.2% | 62.0% | 4.4% | +0.7 |
| E + both + ManualDip x2 | 19.1% | 47.4% | 60.9% | 4.9% | -0.1 |
Not accepted (needs +3 at 44 bd with the breach not more than 1 point higher): the best single leg is +2.0 with 1.3 more breach; the legs overlap (daily capital, guard, shared days) so stacking them gives less than their sum.

## IM2 performance throttle (replay from every start day; pass / breach within 22 and 44 business days)
| Pool | Rule | 22 bd | 44 bd |
|---|---|---|---|
| FT 2022-26 | unthrottled x1.5 | 10.7 / 0.1% | 30.1 / 1.4% |
| FT | T1 x1.5 ON, x1.0 OFF | 10.1 / 0.0% | 29.7 / **0.0%** |
| FT | T2 x2.0 ON, x1.0 OFF | 11.9 / 0.2% | **34.9** / 0.2% |
| MT5 broker 12 months | unthrottled | 35.7 / 0.5% | 79.9 / 0.6% |
| MT5 broker | T1 | 35.7 / 0.5% | 79.9 / 0.6% |
| MT5 broker | T2 | 23.0 / 1.5% | **65.5 / 1.7%** |
Not accepted (T2 loses 14 points in the good regime; T1 does not raise the pass rate). T1 is a free safety: it costs 0.4 points of passing and removes the breaches in the bad regime (1.4% -> 0.0%); the account is ON today, so it would not change anything now.
