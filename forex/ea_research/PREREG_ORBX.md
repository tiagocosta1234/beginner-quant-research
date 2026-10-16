# PREREG ORBX - London opening-range breakout + news-day and trend filters

Registered 2026-10-16 ~14:55 local (local clock), before any filtered P&L was computed.
Requested by the trader ("(original wording omitted)") after the descriptive GBPUSD / 46-market screens of 2026-10-16.

## What is already known (seen today, descriptive)
- Base rule (below) on the 46 MT5 broker: gross (mid) positive in 33/46 (2022-25) and 35/46 (2026); net of real
  bid/ask negative in 37/46; pooled net about -0.01R/trade (38 non-crypto markets, 2022-24). Best single market
  t 1.4 with spread (noise for 46). A portfolio of the 8 best (in-sample) made +265R 2022-26 but the 9 chosen on
  2022-25 made -3.8R in 2026.
- Net R by spread/box ratio was looked at in all periods: <= 4% is about break-even. This filter is therefore NOT a
  trial here (it is contaminated).
- 2026 has been seen for the base rule; it is reported for information only and cannot accept anything.

## Base rule (fixed, unchanged from the screen)
- Box = high/low of 08:00-08:30 local (server = local + 2 h), bid prices (as MT5 charts).
- From 08:30 to 10:00 local, first trigger only: buy stop at box high (fills when ASK reaches it), TP = high + box
  (on bid), SL = box low (on bid); or sell stop at box low (fills when BID reaches it), TP = low - box, SL = box high
  (on ask). One trade per market per day. Exit 17:00 local if neither hit. Same-minute TP+SL = SL; on the entry
  bar only the SL counts. R = P&L / |entry - SL|.
- Universe: the 38 non-crypto MT5 broker in `forex/data_mt5` (crypto excluded: spread/box makes them -0.2..-0.7R/trade,
  seen today).

## Trials (3; the base rule is the yardstick, not a trial)
- **N  news day**: the day has at least one importance-3 event in the MT5 economic calendar
  (`D:/finance/data_macro/mt5_calendar.csv`, times UTC) for one of the market's currencies with release time in
  [06:00, 10:00) local. Currencies: FX = both legs; XAUUSD, XAGUSD, WTI, BRENT, SP, NSDQ, DOW = USD; DAX = EUR;
  NIKKEI = JPY; ASX = AUD.
- **T  trend agreement**: breakout side == sign(close of the previous server day - close of the server day before
  it), mid prices, last M1 bar of each day. Zero change = no trade.
- **NT**: both N and T.

## Periods
- DEV 2022-01-01 .. 2024-12-31 (selection), VAL 2025-01-01 .. 2025-12-31 (one look, passers only).
- 2026-01-01 .. 2026-10-02: information only (base rule already seen). Final confirmation of any passer = forward paper
  record from 2026-10-19, no live money.
- Calendar coverage ends 2026-08-15: N and NT are reported for 2026 only up to that date.

## Statistics and acceptance
- Unit: net R per trade (real bid/ask), pooled over markets; standard error clustered by day (trades of one day are
  correlated); t = mean / clustered SE.
- Placebo: for each trial, 500 draws keeping the same number of trades per market but on random days of that
  market's DEV trades; the real DEV mean must exceed the placebo 95th percentile.
- DEV pass: mean > 0, clustered t >= 2.4 (Bonferroni for 3 one-sided trials at 5% is z 2.13; rounded up for
  heavy tails), above the placebo 95th percentile, and >= 300 trades.
- VAL pass (only for DEV passers): mean > 0, clustered t >= 1.65, >= 100 trades.
- Anything that passes both still needs the MT5 broker pass-speed gate before it is called usable.

## Honest prior
Below 10%. Opening-range information is public; the gross edge is about +0.02R/trade against a cost of the same
size. A news day can enlarge the box (lower cost share) but can also make the first break a fake-out.

## Kill rule
If no trial passes DEV and VAL, the London opening-range breakout family is closed for this account.
Variants used today on this family (descriptive): about 15; these 3 trials bring the window to about 18 of 40.

Script: `python -m forex.ea_research.orbx --dry-run` (counts only, no P&L), then `--run`.
