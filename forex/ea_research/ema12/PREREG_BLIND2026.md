# PREREG_BLIND2026: blind replay of the trader's discretionary 12 EMA entries on days he has not seen (XAUUSD, London open)

Written 2026-10-19 14:25 (local clock, main PC) BEFORE any trade of this test is logged. the trader, 19 Oct: "i'm down for the blind replay ... plan what i should be backtesting ... run a january 2026 run". The mechanical January look is `JAN2026_RESULT.md`; this file is the plan for the test that matters: his own entries.

## Question
Do the sides the trader picks (12 EMA + FVG, London open) beat a random side taken at the same minute with the same stop and target distances, on MT5 broker bid/ask, on days he has not seen?

## Why a blind replay
- His 30 FX Replay trades (14 Apr-12 May 2025) replayed on MT5 broker bid/ask: 24 wins, mean R +0.219, random-side P 0.007 (London 17 trades, 14 wins, +0.254, P 0.046; NY 13 trades, 10 wins, +0.173, P 0.044). One regime, four weeks, the person who built the rule, no record made before the outcomes.
- No mechanical stand-in reproduces his sides: EMA12 0 of 32, MANUALRULE 0 of 12 (2022-25), and the January 2026 look is the same (all-44 mean R -0.066). Only his own entries can be tested, and only on days he has not seen.

## What is replayed (frozen)
The rules card "(original wording omitted)" (Notion): XAUUSD, London only, at most one trade a day, market entry between 08:00 and 08:15 local clock (= 10:00-10:15 MT5 broker server), setup candle opens one side of the 12 EMA and closes clearly on the other with body larger than its bigger wick and not small, target an FVG (whole if small, part if big), stop at twice the target distance (0.5 RR). No rule changes during the test; an idea for a change goes in the notes and is applied only after the verdict. NY is not part of this test (demo only on the real account); if the trader adds it, it is secondary.

## Days
- **Batch 1:** every weekday of January 2026 with MT5 broker data at the London open (21; 1 Jan has none), replayed **in calendar order** (Amendment 3) in one FX Replay session from Fri 2 Jan 07:30 to Fri 30 Jan, none skipped, never past 30 Jan (February is sealed). `blind_days.py --batch 1` (numpy `default_rng(20261019)`) first drew them in this shuffled order, kept in `BLIND_BATCH1.csv` (column `order`; calendar order in `cal_order`):
  12 Jan, 19 Jan, 16 Jan, 15 Jan, 27 Jan, 8 Jan, 7 Jan, 9 Jan, 5 Jan, 26 Jan, 23 Jan, 6 Jan, 20 Jan, 13 Jan, 30 Jan, 14 Jan, 2 Jan, 28 Jan, 29 Jan, 21 Jan, 22 Jan (2026).
