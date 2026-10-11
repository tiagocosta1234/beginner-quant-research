# DA: confirmed index dip-reversal as an add-on to the gold pair on MT5 broker: result (2026-10-11)

Pre-registration `PREREG_DIP_ADDON.md` (commit e749a72), code `dip_addon.py`, output `DIP_ADDON_OUTPUT.txt`.

## Verdict: real and uncorrelated, but misses acceptance 3 by one point (+2 instead of +3); not built
| check | result | bar | pass |
|---|---|---|---|
| 1. mean net per trade on MT5 broker 2022-26 | +77.7 USD (+62.8 bp), 84 trades on 50 days, win 57%, 3.6% stopped; USD positive in 4 of 5 years (2025 -504) | > 0, >= 3 of 5 years | yes |
| 2. daily correlation with the pair | +0.05 (MT5 broker pool), -0.00 (FT pool) | <= 0.3 | yes |
| 3. MIX P(pass) by 22 Dec / 30 Nov, breach | 54% -> 56% / 35% -> 37%, breach 0.4% -> 0.4% | >= +3 points, 30 Nov not lower | **no (+2)** |

Per market (bp/trade): NSDQ +142, SP +75, DAX +35, DOW +30. By year USD: 2022 +1,544, 2023 +510, 2024 +2,547, 2025 -504, 2026 +2,427.

## Reading
The edge confirmed on 1990-2017 data is still there on MT5 broker's CFDs (no swap helps), and it does not move with gold. It is just rare:
about 10 signal days a year, sized at MT5 broker's 1% per idea, so over the 52 business days to 22 Dec it adds about 2 points of pass probability.
The registered bar was 3, so the rule says no EA. If the trader wants every small edge on the account regardless, this is the cheapest one to
build (one daily decision, one market group, stop at 3 sigma) and it carries no extra breach in the simulation; that is the trader's call, not a pass.

## DA2 (Z = 1.5, amendment registered before its run): also misses acceptance 3 (+2.5 instead of +3); family closed
209 trades on 114 days, +36.7 USD (+32.2 bp) per trade, win 53%, USD by year 2022 +876, 2023 -539, 2024 +1,708, 2025 +3,624, 2026 +1,998;
correlation with the pair +0.06 / +0.01. MIX P(pass) 30 Nov 35.5% -> 37.8%, 22 Dec 53.9% -> 56.4%, breach unchanged (0.2% / 0.4%).
(DA with one decimal: 30 Nov 37.2%, 22 Dec 55.7%.) A first DA2 run did not apply Z = 1.5 (clean_boot_lib rewrites sys.argv);
the switch now uses the env var DA_Z and that duplicate ledger row was removed.
Final reading: the best uncorrelated add-on found so far gives +2 to +2.5 points of pass probability with no extra breach. The bar was 3.
