# Market demo screen (stage 1 = real ticks 2025Q4 + 2026; stage 2 = modelled 2022-2025)

## mkt_asurastrike_M5: stage 1 fail
net +838 USD, PF 1.03, 277 trades
- FAIL net > 0 in BOTH windows
- FAIL pooled PF 1.03 >= 1.30
- ok   277 trades >= 60
- FAIL net / max equity DD 0.3 >= 2
- FAIL max concurrent 1 <= 3 and lot ratio 13.8 <= 3 (grid / martingale)
- ok   23.1 trades a month >= 5

## mkt_chiroptera_M15: no deals in 2026
## mkt_darkmoon_M15: stage 1 fail
net -234 USD, PF 0.82, 649 trades
- FAIL net > 0 in BOTH windows
- FAIL pooled PF 0.82 >= 1.30
- ok   649 trades >= 60
- FAIL net / max equity DD -0.2 >= 2
- FAIL max concurrent 13 <= 3 and lot ratio 13.0 <= 3 (grid / martingale)
- ok   54.1 trades a month >= 5

## mkt_darkvenus_M15: stage 1 fail
net +3,249 USD, PF 2.11, 1954 trades
- ok   net > 0 in BOTH windows
- ok   pooled PF 2.11 >= 1.30
- ok   1954 trades >= 60
- FAIL net / max equity DD 1.0 >= 2
- FAIL max concurrent 31 <= 3 and lot ratio 28.0 <= 3 (grid / martingale)
- ok   162.8 trades a month >= 5

## mkt_ghostscalper_H1: stage 1 fail
net +661 USD, PF 1.47, 1354 trades
- FAIL net > 0 in BOTH windows
- ok   pooled PF 1.47 >= 1.30
- ok   1354 trades >= 60
- ok   net / max equity DD 3.2 >= 2
- FAIL max concurrent 4 <= 3 and lot ratio 1.0 <= 3 (grid / martingale)
- ok   112.8 trades a month >= 5

## mkt_goldbeaver_M15: stage 1 fail
net +87,789 USD, PF 2.66, 106 trades
- ok   net > 0 in BOTH windows
- ok   pooled PF 2.66 >= 1.30
- ok   106 trades >= 60
- ok   net / max equity DD 4.4 >= 2
- FAIL max concurrent 3 <= 3 and lot ratio 162.0 <= 3 (grid / martingale)
- ok   8.8 trades a month >= 5

## mkt_goldenshot_M15: STAGE 1 PASS
net +31,738 USD, PF 3.86, 386 trades
- ok   net > 0 in BOTH windows
- ok   pooled PF 3.86 >= 1.30
- ok   386 trades >= 60
- ok   net / max equity DD 12.9 >= 2
- ok   max concurrent 1 <= 3 and lot ratio 1.5 <= 3 (grid / martingale)
- ok   32.2 trades a month >= 5

stage 2: PF >= 1.0 in 3 of 4 years: 2022 PF 0.80 net -3,352 (195 trades), 2023 PF 1.04 net +503 (195 trades), 2024 PF 1.53 net +8,193 (269 trades), 2025 PF 2.93 net +24,830 (361 trades)
## mkt_goldenshot_H1: STAGE 1 PASS
net +31,738 USD, PF 3.86, 386 trades
- ok   net > 0 in BOTH windows
- ok   pooled PF 3.86 >= 1.30
- ok   386 trades >= 60
- ok   net / max equity DD 12.9 >= 2
- ok   max concurrent 1 <= 3 and lot ratio 1.5 <= 3 (grid / martingale)
- ok   32.2 trades a month >= 5

## mkt_havana_M5: stage 1 fail
net -60,837 USD, PF 0.51, 4487 trades
- FAIL net > 0 in BOTH windows
- FAIL pooled PF 0.51 >= 1.30
- ok   4487 trades >= 60
- FAIL net / max equity DD -1.6 >= 2
- FAIL max concurrent 2 <= 3 and lot ratio 6.3 <= 3 (grid / martingale)
- ok   373.9 trades a month >= 5

## mkt_marketanomalies_M15: stage 1 fail
net +58,005 USD, PF 1.36, 746 trades
- ok   net > 0 in BOTH windows
- ok   pooled PF 1.36 >= 1.30
- ok   746 trades >= 60
- ok   net / max equity DD 3.0 >= 2
- FAIL max concurrent 3 <= 3 and lot ratio 8.6 <= 3 (grid / martingale)
- ok   62.2 trades a month >= 5

## mkt_marketanomalies_H1: stage 1 fail
net +52,521 USD, PF 1.33, 743 trades
- ok   net > 0 in BOTH windows
- ok   pooled PF 1.33 >= 1.30
- ok   743 trades >= 60
- ok   net / max equity DD 2.6 >= 2
- FAIL max concurrent 3 <= 3 and lot ratio 8.5 <= 3 (grid / martingale)
- ok   61.9 trades a month >= 5

## mkt_orbrevolution_M5: stage 1 fail
net +32,894 USD, PF 1.28, 258 trades
- ok   net > 0 in BOTH windows
- FAIL pooled PF 1.28 >= 1.30
- ok   258 trades >= 60
- FAIL net / max equity DD 1.4 >= 2
- FAIL max concurrent 1 <= 3 and lot ratio 5.4 <= 3 (grid / martingale)
- ok   21.5 trades a month >= 5

## mkt_brokergold_M30: STAGE 1 PASS
net +37,014 USD, PF 1.36, 345 trades
- ok   net > 0 in BOTH windows
- ok   pooled PF 1.36 >= 1.30
- ok   345 trades >= 60
- ok   net / max equity DD 2.0 >= 2
- ok   max concurrent 3 <= 3 and lot ratio 1.4 <= 3 (grid / martingale)
- ok   28.8 trades a month >= 5

