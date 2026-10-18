# PREREG BRK100C - another 100 ideas: CME microstructure, MT5 broker liquidity-weighted prices, minute lead-lag, untested calendars, adaptive rules and untested indicators

Registered 2026-10-18 (time in the hash file below, local clock, second PC PC-2), before any P&L of these ideas was computed and
while BRK100B was still in its dry run (no BRK100B result had been seen).
the trader (18 Oct evening): "get back to work and test another 100 ideas, always update CLAUDE.md often", then "another 100 ideas".

**Untested, checked by a repo-wide search of every PREREG file before writing (18 Oct ~22:00):** no hits for VPIN, Kyle's lambda,
Amihud, roll weeks, IMM dates, Chinese New Year / Golden Week, Diwali, Japan's Golden Week, lunar phases, Sell-in-May, the Fed
blackout, earnings season, payroll week, DEMA, ZLEMA, Tillson T3, ALMA, McGinley, FRAMA, LSMA, SMI, RMI, PMO, the random walk
index, the intraday momentum index, Chande's dynamic momentum index, polarized fractal efficiency, the projection oscillator, the
pretty good oscillator, the market facilitation index, the psychological line, SafeZone, inertia, three soldiers / crows, harami,
piercing / dark cloud, tweezers, principal-factor residuals. **Left out because a cousin was tested:** Monday ranges (BRK-WEEK W1),
efficiency-ratio regimes (J17), equity-curve filters (PAIR_OVERLAY O2, OUTSIDE_BOX EC), divergences (BRK30, ICT2), PPO (= MACD, K09 /
K10). **Cousins named openly:** XMKT X11 / X12 tested SP-NSDQ minute lead-lag (group C uses 12 other pairs and the same rule form);
BRK100B M015-M020 used a CME-volume VWAP on 4 markets (group B uses a 1 / spread "liquidity-weighted" price on all 38, MT5-native);
BRK100B M001-M014 used each market's own spread (N025 / N026 use other markets' spread shocks); K27 tested the OPEX-Friday pin and
K28 quarter-end rebalancing (not the roll week); L035 tested VIX >= VIX3M on US indices (N098 applies it to yen carry: a market
extension); I41 tested the intraday oil direction for USDCAD (N099 uses the daily oil shock).
**Pre-registration evidence (no commits on 18 Oct):** SHA-256 and time in `C:\work\scratch\brk100c_prereg.sha256` before any P&L.

## Common rules
Exactly BRK100B's (`PREREG_BRK100B.md`, "Common rules"): `brk50.Mkt` fills / rollover ban / mirror / R; ALL = the 38 non-crypto
markets; FX, USI, IDX6, CME4, USDM as there; lesson (a): no market entry or mark at the first minute of a server hour, BC entries at
the second minute after the bar close; BC H1 1.5 ATR14 / 24 bars, H4 2 ATR14 / 30 bars; SESSION, LB, NB, COMEX and CME session boxes,
DL, DL FADE and D-NEXT as there; daily signals use data up to the previous trading day's close; rs = BRK100B's minute spread ratio;
helper rows (names starting "_") feed a post-stage that only uses same-day information known before the entry.

## A. CME MICROSTRUCTURE (research: needs a volume feed) - CME4 unless stated
Bulk volume classification: signed volume sv = v x (2 Phi(dm / s) - 1) per minute, dm = the minute's mid change, s = the SD of
session minute mid changes over the previous 20 sessions, Phi = the normal CDF. Blocks = 30-minute server-clock blocks outside the
rollover window; block imbalance = |sum sv| / sum v. VPIN(x) = the mean imbalance of the last 16 blocks completed before x.
- N001 VPIN HIGH FOLLOW: VPIN at the CME box end >= the 80th percentile of its values at that time over the previous 60 sessions ->
  CME session box FOLLOW.
