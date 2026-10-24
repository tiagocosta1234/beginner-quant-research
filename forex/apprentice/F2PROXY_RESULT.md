# F2PROXY result: FAIL (24 Oct 2026, 23:03 local clock)
Pre-registration `PREREG_F2PROXY.md` (sha256 b59db001...). Output `F2PROXY_OUTPUT.txt`.
- DEV 2020-22 (244 trades): 1R +0.032, 1.5R +0.003, 2R -0.018, 3R -0.003 mean R.
- VAL 2023-24 (174 trades): 1R -0.095, 1.5R -0.073, 2R -0.049 (P 0.71), 3R +0.006.
- Bar: 2R > 1R (yes on VAL, no on DEV) AND 2R > 0 at P <= 0.05 (no) -> FAIL. HOLD 2025 not opened.
## Reading
- The mechanical proxy (daily + 1h agree at 08:00, stop beyond the overnight range) has no edge at any target: it is the "always a side" kind of call that went 13W/13L in replay.
- The +0.21R for 2R on the 27 replay entries was the June 2026 regime (100-pt days), not a general rule.
- Whatever edge exists is in the part the proxy leaves out: the discretionary "clean level" read (the trader's batch read 11W/5L). F1 stays as frozen (1:1); no switch to 2R.
- Time correction: the '~hh:mm' in PREREG_F2PROXY.md was estimated, not read from the clock; the file's write time is 23:03 (24 Oct 2026, local clock). The pre-registration was still written before any outcome was computed.
