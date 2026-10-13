# ManualDip.mq5 verification on MT5 broker real ticks (2026-10-11)

Script `verify_manualdip_mt5.py`, raw output `MANUALDIP_VERIFY_OUTPUT.txt`. Portable tester terminal, Model 4 (real ticks), NSDQ+ M1 chart
trading SP+ / NSDQ+ / DOW+ / DAX+, 2025-10-01..2026-09-30, default inputs (Z 1.5, 3-sigma stop, 500 USD day risk).

| | Python simulation (dip_addon.py, DA2) | EA in the tester |
|---|---|---|
| trades | 43 | 43 (same dates, same indices: SP 8, NSDQ 10, DOW 11, DAX 14) |
| stopped | 1 (NSDQ 2026-06-08) | the same one (server-side SL) |
| net | +929 USD | +698 USD, equity DD 812 |

- Clock: decisions at 22:50 server (15:49 NY) and 18:20 (17:19 Berlin); in the March weeks when the US had changed to summer time and
  Europe had not, the EA decided at 21:50 server, as it must. The MQL conversion functions were also checked in Python against the tz
  database on every weekday 2022-2027 (3,130 dates, 0 mismatches).
- The gap (about -25%) comes from lot rounding down to 0.01 and real-tick entry prices a little worse than the M1 bar's ask; the
  account simulations of the add-on should be read at about 75% of their profit.
- Live requirement: the EA reads about 130 calendar days of M1 history for 4 symbols. MT5's default "Max bars in chart" (100,000) is
  about 72 trading days of index M1: set Tools > Options > Charts > Max bars in chart = Unlimited and restart the terminal, then check that
  the Experts tab shows "z3 ... sigma60 ..." lines and never "no signal data".
