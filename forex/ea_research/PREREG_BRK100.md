# PREREG BRK100 - 100 more untested breakout tests (79 new concepts + 21 out-of-sample market extensions), one round

Registered 2026-10-18 18:45 local (local clock, second PC PC-2), before any P&L of these ideas was computed.
the trader (/goal, 18 Oct): "keep testing untested breakout ideas, atleast 100 more".

**Window note.** the trader's 40-variant window is closed; at his request this is one more pre-registered family of FIXED rules,
judged with a Bonferroni bar for its 100 tests (t >= 3.29). **What "untested" means here, checked against the repo:** excluded are
BRK50 (54 ideas and the ~45 families in its pre-registration), BRK50B (50), BRK30 (30), GN1-GN13, BRK_PATTERNS, the ICT rounds,
UT Bot / Supertrend flips, GOTOBI, EIA_OIL, FX3_OPEN, basket / USD-index rounds, weekly-open levels. Two cousins are named openly:
round 1 tested each market's main-session 30-minute box (crypto on the New York session) and BRK-HOURS tested 60-minute boxes at
every server hour on all 46 markets; the fixing / cut / exchange-time ideas below use 30-minute boxes at other times and are new
rules but relatives of that map. **L080-L100 are not new concepts:** they are today's NSDQ / XAUUSD-only ideas run on the markets
where they were never run (cross-market out-of-sample tests).
**Pre-registration evidence (no commits on 18 Oct):** SHA-256 and time in `data\scratch\brk100_prereg.sha256` before any P&L.

## Common rules
- Data, clock, daily H / L / C / O / ATR, fills, rollover ban, mirror trade, R as BRK50 / BRK50B / BRK30 (`brk50.Mkt`); BRK30's bar
  machinery (BC: bar-close entry at the next minute, H1 stop 1.5 ATR14 / exit 24 bars, H4 2 ATR14 / 30 bars; BS: bar stop orders).
- Universes: ALL = 38 non-crypto; X36 = ALL without NSDQ and XAUUSD; CRY = 8 crypto (7 days a week); FX = 28 pairs; USDM =
  AUDUSD EURUSD GBPUSD NZDUSD USDCAD USDCHF USDJPY; JPYX = AUDJPY CADJPY CHFJPY EURJPY GBPJPY NZDJPY USDJPY.
- BOX(zone; box; orders; exit) = bid high / low of the box minutes (at least 80% present), stop orders in the order window (first
  touch, both in one minute = none), stop at the other side, exit at the stated time. FADE = first touch, enter the other way at
  the next minute, stop 0.5 x the range beyond the entry, same exit. LB = BOX(local; 08:00-08:29; 08:30-10:59; 17:00). NB =
  BOX(New York; 09:30-09:59; 10:00-11:59; 15:55). DL = stop orders 08:00-18:59 local, stop 0.5 ATR, exit 20:45 local.
  Session boxes for L065 / L079 / L081 / L099: LB for FX, metals, energy and DAX; NB for SP, NSDQ, DOW; Tokyo BOX(Tokyo; 09:00-09:29;
  09:30-11:29; 14:55) for NIKKEI; Sydney BOX(Sydney; 10:00-10:29; 10:30-12:29; 15:55) for ASX. Crypto exits never fall in the
  rollover window (moved out as BRK50).
- Calendars: CPI / NFP / FOMC `EVENT_CALENDAR_2022_2026.csv`; FOMC `fomc_statement_dates.csv`; auctions `treasury_coupon_auctions.csv`.
  Daily Yahoo files (VIX, VIX9D, VIX3M, RTY, ES, HG, GC, ZN): the last close strictly before the day. CME minute volume (Databento
  NQ / ES / GC / SI) for NSDQ / SP / XAUUSD / XAGUSD.

