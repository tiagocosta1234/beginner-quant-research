# PROTOCOL_DAILY_READ: the trader's own read, every day, two slots

Written 24 Oct 2026 (local clock), before the next FX Replay session (starts 27 May 2026 07:30 local).
the trader: "we cant take more than 2 weeks passing an test" / "yes bro".

## Why
- Batch-2 own read: 11 trades, 8W / 3L, +5R. P(>=8/11 by luck) ~ 11%: not proven.
- Passing a 50K eval ($3K target, $2K EOD trailing, $1K daily loss) in 10 trading days needs ~2 trades a day.
  - Monte Carlo (24 Oct): 70% win, $750 risk, 2 trades/day -> pass 81%, blown 5%.
  - At 55-60% win it drops to 32-48% pass with 22-37% blown.
- So the read must be proven on BOTH a London and a New York slot.

## Slots (local clock = the FX Replay clock, UTC+1 in summer)
- **LDN:** call at 08:00 (replay stopped at 07:59). Trigger cutoff 10:00.
- **NY:** call at 14:30 (replay stopped at 14:29, the US cash open). Trigger cutoff 16:30.
- Each slot is a separate trade.

## Order of play (every slot, every day, not only batch days)
1. the trader gives his bias FIRST: long / short / no trade. If trading: entry, stop, target.
2. Claude then locks its own v5 call in `FXR_CLAUDE_TRADES.csv` (unchanged process) and logs the trader's read in `MANUAL_READ_LOG.csv`.
3. the trader executes his own read. Claude checks the order only: direction, box sides, stop beyond the wick.
4. "check" -> Claude grades from the chart and fills in the result.

## Frozen rules for the test
- 1:1 always; stop and target set at entry.
- Risk $750 per trade in replay, to mirror the eval plan.
- **A losing trade ends the day** (no NY trade after a London loss). This protects the $1K daily limit.
- No moving stops or targets after entry.
- No changes to these rules until the gate is reached.

## Gate
- **40 or more of the trader's executed trades with >= 26 wins (65%).** One-sided binomial P ~ 0.04.
- Report the London and NY slots separately. A slot below 55% over 15 or more trades is dropped from the eval plan.
- Pass -> forward test = the eval itself (Broker 50K, No Setup fee plan if passing inside 3 months), 2 trades/day at $750, stop after a loss. the trader buys; Claude never does.
- Fail -> no purchase; back to the drawing board.

## Counting
- Batch-2 rows already in `../ea_research/ema12/BLIND_LOG_BATCH2_FXR.csv` (11) count toward the 40 as LDN-slot trades.
- No-trade calls are logged but do not count as trades.

## Amendment 1 (24 Oct 2026, before any trade under the new rules)
the trader: "switch to always a side" / "i dont wanna be skipping sessions while im in class, even though i cant be managing trades in class".
- **Claude's read is now tested too:** every slot, Claude locks a SIDE (long or short) with entry / stop / target at 1:1. No "no trade". Logged in `CLAUDE_READ_LOG.csv`, graded from the chart, same gate (40 trades, >= 26 wins). the trader still calls first and does not see Claude's call before giving his own.
- **Nothing that needs a hand mid-session:** every trade is a bracket (entry + stop + target) set once and never touched.
  - **LDN:** market order at 08:00 (phone, about 60 s).
  - **NY:** cannot be clicked at 14:30 during class. So the NY trade is a **pending bracket order placed at 12:00** (before class): a sell limit / buy limit (retest) or a sell stop / buy stop (break) at the planned level, with stop and target attached. It is never cancelled by hand: an unfilled order lapses at the session flat time (21:00 local in replay; Broker's own flat time live). Graded exactly that way in replay: placed at 12:00 replay time, untouched.
- A losing LDN trade still ends the day: the NY pending order is then not placed (it is decided at 12:00, after LDN has usually resolved; if LDN is still open at 12:00, the NY order is placed and both run).

## Amendment 2 (24 Oct 2026, 29 May NY slot)
the trader: "you're supposed to be the trader, you're still in the learning phase".
- In replay, **Claude is the trader**: every slot Claude gives the order (side, type, entry, stop, target) and the trader places it as given. Claude's record (`CLAUDE_READ_LOG.csv`) is the main test; the replay balance now tracks Claude's calls.
- the trader's own read is optional (logged when he gives one, before seeing Claude's call).
- Unchanged: the 40-trade / 26-win gate before any real money; real-money orders are always placed by the trader; a losing trade ends the day; brackets are never touched.

