# PREREG BRK50B - 50 more breakout ideas on gold and Nasdaq, tested in one round

Registered 2026-10-18 17:27 local (local clock, second PC PC-2), before any P&L of these ideas was computed.
the trader (18 Oct, after GN13 closed the 40-variant window): "no more commits today, just push everything done until now and then keep
trying breakout ideas (50 more ideas)".

**Window note.** the trader's kill rule is 40 variants per research window, and today's window closed at 40 (GN1-GN13). At his request
this is one more pre-registered family of 50 FIXED rules (no tuning, no variants), judged with a Bonferroni bar for 50 tests, as
BRK50 was. It reopens no closed family: excluded are BRK50's 54 ideas, the ~45 families listed in `PREREG_BRK50.md`, BRK_PATTERNS
/ CONFIRM / TWOWAY / FVG, the ICT rounds, the noise area, the hour map and TRB grids, and GN1-GN13.
**Pre-registration evidence (no commits today):** this file's SHA-256 and the PC-clock time are written to
`C:\work\scratch\brk50b_prereg.sha256` before any P&L; the file is committed unchanged later (amendments appended below).

## Common rules
- Data: MT5 broker M1 bid/ask, `forex/data_mt5`, 2021-12 .. 2026-10-16, zero-spread minutes repaired (`brk_patterns.load`); server clock =
  Athens; day = server trading day (minutes 01:00-23:00 server, weekdays); daily H / L / C from minute mids, O = the first mid of
  the day; ATR = 20-day mean of completed daily ranges (`brk50.Mkt`). Times: LIS = local, NY = New York, JST = Tokyo.
- Universe: **GN = NSDQ + XAUUSD** (pooled), N = NSDQ only, G = XAUUSD only.
- **Session box (SB):** NSDQ bid high / low of 09:30-09:59 NY, stop orders 10:00-11:59 NY, stop at the other side, exit 15:55 NY;
  XAUUSD 08:20-08:49 NY (COMEX open), orders 08:50-10:59 NY, stop at the other side, exit 13:25 NY. "SB long-only / short-only" =
  only the buy / sell stop. **SB fade:** at the first touch enter the other way at the next minute's open, stop 0.5 box beyond the
  entry, same exit. **London box (LB):** 08:00-08:29 LIS, orders 08:30-10:59 LIS, stop at the other side, exit 17:00 LIS.
- **Daily-level rule (DL):** stop orders at the stated levels 08:00-18:59 LIS, stop 0.5 ATR from the entry, exit 20:45 LIS.
- Sessions for the "previous session" ideas: NSDQ 09:30-15:59 NY, XAUUSD 08:20-13:29 NY (COMEX); "closing hour": NSDQ 15:00-15:59
  NY, XAUUSD 12:30-13:29 NY.
- Fills, stops, exits, the arming rule (a level is armed only if the mid at the window start is on its near side), the rollover
  ban (no fills 23:00-00:59 server) and the MIRROR trade (opposite side, next minute, same stop distance and exit;
  information = R - R_mirror) exactly as `brk50.Mkt.level` / `.trade`. R = net P&L / |entry - stop|. One trade per idea, market
  and day (weekly ideas: per week). Every input is known at its decision time (truncation test in the dry run).

## The 50 ideas
LEVELS AND DAILY STRUCTURE
- J01 MORNING-HELD PDH/PDL BROKEN IN NY, GN: a prior-day high (low) not traded through 08:00-14:29 LIS gets a buy (sell) stop
  14:30-18:59 LIS; stop 0.5 ATR; exit 20:45. [a level defended through Europe, broken on US volume]
- J02 PRIOR NY SESSION RANGE IN TODAY'S NY SESSION, GN: yesterday's 14:30-20:59 LIS range, orders today 14:30-18:59 LIS, stop at
  the other side (0.5 ATR if the range > 1 ATR), exit 20:45. [BRK50 I25 used it in London only]
