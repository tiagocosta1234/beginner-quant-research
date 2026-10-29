# The USDJPY London breakout on the MT5 broker account from today, alone and next to the gold EA pair (2026-10-15 14:19, local clock)
Scripts `usdjpy_mt5sim.py` (alone; table `data/si_ledgers/USDJPY_MT5SIM.csv`) and `pair_plus_usdjpy.py` (with the pair; machinery of `pair_from_today.py`). Start: balance 97,708.08, counted -2,291.92, first day Fri 16 Oct. Rules of the leg = PRESAMPLE L1 (box 08:00-08:30 London, OCO stop orders until 11:00, stop at the other side of the box, no target, exit 17:00 London); it fills on about 98% of days.

**Alone** (block bootstrap; pass % / breach %):
| risk a trade | 22 Dec | 31 Mar 2027 | 30 Jun 2027 |
|---|---|---|---|
| $150 | 0 / 0 | 1-5 / 0.4-1.2 | 7-20 / 1-3 |
| $250 | 1 / 1-2 | 10-18 / 6-12 | 22-39 / 8-18 |
| $400 | 4-5 / 12-18 | 16-26 / 26-39 | 25-41 / 32-49 |
| $1,000 | 2-3 / 86 | 3 / 96 | 3 / 97 |
(ranges = MT5 broker 2022-26 pool to HistData 2020-21 pool.) Its long losing stretches (-81 R in 2023) do not fit the 5,708 buffer at any size that would pass quickly: alone it is not a way to pass.

**Next to the gold EA pair** (MIX of the pair's MT5 broker-12-month and FT 2022-26 pools; USDJPY days aligned by date; daily correlation with the pair -0.04 / -0.00; a USDJPY trade day counted at -1R intraday, conservative):
| config | 30 Nov | 22 Dec | 31 Jan 2027 |
|---|---|---|---|
| pair x1.2 | 12.2% (breach 2.0%) | 29.1% (3.0%) | 53.2% (4.1%) |
| pair x1.2 + USDJPY $150 | 14.8% (2.8%) | **34.3% (4.2%)** | 59.4% (5.5%) |
| pair x1.2 + USDJPY $250 | 16.1% (5.1%) | 34.9% (7.1%) | 58.6% (9.0%) |
| pair x1.5 + ManualDip 500 | 18.0% (4.3%) | 36.5% (6.2%) | 58.8% (8.1%) |
| pair x1.5 + ManualDip 500 + USDJPY $150 | 21.0% (5.8%) | **41.0% (7.7%)** | 63.5% (9.5%) |
| pair x1.5 + ManualDip 500 + USDJPY $250 | 22.1% (8.5%) | 41.3% (11.3%) | 62.2% (13.7%) |
Reading: because it is uncorrelated with gold, a small USDJPY leg ($150 a trade) adds about 5 points of pass probability by 22 Dec for 1-1.5 points of extra breach; more size adds breach faster than passes. Caveats: the MT5 broker-years USDJPY numbers are the ones it was selected on (only 2020-21 is out of sample), the pair's numbers are in-sample and gold-trend flattered, and nothing reaches 30 Oct.
