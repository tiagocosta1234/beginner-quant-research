# ICT3_RESULT - the remaining ICT concepts as complete strategies on every MT5 broker symbol (2026-10-15, local clock 18:26)
Pre-registration PREREG_ICT3.md (commit 82024ed4). Code ict3.py, output ICT3_OUTPUT.txt, tables D:/finance/si_ledgers/ICT3_*. Dry run: truncation identical (5,805 trades).

## Verdict: 0 of 8,454 cells, 0 of 1,018 pools; no class pick is positive in 2025 and 2026, so no out-of-time check was triggered. The ICT family is closed for mechanical rules.
Models: Judas swing / PO3 around the midnight open, silver bullet FVG toward the draw on liquidity, OTE (70.5% retracement after sweep + MSS), breaker block, turtle soup (20-day range), CBDR 2-SD fade; filters none / midnight open / draw on liquidity; targets 1R / 2R / 3R / liquidity / 15:55 NY; 413,710 rule trades with a matched random trade each.
1. **Every model loses with every target** (all symbols 2022-25): Judas -0.09 R a trade, breaker -0.09..-0.11, OTE -0.10..-0.17, silver bullet to DOL -0.13..-0.15, turtle soup -0.12..-0.13, CBDR -0.06..-0.11. Every year 2022-2026 negative (-0.06 to -0.14).
2. **Against the matched random trade:** Judas and turtle soup are no better than random; CBDR is WORSE than random at 2R+ (-0.07..-0.11 vs about 0); OTE / breaker / silver bullet look better than their twin only because a limit fills at the level while the twin pays the spread at market (the same artefact as ICT_GRID).
3. **Filters and killzones:** midnight-open -0.121, draw on liquidity -0.110, none -0.111; NY AM -0.081 is the least bad killzone, NY PM -0.153 the worst.
4. **Cells:** highest t 3.19 (NSDQ OTE NY AM DOL 1R: +0.320 / +0.103 / **-0.125**); matched null 2.77; bar 4.67.
5. **Walk-forward (best of 240 per symbol on 2022-24):** DEV +0.325 -> 2025 **-0.237** -> 2026 **-0.180** R; 1 of 46 positive in both. Every class's DEV-best rule is negative in 2025.

## Reading for the trader
With ICT_GRID and the earlier ICT rounds, about 33,000 symbol-level ICT strategies have now been tested on MT5 broker data with real spreads: every concept loses in every year, and the best combination chosen on 2022-24 loses afterwards. There is no mechanical ICT strategy on these markets. The only remaining way to test ICT is the trader's own written model or a log of his real trades.

Timestamp note: the stamps of BEST3M_CYCLE, ORB11_ICTSTOP, ICT_GRID and four day-log / ledger lines were first written from an estimate and were corrected to the commit times (17:45, 17:48, 17:54, 17:57, 18:06, 18:16).