- N002 VPIN HIGH FADE: the same condition -> CME session box FADE.
- N003 VPIN LOW FOLLOW: VPIN <= its 20th percentile -> CME session box FOLLOW.
- N004 KYLE LAMBDA HIGH: lambda = the OLS slope of minute mid changes on minute signed volume over yesterday's session; >= the 80th
  percentile of the previous 60 sessions -> CME session box FOLLOW.
- N005 KYLE LAMBDA LOW: <= the 20th percentile -> CME session box FADE.
- N006 AMIHUD HIGH (D1): yesterday's |close-to-close return| / session volume >= the 80th percentile of the previous 60 -> DL.
- N007 AMIHUD LOW (D1): <= the 20th percentile -> DL FADE.
- N008 CLOSING SIGNED VOLUME (D1): yesterday's last 30 session minutes sum sv / sum v >= +0.2 -> D-NEXT long; <= -0.2 -> D-NEXT short.
- N009 OVERNIGHT VOLUME SHARE: volume from 18:00 New York (the day before) to today's session open / yesterday's session volume >=
  1.5x its 20-session median -> CME session box FADE.
- N010 NQ SHARE SURGE (NSDQ): NQ / (NQ + ES) volume in the first 30 session minutes >= 1.2x its 20-session median -> NB FOLLOW.
- N011 ES SIDE OF THE SHIFT (SP): the same NQ-share condition -> SP NB FADE.
- N012 SI SHARE SURGE (XAGUSD): SI / (SI + GC) volume in the COMEX box >= 1.3x its 20-session median -> XAGUSD COMEX box FOLLOW.
- N013 VWAP OVER TWAP (D1): yesterday's session VWAP - TWAP (mean minute mid) >= +0.1 ATR20 -> today's CME session box long-only;
  <= -0.1 ATR20 -> short-only.
- N014 VOLUME SURGE ON A QUIET SPREAD: the first session minute (open + 15 .. end - 65) with CME volume >= the 99th percentile of the
  previous 20 sessions' minutes and MT5 broker rs <= 1.2 -> enter in its direction (mid close - mid open of that minute) at the next
  minute, stop 0.2 ATR20, exit 60 minutes later.
- N015 INDEX ROLL WEEK (NSDQ, SP): Monday-Friday of the week before the expiry week of March / June / September / December (expiry =
  the 3rd Friday) -> NB FADE.

## B. MT5 broker LIQUIDITY (MT5-native, deployable)
LWAP = the liquidity-weighted price: sum(mid / spread) / sum(1 / spread) of the session's minutes from the session open (1 / spread
weights: the MT5 broker-native stand-in for VWAP); sigma = its 1 / spread-weighted SD. Sessions: LB markets 08:00-16:59 local (exit 17:00);
SP NSDQ DOW 09:30-15:54 New York (exit 15:55); NIKKEI 09:00-14:54 Tokyo (exit 14:55); ASX 10:00-15:54 Sydney (exit 15:55). Signal
window = open + 30 min .. end - 60 min; one trade per idea, market and day; intraday stops at least 0.1 ATR20 from the entry.
- N016 LWAP RECLAIM (ALL): BRK100B M015's rule with LWAP.
- N017 LWAP 2-SIGMA BREAK (ALL): M017's rule with LWAP.
- N018 LWAP PULLBACK IN TREND (ALL): M020's rule with LWAP.
- N019 LWAP TREND HOLD (ALL): M016's rule with LWAP.
- N020 LWAP OVER TWAP (ALL, D1): yesterday's session LWAP - TWAP >= +0.05 ATR20 -> today's SESSION long-only; <= -0.05 -> short-only.
- N021 SPREAD PERSISTENCE (ALL): the lag-1 autocorrelation of yesterday's minute rs (08:00-18:59 local) >= 0.6 -> SESSION FADE.
- N022 THIN ASIA (FX, metals, energy, DAX): mean rs 01:05-07:59 local / the median rs of the LB box >= 1.5 -> LB FOLLOW.
- N023 QUIET-SPREAD DONCHIAN H4 (ALL): the bar's mean rs < 0.9 and its close beyond the previous 20-bar closing high / low -> BC.
- N024 SHOCK-DAY CONTINUATION (ALL): yesterday had >= 3 shock minutes (rs >= 4, 08:00-18:59 local) and closed in the top (bottom)
  25% of its range -> DL long-only at yesterday's high (short-only at its low).
