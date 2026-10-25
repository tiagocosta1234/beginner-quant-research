# MANUAL_1M_B: new 1-minute strategy (EMA as confluence), phase 1 = discovery

Opened 25 Oct 2026 (local clock). the trader: "I'm going for a new 1 min strategy, still with ema as confluence" and "you'll conclude those answers after the 40 trades". The card test (`MANUAL_1M_APPROACH.md`, hash in `MANUAL_1M_APPROACH.sha256`) stays frozen and unchanged; it is not mixed with this file. No Test 2 trade had been logged under the card when B started (as far as Claude knows).

## What phase 1 is, and is not
- Phase 1 is DISCOVERY: the trader trades the new strategy 40 times; Claude then writes the rules from what the log shows. The rules are NOT pre-registered, so the first 40 trades prove nothing. Any win rate or R on them is in-sample and is never quoted as evidence of an edge.
- Its job is only to make the strategy describable and testable. Claude will list every rule it cannot read from the log as a question for the trader.

## What the trader logs for each trade (so the rules can be rebuilt)
Notion database "1 minute approach backtest" (Entry, Stop, Target, Tipo de alvo, Result columns to be added), one row per trade, written BEFORE stepping forward after the entry:
- Data, Direction, time of the setup candle, entry price, stop price, target price, screenshot (with the EMA(s) and any box / level visible).
- Which EMA (length) and how it is used: side of price relative to it, distance, whether the candle closed through it, or a pullback to it.
- What the target is (level, FVG, high / low) and why that stop.
- Skips: a row with Direction "No trade" and one line on what he saw and why he skipped. Skips matter as much as trades.
- Result afterwards (Win / Loss / BE) and one line of notes, including anything he did differently from his usual idea.

## Window
- Start 2 Mar 2023 and go forward in calendar order, one session at a time, never back. Stop at 40 executed trades. These days are then "seen" and are never used to confirm the rules.

## Phase 1 result (done 25 Oct 2026; in-sample, proves nothing)
- 41 closed trades, 2 Mar - 27 Apr 2023 (FX Replay export in `MANUAL_1M_B_PHASE1_TRADES.csv`; Notion B42 of 28 Apr is not in FX Replay and is excluded). 19 W / 22 L (46%), mean +0.11 R (standard error 0.19), about 0.00 R after 0.11 R costs, longest losing streak 4.
- Shape: XAUUSD, London morning, mostly 1 trade a day, entries 08:00-09:17 local (19 of 41 in 08:00-08:15), 36 market / 5 limit, median stop 1.72 points, target 1.0-2.06 x the stop (median 1.43).
- Post-hoc slice, NOT a finding: 08:00-08:15 entries +0.40 R (n=19) against -0.15 R after 08:15 (n=22); about 15 slices were looked at, so this is a hypothesis for phase 2 only.

## Phase 2 rules (FROZEN 25 Oct 2026, time in `MANUAL_1M_B.sha256` log below, before any phase 2 trade; the trader's answers 25 Oct, Claude's wording)
- XAUUSD, 1-minute chart, local clock, news / calendar overlays off. Window 08:00-09:20 local (covers every phase 1 entry). At most 2 trades a day (phase 1 had 2 on two days), the second only after the first is closed. 08:00-08:15 entries are reported as a pre-declared descriptive split, never a bar.
- **Bias:** the trend on the 15-minute chart (the trader), written before 08:00 as long / short / neutral. Neutral = no trade. The bias is not changed after 08:00.
- **Entry:** only when a 1-minute candle CLOSES beyond the 12 EMA on the side of the bias (above for long, below for short) (the trader: "the candle closes above/below the EMA in favor of my bias"). The EMA length is 12, as on his 12 EMA card; if it is another length the trader amends this BEFORE phase 2 trade 1.
- **Target (set before entry, one of three):** a high / low, an order block, or an FVG. "Tipo de alvo" is logged (High-Low / OB / FVG).
- **Planned RR:** target distance at least 1.0 x the stop distance (the phase 1 minimum); median phase 1 was 1.43.
- **Risk:** USD 750 in the evaluation, USD 500 once live.
- **Stop:** above / below an order block or an FVG (the trader). The stop price is logged before entry and not moved afterwards.
- **No changes during phase 2.** An idea for a change goes in the notes and is applied only after the verdict.
- **Logged BEFORE stepping forward after the entry:** bias, side, candle time, entry, stop, target, Tipo de alvo, screenshot. Days without a trade get a "No trade" row with the reason.
- **Window of days:** see Amendment 1 below (supersedes the 28 Apr 2023 start). Forward only, 40 executed trades.
- **Gate:** mean R >= +0.30 after costs (gold spread 0.48, desk costs about 0.11 R a trade); at the phase 1 payoff (median RR 1.43) that is about 24 wins out of 40 (60%). Why +0.30 and not +0.10: the standard error of 40 trades is about 0.19 R, so +0.10 is indistinguishable from luck. the trader's own long-run target is +0.5 R (about 27 wins out of 40). This number can be changed only before phase 2 trade 1.

## Phase 2: confirmation (only after phase 1)
1. Claude writes the rules from the phase 1 log and sends them to the trader; the trader corrects them.
2. The agreed rules are frozen and hashed (sha256 file) BEFORE any phase 2 trade, with the risk numbers (eval USD 750, live USD 500).
3. Phase 2 runs on the window and rules in "Phase 2 rules (FROZEN ...)" and Amendment 1 below (this outline was written before the freeze; where it differs, the frozen block and Amendment 1 win).
4. Gate: the frozen block's gate (mean R >= +0.30 after costs, about 24 wins of 40) wins over the +0.10 in the first outline.
5. Pass: Broker / Broker evaluation plan. Fail: no purchase and no re-tuning on the same days. the trader buys; Claude never does.
- Every strategy tested adds a chance of a lucky pass: phase 2 is the only result that counts, and a second strategy means a new phase 2 window.

## Amendment 1 (2026-10-25 16:52 local clock; made before any phase 2 trade; changes ONLY the window of days)
- the trader: "I'll start at 16 Jun 2025". The phase 2 window is now **fresh days starting Mon 16 Jun 2025**, forward only, in calendar order, never going back, 40 executed trades, XAUUSD 1-minute on FX Replay.
- Reason: a different year and price regime from phase 1 (2023), so a pass is stronger out-of-sample evidence, and it is closer to the current gold market (higher price, so stops in points are larger and the futures contract cap binds less). Claude proposed it; the trader chose the start date.
- Days to avoid, from the project logs: 14 Apr - 12 May 2025 (the trader's first FX Replay sample), 28 Feb - 29 Mar 2025 (reserved for the 12 EMA blind extension), 23 Oct - 21 Nov 2025 (the trader's 2025 session). 16 Jun 2025 onward clears the first two; if 40 trades run into 23 Oct 2025 the window stops before it.
- Any trade already logged from the old 2023 window (28 Apr 2023 onward) is NOT phase 2 and is discarded from the count: those days are seen.
- Not changed: the rules (bias from the 15m trend before 08:00, 1-minute close beyond the 12 EMA, target high-low / order block / FVG, stop beyond an order block or FVG), the 08:00-09:20 window, risk, the gate (mean R >= +0.30 after costs, about 24 wins of 40), and logging. Hindsight check: the bias is written from the chart up to 08:00 only, and a day the trader recognises from memory is logged as "recognised" in the notes.
- Contract-cap note (not a rule change): futures sizing is capped (3 minis / 30 micros on the likely Broker Flex plan), so the R result is unaffected but dollars on tight-stop trades will be smaller than FX Replay's uncapped sizing.
