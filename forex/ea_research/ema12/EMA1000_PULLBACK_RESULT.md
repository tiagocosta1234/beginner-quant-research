# EMA1000 with a pullback limit order (run 20 Oct 2026 14:38-15:10, main PC, local clock)

the trader: "test the pullback limit order". Pre-registration `PREREG_EMA1000_PULLBACK.md` (sha256 58f0f9c5b07fce07c2945e409c62113b3d64cbf9495136344613450fa66b712f, 14:35:56). Engine `ema1000_pullback.py`, checks `EMA1000_PULLBACK_DRYRUN_OUTPUT.txt` (813,196 invariant checks, 0 violations; truncation test 256 fills, 0 mismatches). Output `EMA1000_PULLBACK_OUTPUT.txt`, `EMA1000_PULLBACK_TRIALS.csv`, `EMA1000_PULLBACK_MARKETS.csv`. Same 1,000 variants, 46 MT5 broker, DEV 2022-24 / VAL 2025; nothing after 2025-12-31 loaded.

## Result: 0 candidates; a pullback does not help, with or without spread
Median over the 1,000 variants, DEV mean R per filled trade (rule / inverted side), with the fill rate:

| Entry | No spread | Real bid / ask | Fill (no spread / real) |
|---|---|---|---|
| Market order (EMA1000, NOCOST Z) | -0.005 / -0.008 | -0.180 (market, real) | 100% |
| Limit at the signal close (NOCOST L / Q) | -0.013 / -0.015 | -0.139 / -0.143 | 98% / 81% |
| Pullback 0.25 ATR | -0.021 / -0.028 | -0.155 / -0.158 | 87% / 76% |
| Pullback 0.5 ATR | -0.021 / -0.026 | -0.152 / -0.151 | 76% / 65% |
| Pullback 1.0 ATR | -0.019 / -0.019 | -0.130 / -0.128 | 55% / 47% |
| Retest of the EMA | -0.019 / -0.023 | -0.143 / -0.146 | 73% / 62% |

- **No variant is positive on real quotes** (best -0.022 inverted at 1.0 ATR; best rule -0.036), and no market has a positive median on real quotes at any depth. 0 candidates in all 16 cases (bar t >= 4.19).
- **No spread:** the best variant is +0.039 R (inverted, 1.0 ATR, t +2.47, VAL -0.030): noise among 1,000 variants; the rule side peaks at t +0.93 (1.0 ATR). VAL 2025 is negative for every depth.
- **A pullback makes the entry price better but the trade worse.** Fill rates fall to 47-87% and the per-trade result is slightly worse than a market order at zero spread (-0.02 against -0.005): the limit fills most often when the move has turned against the trade (adverse selection), and my convention that the target does not count in the fill minute removes some wins. The deeper pullback loses less per filled trade on real quotes only because it saves more spread and fills less; per signal it is -0.06 R (1.0 ATR), still negative.
- **Direction skill (rule minus inverted) / 2:** +0.002 R at most, 0.000 at 1.0 ATR; 49-66% of variants above zero.
- **No spread, a few markets are slightly positive:** EURCAD and ASX at 0.25 ATR, five FX crosses at 1.0 ATR (CHFJPY, NZDCHF, EURCAD, AUDUSD, GBPUSD); none survives the spread.

## What it means
- The 12 EMA cross rule has nothing to sell before costs and a pullback entry does not turn that around: with limit entries of five kinds (signal close, 0.25 / 0.5 / 1.0 ATR, EMA retest), zero or real spread, rule or inverted side, 1,000 variants and 46 markets, 0 candidates.
- Mechanical question closed under every fill model tried (3 fill models in NOCOST + 4 pullback depths). The 2026 hold-out stays sealed; nothing goes near the account.
- Whatever the trader adds by hand is not a pullback or a fill trick. The open test is the blind replay (batch 2) and the forward log.
