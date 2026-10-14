# GOLD-FIX result (2026-10-14 ~20:20): trading around the LBMA gold auctions on MT5 broker gold, 2022-2025
Pre-registration `PREREG_GOLD_FIX.md`, engine `gold_fix.py`, output `GOLD_FIX_OUTPUT.txt`. 6 real cells (AM 10:30 / PM 15:00 London x PRE momentum / POST fade / DRIFT short), 18 placebo cells at six fake auction times. 2026 sealed.
## Verdict: no fix effect; closed
- No real cell passes. The largest real |t| are AM DRIFT -4.03 (the short LOSES 1.6 bp: gold rose into the AM fix in 2022-24, gone in 2025, -0.15 bp) and AM PRE -2.90; the placebo cells at fake times reach |t| 4.33 (95th percentile 4.09), so neither is special to the auction.
- The PRE cells lose about 0.8-1.3 bp per trade at the real AND at every fake time: that is the round-trip cost of a 15-minute gold trade (spread ~1 bp) paid by a signal with no information. POST and the PM cells are within noise (|t| <= 1.7) and switch sign between years.
- Reading: whatever pre-fix leakage or fix-time pressure the 2004-2014 studies found is not in MT5 broker gold prices in 2022-2025 (the LBMA moved to an electronic, IBA-administered auction in 2015). The earlier DAY2K-D continuation lead at 14:35 London is therefore not a fix effect either.
Nothing to multi_fx_ea; no variants.
