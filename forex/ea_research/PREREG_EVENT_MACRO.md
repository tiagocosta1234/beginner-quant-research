# Pre-registration: scheduled US macro events on MT5 broker instruments (family V, two trials)

Written 2026-10-10 14:55 local (local clock; the hand-written stamp said 14:56, corrected from the commit 2782714 at 14:55:49), BEFORE any simulation of these rules. Context: the trader's goal "um novo sistema, 70% chance de passar o desafio este mes" (spec: about 500-600 USD a day, daily Sharpe 0.5-0.85); intraday stat-arb (family R) and every price-only indicator family are closed. Scheduled macro announcements are the last source of information not yet used in this lab. Even a real event edge trades only on 3-5 days a month, so it CANNOT meet the 70%-this-month spec (it would have to earn the whole month's 8% on a handful of days); the test is run for the second-leg target (+62 USD a day, 22 Dec at 70%) and to close the class.

## Calendar (public, saved before any P&L in `data\data_macro\event_calendar.csv`)
FOMC statement days from federalreserve.gov/monetarypolicy/fomccalendars.htm (second day of each scheduled meeting; the 2025-08-22 notation vote excluded); Employment Situation (NFP) and CPI release days from the BLS release archives (bls.gov/bls/news-release/empsit.htm, cpi.htm; dates from the archive file names), plus the NFP of 2022-01-07 (December 2021 report). The October 2025 reports were not published (federal funding lapse); the delayed November / December 2025 dates are kept as published. All releases at 08:30 ET, FOMC statements at 14:00 ET. Times are converted with the America/New_York and Europe/Athens (MT5 broker server) time zones.

## V1: pre-FOMC drift (Lucca and Moench 2015), long US indices
For each FOMC statement day D: buy SP, NSDQ and DOW (equal notional) at the open of the 14:02 ET minute of the previous business day, sell at the open of the 13:55 ET minute on D (before the statement). Quoted ask to buy, bid to sell, plus 0.1 bp slippage per side. Event P&L = mean of the three indices in bp.

## V2: continuation of the first 15 minutes after an 08:30 ET release (NFP and CPI days)
For each release day R and each market in XAUUSD, EURUSD, USDJPY, NSDQ: direction s = sign(mid at the open of 08:45 ET - mid at the open of 08:29 ET); enter in direction s at the open of the 08:47 ET minute (ask to buy, bid to sell, +0.1 bp), exit at the open of the 11:30 ET minute. No stop, no target. Event P&L = mean of the four markets in bp. A market with a missing minute is left out of that event.

## Statistics and periods
Per event net bp (and gross at mids), t over events, win rate, per-year means, per-market means. DEV 2022-01-01 .. 2024-12-31, VAL 2025, HOLD-OUT 2026-01-01 .. 2026-09-30 (one look, only for a trial that passes 1-2).

## Acceptance (Bonferroni, two trials)
1. DEV: mean net bp per event > 0 and t >= 2.0 (one-sided p < 0.025 for each of two trials).
2. VAL 2025: mean net bp per event > 0.
3. HOLD-OUT 2026: mean net bp per event > 0 (one look).
4. Use only as a second leg after the clean simulation shows the uplift (correlation with the pair <= 0.3, <= 1 point of extra breach) and MT5 broker's news-trading terms are checked (some account products restrict trading around high-impact news).
If 1 fails the trial is closed.

## Honest prior
V1 about 15% (the pre-FOMC drift was strong in 1994-2011 and much weaker afterwards); V2 about 7% (macro releases are absorbed within minutes in liquid markets; a 15-minute direction has weak documented continuation). Sample sizes are small (V1: 24 DEV events, 8 VAL; V2: about 72 DEV events, 22 VAL), so only a large effect can pass.

## Dry-run (2026-10-10, no P&L; `EVENT_MACRO_DRYRUN.txt`)
Time-zone conversion checked on both DST-mismatch weeks (14:02 ET = 20:02 server on 2025-03-18, 08:29 ET = 14:29 server on 2024-11-01) and on normal weeks (14:02 ET = 21:02 server, 08:29 ET = 15:29 server). V1: 38 of 40 FOMC events have all three indices quoted (the two missing are October and December 2026, still in the future). V2: 111-113 of 113 release days have all four minutes quoted per market. Calendar copy committed as `EVENT_CALENDAR_2022_2026.csv`.
