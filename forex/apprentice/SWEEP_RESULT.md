# SWEEP result: FAIL, 0 of 4 (24 Oct 2026, 23:10 local clock)
Pre-registration `PREREG_SWEEP.md`; output `SWEEP_OUTPUT.txt`. HOLD not opened.
- DEV 2020-22: -0.13 to -0.20R in all 4 variants. VAL 2023-24: PD/none -0.002R (55% wins), PD/trend -0.024R, PD+AS -0.145 / -0.165R.
- Mechanical sweep-and-reclaim at prev-day / Asia levels loses on gold at 1:1 with a stop under the sweep bar (median risk 4.5 pts: the reclaim gets swept again).
- Our replay stop-outs were a real pattern, but entering on the first reclaim is not the fix.
- Time correction: the '~hh:mm' in PREREG_SWEEP.md was estimated, not read from the clock; the file's write time is 23:09 (24 Oct 2026, local clock). The pre-registration was still written before any outcome was computed.