## The 100 tests
CRYPTO (CRY)
- L001 FUNDING 08:00 UTC: BOX(UTC; 07:30-07:59; 08:00-11:59; 15:55). L002 FUNDING 16:00 UTC: BOX(UTC; 15:30-15:59; 16:00-18:59; 19:30).
- L003 MONDAY RANGE: Monday 00:00-03:59 UTC range, orders Monday 04:00 - Wednesday 19:29 UTC, stop other side, exit Wednesday 19:30.
- L004 ASIA UNTOUCHED TO THE US SESSION: the 00:00-07:59 UTC range, if not traded through by 13:29 UTC, orders 13:30-18:59 UTC, exit 19:30.
- L005 TOKYO BOX: BOX(Tokyo; 09:00-09:29; 09:30-11:29; 15:00). L006 SATURDAY: BOX(UTC Saturday; 00:00-03:59; 04:00-15:59; 19:30).
- L007 ALT STRENGTH VS BTC (7 alts): BOX(UTC; 00:00-00:59; 01:00-07:59; 19:30) long-only if the alt / BTC close ratio (yesterday)
  is above its 20-day mean, short-only if below.
- L008 MONTH-END EXPIRY FADE: last Friday of the month, FADE of the 00:00-07:59 UTC range during 08:00-15:59 UTC, exit 19:30.
- L009 TIER-1 RELEASES: CPI / NFP days BOX(New York; 08:30-08:44; 08:45-10:59; 15:55); FOMC days BOX(New York; 14:00-14:44; 14:45-15:29; 15:55).
- L010 SUNDAY FADE: FADE of the Sunday 00:00-03:59 UTC range during 04:00-15:59 UTC, exit 19:30.
- L011 SUNDAY DIRECTION -> MONDAY: Monday BOX(UTC; 08:00-08:29; 08:30-11:59; 15:55) only in the direction of Sunday 00:00 -> 20:00 UTC.
- L012 US-CLOSE CONTINUATION (BTCUSD, ETHUSD): at 15:00 New York enter in the direction of the 09:30 -> 14:59 move, stop 2 x the
  14-day mean |15:00 -> 15:55| move, exit 15:55.
