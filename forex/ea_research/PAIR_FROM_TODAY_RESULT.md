# The switched-off gold EA pair, re-simulated from today's account state (2026-10-15 14:03, local clock)
Script pair_from_today.py (machinery of combo_grid.py / pass70.py: block bootstrap, 20,000 paths per pool, 50/50 MIX of the MT5 broker last-12-months pool and the FT 2022-26 pool; MT5 broker rules: +2,000 counted a day, -2,500 a day = breach, floor 92,000, pass lock). Start: balance 97,708.08, counted -2,291.92, first day Fri 16 Oct; 11 / 32 / 48 / 76 trading days to 30 Oct / 30 Nov / 22 Dec / 31 Jan.
| config | 30 Oct | 30 Nov | 22 Dec | 31 Jan 2027 |
|---|---|---|---|---|
| final plan of 11 Oct: ManualSDB 0.18 + XAU5 0.06 (x1.5), guard day stop 1,500, CPI news flat, ManualDip 500 | 0.3% (breach 0.7%) | 18.0% (4.3%) | 36.5% (6.2%) | 58.8% (8.1%) |
|   of which MT5 broker-12-month pool / FT 2022-26 pool | 1% / 0% | 29% / 7% | 55% / 18% | 80% / 37% |
| x1.2 pair only (0.14 + 0.05), day stop 1,500 | 0.1% (0.2%) | 12.1% (1.9%) | 28.9% (3.0%) | 53.4% (4.1%) |
For comparison, the daily breakout card from the same start (CARD_SIZING_RESULT.md): 00 a trade 5-12% by 22 Dec with 16-25% breach; ,000 a trade 29-35% by 22 Dec with 45-56% breach.

Reading: from today, nothing passes by 30 Oct. The EA pair's chance of passing is several times its chance of breaching at every horizon; the card's breach chance is larger than its pass chance at every size. Caveats that must travel with these numbers: the pair's history is in-sample and flattered by the 2025-26 gold trend (ManualSDB was found by a 2-million-candidate search; XAU5 is a trend follower); in the 2022-26 pool alone the pair reaches only 18% by 22 Dec. Restarting the EAs is the trader's decision and his hands-on step (Claude does not arm Algo Trading or attach EAs).
