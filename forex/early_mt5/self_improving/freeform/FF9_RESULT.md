# Free-form trader v5 (macro calendar + intrabar structure + MT5 broker environment): result (2026-10-13)

Pre-registration: PREREG_V5_PROP.md (plus everything in PREREG_FREEFORM.md). Code: ff5_data.py, acct_env.py, ff5_agent.py, env_check.py. Ledgers (outside git): D:\finance\si_ledgers\FF9_*. 2026 never loaded.

## What was added
- 19 new causal features (41 in total): macro event calendar (hours until / since CPI, NFP, FOMC and any), daily macro regime with a one-day lag (VIX rank and 5-day change, 10y-2y slope change, dollar index change), intrabar structure from the MT5 broker M1 bid/ask OHLC (bar range z, close location, shadows, range vol vs close vol, spread variability, activity).
- Real ticks exist only from 2025-10-01 (about one year, MT5 cache and XAUUSD tick_volume file), so none of windows A (2022-01..2023-06) and B (2023-07..2024-12) can use them; they are reserved for the MT5 real-tick tester of any survivor.
- The MT5 broker Pro 100K environment: daily loss 2.5% on equity, floor 92,000, 2,000/day counted cap, target 8,000, our 1,500 day guard, swap-free, stop at 2 hourly-vol units of the holding period, size from USD 500 risk with a USD 1,000 total open stop-risk cap, 0.2 bp slippage, entry at the first signal when flat, simulated with the existing pass70 simulator. The agent's elites and operator credit are ranked by P(pass by 44 bd) - 3 x P(breach) on window A.
- Environment sanity check found, before any training, that sizing USD 500 per trade without a total risk budget made the (statistically positive) R7 rule an account killer (breach 33-43%) because FX signals fire in many correlated pairs at once; fixed with the USD 1,000 open-risk cap. Under the capped environment R7 is harmless but useless: add-on to the installed system delta P(pass) -0.7 points, delta breach +1.7 points.

## Calibration (gate before the real run): PASSED
Never-seen placebo worlds 21, 22, 23 (calendar and daily macro kept real, bars shuffled), 40,000 rules each, environment scoring on: 0 S1 and 0 S2 in every world.

## Real run (100 generations): 148,966 rules explored
| | value |
|---|---|
| rules meeting the A floors | 39,116 |
| best A z | 4.52 |
| B tests (promoted) | 9,595 |
| best B z (min p) | 3.44 (5.8e-4) |
| BH q = 0.05 needs p <= | 5.2e-6 |
| S1 | **0** |
| S2 | **0** |
| rules scored in the environment on A | 2,366 |
| best environment score on A | 0.084 |
| rules with P(pass by 44 bd) > 10% on A | 0 (best 9.6%, breach 1.8%) |
Two thirds of the best 500 B rules use at least one of the new features, so the agent did explore the macro and intrabar information; none of it survives the calibrated test. The smallest B p (5.8e-4) is what the best of about 9,600 null tests gives (about 1e-4). The best rule (idx short, H=4, run and range-position conditions; net +9.6 bp on 168 trades) is a chance-level candidate and is not pursued.

## Verdict
With macro event timing, a daily macro regime and intrabar structure added to price and spread, in the MT5 broker account environment, no rule among 149,000 explored survives the calibrated test; the environment finds none that would lift P(pass) (best standalone on A 9.6%, far from the installed system). The installed system stays on the account. 2026 (HOLD) not read; nothing reached S3, the add-on test (stage E) or the tester.

## What this leaves open
1. Information the data does not have: consensus forecasts / event surprises (no data), real ticks before 2025-10, order flow, positioning beyond the COT folder, news text.
2. A layer on the installed system instead of new rules: regime switches of its size using the macro regime (the pair and ManualDip are the part that works); testable in the same environment.
3. Waiting for the live account: the evaluation clock keeps running with the installed system.
