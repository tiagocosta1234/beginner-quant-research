# FX3-JPY22 result (2026-10-14): the USDJPY 22:00 server-hour lead does not confirm

Pre-registration `PREREG_FX3_JPY22.md` (committed before the numbers), output `FX3_JPY22_OUTPUT.txt`. One trial.
- 2026-01..09 (unseen): 191 trades, net +0.51 bp per trade, t +1.03 (bar: t >= 1.65): FAILS.
- 2022-25 (context): net +0.24 bp, t +1.05; by year +0.91 / +0.21 / -0.13 / -0.01, i.e. the lead faded to zero by 2024-25 (the t +4.3 was a selection effect from scanning 924 cells and gross of cost).
- Descriptive: exiting at 22:55 instead of 23:05 gives net -0.19 bp (2022-25) and -0.18 (2026): whatever gain exists sits in the last minutes before the 23:00 rollover, the window the project's rollover rule excludes.
Closed. The three pairs have no open lead left. Live pair unchanged.
