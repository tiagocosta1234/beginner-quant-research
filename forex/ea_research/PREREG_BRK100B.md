# PREREG BRK100B - 100 more ideas: information the breakout tests never used (MT5 broker spread, CME volume, cross-market states) plus untested named systems

Registered 2026-10-18 21:39 local (local clock, second PC PC-2), before any P&L of these ideas was computed (the first
hash, 21:39:38, carried a guessed "21:50" here; corrected and re-hashed before any code ran).
the trader (18 Oct evening): "get back to work and test another 100 ideas, always update CLAUDE.md often".

**Why these 100.** About 600 breakout tests on MT5 broker prices (the I / J / K / L / P / GN families and the 15-16 Oct rounds) found no
edge net of MT5 broker costs; the recommendation on record (CLAUDE.md START HERE, section 4) is to spend new tests on information not yet
used. This batch: (A) MT5 broker's own minute spread as a signal (MT5-native, deployable); (B, G) CME 1-minute volume for NSDQ / SP /
XAUUSD / XAGUSD (research only: needs a feed; MT5 tick volume is the deployable proxy, on the main PC); (C) cross-market states built
from other MT5 broker symbols (MT5-native); (F) the VIX term structure and the implied-realised gap (research only); (H) the US holiday
calendar (scheduled); (D, D2, E) 35 named indicators and statistical filters never tested here (price only: the space already shown
to be used up, expected about 0).
**Untested, checked by a repo-wide search of every PREREG / RESULT / knowledge file before writing (18 Oct 21:2x-21:36):** no hits
for Dual Thrust, R-Breaker, MFI, Klinger, Force Index, ease of movement, Chaikin oscillator, VPT, PVO, VZO, VW-MACD, Twiggs, VPCI,
NVI, volume climax, spread shock / spread regime, Hurst, entropy, Kalman, the Ehlers filters (Super Smoother, Laguerre, roofing,
instantaneous trendline, MAMA, cyber cycle, centre of gravity, decycler, sinewave), QQE, WaveTrend, SSL, Range Filter, HalfTrend,
AlphaTrend, Trend Magic, Coral, Elder impulse, TSI, VIDYA, Coppock, Chande Kroll, VHF, Qstick, Ulcer index, inverse Fisher RSI,
Williams VIX Fix. **Cousins named openly:** BRK-VOLREG / BRK2 tested MT5 tick volume at the break and in the box (main PC data);
BRK100 L075 / L076 CME volume at the break and in a quiet box; GN7 the 5-minute ORB on high CME relative volume; J32 overnight CME
volume; NOISE_AREA / NQ3 used a TWAP (no volume) where group B uses a true VWAP; BRK-COST filtered by box width in spreads (a cost
filter, not spread dynamics); BRK-LAG (laggards), XMKT (SP-NSDQ lead-lag), BRK-XS (20-day relative strength) and L056 (unconfirmed
partner) are cross-market but different rules; J25 / J26 used the intraday variance ratio (group E uses Hurst, entropy, a Kalman
slope and daily autocorrelation); L035 / L036 used VIX >= VIX3M and VIX9D / VIX; BRK-CLASSICS C1 tested Larry Williams' one-day
volatility breakout (Dual Thrust uses a 4-day range); P06 tested the Fisher transform (M095 is the inverse Fisher of RSI).
**Data limits found while designing (18 Oct):** MT5 broker minute files carry bid OHLC and one spread per minute (ask = bid + spread, so no
intrabar spread information); the event calendar has dates only (no forecasts); the Yahoo daily files have no volume (the planned
ETF-volume ideas were replaced by CME-volume regimes, group G).
**Pre-registration evidence (no commits on 18 Oct):** SHA-256 and time in `C:\work\scratch\brk100b_prereg.sha256` before any P&L.

## Common rules
- Data, clock, daily H / L / C / ATR20, fills, rollover ban, mirror trade and R as BRK50 / BRK100 (`brk50.Mkt`). ALL = the 38
  non-crypto markets (crypto is left out: it loses its spread at every hour, BRK-HOURS / BRK100). FX = the 28 pairs; USI = SP NSDQ
  DOW; IDX6 = USI + DAX NIKKEI ASX; CME4 = NSDQ (CME NQ volume), SP (ES), XAUUSD (GC), XAGUSD (SI).
