# PREREG I20_CONF - confluences for the I20 post-expansion-day fade (in-sample shortlist, not a new trial)

Registered 2026-10-17 23:29 local (local clock, second PC PC-2), before any confluence split of I20 was computed.
the trader: "add more confluences to the I20 fade". I20 (BRK50: when yesterday's range > 1.8 ATR20, fade the first touch of yesterday's
high / low 08:00-19:00 local at the next minute's open, stop 0.5 ATR, exit 20:45) was the best of 54 ideas on 2022-25
(+0.100 R t 1.58 DEV, +0.310 R t 1.58 VAL, n 564 + 198). Any split of it on 2022-25 is IN-SAMPLE: I20 was chosen on these
years. This round only builds a shortlist; the decisive test stays the unchanged out-of-time check on 2020-21 (HistData, on
the main PC), and the 2026 hold-out stays sealed.

## Events
The I20 trades in `C:\work\scratch\brk50_trades.parquet` (frozen with BRK50), 38 non-crypto markets, 2022-2025 only. No 2026 row
is read. Expansion day = yesterday (the previous trading day); up day if its close > its 01:00-server open. "Touched level" =
PDH (fade = short) or PDL (fade = long).

## Confluences (7, fixed a priori; each is a yes / no flag known at the touch)
- **C1 continuation attempt:** the touched extreme is the one in the expansion's direction (PDH after an up day, PDL after a
  down day). [fading a second push in the same direction = exhaustion]
- **C2 close at the extreme:** yesterday closed in the outer 25% of its range on the side of the touched level.
  [the push into the close is what gets faded]
- **C3 stretched 5 days:** the 5-day change (yesterday's close vs 5 trading days earlier) is >= 1.5 ATR toward the touched
  level. [multi-day overextension]
- **C4 daily RSI(2) extreme:** RSI(2) of daily closes through yesterday >= 90 when the level is PDH, <= 10 when it is PDL.
  [short-term reversal; RSI(2) had t 2-3 per signal in the 2026-10-10 confluence panel]
- **C5 morning touch:** the touch is before 12:00 local.
- **C6 slow approach:** the mid moved less than 0.25 ATR toward the level in the 30 minutes before the touch. [no momentum into it]
- **C7 isolated spike:** the day before the expansion day had a range < 1.2 ATR. [a one-off shock, not a volatility regime]

## Keep rule (per confluence)
Kept only if ALL hold: R(with) > R(without) pooled over 2022-25 with Welch t >= 2.0; R(with) > R(without) in 2022-24 AND in
2025 separately; R(with) > 0 in 2022-24 AND in 2025; n(with) >= 80. Kept confluences are combined (AND) into one shortlist
rule, reported in-sample with the account view (standing rule: NSDQ + XAUUSD at $250 and the 38 markets at $50, at most 5 a
day, from 95,472, MT5 broker rules), and passed to the 2020-21 out-of-time check unchanged. If none is kept, I20 goes to that check as is.

## Honest prior
Small n (762 trades, splits of 100-500) and in-sample selection: most likely no confluence meets the keep rule, and any that
does is at least as likely luck as structure.

## Amendments
(none yet)