- N025 PARTNER SPREAD SHOCK (the 11 BRK100 L056 partner markets): at the partner's first shock of the day (08:00-18:59 local), if
  the market's own rs <= 1.2 -> enter it in the direction of the partner's mid change over the shock minute, at the next minute,
  stop 0.1 ATR20, exit 60 minutes later.
- N026 MULTI-MARKET SHOCK DAY (ALL): yesterday at least 20 of the 38 markets had a shock minute -> today SESSION FADE.

## C. MINUTE LEAD-LAG (MT5-native)
XMKT's X11 rule form: on a 5-minute grid inside the window, the leader's 5-minute mid return z (against the previous 20 days'
5-minute returns of the same window) beyond +/-1.5 while the follower's z is below half of the leader's in the implied direction
-> enter the follower in the implied direction at the next minute; stop 3 SD of the follower's 5-minute returns (previous 20 days)
beyond the entry; exit 15 minutes after the entry; one position at a time. Implied sign + unless stated.
- N027 DAX -> EURUSD (09:00-11:59 Berlin). N028 NIKKEI -> USDJPY (09:00-11:29 Tokyo). N029 XAUUSD -> AUDUSD (08:00-11:59 London).
- N030 WTI -> USDCAD, sign - (09:00-11:29 New York). N031 NSDQ -> DAX (09:30-11:29 New York). N032 USDJPY -> NIKKEI (09:00-11:29 Tokyo).
- N033 XAUUSD -> XAGUSD (08:20-10:59 New York). N034 EURUSD -> GBPUSD (08:00-11:59 London). N035 SP -> DOW (09:30-11:29 New York).
- N036 BRENT -> WTI (08:00-11:59 London). N037 USDJPY -> AUDJPY (09:00-11:59 Tokyo). N038 NSDQ -> AUDJPY (09:30-11:29 New York).

## D. CALENDAR (scheduled)
- N039 IMM DATES (FX): the 3rd Wednesday of March / June / September / December -> LB FADE.
- N040 CHINESE HOLIDAY WEEKS (XAUUSD, XAGUSD): the weekdays of the Chinese New Year and National Day holidays (State Council
  schedules 2022-2026, the list is in the code) -> LB FADE.
- N041 DIWALI WEEK (XAUUSD): the 5 weekdays before Diwali (2022-10-24, 2023-11-12, 2024-11-01, 2025-10-20) -> LB long-only.
- N042 JAPAN'S GOLDEN WEEK (USDJPY and the JPY crosses): weekdays 29 April - 6 May -> LB FADE.
- N043 DST MISMATCH WEEKS (ALL): weekdays between the US and EU clock changes (2nd Sunday of March to the last Sunday of March; the
  last Sunday of October to the 1st Sunday of November) -> SESSION FADE.
- N044 NEW MOON (ALL): within 3 days of a new moon (mean synodic month 29.530589 days from the new moon of 2000-01-06 18:14 UTC) ->
  SESSION FOLLOW.
- N045 FULL MOON (ALL): within 3 days of a full moon -> SESSION FADE.
- N046 HALF-YEAR SWITCH (IDX6): May-October -> SESSION FADE; November-April -> SESSION FOLLOW.
- N047 FED BLACKOUT (USDM, XAUUSD, USI): from the second Saturday before an FOMC statement to the statement day -> SESSION FOLLOW.
- N048 EARNINGS SEASON (USI): calendar days 8-35 of January, April, July and October -> NB FOLLOW.
- N049 PAYROLL-WEEK PREAMBLE (USDM): Monday-Wednesday of a week containing an NFP release (event calendar) -> LB FADE.
- N050 TUESDAY TURNAROUND (USI): a Tuesday after a down Monday (Monday's close below Friday's) -> NB long-only.
- N051 UK BANK HOLIDAYS (FX): England and Wales bank holidays on weekdays (list in the code, including the 2022-23 special days) ->
  LB FADE.