- **Batch 2:** only if the batch-1 rule below says continue. 30 weekdays drawn without replacement from the 172 eligible days of 2026-02-02..2026-09-30 by `blind_days.py --batch 2` (`default_rng(20261020)`), drawn now so the list cannot be changed later (dates only; no prices were read). In order:
  6 Aug, 12 May, 9 Jun, 21 Apr, 17 Jun, 23 Mar, 11 May, 8 Jun, 2 Mar, 18 Jun, 4 Mar, 12 Aug, 20 Mar, 24 Jul, 22 Jul, 9 Jul, 14 Sep, 17 Feb, 25 Jun, 23 Apr, 23 Jun, 1 May, 23 Feb, 29 Apr, 25 Feb, 28 Sep, 11 Mar, 26 Aug, 17 Mar, 25 Mar (`BLIND_BATCH2.csv`). Replayed in calendar order (`cal_order` in the CSV). the trader sees this list only when batch 2 starts. It spends part of the sealed 2026 hold-out on this one candidate (the trader's OK of 19 Oct to "30 random 2026 days"); no other use of those days.
- Days after 30 Sep 2026 are not used: the trader traded and remembers them.
- **Extension windows (Amendment 2; used only if Look 1 below does not decide):** two 30-calendar-day windows of 2022-2025, drawn now by `blind_window.py` (dates only), chronological order, same rules. Window 1 = 2023-11-28..2023-12-27 (seed 202610193, 21 sessions, `BLIND_EXTRA.csv`, already in the Notion page). Window 2 = 2025-02-28..2025-03-29 (seed 202610194, avoids window 1 and his first sample, 21 sessions, `BLIND_EXTRA2.csv`), shown to him only when needed. Unsealed data, so they cost nothing of the 2026 hold-out.

## How each day is run (anti-hindsight rules)
1. FX Replay, XAUUSD, 1-minute chart, local clock, his usual indicators. News / calendar overlays off. **Leak check once before the first day:** any indicator that draws the current day's candle (PO3, daily range) must show only what has happened up to the cursor; if it shows the day's full body or wicks at 07:30, switch it off.
2. Never open a listed date on an ordinary chart; never look at the days after it. Replay in calendar order and never go back to an earlier date once a later one has been seen (Amendment 3: otherwise knowledge of later prices leaks into earlier days).
3. Be at 07:30 local of that day (the first day is the start of the session; later days move forward, never back). Before 08:00 write the day's bias (long / short / neutral) and the level swept, if any (optional, secondary).
4. Step one minute at a time from 08:00. At most one trade, only inside 08:00-08:15, by the card's rule. No setup by 08:15 = "no setup" (logged; it counts as a no-trade day).
5. **Before stepping forward after the click**, write in the log: side, the time of the last candle visible when he clicked, entry, stop, target, and tick "logged before the result". Then play on.
6. Never move the stop or target, never rewind, never delete a trade. Run to stop or target; if still open at 17:00 local, close at market and write the price.
7. Tick "recognised the day" if, before entering, he remembered what happened on that date (a big news move, a famous day). Such trades are scored separately.
8. If the data for a day is missing in FX Replay: "no data", next day.

## Scoring (`blind_score.py`, validated on the 30 old trades: R_mine and R_mirror equal `direction_skill.csv` to 1e-16; his +0.219, mirror -0.439, random -0.110, P 0.0069)
- Scorable = London trade with side, entry, stop, target and time, "recognised the day" off, "logged before the result" on, entry minute found in the MT5 broker data.
- Each trade is replayed on MT5 broker M1 bid/ask from the entry minute (the candle after the one he logged): long enters at the ask open, short at the bid open, exits at bid (long) / ask (short), his stop and target distances from his logged prices, same-minute stop and target = loss, still open at 17:00 local = marked at the exit side.
- Time check: the logged entry price must match the MT5 broker mid within 1.5 USD within +-5 minutes for at least 90% of trades, otherwise stop and settle the chart clock before scoring anything.
- **Primary:** mean R of his sides on scorable trades, and P = share of 200,000 random side assignments (same minutes, same distances) with mean R >= his.

## Decision rules (fixed now)
- **After batch 1:** if scorable n >= 12 and (his mean R minus the random-side mean R on the same entries) < +0.05, stop: **not supported**, the real account stays off this method. Otherwise (excess >= +0.05, or n < 12) do batch 2. (Amendment 1: the first draft stopped on his raw mean R < 0, which a hard month for every London entry would trigger for the wrong reason.)
- **Look 1 (Amendment 2),** when batch 2 is done (all listed days; at least 35 scorable trades in total, about 44 expected): **supported** iff mean R >= +0.10 and P <= 0.03; **not supported** iff excess < +0.05; otherwise continue to the two extension windows.
- **Look 2 (final),** after the extension windows (about 80 scorable trades in total): **supported** iff mean R >= +0.10 and P <= 0.03 on all scorable trades; otherwise **not supported**. Fewer than 30 scorable trades at the end = **inconclusive**. P <= 0.03 at both looks is the Pocock bound for two looks at one-sided 0.05 overall (z 1.875): a mean of +0.05 or a P of 0.08 is not a pass.
- **Supported unlocks Stage 3, not Plan B directly (Amendment 2):** 10 London trades on the MT5 broker account at about USD 100 risk each (about 0.27 lots at a 3.75 USD stop, never above 3.1 lots), logged before entry, stage halted if it loses USD 400. It checks what a replay cannot (real fills, live decisions): pass iff every trade was logged before entry and the average adverse difference between planned and filled prices (entries and stop exits) is <= 0.30 USD. Then the rules card's Plan B may start (London only, the trader's choice). It does not mean proven. Not supported / inconclusive: no money on this method.
- Descriptive, never changing the verdict: +0.30 USD extra cost per trade; entry minute +-1; flagged days included; NY if logged; batch 1 against batch 2; pooled with the old London 17; the stated bias against the MT5 broker move 08:00-12:00.

## Power (`blind_power.py`; MT5 broker 2023-25 prices, random London entry minutes, his stop/target distances; skill s = chance he takes the side that wins; random side averages -0.050 R)
| expected mean R of his side | P(supported) n=25 | n=35 | n=45 | P(stop after 18 trades, amended rule) |
|---|---|---|---|---|
| -0.05 (no skill) | 0.05 | 0.05 | 0.04 | 0.65 |
| +0.01 | 0.10 | 0.11 | 0.13 | 0.50 |
| +0.07 | 0.21 | 0.25 | 0.28 | 0.36 |
| +0.12 | 0.35 | 0.44 | 0.49 | 0.23 |
| +0.18 | 0.53 | 0.65 | 0.75 | 0.12 |
| +0.24 | 0.73 | 0.84 | 0.90 | 0.05 |
| +0.30 | 0.86 | 0.95 | 0.98 | 0.02 |
(Table of the first draft: single read, P <= 0.05.) His first sample showed +0.22; shrunk for selection a true +0.12 to +0.18 is plausible, where the test passes roughly 45% to 75% of the time. A "not supported" at n of 40 is therefore "not shown", not "no skill". The early stop lowers these by roughly the share in the last column (a stop is a loss of the chance to be supported).