- **Lesson (a) everywhere:** no market entry and no mark at the first minute of a server hour; such a time moves to the next minute.
  BC entries are at the open of the SECOND minute after the bar close (BRK30's BC entered at the first).
- BC (bar close): H1 stop 1.5 ATR14(H1), exit at the start of bar b + 1 + 24; H4 stop 2 ATR14(H4), exit at bar b + 1 + 30; one
  position at a time per idea and market. H1 / H4 = server-grid bars of minute mids (bar open = the first minute's open mid).
- SESSION box = BRK100's: LB for FX, metals, energy and DAX; NB for SP NSDQ DOW; Tokyo box for NIKKEI; Sydney box for ASX. FOLLOW =
  stop orders at the box, stop at the other side, session exit; FADE = first touch, enter the other way at the next minute, stop 0.5 x
  the box beyond the entry, same exit. LB = BOX(local; 08:00-08:29; orders 08:30-10:59; exit 17:00). NB = BOX(New York; 09:30-09:59;
  10:00-11:59; 15:55). COMEX box (metals) = BOX(New York; 08:20-08:49; 08:50-10:59; 13:25). CME session box = NB for NSDQ / SP,
  COMEX box for the metals.
- DL = stop orders 08:00-18:59 local, stop 0.5 ATR20, exit 20:45 local; DL FADE = first touch, enter the other way at the next
  minute, stop 0.5 ATR20, exit 20:45. D-NEXT = market order at 08:05 local on the trading day after the signal day, stop 1.5 ATR20,
  exit 20:45 local on the 5th trading day (the entry day is the 1st).
- Daily signals use only data up to the previous trading day's close.
- Helper rows (names starting with "_") are not tests: they carry per-market-day trades and states that a post-stage combines into
  M011, M012, M045-M052 and M100, using only same-day information known before the entry.

## A. MT5 broker SPREAD AS INFORMATION (MT5-native, deployable) - ALL unless stated
rs = the minute's spread / the median spread of the same server minute-of-day over the previous 20 trading days (per market,
causal). A shock = rs >= 4. Day window = 08:00-18:59 local.
- M001 SPREAD-SHOCK FOLLOW: the day's first shock minute k; normalisation n = the first minute in (k, k + 30] with rs <= 1.5 (none:
  no trade); direction = sign(mid close at n - mid close at k - 1); enter at minute n + 1 in that direction; stop at the low (long)
  / high (short) of minutes k..n, at least 0.1 ATR20 from the entry; exit 60 minutes after the entry.
- M002 SPREAD-SHOCK FADE: the same event, entering against the direction; stop at the window's high (short) / low (long), at least
  0.1 ATR20 away; exit 60 minutes after the entry.
- M003 CALM-LIQUIDITY SESSION BOX: SESSION FOLLOW only if the box's median rs <= 0.9 and no box minute has rs >= 2.
- M004 STRESSED SESSION BOX: SESSION FOLLOW only if the box's median rs >= 1.4.
- M005 STRESSED SESSION BOX FADE: the same condition, SESSION FADE.
- M006 THIN-BREAK FADE: SESSION FADE only if the touch minute's rs >= 2.
- M007 DEEP-BREAK FOLLOW: SESSION FOLLOW only if the fill minute's rs <= 0.8.
- M008 STRESS-DAY TREND: yesterday's mean rs over the day window >= 1.3 -> DL at yesterday's high / low.
- M009 CALM-DAY REVERSION: yesterday's mean rs <= 0.8 -> DL FADE at yesterday's high / low.
- M010 STRESS-BAR CONTINUATION H1: the bar's mean rs is the highest of the last 24 H1 bars and above 1, and its close is in the
  bar's top (bottom) quarter -> BC long (short).
- M011 FX-WIDE STRESS FADE (FX): the median over the pairs (at least 20 present) of the LB box's median rs >= 1.3 -> LB FADE on
  every pair that day.
- M012 FX-WIDE CALM FOLLOW (FX): that median <= 0.85 -> LB FOLLOW on every pair that day.
- M013 EVENT-RICH REGIME: at least 5 shock minutes (day window) over the previous 5 trading days -> SESSION FOLLOW.
- M014 THIN MONDAY OPEN (ALL except NIKKEI and ASX, whose boxes start before 03:00 server): Monday's mean rs over 01:00-02:59
  server >= 2 -> Monday SESSION FADE.