FX
- L013 PRE-CUT PINNING FADE (USDM): FADE of the New York 09:00-09:29 range during 09:30-09:59, exit 10:05 New York.
- L014 TOKYO CUT (JPYX): BOX(Tokyo; 14:30-14:59; 15:00-16:59; 18:55).
- L015 ECB REFERENCE RATE (EURUSD EURGBP EURJPY EURCHF EURAUD EURCAD EURNZD): BOX(Berlin; 13:45-14:14; 14:15-15:29; 16:55).
- L016 US RELEASES (USDM): CPI / NFP days BOX(New York; 08:30-08:44; 08:45-10:59; 15:55).
- L017 FOMC (USDM): BOX(New York; 14:00-14:44; 14:45-15:29; 15:55). L018 TREASURY AUCTIONS (USDM): BOX(New York; 13:00-13:14; 13:15-14:29; 15:55).
- L019 RISK-OFF COMMODITY FX: after a VIX change >= +8% LB with AUDUSD / NZDUSD short-only and USDCAD long-only; after <= -5% the opposite.
- L020 US RATES -> DOLLAR (EURUSD GBPUSD AUDUSD NZDUSD USDCAD USDCHF): LB only in the dollar direction of the 10-year yield's last change.
- L021 GOLD AS ANTI-DOLLAR (EURUSD GBPUSD AUDUSD NZDUSD): LB only in the direction of gold's move 01:00 server -> 07:59 local.
- L022 BTC RISK GAUGE (AUDJPY NZDJPY CADJPY): LB only in the direction of BTCUSD's move 01:00 server -> 07:59 local.
- L023 CHINA MORNING (AUDUSD NZDUSD AUDJPY NZDJPY): BOX(Shanghai; 09:30-09:59; 10:00-11:29; 15:00).
- L024 QUARTER-END DOLLAR DEMAND (USDM): the last 2 trading days of a quarter, LB only in the dollar-up direction.
- L025 CARRY SIDE (AUDJPY NZDJPY CADJPY GBPJPY EURJPY USDJPY): LB long-only.
- L026 US BOND-MARKET CLOSE (USDM): BOX(New York; 14:30-14:59; 15:00-15:44; 15:55).
- L027 WEEKEND-GAP DIRECTION (FX): Mondays, LB only in the direction of the weekend gap (Monday's first mid vs Friday's last mid).
- L028 NARROWEST BOX OF THE DAY (FX): the LB trade of the pair with the smallest box / ATR. L029 WIDEST BOX OF THE DAY (FX): the largest.
INDICES
- L030 DAX AFTER THE CASH CLOSE: BOX(Berlin; 17:30-17:59; 18:00-20:59; 21:55). L031 DAX AT THE US OPEN: BOX(Berlin; 15:30-15:59; 16:00-17:24; 17:25).
- L032 NIKKEI AFTERNOON: BOX(Tokyo; 12:30-12:59; 13:00-14:29; 14:55).
- L033 NIKKEI SQ FADE: second Friday, FADE of the Tokyo 09:00-09:29 box during 09:30-11:29, exit 14:55.
- L034 ASX AT THE CHINA OPEN: BOX(Shanghai; 09:30-09:59; 10:00-11:29; 15:00).
- L035 VIX BACKWARDATION (SP NSDQ DOW): VIX >= VIX3M -> NB. L036 FRONT-END STRESS FADE (SP NSDQ DOW): VIX9D / VIX >= 1.1 -> NB FADE.
- L037 SMALL-CAP LEADERSHIP (SP NSDQ DOW): RTY's last daily change above ES's -> NB long-only; below -> short-only.
- L038 WEAK EURO -> DAX: DAX LB only opposite to EURUSD's move 01:00 server -> 07:59 local.
- L039 WEAK YEN -> NIKKEI: Tokyo box only in the direction of USDJPY from 15:59 New York (the day before) to 08:59 Tokyo.
- L040 COPPER -> ASX: Sydney box only in the direction of copper's last daily change.
- L041 DAX ON US RELEASE DAYS: CPI / NFP days BOX(Berlin; 14:30-14:44; 14:45-16:29; 17:25).
- L042 DAX EXPIRY FRIDAY: third Friday BOX(Berlin; 12:30-12:59; 13:00-14:59; 17:25).
COMMODITIES
- L043 GOLD LBMA AM: XAUUSD BOX(London; 10:00-10:29; 10:30-11:59; 15:00). L044 GOLD LBMA PM: XAUUSD BOX(London; 14:30-14:59; 15:00-16:29; 18:00).
- L045 SILVER LBMA: XAGUSD BOX(London; 11:30-11:59; 12:00-13:59; 17:00).
- L046 OIL SETTLEMENT (WTI BRENT): BOX(New York; 14:00-14:29; 14:30-15:29; 15:55). L047 RIG COUNT FRIDAY (WTI BRENT): Fridays BOX(New York; 13:00-13:14; 13:15-14:29; 15:55).
- L048 OIL IN ASIA (WTI BRENT): BOX(London; 01:00-01:29; 01:30-04:59; 07:55).
- L049 GOLD-SILVER RATIO -> SILVER: XAGUSD LB long-only if the gold / silver close ratio is above its 20-day mean, short-only if below.
- L050 RISK-OFF OIL (WTI BRENT): BOX(New York; 09:00-09:29; 09:30-11:29; 14:25) short-only after VIX >= +8%, long-only after <= -5%.
- L051 SHANGHAI PM BENCHMARK: XAUUSD BOX(Shanghai; 13:45-14:14; 14:15-15:29; 16:00). L052 INDIAN SESSION: XAUUSD BOX(Kolkata; 09:15-09:44; 09:45-11:59; 14:00).
STRUCTURE (ALL)
- L053 YESTERDAY'S AVERAGE PRICE: yesterday's mean minute mid as one level, a buy stop if price is below it at 08:00 local, a sell
  stop if above, DL timing and stop.
