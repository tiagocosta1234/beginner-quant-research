# Forward log of the 12 EMA London rule (no risk): rules written Tue 2026-10-20 09:15 local (local clock), before any forward row exists

the trader 2026-10-20: "create the forward log in notion" (he liked the idea of a no-risk forward log of the live London setups). Claude wrote these rules; the trader may object before the first row (Wed 21 Oct 2026); after that they change only by a dated amendment made before it is used.

## 1. What it is, and what it is not
- An independent, hindsight-free confirmation of the blind replay (`PREREG_BLIND2026.md`). It does NOT replace that gate: "supported" there still unlocks Stage 3 (10 live London trades at about USD 100 risk), and nothing is risked on account <acct> because of this log.
- Paper only. The 20 Oct setups (1-minute short 4134.01 / 4141 / 4130.5 and the 5-minute short) were logged after the outcome and do NOT count.

## 2. The trades
- XAUUSD, 1-minute chart, his 12 EMA rule frozen as on the Notion rules card of 20 Oct (Amendment 4: the target is an FVG or a nearby high / low; stop about twice the target distance).
- Decision window 08:00-08:15 local (10:00-10:15 MT5 broker server), at most one trade a day, London only. First day Wed 21 Oct 2026. Every weekday gets a row (a day without a setup gets Direction "No trade").
- 5-minute setups: logged under Teste "Forward 5m 2026 (descritivo)"; never in the bars below.

## 3. Logging (Notion, database "12 ema backtest", view "Forward log")
- the trader creates the row HIMSELF, from that view (it fills Teste, Session = London, Symbol = XAU, Setup = EMA 12 + FVG), when the setup candle has closed and before he enters. Notion's `createdTime` is the canonical timestamp: no pre-created rows.
- Fields: Data, Direction, Hora do registo (the last closed 1-minute candle, local clock), Entry, Stop, Target (typed before entry), Setup image (screenshot taken after drawing the box and before entering), optional Tipo de alvo; Result afterwards.
- Scorable = Direction Long / Short, Entry / Stop / Target typed, `createdTime` at most 5 minutes after the logged candle, Hora do registo inside 08:00-08:15, the screenshot shows the same last candle and the same three prices (Claude checks them; a mismatch is excluded and reported), and the entry price within 1.5 USD of the MT5 broker mid at that minute (same check as the blind replay).
- A weekday without a row is "unlogged". If more than 10% of the weekdays since 21 Oct are unlogged at a look, the log is void for that look (it cannot show there was no cherry-picking). No row is ever back-dated.

## 4. Scoring (same as the blind replay)
- Entry at the real quote of the candle after the logged one (short: bid open, long: ask open), exits on the exit side of MT5 broker M1 bid / ask, same-minute stop + target = loss, still open at 17:00 local = marked there; his side against the mirror side and against a random side on the same entries (200,000 draws), stop and target distances as logged.
- MT5 broker M1 bid / ask comes from the main PC's MT5 terminal, read-only. A scorer wrapper around `blind_score.py` is written before the first scoring, from the format only (no outcomes).

## 5. Decision bars (reporting; no go-live decision rests on this log alone)
- Look F1 at 44 scorable trades (about 22 Dec 2026) and Look F2 at 80 (about mid-Feb 2027): "supported" iff mean R >= +0.10 and P(random side) <= 0.03 (Pocock, same as the blind Looks).
- Futility: at 20 or more scorable trades, excess over the random side < +0.05 R stops the log ("no edge shown"). Fewer than 30 scorable at F2 = inconclusive.
- Descriptive only (never a bar): extra cost 0.30 USD, entry +-1 minute, split by Tipo de alvo, the 5-minute log, first half against second half.

## 6. Honest limits
- 80% power against a true edge over a random side needs about +0.32 R at 44 scorable trades and about +0.24 R at 80 (per-trade spread taken from the January blind sample); a smaller edge cannot be proven in this time. January's blind result (excess +0.115, P 0.255, n 20) is consistent with no skill and with a +0.15 R edge.
- The log counts what the trader decides in real time; any rule change mid-log (tighter stop, different target) is a new test, not a variant of this one.

## Amendment 1 (Tue 2026-10-20 09:42 local, local clock; made before any forward row exists)
Reason: the trader 20 Oct answered "yes" to making the target type required, after the check of the 50 past setups (`TARGET_ORIGIN_OUTPUT.txt`, `TARGET_ORIGIN2_OUTPUT.txt`) showed that prices alone cannot tell an FVG target from a high / low and that no preference for small FVGs is visible.
- Every Long / Short row has "Tipo de alvo" (FVG, High / Low, or Outro) set BEFORE entry; when it is FVG, "Largura FVG (pts)" (new Notion number column) = the width of that gap in points (high edge minus low edge) on the chart he trades, and the gap is visible in the screenshot.
- Descriptive only, never a bar: a missing label does NOT remove a trade from the bars (they never depend on the label), but unlabelled rows are counted and reported; if more than 10% of the scorable rows are unlabelled, the split by target type is not reported.
- At F1 and F2 the split (FVG against High / Low, and FVG width) is reported beside the bars. The label is the only data on target origin (it cannot be recovered from prices). Nothing else changes: rule, window, bars, scoring, logging protocol.
