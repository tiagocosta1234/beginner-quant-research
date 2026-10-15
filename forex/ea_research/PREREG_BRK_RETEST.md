# Pre-registration BRK-RETEST (breakout day, round 2; written 2026-10-15 11:42 local (commit time), before any code or result)
Question: is the breakout better entered on the RETEST of the broken level than on the stop order, and is a FAILED breakout tradeable the other way? Same 46 markets, sessions and 30-minute boxes as BRK-EXITS (round 1). Breakout = the first minute after the box in which the ask reaches the box high (up) or the bid reaches the box low (down), within open + 3 h; both in one minute = no event.

## Entries (one per market and day per entry type)
- **R1 retest limit:** after an up-breakout, a buy limit AT the box high, live for the next 60 minutes (fills when the ask comes back to it; at the minute's ask open if it opens below). Stop = the box middle. Down mirrored.
- **R2 retest confirmed:** after an up-breakout, wait until the bid comes back to the box high (the retest, within 60 minutes), then the first M5 close (session clock) back above the box high within the following 60 minutes -> buy at the next minute's ask; stop = the lowest bid since the breakout, minus one spread. Down mirrored.
- **R3 failed breakout reversal:** after an up-breakout, the first M5 close back below the box middle within 90 minutes -> SELL at the next minute's bid; stop = the highest ask since the breakout plus one spread. Down mirrored.
Stop distance R = |entry - stop|; skipped if R < 2 spreads.
## Exits (from round 1, fixed before this round's results): E-close = no target, close at the session end (capped 22:55 server); E-2R = target 2R. Stop -1R in both.
## Control: for each real trade, a random entry minute in the same order window of that day, random side, the same R, the same exit.

## Cells (6) = {R1, R2, R3} x {E-close, E-2R}; DEV 2022-24, VAL 2025, 2026 non-clean look.
Gates: 1. DEV mean >= +0.05 R and t >= 2.4 (daily portfolio, NW lag 1; Bonferroni 6); 2. VAL mean > 0 and t >= 1.65; 3. beats its control by >= 0.05 R in DEV and VAL. Reported by class (indices separately), by year.
## Honest prior
About 5%; R3 is a cousin of the sweep/turtle-soup rules that lost in the ICT scan, R1/R2 trade the same information as the stop order at a better price but fill only when the breakout first fails partly.