stage 2: PF >= 1.0 in 4 of 4 years: 2022 PF 1.01 net +1,004 (421 trades), 2023 PF 1.11 net +7,619 (432 trades), 2024 PF 1.44 net +27,095 (405 trades), 2025 PF 1.33 net +26,681 (382 trades)
## mkt_qcommander_M5: STAGE 1 PASS
net +137,732 USD, PF 2.85, 349 trades
- ok   net > 0 in BOTH windows
- ok   pooled PF 2.85 >= 1.30
- ok   349 trades >= 60
- ok   net / max equity DD 7.8 >= 2
- ok   max concurrent 3 <= 3 and lot ratio 2.3 <= 3 (grid / martingale)
- ok   29.1 trades a month >= 5

stage 2: PF >= 1.0 in 4 of 4 years: 2022 PF 2.83 net +52,869 (237 trades), 2023 PF 2.59 net +30,244 (210 trades), 2024 PF 2.05 net +34,585 (261 trades), 2025 PF 3.40 net +112,168 (308 trades)
## mkt_qcommander_H1: STAGE 1 PASS
net +137,732 USD, PF 2.85, 349 trades
- ok   net > 0 in BOTH windows
- ok   pooled PF 2.85 >= 1.30
- ok   349 trades >= 60
- ok   net / max equity DD 7.8 >= 2
- ok   max concurrent 3 <= 3 and lot ratio 2.3 <= 3 (grid / martingale)
- ok   29.1 trades a month >= 5

## mkt_rangebreakout_M15: stage 1 fail
net -16,131 USD, PF 0.82, 255 trades
- FAIL net > 0 in BOTH windows
- FAIL pooled PF 0.82 >= 1.30
- ok   255 trades >= 60
- FAIL net / max equity DD -1.0 >= 2
- FAIL max concurrent 4 <= 3 and lot ratio 23.6 <= 3 (grid / martingale)
- ok   21.2 trades a month >= 5

## mkt_rangebreakout_H1: stage 1 fail
net -6,264 USD, PF 0.66, 47 trades
- FAIL net > 0 in BOTH windows
- FAIL pooled PF 0.66 >= 1.30
- FAIL 47 trades >= 60
- FAIL net / max equity DD -1.2 >= 2
- FAIL max concurrent 3 <= 3 and lot ratio 10.1 <= 3 (grid / martingale)
- FAIL 3.9 trades a month >= 5

## mkt_rbclaye_M15: stage 1 fail
net +22 USD, PF 1.00, 341 trades
- FAIL net > 0 in BOTH windows
- FAIL pooled PF 1.00 >= 1.30
- ok   341 trades >= 60
- FAIL net / max equity DD 0.0 >= 2
- ok   max concurrent 1 <= 3 and lot ratio 1.0 <= 3 (grid / martingale)
- ok   28.4 trades a month >= 5

## mkt_scrapergold_M15: stage 1 fail
net +24,448 USD, PF 1.66, 338 trades
- FAIL net > 0 in BOTH windows
- ok   pooled PF 1.66 >= 1.30
- ok   338 trades >= 60
- ok   net / max equity DD 4.3 >= 2
- ok   max concurrent 3 <= 3 and lot ratio 1.3 <= 3 (grid / martingale)
- ok   28.2 trades a month >= 5

## mkt_scrapergold_H1: stage 1 fail
net +23,585 USD, PF 1.64, 339 trades
- FAIL net > 0 in BOTH windows
- ok   pooled PF 1.64 >= 1.30
- ok   339 trades >= 60
- ok   net / max equity DD 4.1 >= 2
- ok   max concurrent 3 <= 3 and lot ratio 1.3 <= 3 (grid / martingale)
- ok   28.2 trades a month >= 5

## mkt_smartgoldhunter_M15: stage 1 fail
net +162 USD, PF 1.60, 136 trades
- FAIL net > 0 in BOTH windows
- ok   pooled PF 1.60 >= 1.30
- ok   136 trades >= 60
- ok   net / max equity DD 3.6 >= 2
- ok   max concurrent 1 <= 3 and lot ratio 1.0 <= 3 (grid / martingale)
- ok   11.3 trades a month >= 5

## mkt_smartgoldhunter_H1: stage 1 fail
net +162 USD, PF 1.60, 136 trades
- FAIL net > 0 in BOTH windows
- ok   pooled PF 1.60 >= 1.30
- ok   136 trades >= 60
- ok   net / max equity DD 3.6 >= 2
- ok   max concurrent 1 <= 3 and lot ratio 1.0 <= 3 (grid / martingale)
- ok   11.3 trades a month >= 5

## mkt_titanforge_H1: stage 1 fail
net -1,063 USD, PF 0.00, 2 trades
- FAIL net > 0 in BOTH windows
- FAIL pooled PF 0.00 >= 1.30
- FAIL 2 trades >= 60
- FAIL net / max equity DD -1.9 >= 2
- ok   max concurrent 1 <= 3 and lot ratio 1.0 <= 3 (grid / martingale)
- FAIL 0.2 trades a month >= 5

## mkt_universalbreakout_M15: stage 1 fail
net -38,419 USD, PF 0.73, 269 trades
- FAIL net > 0 in BOTH windows
- FAIL pooled PF 0.73 >= 1.30
- ok   269 trades >= 60
- FAIL net / max equity DD -0.9 >= 2
- FAIL max concurrent 2 <= 3 and lot ratio 22.9 <= 3 (grid / martingale)
- ok   22.4 trades a month >= 5