- L054 LONDON AGAINST A BIG ASIA: |move 01:00 server -> 07:59 local| > 0.5 ATR -> LB only against it.
- L055 NEW YORK AGAINST A BIG LONDON: |move 08:00 -> 14:29 local| > 0.5 ATR -> NB only against it.
- L056 UNCONFIRMED-PARTNER FADE (EURUSD-GBPUSD, AUDUSD-NZDUSD, SP-NSDQ, SP-DOW, XAUUSD-XAGUSD, WTI-BRENT): at a market's first LB touch,
  if the partner has not touched its own LB edge on the same side by then, FADE it (exit 17:00).
- L057 PRIOR NEW YORK RANGE IN ASIA (JPYX, AUDUSD, NZDUSD, NIKKEI, ASX, XAUUSD): yesterday's 14:30-20:59 local range, orders 01:00-07:29
  local, stop other side (0.5 ATR if > 1 ATR), exit 07:55 local.
- L058 UNTOUCHED ASIA IN NEW YORK: the 01:00 server - 07:59 local range, if untouched by 14:29 local, orders 14:30-18:59, stop other
  side (0.5 ATR if > 1 ATR), exit 20:45.
NAMED SYSTEMS (ALL)
- L059 PIVOT REVERSAL (TradingView) H1: stop orders at the latest pivot high / low (4 left, 2 right) for the next bar, re-armed each
  bar; stop 1.5 ATR14; exit 24 bars after the fill.
- L060 CONSECUTIVE UP / DOWN (TradingView) H1: 3 higher closes -> BC long; 3 lower -> BC short.
- L061 MOMENTUM (TradingView) H1: MOM(12) > 0 and rising -> buy stop at the bar's high for the next bar; mirror; stop 1.5 ATR14; 24 bars.
- L062 SMASH DAY (Williams) D1: yesterday closed below the prior low -> DL buy stop at yesterday's high; above the prior high -> DL
  sell stop at yesterday's low.
- L063 80-20 (Raschke) D1: yesterday opened in the top 20% and closed in the bottom 20% -> after price trades below yesterday's low,
  a buy stop at that low (DL timing, stop 0.5 ATR); mirror.
- L064 ACD (Fisher): opening range 08:00-08:14 local, A = 0.1 ATR; 7 consecutive minute closes above OR high + A (08:15-11:59) ->
  enter at the next minute, stop at the OR low, exit 17:00; mirror.
- L065 OPEN-DRIVE (Dalton): the session box closing in its top (bottom) 10% after opening in its bottom (top) 20% -> enter at the
  box end in the drive direction, stop at the other side, the session exit.
- L066 RENKO TREND: bricks of 0.5 ATR14(H1) on minute mids; two up bricks after a down brick -> enter at the next minute (mirror);
  stop 1.5 ATR14(H1); exit 24 hours later.
- L067 POINT AND FIGURE DOUBLE TOP: box 0.25 ATR, 3-box reversal, on H1 closes; an X column above the previous X column's high ->
  enter at the next minute (mirror for O columns); stop 3 boxes; exit 24 H1 bars later.
- L068 TREND QUALITY D1: R-squared of a 20-day regression of daily closes > 0.7 -> DL only in the slope direction.
- L069 LBR MOMENTUM PINBALL: RSI(3) of the daily change < 30 yesterday -> buy stop at the 08:00-08:59 local high during 09:00-18:59,
  stop at that hour's low, exit 20:45; > 70 -> mirror.
- L070 STOCHASTIC POP (Bernstein) H4: ADX(14) < 20 and slow %K(14, 3) crosses above 80 -> BC long; below 20 -> BC short.
- L071 ROSS 1-2-3 H1: pivot low (1), pivot high (2), higher pivot low (3) -> buy stop at (2) for 12 bars, stop at (3), exit 24 bars
  after the fill; mirror.
- L072 ROSS HOOK H1: after a new 20-bar high, the first bar without a new high -> buy stop at that high for 6 bars, stop at the hook
  bar's low, exit 24 bars; mirror.
- L073 HIKKAKE H1: bar 2 inside bar 1, bar 3 breaks one side of bar 2; if within 3 more bars price reaches the other side of bar 2,
  a stop order there in that direction, stop at bar 3's extreme, exit 24 bars after the fill.