## B. CME VOLUME (research: needs a volume feed; MT5 tick volume is the deployable proxy) - CME4
Minute volume = the CME front-month volume of the same server minute (Databento NQ / ES / GC / SI). Sessions (New York time):
indices 09:30-15:59 (exit 15:55), metals 08:20-13:29 (exit 13:25). VWAP = the cumulative volume-weighted minute mid from the session
open; sigma = the volume-weighted SD of the mid around VWAP. Signal window = session open + 30 min .. session end - 60 min; at most
one trade per idea, market and day; intraday stops at least 0.1 ATR20 from the entry.
- M015 VWAP RECLAIM: the first minute close crossing above VWAP after the mid had been >= 0.25 ATR20 below VWAP earlier in the
  session -> long at the next minute, stop at the session low so far, exit at the session exit; mirror.
- M016 VWAP TREND HOLD: at open + 90 min, if every minute close from open + 30 to open + 90 was above VWAP -> long, stop VWAP - 0.1
  ATR20, exit at the session exit; mirror.
- M017 VWAP 2-SIGMA BREAK: the first close above VWAP + 2 sigma -> long at the next minute, stop at VWAP, session exit; mirror.
- M018 VWAP 2-SIGMA FADE: the same signal, enter the other way, stop 1 sigma beyond the entry, session exit.
- M019 YESTERDAY'S VWAP AS A LEVEL: yesterday's session VWAP; from today's session open a buy stop at it if the mid is below it, a
  sell stop if above, live 3 hours; stop 0.25 ATR20; session exit.
- M020 VWAP PULLBACK IN TREND: after the session high has been >= 0.5 ATR20 above VWAP, the first minute whose low touches VWAP ->
  long at the next minute, stop VWAP - 0.25 ATR20, session exit; mirror.
- M021 VOLUME-CLIMAX FADE: the first minute (open + 15 .. end - 65) with volume >= the 99.5th percentile of the previous 20
  sessions' session minutes and range >= 3x their median minute range; if one of the next 5 minutes closes back beyond that
  minute's midpoint -> enter against the climax direction at the next minute, stop beyond the climax extreme, exit 60 minutes later.
- M022 VOLUME-CLIMAX FOLLOW: the same climax without that retracement -> enter with it at climax minute + 6, stop at the climax
  midpoint, exit 60 minutes later.
- M023 LUNCH DRY-UP BREAK (NSDQ, SP): the 11:30-12:59 New York range with CME volume < 0.5x the median of the same window over the
  previous 20 sessions -> stop orders at it 13:00-15:29, stop at the other side, exit 15:55.
- M024 ABSORPTION BREAK: the first 15-minute block (starting on :00 / :15 / :30 / :45, from open + 30 to end - 75) with volume >= 2.5x
  and range <= 0.5x the medians of that block over the previous 20 sessions -> stop orders at the block's high / low for the next 60
  minutes, stop at the other side, session exit.
- M025 OPENING-HOUR SIGNED VOLUME: over the first 60 minutes, the volume of up-minutes / the volume of down-minutes (mid close vs
  the previous minute) >= 1.5 -> long at open + 60, stop at the first-hour low; <= 1 / 1.5 -> short, stop at its high; session exit.
- M026 CUMULATIVE-DELTA DIVERGENCE FADE: delta = volume x (close - open) / (high - low) per minute (mid OHLC); at open + 120, the mid
  above the session open with cumulative delta < 0 -> short, stop at the session high + 0.05 ATR20; mirror; session exit.
- M027 HEAVY-VOLUME STRONG CLOSE (D1): yesterday's session volume >= 1.5x the median of the previous 20 sessions and yesterday's
  close in the top 20% of its daily range -> DL buy stop at yesterday's high; bottom 20% -> DL sell stop at yesterday's low.
- M028 LIGHT-VOLUME MOVE FADE (D1): yesterday's close-to-close >= +0.5 ATR20 on session volume <= 0.8x that median -> DL FADE at
  yesterday's high only; <= -0.5 ATR20 -> DL FADE at yesterday's low only.
- M029 VWAP CLOSE LOCATION (D1): yesterday's session-end mid - yesterday's session VWAP >= +0.25 ATR20 -> today's CME session box
  long-only; <= -0.25 ATR20 -> short-only.
- M030 VOLUME-PROFILE SHAPE FADE (D1): yesterday's session VWAP in the top 30% of yesterday's session range -> DL FADE at yesterday's
  high only; in the bottom 30% -> DL FADE at yesterday's low only.
