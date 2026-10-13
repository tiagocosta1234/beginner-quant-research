# RS1 result: gold 200-day-average risk switch for the pair (2026-10-12)

Pre-registration: PREREG_RISK_SWITCH.md. Rule: x1.5 when the previous gold close is above its 200-day average, else x1.0. FT pool 2022-26 and MT5 broker 12-month pool, ManualDip and guard as live.

| | live x1.5 | switch | x1.0 |
|---|---|---|---|
| MIX P(pass) 30 Nov / 22 Dec / 31 Jan | 42.3 / 59.2 / 75.5% | 37.7 / 55.1 / 72.6% | 26.2 / 44.5 / 65.5% |
| breach by 31 Jan | 2.2% | 1.8% | 0.3% |
| FT 2022-23 net / max drawdown | +1,423 / 17,418 | **-476 / 16,170** | +6,539 / 9,622 |
| FT 2024-26 net / max drawdown | +107,601 / 6,761 | +102,511 / 6,761 | +77,409 / 5,172 |

## Verdict: not adopted (criterion 1 fails by 3 points, criterion 2 fails; criterion 3 passes at 95%).
- The filter is ON on 80% of days in the FT pool (71% in the MT5 broker pool): gold sat above its 200-day average through most of 2022-26, so the switch is mostly x1.5 and rarely helps.
- It does NOT cure the 2022-23 problem: max drawdown only falls from 17,418 to 16,170 (7%) and the 2022-23 net turns negative. The bad stretch is not "gold below its 200-day average".
- It costs 4-5 points of pass probability by 30 Nov and 22 Dec for 0.4 points of breach.
- The pair x1.5 earned +31,733 on the 244 days the filter was OFF (and +77,291 on the 981 ON days): the pair does not depend on gold being above its average.
Live config unchanged. The only config that cuts the 2022-23 drawdown a lot is a flat x1.0 (9,622), and it costs 16 points of pass probability by 30 Nov.
