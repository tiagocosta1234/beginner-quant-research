# Pre-registration: Family DA, the confirmed index dip-reversal rule as an ADD-ON to the gold pair on MT5 broker (written 2026-10-11, before any code or result)

The rule is not new: Round 285 found it, Round 286 confirmed it on independent 1990-2017 cash-index data (8 of 8 indices, +30 bp/trade,
P = 1.000), Round 287/288 checked real M1 fills and a 3-sigma stop on MT5 broker 2022-26 CFDs. It was rejected only as a STAND-ALONE account
(too slow) and under MT5 broker swap. Never tested: on MT5 broker (no swap, no commission, verified 2026-10-11), as a second leg next to the gold pair.
There is NO untouched hold-out for this rule in 2022-26 (Round 287 used MT5 broker 2022-26); the evidence for the edge is the 1990-2017 confirmation.
This round is a deployment check: does it survive MT5 broker prices and an EA-exact implementation, and does it raise P(pass) of the live account?

## Rule (fixed; Round 286 rule with an EA-safe clock)
Markets SP+, NSDQ+, DOW+, DAX+ (MT5 broker M1 bid/ask, `.dt` time conversion). Decision minute 15:49 New York (DAX: 17:19 Berlin), i.e. outside the
server 23:00-01:00 window. dec_t = bid close of the decision minute on day t. sigma60 = std of the last 60 daily returns of dec (min 40).
z3 = ln(dec_t / dec_t-3) / (sigma60 * sqrt(3)). LONG if z3 <= -2.0 and the next trading day is the next weekday (Mon-Thu entries).
Fill at the ask open of the next minute (15:50 / 17:20); exit next trading day at the bid open of the same minute.
Stop: 3 x sigma60 below the fill, on M1 bid lows; fill at min(stop, bar bid open).
Size: MT5 broker "1% risk per trade idea": one idea per day = all indices that signal that day share 1.0% (1,000 USD) of risk at the stop;
notional per market = 1,000 / n_signals / (3 * sigma60), capped at 150,000 USD per market. Cost: bid/ask + 0.1 bp each side.

## Outputs
Per trade and daily USD series 2022-26 on MT5 broker's server days: V (day close P&L incl. floating at the server day end), B (intraday low), Hi.
Account effect: pass70's simulation (same rules: guard 2,000, counted cap, breach, lock, no-hedge on the pair) for the pair x1.2 alone vs
pair + DA (days matched; B summed = conservative), start counted +560 on 2026-10-12, pools MT5 broker (last 12 months), FT (2022-26), MIX.

## Acceptance (all needed to build the EA)
1. Mean net per trade > 0 on MT5 broker 2022-26 and positive in at least 3 of the 5 years.
2. Daily correlation with the pair <= 0.3.
3. MIX P(pass by 22 Dec) higher by >= 3 points AND P(pass by 30 Nov) not lower, with breach at most 1 point higher.

## Amendment DA2 (written 2026-10-11 after the DA result, before any DA2 run)
DA missed acceptance 3 by one point because it is rare (about 10 signal days a year). Round 286's independent 1990-2017 confirmation
reported the edge at Z = 1.5 too (+22.5 bp/trade vs +30.2 at Z = 2, monotonic in Z). ONE extra variant, everything else unchanged:
DA2 = the same rule with Z = 1.5. Same three acceptance tests, compared with the pair alone (not with DA). This is the last variant of
this family: no other Z, stop, size or market set will be tried.