- N052 YEAR-END WEEKS (ALL): weekdays from 22 December to 2 January -> SESSION FADE.

## E. ADAPTIVE AND ENSEMBLE RULES (ALL)
- N053 TURTLE FILTER: SESSION FOLLOW only if the market's previous SESSION FOLLOW trade lost (R < 0).
- N054 ANTI-TURTLE: SESSION FOLLOW only if that previous trade won.
- N055 MODE MOMENTUM: if the mean R of the market's last 20 SESSION FOLLOW trades exceeds that of its last 20 SESSION FADE trades ->
  SESSION FOLLOW, else SESSION FADE (only trades closed before the day count).
- N056 TREND VOTE (D1): close > SMA50, SMA20 > SMA50, 20-day ROC > 0, MACD(12, 26) > its 9-signal, RSI14 > 50: all 5 up -> DL
  long-only at yesterday's high; all 5 down -> DL short-only at yesterday's low.
- N057 FOUR-DAY STREAK FADE (D1): 4 consecutive higher closes -> DL short-only at yesterday's low; 4 lower closes -> DL long-only at
  yesterday's high.

## F. UNTESTED MOVING AVERAGES (price only; the close crosses the average -> BC, H4) - ALL
- N058 DEMA 21. N059 ZLEMA 21. N060 TILLSON T3 (8, 0.7). N061 ALMA (21, 0.85, 6). N062 McGINLEY DYNAMIC 14. N063 FRAMA 16.
- N064 LSMA 25. N065 TRIMA 21. N066 SMMA 21 (Wilder). N067 EHLERS 2-POLE GAUSSIAN 20. N068 EHLERS 3-POLE BUTTERWORTH 20.
- N069 HOLT DOUBLE EXPONENTIAL (alpha 0.2, beta 0.1): the trend term changes sign -> BC.
- N070 EHLERS ULTIMATE SMOOTHER 20.

## G. UNTESTED OSCILLATORS (price only unless stated) - ALL
- N071 SMI (10, 3, 3) H1: crosses its signal below -40 -> BC long; above +40 -> BC short.
- N072 RMI (14, momentum 5) H1: crosses above 30 -> BC long; below 70 -> BC short.
- N073 PMO (35, 20, 10) H4: crosses its signal -> BC.
- N074 RANDOM WALK INDEX (14) H4: RWI-high crosses above RWI-low with RWI-high > 1 -> BC long; mirror.
- N075 INTRADAY MOMENTUM INDEX (14) H1: crosses above 30 -> BC long; below 70 -> BC short.
- N076 CHANDE DYNAMIC MOMENTUM INDEX (RSI length 5-30 from the 5 / 10-bar SD ratio) H1: crosses above 30 -> BC long; below 70 -> short.
- N077 POLARIZED FRACTAL EFFICIENCY (10, 5) H4: zero cross -> BC.
- N078 PROJECTION OSCILLATOR (14) H4: crosses above 20 -> BC long; below 80 -> BC short.
- N079 PRETTY GOOD OSCILLATOR (14) H4: crosses above +3 -> BC long; below -3 -> BC short.
- N080 MARKET FACILITATION INDEX (Bill Williams, CME4 volume) H1: a green bar (MFI and volume both up) closing in its top half -> BC
  long; in its bottom half -> BC short.
- N081 PSYCHOLOGICAL LINE (12) D1: >= 75% up days -> DL short-only at yesterday's low; <= 25% -> DL long-only at yesterday's high.
- N082 ELDER SAFEZONE (10, 2) H4: the close crosses the SafeZone stop -> BC.
- N083 INERTIA (Dorsey: 20-bar linear-regression value of RVI 10) H4: crosses 50 -> BC.
- N084 EHLERS REFLEX (20) H4: zero cross -> BC. N085 EHLERS TRENDFLEX (20) H4: zero cross -> BC.
- N086 EHLERS CORRELATION TREND (20) H4: crosses above +0.5 -> BC long; below -0.5 -> BC short.

