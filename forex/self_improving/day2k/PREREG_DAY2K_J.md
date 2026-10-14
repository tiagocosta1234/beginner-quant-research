# PREREG DAY2K-J - rank every MT5 broker symbol and go long the one most likely to go up (written 2026-10-14, the trader: "analyze every symbol on the MT5 broker list and go long on the one with the better chance to go up")

Long-only cross-sectional pick: each day rank the 34 liquid MT5 broker (spread/ATR20 <= 2%, the DAY2K-G/H universe) by a score and buy the top one. The test is whether the top pick goes up MORE than the average market on the same day, because most markets drift up over 2021-25 (a long-only rule can look good just from drift).

## Rankers (6), horizons (3), trials (18)
Rankers: (1) pooled logistic and (2) pooled boosting P(up) from DAY2K-H (walk-forward, features as in that round); (3-5) trend: 20, 60, 120-day change / ATR20; (6) 5-day reversal: -(5-day change) / ATR20. Entry at the T+60 bar open on the ask; horizons: H1 = T 10:05 to 21:55 same day; H2 = T 16:35 to 21:55 same day; H3 = T 10:05 to the 21:55 bar open of the 5th trading day (exit on the bid). 6 x 3 = 18 trials (the P(up) rankers are only defined from 2022-12; the simple rankers are also scored only from 2022-12 so all cells share one window).
Net return in ATR20 units = (exit bid - entry ask) / ATR20.

## Acceptance (Bonferroni 18, one-sided 5%: z 2.91)
DEV' (2022-12..2024-12): mean net return of the top pick > 0 with block-t >= 2.91 (5-day blocks, 10-day for H3) AND the paired difference top-pick minus equal-weight-all-markets (same days, same costs) has block-t >= 2.0; VAL 2025: mean net > 0 with block-t >= 1.65 and the paired difference > 0. HOLD 2026 sealed.
Reported with every cell: win share (top pick closed higher than it was bought), mean net return of buying every market, of a random market, and the share of picks by class and by market.

## Gates
Positive control: picking the realised best market must give a large positive mean. Placebo worlds: scores shuffled across markets within each day (seeds 181-183) must give 0 survivors. Truncation: scores come from the tested DAY2K-B/H code.

## Honest prior
Cross-sectional momentum is documented within asset classes over weeks to months, not across a mixed universe at day to week horizons; round G found the strongest-trend pick worse than a random pick with the same mix. P(survivor) under 5%. This test cannot change the account: the live pair stays, and nothing here places an order.

## Dry-run record (2026-10-14, before any cell result)
Market-day rows with a net return (kept 34 markets): H1 35,061, H2 35,038, H3 34,639. Mean net return of buying every market in ATR units: H1 -0.0035, H2 -0.0057, H3 +0.051 (the 5-day drift); mean spread cost 0.011 ATR. No trial or threshold changed.
