# ORB trend-direction breakouts in 2026 (HOLD-OUT OPENED at the trader's request, exploratory) - 2026-10-15 ~11:00 local
the trader: "for the whole 2026 risking 1000$ per trade, what's the equity curve on each symbol?" The ORB-REFINE cells did NOT pass development, so under the protocol the 2026 hold-out was not theirs to open; it was opened on request and is now SPENT for this breakout family (no clean confirmation left on MT5 broker data). Script `orb_trend_2026.py` (run `python forex/ea_research/orb_trend_2026.py`; uses `orb_refine.trades`, data 2026-01-02..2026-10-02), trades `D:\finance\si_ledgers\ORB_TREND_2026_<MKT>.parquet`, chart `D:\finance\scratch\charts\ORB_TREND_2026.png`.

| $1,000 risk per trade | trades | win | avg R | total | max drawdown | longest losing streak | positive months |
|---|---|---|---|---|---|---|---|
| Gold, trend-direction only | 93 | 32% | -0.098 | -9,141 | -15,458 | 8 | 4/9 |
| Gold, card as is (all breakouts) | 175 | 33% | -0.115 | -20,150 | -23,909 | 7 | 4/10 |
| Nasdaq, trend-direction only | 92 | 41% | +0.082 | +7,528 | -12,000 | 12 | 6/10 |
| Nasdaq, card as is | 189 | 38% | +0.017 | +3,197 | -18,000 | 10 | 6/10 |
| Both, trend-direction only | 185 | | | -1,613 | -15,898 | | (worst day -2,129) |

Months (trend-direction): gold Jan -5,783, Feb -4,000, Mar +742, Apr +1,793, May -6,000, Jun -210, Jul -1,911, Aug +2,227, Sep +4,000; Nasdaq Jan +4,664, Feb +3,479, Mar -12,000, Apr +5,000, May +6,851, Jun +1,929, Jul -2,045, Aug -346, Sep +996, Oct -1,000.

Reading: the Nasdaq trend-direction lead held its sign in 2026 (+0.08 R a trade, the third positive period in a row: 2022-24 +0.185, 2025 +0.100), the gold breakout lost in 2026 in both forms (-0.10 / -0.12 R). At $1,000 risk per trade every curve has a drawdown of $12,000-24,000, larger than the MT5 broker account's whole static buffer (8,000; 5,708 left on 2026-10-15): March 2026 alone was 12 Nasdaq losses in a row (-$12,000). Consequences for the card: the gold leg has no support (2022-24 zero, 2026 negative); the Nasdaq leg is the only one worth keeping, and only at a size whose worst historical streak fits the floor.