## H. CANDLESTICK PATTERNS (D1) - ALL
- N087 THREE WHITE SOLDIERS / THREE BLACK CROWS (3 bodies >= 0.3 ATR20 the same way, each close beyond the previous) -> D-NEXT.
- N088 HARAMI (a body inside the previous day's body of >= 0.6 ATR20) -> DL in the reversal direction (after a long down body a buy
  stop at yesterday's high; mirror).
- N089 PIERCING LINE / DARK CLOUD COVER (after a long down body, a day opening below its close and closing above its midpoint; mirror)
  -> DL in the reversal direction.
- N090 TWEEZER BOTTOM / TOP (two lows within 0.05 ATR20, the second day closing up; mirror) -> DL long-only at yesterday's high (short
  at its low).
- N091 THREE INSIDE UP / DOWN (a harami whose third day closes beyond the first day's open) -> D-NEXT in the reversal direction.

## I. CROSS-MARKET FACTORS (MT5-native)
- N092 DOLLAR-FACTOR RESIDUAL (USDM): each USD pair's USD-signed move 08:05 -> 08:29 local minus the mean of the other six -> LB only
  on the side of the residual (the pair's own currency stronger than the dollar factor implies: XXXUSD long-only, USDXXX short-only).
- N093 INDEX-FACTOR RESIDUAL (USI): each US index's move 01:05 server -> 09:29 New York minus the mean of the six IDX6 moves over the
  same span -> NB only in the residual's direction.
- N094 COMMODITY-BLOC CONFIRMATION (AUDUSD, NZDUSD, USDCAD): all three USD-signed moves 01:05 server -> 08:29 local with the same sign
  -> LB only in the bloc's direction.

## J. CME VOLUME AS ATTENTION FOR OTHER MARKETS (research)
- N095 GC VOLUME AT THE SHANGHAI OPEN (XAUUSD): GC volume 09:00-09:59 Shanghai >= 1.5x its 20-day median -> XAUUSD LB FOLLOW.
- N096 ES VOLUME AT THE FRANKFURT OPEN (DAX): ES volume 08:00-08:29 Berlin >= 1.5x its 20-day median -> DAX LB FOLLOW.
- N097 NQ VOLUME AT THE TOKYO OPEN (NIKKEI): NQ volume 09:00-09:29 Tokyo >= 1.5x its 20-day median -> NIKKEI Tokyo box FOLLOW.

## K. EXTENSIONS AND EVENT LOAD
- N098 VIX TERM INVERSION FOR YEN CARRY (AUDJPY, NZDJPY, CADJPY): VIX >= VIX3M (last closes before the day) -> LB short-only.
- N099 OIL SHOCK NEXT DAY (USDCAD): yesterday's CL futures close-to-close >= +3% -> LB short-only; <= -3% -> LB long-only.
- N100 HEAVY EVENT WEEK (USDM, USI, XAUUSD): Monday and Tuesday of a week with >= 2 tier-1 events (CPI / NFP / FOMC) -> SESSION FADE.

## Periods, acceptance, dry run
As BRK100B: DEV 2022-24 (n >= 100, day-clustered t >= 3.29 = Bonferroni for 100, >= 2 of 3 years positive, information t >= 2.0), VAL
2025 (t >= 1.65), HOLD 2026 one look for DEV + VAL passers only; the account view for the 5 best and any passer; group summaries;
dry run with counts, a truncation test (EURUSD, XAUUSD, NSDQ) and 12 hand checks, no P&L.

## Honest prior
About 0-1 pass. The 34 price-only indicators and patterns (F, G, H) are the kind that averaged a DEV t of -1.6; the calendar effects
are small samples of days; CME microstructure is limited to 4 markets; the lead-lag rules pay a spread for a 15-minute hold, which
XMKT found too small to beat on SP / NSDQ.