- J03 PRIOR CLOSING-HOUR RANGE, GN: yesterday's closing-hour range, DL window, stop at the other side (0.5 ATR if > 0.5 ATR),
  exit 20:45. [where the day's last positioning sat]
- J04 REVERSAL BREAK AFTER THREE LOWER HIGHS / HIGHER LOWS, GN: three lower daily highs in a row -> buy stop at yesterday's high;
  three higher lows -> sell stop at yesterday's low; DL. [end of a pullback]
- J05 STAIRCASE CONTINUATION, GN: three days of higher highs and higher lows -> buy stop at yesterday's high; three lower highs and
  lower lows -> sell stop at yesterday's low; DL.
- J06 "OOPS" (Larry Williams), GN: session open (first minute mid) below yesterday's session low -> buy stop at that low from the
  next minute to the SB order-window end; open above yesterday's session high -> sell stop at it; stop 0.5 ATR; SB exit.
- J07 DAILY PIN BAR, GN: yesterday's lower wick > 2x body and close in the top third -> buy stop at yesterday's high; upper wick
  > 2x body and close in the bottom third -> sell stop at yesterday's low; DL.
- J08 DAILY DOJI, GN: yesterday's |C - O| < 0.1 x range -> stop orders at yesterday's high and low; DL.
- J09 CLOSE-LOCATION TREND, GN: the last 5 daily closes all in the top half of their ranges -> buy stop at yesterday's high only;
  all in the bottom half -> sell stop at yesterday's low only; DL.
- J10 YESTERDAY'S CLOSING-HOUR DIRECTION, GN: SB only in the direction of yesterday's closing-hour move (first to last minute).
- J11 DAILY-CLOSE BREAKOUT SWING, GN: yesterday closed above the prior day's high -> buy at today's 08:00 LIS (ask); below the prior
  day's low -> sell; stop 1 ATR; exit 20:45 on the third trading day (today + 2).
- J12 WEEKLY-CLOSE BREAKOUT SWING, GN: on the week's first trading day, last week closed above the week-before's high -> buy at
  08:00 LIS; below its low -> sell; stop 1 ATR; exit 20:45 on the week's last trading day.
INTRADAY STRUCTURE
- J13 OWN-LONDON-DIRECTION NY BREAK, GN: SB only in the direction of the market's own move from 08:00 LIS to the minute before
  the box.
- J14 OWN-ASIA-DIRECTION LONDON BREAK, GN: LB only in the direction of the market's move from 01:00 server to 07:59 LIS.
- J15 GAP-AND-GO BEYOND YESTERDAY'S SESSION RANGE, GN: session open above yesterday's session high -> buy stop at the high of the
  first 5 minutes, from the 6th minute to the SB order-window end, stop at the 5-minute low; open below the low -> mirror; SB exit.
- J16 UNFILLED-GAP SESSION BREAK, GN: gap = session open - yesterday's session close; if |gap| > 0.2 ATR and the gap is not filled
  inside the box minutes, SB only in the gap direction.
- J17 TREND MORNING (EFFICIENCY RATIO), GN: morning NSDQ 09:30-10:59 NY / XAUUSD 08:20-09:59 NY; ER = |net move| / sum |minute
  moves| (mids); ER > 0.4 -> stop order at the morning high (up-move) or low (down-move) during 11:00-13:59 / 10:00-12:29 NY, stop
  at the morning-range midpoint, SB exit.
- J18 CHOP MORNING FADE, GN: the same mornings with ER < 0.15 -> fade the first touch of either edge in the same window, stop 0.5
  range beyond the entry, SB exit.
- J19 AFTERNOON BREAK ON A SMALL-RANGE DAY, GN: NSDQ range 09:30-13:59 NY < 0.6 ATR -> stop orders at its edges 14:00-15:29 NY,
  stop 0.25 ATR, exit 15:55; XAUUSD 08:20-11:29 < 0.6 ATR -> orders 11:30-12:59, stop 0.25 ATR, exit 13:25.
- J20 H1 INSIDE BAR, GN: the first H1 bar (server-hour grid) starting 09:00-17:59 LIS whose range lies inside the previous bar ->
  stop orders at its high / low for the next 2 hours (to 18:59 at most), stop at its other side, exit 20:45.
- J21 M15 DOUBLE INSIDE BAR, GN: the first two consecutive M15 bars each inside its predecessor, ending 13:00-17:59 LIS -> stop
  orders at the mother bar's high / low for the next hour, stop at its other side, exit 20:45.
- J22 H1 WIDE-RANGE BAR, GN: the first H1 bar starting 09:00-17:59 LIS with range > 2x the mean of the previous 20 H1 ranges and a
  close in its top (bottom) quarter -> buy (sell) at the next minute, stop at the bar's midpoint, exit 20:45.
- J23 H1 THREE-BAR MOMENTUM, GN: the first time three consecutive H1 bars (ending 10:00-18:59 LIS) each close above the previous
  bar's high (below its low) -> buy (sell) at the next minute, stop at the three bars' lowest low (highest high), exit 20:45.
- J24 HOLY GRAIL (Raschke) H1, GN: ADX(14) > 30 with +DI > -DI and a bar whose low touches the EMA(20) -> buy stop at that bar's
  high for the next 3 bars, stop at its low (mirror for downtrends); exit after 12 H1 bars (outside the rollover window); one
  position at a time.
VOLATILITY / REGIME STATES
- J25 VARIANCE-RATIO TREND REGIME, GN: VR = var(30-minute returns) / (6 x var(5-minute returns)) of mids 08:00-20:59 LIS over the
  previous 20 days; VR > 1.1 -> SB (both sides).
- J26 VARIANCE-RATIO REVERSION FADE, GN: VR < 0.9 -> SB fade.
- J27 VIX CLOSE CHANGE, N: the VIX's last close change before the day <= -5% -> SB long-only; >= +8% -> SB short-only.
- J28 VIX OPENING GAP, N: today's VIX open / yesterday's close - 1, ranked against the previous 250 days (the VIX open has an
  upward bias): bottom fifth -> SB long-only, top fifth -> SB short-only (the VIX open prints at 09:30 NY; orders start 10:00).
- J29 BOND-SHOCK DAY, GN: the 10-year note's (ZN) last daily return before the day exceeds 2x the SD of its previous 60 returns
  -> SB (both sides).
- J30 CALM AFTER THE STORM, GN: yesterday's range > 1.5 x its ATR and today's box < 0.25 ATR -> SB.
- J31 MULTI-DAY CONTRACTION, GN: mean range of the last 5 days < 0.7 ATR -> DL at yesterday's high and low.
- J32 OVERNIGHT EXCHANGE-VOLUME SURGE, GN: CME volume (Databento NQ / GC) from 18:00 NY the day before to the box start > 1.5x
  its mean over the previous 20 days -> SB.
CROSS-ASSET LEADS (MT5 broker partner mids unless noted)
- J33 BTC WEEKEND MOVE, N: on Mondays, BTCUSD from Friday 16:00 NY to Monday 09:29 NY > +2% -> SB long-only, < -2% -> short-only.
- J34 BTC OVERNIGHT MOVE, N: BTCUSD from yesterday 16:00 NY to 09:29 NY > +1% -> SB long-only, < -1% -> short-only.
- J35 DAX MORNING, N: SB only in the direction of DAX's move 08:00 -> 14:29 LIS.
- J36 NIKKEI SESSION, N: SB only in the direction of NIKKEI's move 09:00 -> 15:00 JST (same day).
- J37 USDJPY RISK GAUGE, N: SB only in the direction of USDJPY's move 08:00 -> 14:29 LIS (yen weaker = risk-on = long).
- J38 OIL FOR GOLD, G: SB only in the direction of WTI's move 08:00 LIS -> 08:19 NY.
- J39 COPPER FOR NASDAQ, N: SB only in the direction of copper futures' (Yahoo HG) last daily change before the day.
- J40 GOLD-SILVER RATIO, G: yesterday's XAUUSD / XAGUSD close ratio below its 20-day mean -> SB long-only; above -> short-only.
- J41 GOLD AGAINST THE NASDAQ OPEN, G: gold's 09:30-09:59 NY box, orders 10:00-11:59 NY, stop at the other side, exit 15:55 NY,
  only in the direction OPPOSITE to NSDQ's move 09:29 -> 09:59 NY.
- J42 YEN-HAVEN GOLD IN LONDON, G: LB only in the direction opposite to USDJPY's move from 01:00 server to 07:59 LIS.
CALENDAR AND EVENTS
- J43 FOMC-CYCLE EVEN WEEKS (Cieslak, Morse, Vissing-Jorgensen), N: SB long-only on trading days -1..3, 9..13, 19..23, 29..33
  relative to the last FOMC statement day (`futures/data/events/fomc_statement_dates.csv`).
- J44 DAY AFTER A TIER-1 RELEASE, GN: the day after a CPI / NFP / FOMC day (`EVENT_CALENDAR_2022_2026.csv`), SB only in the
  direction of the release day's move from the minute before the release (08:29 / 13:59 NY) to the session close (NSDQ 15:59;
  XAUUSD 13:29 after CPI / NFP, 15:59 after FOMC).