INFORMATION AND EVENTS
- L074 FOMC MINUTES (USDM, XAUUSD, SP, NSDQ, DOW): 21 days after each statement, BOX(New York; 14:00-14:29; 14:30-15:29; 15:55).
- L075 CME VOLUME AT THE BREAK (SP NSDQ: NB; XAUUSD XAGUSD: BOX(New York; 08:20-08:49; 08:50-10:59; 13:25)): taken only if the CME
  volume of the breakout minute >= 3x the median of that minute over the previous 20 days.
- L076 QUIET BOX BY CME VOLUME (the same boxes): taken only if the box's CME volume < 0.6x its 20-day mean.
- L077 PRE-FOMC FADE (ALL): the 2 trading days before a statement, LB FADE. L078 RELEASE-MORNING FADE (ALL): CPI / NFP days, LB FADE.
- L079 COPPER / GOLD RATIO (SP NSDQ DOW DAX ASX AUDUSD): HG / GC daily ratio above its 20-day mean -> session box long-only; below -> short-only.
OUT-OF-SAMPLE MARKET EXTENSIONS OF TODAY'S NSDQ / XAUUSD-ONLY IDEAS (rules as in PREREG_BRK50B / PREREG_GN13, other markets)
- L080 J01 morning-held PDH / PDL broken in New York (X36). L081 J16 unfilled-gap session break (SP DOW DAX NIKKEI ASX, session boxes).
- L082 J36 Nikkei-session direction -> NB (SP DOW). L083 J49 failed-breakout day (X36). L084 J04 reversal after 3 lower highs (X36).
- L085 J45 level confluence on the LB (ALL). L086 J13 own-London direction -> NB (X36). L087 J20 H1 inside bar (X36).
- L088 J22 H1 wide-range bar (X36). L089 J23 H1 three-bar momentum (X36). L090 J24 Holy Grail H1 (X36).
- L091 J25 variance-ratio trend regime -> LB (ALL). L092 J26 variance-ratio reversion -> LB FADE (ALL).
- L093 J07 daily pin bar (X36). L094 J08 daily doji (X36). L095 J09 close-location trend (X36). L096 J11 daily-close swing (X36).
- L097 J46 late-week fade of the Monday-Tuesday range (X36). L098 J47 Turtle Soup plus one (X36).
- L099 GN13 bond-trend-aligned session box (DOW DAX NIKKEI ASX). L100 J27 VIX close change -> NB side (SP DOW).

## Periods
DEV 2022-01-01 .. 2024-12-31; VAL 2025; HOLD 2026-01-01 .. 2026-10-16 (Yahoo-file ideas to 2026-09-21, CME-volume ideas to
2026-09-25), one look, only for ideas passing DEV and VAL.

## Acceptance (per idea, pooled over its universe)
- DEV: n >= 100; mean net R > 0 with day-clustered t >= 3.29 (Bonferroni, 100 one-sided tests at 5%); positive in >= 2 of the 3
  years; direction information mean(R - R_mirror) > 0 with t >= 2.0.
- VAL: mean > 0 with t >= 1.65. HOLD: mean > 0 with t >= 1.65.
- Account environment: the 5 best by DEV t and any passer replayed from 95,472 with the MT5 broker rules on 2022-25 trades (universe at $50
  a trade, at most 5 a day; NSDQ + XAUUSD at $250 where present); usable only if P(pass) > P(breach) by 30 Jun 2027.
- Multiple-testing context: the 100 DEV t-values against the null (about 5 above t 1.65 by luck).

## Dry run (no P&L)
Counts per idea and period, markets per idea, long share, median stop in spreads; truncation test (random cuts on EURUSD, XAUUSD,
NSDQ, BTCUSD); hand check of one entry for 12 ideas.

## Honest prior
About 0-1 pass. Crypto loses at every hour on MT5 broker spreads (BRK-HOURS: -0.06 .. -0.37 R); FX boxes have shrunk to ~14 spreads; the
cross-market tests ask whether today's small Nasdaq effects travel, which their 2022-25 Nasdaq-drift origin makes unlikely.