### Two-look design of Amendment 2 (`blind_power2.py`; blocks of 18 / 26 / 18 / 18 scorable trades, cumulative 18 / 44 / 62 / 80)
| expected mean R of his side | single read at 44 (first draft) | two looks, overall P(supported) | average trades logged |
|---|---|---|---|
| -0.05 (no skill) | 0.04 | 0.04 | 34 |
| +0.06 | 0.26 | 0.30 | 48 |
| +0.12 | 0.47 | 0.56 | 50 |
| +0.18 | 0.70 | 0.80 | 49 |
| +0.24 | 0.87 | 0.93 | 46 |
| +0.29 | 0.96 | 0.98 | 45 |
Same false-positive rate (4%), about ten points more power at +0.12 to +0.18, for about eight more trades on average. The test is built to find edges that matter: at +0.06 R and USD 1,000 a trade the account makes USD 60 a day and needs over 200 trading days to reach the target, so missing such an edge costs little.

## Limits (written now)
- Across blocks, knowledge of one block can reach another (the 2023 and 2025 windows are earlier than 2026 in calendar time and are replayed later); he also lived through those years. The "recognised the day" flag and the small effect of a price level on a 1-minute entry decision are the only guards.
- FX Replay quotes differ from MT5 broker's; scoring uses his distances on MT5 broker quotes, so only his side and timing are tested.
- January 2026 is nine months back; he may remember famous days. The flag handles what he is willing to admit.
- Rules in his head can still drift between days; the frozen card and the notes are the only guard.
- The first 30 trades are the sample the rule was built on; expect a smaller number now.
- This is not a test of NY, of other markets, or of the MT5 broker pass odds (those follow from the Monte Carlo of the card once an edge is supported).

## Files
`blind_days.py`, `blind_score.py`, `blind_power.py`, `blind_power2.py`, `blind_window.py`, `BLIND_BATCH1.csv`, `BLIND_BATCH2.csv`, `BLIND_EXTRA.csv`, `BLIND_EXTRA2.csv`, `JAN2026_RESULT.md`. Ledger family `blind2026` is written when batch 1 is scored and at the final read.

## Amendment 1 (2026-10-19 14:30, before any trade of this test was logged; no P&L of this test exists)
Original file hash (14:25): sha256 9fd408a74e6b0fbc154e766fb16bdba9c022cd31ce0836dc7530a78f958b115f. Changed: only the batch-1 stop rule (above) and its column in the power table. Reason: the stop must ask "is he better than a random side on these entries?", not "did money come out positive?", because a hard month (or an easy one) moves every London entry the same way. Mean R >= +0.10 stays an absolute requirement of the final read. `blind_score.py` prints the excess.

## Amendment 2 (2026-10-19 15:53, before any trade of this test was logged; both Notion tables checked empty at 15:5x)
Hash of the version with Amendment 1 only: sha256 480731f260434f1a0f45e6cef52233045b404a0bd676f4c4476f1b323fbd6ab3. the trader: "decide what we need to do to prove my strategy has an edge". Changed: (1) one read at about 44 trades becomes two looks (about 44 and about 80 scorable trades, each at P <= 0.03 and mean R >= +0.10), the extension being the two unsealed windows; (2) "supported" unlocks a 10-trade live check at small size before Plan B. Reason: the single read had 70% power at a true +0.18 R and 47% at +0.12 R; two looks give 80% and 56% at the same 4% false-positive rate, and a replay cannot show real fills or live decisions. Nothing else changes (rules, scoring, futility after batch 1).

## Amendment 3 (2026-10-19 16:55, before any trade of this test was logged; the January Notion table was checked empty at 16:55)
Hash of the version with Amendments 1 and 2: sha256 839230e48d872803eec64eff8af9e03fca10a3425266e19ba6b5b9a93584458a. Changed: replay ORDER only. The first draft shuffled January (seed 20261019) and the sealed batch (seed 20261020), but replaying a day after a later day lets what he saw on the later day (levels, direction) leak into the earlier one, which is exactly the look-ahead the protocol forbids. In calendar order each day is decided with information up to that day, as live. The days are the same and the scoring conditions on the entries, so the statistics are unchanged. the trader had started an FX Replay session on 12 Jan (30 calendar days: it would skip 2-9 Jan and run into the sealed February): January is run as one session from 2 Jan to 30 Jan and stops there. Batch 2 and the extension windows are also replayed in calendar order.
