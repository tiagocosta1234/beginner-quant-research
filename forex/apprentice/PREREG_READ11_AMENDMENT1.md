# PREREG_READ11 Amendment 1: an always-long baseline in the bar

Written 25 Oct 2026 ~23:5x-00:0x local (local clock), during training after R011, BEFORE the test pool is drawn (READ11 not frozen, `state_r11x` empty).

## Why
- Gold rose through 2023 (the training year) and through every test window (2019 H2, Sep-Dec 2024, 2025).
- The excess over the mirror does not control for that drift: a read that mostly buys wins against its own short mirror without any skill. In training so far, every win was a long in an uptrend.

## Change
- New baseline, scored on every test day: **always long, signal 08:02, the same 1:1 bracket (X from `bracket11` at 08:02)**.
- **Supported now also needs: read mean R per trade > always-long mean R per trade** (both after costs), in addition to excess >= +0.10, P <= 0.03, mean R > 0 and n >= 40.
- Also reported (no bar): the read's longs and shorts separately, each with its mirror excess.
