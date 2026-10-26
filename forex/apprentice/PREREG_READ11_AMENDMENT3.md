# PREREG_READ11 Amendment 3: H1 withdrawn, H2 scored mechanically on the sealed pool

Written 26 Oct 2026 ~00:1x local (local clock), after training ended and READ11 was frozen (`READ11_FROZEN.sha256`, 00:08:06), BEFORE the test pool is drawn. (The final training block in READ11.md says "~00:3x"; it was written at about 00:07.)

## Why
- H1 (read11) showed no skill on its own training days: 31 trades, excess +0.005, mean R -0.169 against always-long -0.171. Playing 150 sealed days by hand for it would cost hours and has almost no chance of clearing its bar.
- H2 (naive 08:00 30-minute trend, 1:1 at X) is mechanical, so it can be scored on the sealed pool with no calls.

## Change
- **H1 is withdrawn.** It will not be played on this test pool, and these test days can never be used for H1 or any discretionary read later (their aggregate H2 outcome will be known).
- **H2 is scored once** with `python read11.py test h2` on all 150 drawn test days. The bar is unchanged from Amendment 2: excess >= +0.10, sign-flip P <= 0.015, mean R > 0, mean R > always-long (08:02, same 1:1 bracket), n >= 40. The command refuses a second look.
- If H2 is supported: forward paper only (London 08:00, logged before the outcome). Real money stays the trader's decision; Claude places no real orders.
