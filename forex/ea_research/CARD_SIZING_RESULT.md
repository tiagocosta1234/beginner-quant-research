# The daily card on the MT5 broker account from today: pass vs breach by risk per trade (2026-10-15 13:37, local clock)
Script `card_sizing.py`, rows `D:\finance\si_ledgers\CARD_SIZING.csv`. Start: balance 97,708.08, counted -2,291.92 (pass needs +10,291.92). Day structure as in `CARD_EXPECTATIONS.md` (gold London, then Nasdaq New York if the day is not done); MT5 broker rules: +2,000 counted a day at most, -2,500 in a day = breach (approximated by the closed day), static floor 92,000. Block bootstrap of 5-day blocks, 20,000 paths per cell, from the card's own day series (2025-26 pool or 2022-26 pool). Trading days from Fri 16 Oct: 11 to 30 Oct, 48 to 22 Dec, 115 to 31 Mar 2027.
| version, pool | risk / trade | pass 30 Oct | pass 22 Dec (breach) | pass 31 Mar 27 (breach) |
|---|---|---|---|---|
| Nasdaq both sides, 2022-26 | $250 | 0% | 0.1% (3.3%) | 5.5% (12.5%) |
| | $500 | 0% | 11.8% (24.6%) | 36.5% (38.3%) |
| | $1,000 | 5.3% (breach 24%) | 34.8% (51.5%) | 42.0% (57.2%) |
| Nasdaq both sides, 2025-26 | $500 | 0% | 8.1% (25.0%) | 28.2% (42.2%) |
| | $1,000 | 4.0% (25%) | 29.7% (56.1%) | 37.0% (62.0%) |
| Nasdaq trend-only, 2022-26 | $500 | 0% | 8.3% (18.6%) | 32.3% (32.8%) |
| | $1,000 | 3.9% (19%) | 33.5% (47.0%) | 44.4% (53.7%) |
| Nasdaq trend-only, 2025-26 | $500 | 0% | 4.9% (16.3%) | 24.0% (32.4%) |
| | $1,000 | 2.6% (16%) | 28.6% (45.0%) | 42.1% (54.5%) |
$150 a trade: 0% pass at every horizon, breach under 2%.

Reading: at every size and horizon the card's chance of breaching is larger than its chance of passing (the one tie: trend-only $500 by March, 32% / 33%). By 30 Oct no size gives more than about 5% (with 16-25% breach). These series include the years the legs were chosen from, so the real odds are lower. For comparison, the gold EA pair the trader switched off on 15 Oct was simulated at about 42% by 30 Nov with about 2% breach (`ABS_STOP_2000_OUTPUT.txt`, in-sample and flattered by the 2025-26 gold trend).
