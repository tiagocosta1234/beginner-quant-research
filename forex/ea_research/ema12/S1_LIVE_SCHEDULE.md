# S1 live schedule, 23 Oct - 22 Nov 2026 (30 days)

Adopted by the trader Thu 22 Oct 2026 (local clock ~11:10): "lets go with the plan as written, and schedule everything for the next 30 days". Plan: `S1_LIVE_RISK_PLAN.md`. Claude never places orders or arms Algo Trading; the trader trades by hand.

## Every weekday (local clock = local; Windows scheduled tasks in the folder `\S1Live\`, created by `forex/tools/s1_schedule/register_s1_tasks.ps1`, loud popup + sound that stays until OK)
| Time | What |
|---|---|
| 06:50 | wake-up popup |
| 07:20 | second popup: up and at the desk |
| 07:35 | the read-only morning brief opens in Notepad by itself (`london_brief.py` plus the size card): terminal state, balance and floor, spread, Asia range, EMA12 / ATR, stop table, and the lots for every stop distance |
| 07:55 | popup: at the chart, Algo Trading OFF, no position open |
| 07:56 | the size card opens again in Notepad (fresh balance, spread and position check): for each stop distance in points, the lots, the real risk, the gain at TP and the margin level; it also prints SKIP / STOP lines (open position, trade already taken, spread above 0.75, balance at 93,000 or below) |
| 08:00-08:15 | the London window: one S1 trade at most. After the setup candle read the lots for your stop distance off the card (SL = entry -/+ stop, TP = entry +/- the same distance); create the Notion forward-log row BEFORE entering; order with SL and TP attached, never moved. No command to type; if you want a number that is not on the card, message Claude |
| 08:16 | window closed: no trade = add the "No trade" row; open trade = check SL and TP |
| 17:05 | the day report opens in Notepad by itself (`s1_eod_report.py`): balance and floor, trades still open, trades closed today, the S1 live record since 23 Oct, and the chance to still pass by 30 Nov / 22 Dec from the balance today (the pass tracker). Nothing to type; Claude scores fills against the plan when asked |
| Fri 17:30 | weekly review: R, balance against the 92,000 floor, rule compliance, Notion rows complete; Claude updates CLAUDE.md START HERE; every push needs the trader's OK |
| Sun-Thu 23:15 | bedtime popup (bed by 23:30) |

The tasks only run while the trader is logged in and the PC is on (they are allowed to wake it from sleep). Remove all of them: `powershell -ExecutionPolicy Bypass -File forex/tools/s1_schedule/unregister_s1_tasks.ps1`.

## Rules that never lapse (from the plan)
- Risk = min(2,000, 25% x (closed balance - 92,000), what is still needed to pass); half size (12.5%) after 3 losses in a row; no new entries at a closed balance of 93,000 or below until the trader decides; lots capped at 3.1.
- One trade a day, London window, rules card, target 1.0 R, SL and TP attached and never moved, no re-entry, skip if the spread is above 0.75.
- Log every trade in Notion before entry; review after 10 live trades; no more backtests on S1, brackets or sizing.

## The 30 days
| Date | Day | Business day | Scheduled |
|---|---|---|---|
| 23 Oct | Fri | 1 | daily routine above; **FIRST LIVE S1 DAY.** Before 08:00: the window amendment decision (pending), no other position open. 17:30 first weekly review. |
| 24 Oct | Sat | - | no trading; 10:00 batch 2 slot A (optional, 5-6 h). Read the FX Replay Trades page within a week of playing. |
| 25 Oct | Sun | - | bedtime popup (Sunday night); Clocks go back 1 h (local = London time zone, the window stays 08:00-08:15). The tasks run on local time. |
| 26 Oct | Mon | 2 | daily routine above |
| 27 Oct | Tue | 3 | daily routine above |
| 28 Oct | Wed | 4 | daily routine above |
| 29 Oct | Thu | 5 | daily routine above |
| 30 Oct | Fri | 6 | daily routine above |
| 31 Oct | Sat | - | no trading; 10:00 batch 2 backup slot; last day to read the FX Replay Trades page if batch 2 was played on 24 Oct. |
| 01 Nov | Sun | - | bedtime popup (Sunday night); US clocks go back (NY open moves one hour later in local time; London window unchanged). |
| 02 Nov | Mon | 7 | daily routine above |
| 03 Nov | Tue | 8 | daily routine above |
| 04 Nov | Wed | 9 | daily routine above |
| 05 Nov | Thu | 10 | daily routine above; **10th business day: 17:10 review of the live trades** (live mean R, fills against the plan, rule compliance; pause if mean <= 0 or 4 of the first 6 lost). |
| 06 Nov | Fri | 11 | daily routine above |
| 07 Nov | Sat | - | no trading |
| 08 Nov | Sun | - | bedtime popup (Sunday night) |
| 09 Nov | Mon | 12 | daily routine above |
| 10 Nov | Tue | 13 | daily routine above |
| 11 Nov | Wed | 14 | daily routine above |
| 12 Nov | Thu | 15 | daily routine above |
| 13 Nov | Fri | 16 | daily routine above |
| 14 Nov | Sat | - | no trading |
| 15 Nov | Sun | - | bedtime popup (Sunday night) |
| 16 Nov | Mon | 17 | daily routine above |
| 17 Nov | Tue | 18 | daily routine above |
| 18 Nov | Wed | 19 | daily routine above |
| 19 Nov | Thu | 20 | daily routine above |
| 20 Nov | Fri | 21 | daily routine above |
| 21 Nov | Sat | - | no trading |
| 22 Nov | Sun | - | bedtime popup (Sunday night); 10:00 the schedule expires; re-plan the next block (30 Nov = business day 27, 22 Dec = day 43). |

## After the 30 days
- Mon 30 Nov (business day 27) is the trader's preferred pass date; Tue 22 Dec (day 43) is the latest. Forward-log Look F1 comes at 44 scorable rows (about the end of December) and F2 at 80.
- Dated reminders (batch 2 slots, the 10-trade review, the end of the schedule) run through two daily tasks that check the date (`s1_calendar.ps1`), because one-off tasks showed a broken next-run time across the 25 Oct clock change.
