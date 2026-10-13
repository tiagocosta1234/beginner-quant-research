# Daily profit lock: flatten and stop for the day once the day's P&L touches the cap (2026-10-13)
## CORRECTION (same day): the first version of this file claimed +12 points at 44 bd. That number was WRONG.
It came from a shortcut (replacing a day's P&L by the cap on days whose high touched it), which kept the gains and dropped the cost of the lock: after the flatten, trades that would have opened later in the day are not taken and swing positions are closed, so the following days change. Retracted.
## Correct test: the minute-path simulator with the lock built in (clean_guard_sim.simulate with P = cap, same engine as the loss stop)
Installed system (pair x1.5 + ManualDip, guard 1,500), MIX of the MT5 broker and FT pools, fresh account:
| Lock at | pass 22 bd | pass 44 bd | breach by 60 | % of days ended by the profit lock (MT5 broker / FT) | % of days ended by the loss stop (MT5 broker / FT) |
|---|---|---|---|---|---|
| none (installed) | 17.4% | 47.5% | 2.2% | 0 / 0 | 8.1 / 3.9 |
| +2,000 | 14.3% | 44.2% | 1.8% | 10.5 / 4.6 | 7.8 / 3.8 |
| +1,500 | 9.4% | 35.6% | 1.8% | 14.0 / 7.6 | 7.4 / 3.3 |
The lock LOWERS the chance of passing (-3 points at +2,000, -12 at +1,500): it gives up the days that go on to make more and the swing carry, in exchange for a slightly lower breach. Not adopted. (ManualDip is added after the flatten as a separate series; this is a planning simulation, no live change.)
## Reading for the aim "as many +2,000 days as possible before -2,500"
In the installed system about 10% of MT5 broker-pool days (5% in the FT pool) reach +2,000 and about 8% (4%) hit the loss stop first: +2,000 days outnumber loss days only slightly, which is the small edge. Four such days are the minimum to pass; at one in ten days that is about 40 business days, matching the 48% at 44 bd. A rule on the day cannot raise that frequency; only a better signal (a higher daily Sharpe) does.