MORE STRUCTURE
- J45 LEVEL CONFLUENCE, GN: SB, the long side only if the box high is within 0.15 ATR of yesterday's high, the short side only if
  the box low is within 0.15 ATR of yesterday's low.
- J46 LATE-WEEK FADE OF THE MON-TUE RANGE, GN: on Thursday and Friday fade the first touch of this week's Monday-Tuesday range
  (08:00-18:59 LIS), stop 0.5 ATR, exit 20:45.
- J47 TURTLE SOUP PLUS ONE (Raschke), GN: yesterday closed below the prior 20-day low (set at least 4 days earlier) -> buy stop at
  that low today; closed above the prior 20-day high -> sell stop at it; DL.
- J48 VOLUME-CLOCK OPENING BOX, GN: the box runs from the session start until CME volume reaches 12% of the 20-day mean session
  volume (between 5 and 60 minutes); stop orders until the SB order-window end; stop at the other side; SB exit.
- J49 FAILED-BREAKOUT DAY, GN: yesterday traded above the prior day's high and closed back below it -> sell stop at yesterday's
  low; traded below the prior low and closed back above -> buy stop at yesterday's high; DL.
- J50 GOLD POST-COMEX AFTERNOON, G: the 08:20-13:29 NY range broken 13:30-15:29 NY, stop at its midpoint (0.5 ATR if the range
  > 1 ATR), exit 15:55 NY.

