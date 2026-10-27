# Training plan: toward a 70% win rate at 1:1 (the trader, from Tue 27 Oct 2026)

the trader: "then lets get that 70% win rate twin". Why 70%: on BROKER Builder with London + New York at 1:1, $1,000 risk, a 70% win rate gives about
73% odds of $10K in withdrawals by 31 Dec (`forex/prop10k/XMAS10K_BY_WINRATE_OUTPUT.txt`); 60% gives 15%, 50% gives 0.5%. Measured so far: blind read
about 42% at 1:1 (played at 30-50 seconds a day); claude 5min GC about 50% before costs. Nobody hands out 70%; it has to be trained and measured.

## How the 70% is chased
1. **Selectivity first.** High win rates come from skipping most days. Only take setups you would bet your own money on; "no trade" is a
   good answer. Fewer, better trades beat more trades.
2. **Slow, written reads.** The app's 3-minute lock on scored days. Before every trade write one line: bias (1h / 15m), the level (Asia
   high / low, previous day high / low), why price should reach 1R before the stop.
3. **Practice with feedback, measurement without it.** Practice mode (2026 days, result shown at once) = training volume. The 100 scored
   slow-read days (`PREREG_SLOW_READ.md`, 2024-25) = the measurement. Never mix them.

## Daily routine (about 45 minutes)
- 5 practice days, slowly, then review each one: what did the chart show at entry, what happened, would you take it again.
- 5 scored slow-read days (3-minute lock). No review of scored days until the checkpoint.

## Checkpoints (scored days only, 1:1)
| Scored days | Go on if | Meaning |
|---|---|---|
| 25 | any | first read of the pace; no conclusions |
| 50 | win rate of taken trades >= 55% | the read is above a coin; keep going |
| 100 | >= 60% and random-side P <= 0.05 (registered bar) | real edge: one account, live, same rules |
| next 100 (new days) | >= 65-70% | the year-end target level |

If the 100-day bar fails, the London 1-minute read is closed (as registered) and the training moves to a different method instead of buying
accounts. Live trading only after a checkpoint passes; the current BROKER account trades only the NQ Builder Play ticket or nothing.