- M031 UP / DOWN VOLUME RATIO (D1): over the previous 10 sessions, the volume of up-close days / the volume of down-close days >= 1.5
  -> DL long-only at yesterday's high; <= 0.67 -> DL short-only at yesterday's low.
- M032 NEGATIVE VOLUME INDEX (Fosback, D1): NVI from CME daily bars (trading day ending 17:00 New York, from 2019-10); NVI moves
  with the price only on days whose volume is below the day before; NVI above its 255-day EMA (yesterday) -> DL long-only at
  yesterday's high; below -> DL short-only at yesterday's low.
Bar indicators with CME bar volume (the sum of the minute volumes in the bar):
- M033 OBV LEAD H1: OBV above its previous 20-bar maximum while the close is below its previous 20-bar maximum close -> BC long;
  mirror.
- M034 MFI(14) H1: crosses above 20 -> BC long; crosses below 80 -> BC short.
- M035 KLINGER (34, 55, 13) H1: KVO crosses above its signal while below 0 -> BC long; below its signal while above 0 -> BC short.
- M036 FORCE INDEX (13) H1: zero cross -> BC in its direction.
- M037 EASE OF MOVEMENT (14) H4: its 14-bar SMA crosses 0 -> BC in its direction.
- M038 CHAIKIN OSCILLATOR (3, 10) H1: zero cross -> BC.
- M039 VOLUME PRICE TREND H4: VPT crosses its 13-EMA -> BC.
- M040 PVO (12, 26) H1: crosses above 0 on an up bar -> BC long; on a down bar -> BC short.
- M041 VOLUME ZONE OSCILLATOR (14) H4: zero cross -> BC.
- M042 VOLUME-WEIGHTED MACD (12, 26, 9) H1: crosses its signal -> BC.
- M043 TWIGGS MONEY FLOW (21) H4: zero cross -> BC.
- M044 VPCI (5, 20) H4: crosses above 0 with the close above SMA20 -> BC long; below 0 with the close below SMA20 -> BC short.

## C. CROSS-MARKET STATES (MT5-native)
- M045 STRONGEST VS WEAKEST CURRENCY (FX): each currency's strength = the mean over its 7 pairs of its signed log move 01:05 server
  -> 08:29 local (all 28 pairs present); the pair of the strongest and the weakest currency -> LB only in the strong currency's
  direction.
- M046 STRENGTH-CONSISTENT PAIRS (FX): the 4 pairs of a top-2 currency against a bottom-2 currency -> LB only in the strong
  currency's direction.
- M047 STRONG-WEAK EXHAUSTION FADE (FX): the M045 pair -> LB FADE.
- M048 GLOBAL INDEX BREADTH (USI): at 09:59 New York, the number of IDX6 markets above their previous daily close >= 5 -> NB
  long-only; <= 1 -> NB short-only.
- M049 GOLD IN EUROS (XAUUSD): the sign of the log move of XAUUSD / EURUSD from 01:05 server to 08:49 New York -> COMEX box only on
  that side.
- M050 DOLLAR FILTER FOR METALS (XAUUSD, XAGUSD): the dollar move = the mean of the 7 USD pairs' log moves 01:05 server -> 08:19 New
  York, each signed for the USD; up -> COMEX box short-only; down -> long-only.
- M051 TRIANGLE-CONSISTENT CROSS (the 21 pairs without USD): each currency's move against the USD over 08:05 -> 08:29 local (from its
  USD pair); cross XY long-only if X rose and Y fell against the USD, short-only if X fell and Y rose, else no trade -> LB.