## Periods
DEV 2022-01-01 .. 2024-12-31; VAL 2025; HOLD 2026-01-01 .. 2026-10-16 (ideas on the Yahoo daily files to 2026-09-21; on CME
volume to 2026-09-25), one look, only for ideas passing every earlier gate.

## Acceptance (per idea, pooled over its universe)
- DEV: n >= 100; mean net R > 0 with day-clustered t >= 3.09 (Bonferroni, 50 one-sided tests at 5%); positive in >= 2 of the 3
  years; direction information mean(R - R_mirror) > 0 with t >= 2.0.
- VAL: mean > 0 with t >= 1.65.
- OOT (where the inputs exist for 2020-21: every single-market idea, the VIX / ZN / copper ideas, CME-volume ideas, the gold-
  silver ratio and the FOMC cycle; not the MT5 broker-partner or CPI / NFP ideas): the same rule on 2020-21 CME futures (NQ, GC; MT5 broker cost
  model as GN5-GN13; trades whose holding period contains a roll or flip minute or a 2020-21 NQ roll weekend skipped): mean > 0
  with t >= 1.65.
- HOLD: mean > 0 with t >= 1.65.
- Account environment: the 5 best ideas by DEV t and any passer, replayed from 95,472 with the MT5 broker rules on their 2022-25 trades
  at $250 and $500 a trade; usable only if P(pass) > P(breach) by 30 Jun 2027.
- Multiple-testing context: the 50 DEV t-values against the null (about 2.5 above t 1.65 by luck).

## Dry run (no P&L)
Trade counts per idea and period, long share, median stop in spreads; truncation causality test (data, partners, daily files and
CME volume cut at a random time on NSDQ and XAUUSD: every entry at least 35 days before the cut identical); hand check of one
entry for 10 ideas.

## Honest prior
About 0-1 pass at the Bonferroni bar, 2-3 ideas above t 1.65 by luck. Every breakout family so far carried less information than
the spread; these are the untested remainder, mostly new conditions on the same price data.