## Amendment 3 (24 Oct 2026, 2 Jun 12:00, before the NY order was placed)
- If the LDN trade is still open at 12:00, the NY pending order is sized so the worst day stays inside the $1,000 daily loss limit: NY risk = $1,000 - LDN open risk ($750) = **$250**. Two full-size losers in one day (-$1,500) would breach an eval.

## Amendment 4 (24 Oct 2026, after 4 Jun: two correlated shorts lost $1,002.94 on one spike)
- Combined open risk is capped at **$900** (slippage room under the $1,000 daily limit).
- If LDN is still open at 12:00 and the NY idea is the same side at the same level, **skip NY** (one idea = one position).
- Before placing the NY order, check the calendar for releases 12:30-15:00 local.

## Amendment 5: THE FILTER (24 Oct 2026, after 15 Jun; the trader: "yeah switch to the filter")
Reason: the trader's read 11W/8L overall; 8W/3L on batch days (structured) vs 3W/5L trading every day in session 2eb6e1df (sweeps, news spikes, real breakouts). Account -3,474 (an eval would have failed on 10 Jun).
A slot is traded ONLY if ALL of these hold at the call time (checked by Claude before the trader's levels are drawn):
1. **Daily and 1h agree** on direction (daily = the last 2-3 daily swings; 1h = higher highs/lows or lower highs/lows since the last swing).
2. **Price is at a clean level** in that direction: a pullback into a multi-touch / multi-day level, or a retest of a broken one (within ~0.5 ATR15 of it). Mid-range = no trade.
3. **No red-folder US release** that day before 17:00 local (Forex Factory / FX Replay News panel).
4. **Stop = beyond the wick + 8-12 pts** (about 0.5 ATR15), size cut to keep $750; target 1:1 and in front of the next level.
Otherwise the slot is "FILTER: no trade" (logged with the failed condition).
Counting: filtered trades are a NEW sample, tracked in `MANUAL_READ_LOG.csv` with "FILTER" in the notes. Gate for the filtered read: **30 trades with >= 20 wins** (one-sided P ~ 0.05 vs 50%). The 19 earlier trades stay as history, not mixed in.

## Amendment 6 (24 Oct 2026, 16 Jun NY; the trader: "you're the one trading not me")
- With the filter on, **Claude is the trader in replay** (as in Amendment 2): Claude checks the filter and gives the order; the trader places it exactly.
- The filtered sample under test is Claude's filtered calls (`CLAUDE_READ_LOG.csv`, rows marked FILTER), gate 30 trades / >= 20 wins. the trader's own read is optional and logged separately when given.

## Amendment 7: FROZEN RULE SET "F1" (24 Oct 2026 21:2x PC; the trader: "freeze it and keep going until 10 pm")
No further changes until 30 F1 trades are logged. F1 = Amendment 5 filter + these:
- **Stop = beyond the 1h structure** (the last 1h swing low for longs / swing high for shorts), typically 30-45 pts, plus ~3 pts; size ~0.2 lots so risk = $750.
- Target 1:1, in front of the next level; if 1:1 runs INTO a level within 3 pts, no trade.
- LDN: market at 08:00. NY: pending order placed 12:00 at the level (lapses 21:00). Combined open risk <= $900; a loss ends the day; one idea = one position.
- No red-folder US release that day.
- Claude calls, the trader places. Gate: 30 F1 trades, >= 20 wins. Filtered trade #1 (16 Jun, old stop rule) is NOT in F1.

## Amendment 8 (24 Oct 2026; the trader: "stick to heavy size, higher win rate, and good frequency (2 to 3 setups a week)")
- F1 rules unchanged (win-rate test is unaffected). **Risk per F1 trade = $950** (just under the $1,000 daily loss limit; a loss ends the day; never two open F1 trades).
- Expected frequency 2-3 F1 setups a week. The 2-week pass window is dropped: target pass within ~5 weeks at F1 pace (Broker No Setup fee plan).
- Pass math at $950: about 3-4 net wins = $3,000.