- M052 CORRELATION BREAK (EURUSD GBPUSD AUDUSD NZDUSD SP NSDQ DOW XAUUSD XAGUSD WTI BRENT, partners as BRK100's L056): the 20-day
  correlation of daily log returns with the partner (days before) < 0.5 -> SESSION FOLLOW.

## D. NAMED SYSTEMS NOT YET TESTED (price only) - ALL
- M053 DUAL THRUST: Range = max(HH - LC, HC - LL) of the last 4 days (highest high, lowest close, highest close, lowest low); O = the
  mid at 08:01 local; buy stop O + 0.5 Range, sell stop O - 0.5 Range, live 08:01-18:59 local; stop at O; exit 20:45.
- M054 R-BREAKER TREND: P = (H + L + C) / 3 of yesterday; buy stop at H + 2 (P - L), sell stop at L - 2 (H - P); DL timing and stop.
- M055 R-BREAKER REVERSAL: once today's high (from 08:00 local) has exceeded P + (H - L), the first minute close <= 2P - L -> short
  at the next minute, stop at today's high so far, exit 20:45; mirror with P - (H - L) and 2P - H; signals 08:00-18:59; first only.
- M056 ACCELERATOR OSCILLATOR H4: AC = AO - SMA5(AO), AO = SMA5 - SMA34 of median prices; zero cross -> BC.
- M057 QQE (14, 5, 4.236) H1: the QQE trend (EMA5 of RSI14 against its trailing band) flips -> BC.
- M058 WAVETREND (10, 21) H4: WT1 crosses above WT2 below -53 -> BC long; below WT2 above +53 -> BC short.
- M059 SSL CHANNEL (10) H4: the state (close above SMA10 of highs = up, below SMA10 of lows = down) flips -> BC.
- M060 RANGE FILTER (100, 3) H1: the filter's direction flips -> BC.
- M061 HALFTREND (amplitude 2) H4: trend flips -> BC.
- M062 ALPHATREND (14, 1, RSI form) H4: AlphaTrend crosses its value 2 bars earlier -> BC.
- M063 TREND MAGIC (CCI 20, ATR 5) H4: the close crosses the Trend Magic line -> BC.
- M064 CORAL TREND (21, 0.4) H4: the Coral line's slope flips -> BC.
- M065 ELDER IMPULSE D1: a green day (EMA13 and the MACD(12, 26, 9) histogram both rising) after a non-green day -> D-NEXT long; red
  after non-red -> D-NEXT short.
- M066 TRUE STRENGTH INDEX (25, 13, 7) H1: TSI crosses its signal -> BC.
- M067 VIDYA (14, CMO 9) H4: the close crosses VIDYA -> BC.
- M068 COPPOCK CURVE D1: WMA10(ROC14 + ROC11) turns up while below 0 -> D-NEXT long; turns down while above 0 -> D-NEXT short.
- M069 CHANDE KROLL STOP (10, 1, 9) H4: the close crosses above the short stop -> BC long; below the long stop -> BC short.
- M070 VHF TREND BREAK (28) H4: VHF > 0.4 and the close beyond the previous 28-bar closing high / low -> BC.
- M071 QSTICK (14) H4: SMA14(close - open) zero cross -> BC.
- M072 ULCER-INDEX CALM BREAK D1: the Ulcer index (14) at its 60-day low (yesterday) -> DL at yesterday's high / low.
- M073 EHLERS SUPER SMOOTHER CROSS (10 / 40) H4 -> BC.
- M074 LAGUERRE RSI (gamma 0.5) H1: crosses above 0.2 -> BC long; below 0.8 -> BC short.
- M075 EHLERS ROOFING FILTER (48, 10) H4: zero cross -> BC.
- M076 EHLERS INSTANTANEOUS TRENDLINE (0.07) H4: the trigger (2 IT - IT two bars earlier) crosses IT -> BC.
- M077 MAMA / FAMA (0.5, 0.05) H4: MAMA crosses FAMA -> BC.
- M078 EHLERS CYBER CYCLE (0.07) H4: crosses above its 1-bar trigger while below 0 -> BC long; below it while above 0 -> BC short.
- M079 EHLERS CENTRE OF GRAVITY (10) H1: crosses its 1-bar trigger -> BC.
- M080 EHLERS DECYCLER OSCILLATOR (30 / 60) H4: zero cross -> BC.
- M081 EHLERS EVEN-BETTER SINEWAVE (HP 40, SS 10) H4: crosses above -0.9 -> BC long; below +0.9 -> BC short.

## E. STATISTICAL REGIMES - ALL
- M082 HURST TREND H1: the R/S Hurst exponent of the last 128 H1 log returns (scales 8 / 16 / 32 / 64 / 128) > 0.6 and the close
  beyond the previous 20-bar closing high / low -> BC follow.
- M083 HURST REVERSION H1: Hurst < 0.4 and the same close break -> BC against it.
- M084 LOW-ENTROPY TREND H1: the normalised permutation entropy (order 3) of the last 60 closes < 0.9 and the same close break -> BC
  follow.
- M085 KALMAN SLOPE TURN H1: local-linear-trend Kalman filter of closes (measurement variance = the variance of the previous 250
  close changes; process variances 0.01 and 0.0001 of it for level and slope); the slope changes sign -> BC.
- M086 DAILY AUTOCORRELATION TREND: the lag-1 autocorrelation of the last 60 daily log returns > +0.1 -> DL at yesterday's high / low.
- M087 DAILY AUTOCORRELATION REVERSION: < -0.1 -> DL FADE at yesterday's high / low.

## F. IMPLIED VOLATILITY (research only, Yahoo daily, last close strictly before the day) - USI
- M088 VIX TERM STEEPENING: (VIX3M - VIX) minus its value 5 trading days earlier >= +1.5 -> NB long-only.
- M089 VIX COMPLACENCY: VIX at or below the 10th percentile of its last 252 closes -> NB FADE.
- M090 IMPLIED OVER REALISED: VIX - the market's 20-day realised volatility (annualised, in %) >= 8 -> NB FADE.
- M091 REALISED OVER IMPLIED: realised - VIX >= 0 -> NB FOLLOW.

## G. CME VOLUME REGIMES (research) - CME4
- M092 CLIMAX-DAY REVERSAL: yesterday's session volume >= 2x its 20-session median with close-to-close <= -1 ATR20 -> today's CME
  session box long-only; >= +1 ATR20 -> short-only.
- M093 ACTIVE MARKET: the 10-session mean volume / the 60-session mean >= 1.2 -> CME session box FOLLOW.
- M094 QUIET MARKET: that ratio <= 0.8 -> CME session box FADE.

## D2. TWO MORE UNTESTED INDICATORS - ALL
- M095 INVERSE FISHER RSI H1: IFT of 0.1 x (RSI5 - 50) smoothed by WMA9; crosses above -0.5 -> BC long; below +0.5 -> BC short.
- M096 WILLIAMS VIX FIX D1: WVF = (22-day highest close - low) / highest close; WVF above its upper Bollinger band (20, 2) yesterday
  -> DL long-only at yesterday's high; the inverted fix (high - 22-day lowest close) / lowest close above its band -> DL short-only
  at yesterday's low.

## H. US HOLIDAY CALENDAR (scheduled; holidays = weekdays without a SPY close)
- M097 US-HOLIDAY FX FADE (FX): on US market holidays -> LB FADE.
- M098 BEFORE A US HOLIDAY (USI): the trading day before -> NB FADE.
- M099 AFTER A US HOLIDAY (USI): the trading day after -> NB FOLLOW.
- M100 CME RELATIVE-VOLUME LEADER (NSDQ, SP): the index whose 09:30-09:59 CME volume / its 20-session median is higher -> only its NB
  FOLLOW.

## Periods
DEV 2022-01-01 .. 2024-12-31; VAL 2025; HOLD 2026-01-01 .. 2026-10-16 (CME ideas to 2026-09-25, VIX-file ideas to 2026-09-21), one
look, only for ideas passing DEV and VAL.

## Acceptance (per idea, pooled over its universe)
- DEV: n >= 100; mean net R > 0 with day-clustered t >= 3.29 (Bonferroni, 100 one-sided tests at 5%); positive in >= 2 of the 3
  years; direction information mean(R - R_mirror) > 0 with t >= 2.0. VAL: mean > 0 with t >= 1.65. HOLD: mean > 0 with t >= 1.65.
- Account environment: the 5 best by DEV t and any passer replayed from 95,472 with the MT5 broker rules on 2022-25 trades (universe at $50 a
  trade, at most 5 a day; NSDQ + XAUUSD at $250 where present); usable only if P(pass) > P(breach) by 30 Jun 2027.
- Multiple-testing context: the 100 DEV t-values against the null (about 5 above t 1.65 by luck), by group (A spread, B + G CME
  volume, C cross-market, D + D2 + E price-only indicators, F VIX, H calendar).

## Dry run (no P&L)
Counts per idea and period, markets per idea, long share, median stop in spreads; truncation test (random cuts on EURUSD, XAUUSD,
NSDQ: tests and helpers entered >= 35 days before the cut must be identical); hand check of one entry for 12 ideas.

## Honest prior
About 0-1 pass. The 35 price-only indicators (D, D2, E) are the kind BRK26 / BRK30 found at a DEV t mean of -1.6. The
new-information groups are small (CME4 = 4 markets; FX-wide, breadth and holiday states are rare) and their spread and volume
states have to beat MT5 broker's spread on the same session boxes that lost it before. A positive here would start its own research window
and need MT5 broker real ticks (and, for B / G, MT5 tick volume) before it means anything.
