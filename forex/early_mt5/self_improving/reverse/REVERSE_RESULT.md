# Result: fit on 2025, validate backwards (2026-10-13)
Pipeline as in PREREG_REVERSE.md, no amendments. Calibration: 0 real winners in placebo worlds 81, 82, 83 (their 2025 top-20 averaged +10.4 / +34.6 / +11.2 bp, and -18.7 / -28.6 / +1.7 bp on 2022-23H1) -> gate passed.
Real data: 2025 top-20 mean net +13.1 bp per trade; the same 20 rules on 2022-23H1 -18.3 bp, on 2023H2-24 -7.5 bp. REAL winners (net>0 and p<0.05 on both A and B): **0 of 20**.
Reading: a strategy that "works very well in 2025" is easy to select (thousands of rules pass the 2025 filter, including in shuffled placebo data), but its profit in 2025 is no larger than what shuffled data gives, and it loses backwards. 2025 is now burnt as a clean validation window for this rule family. Nothing was deployed.
Files: D:\finance\si_ledgers\REV_real.csv (the 20 rules and their stats), REV_pl81..83.csv.
