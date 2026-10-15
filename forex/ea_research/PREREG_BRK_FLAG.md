# Pre-registration BRK-FLAG (breakout day, round 22; written 2026-10-15 12:49 local (commit time), before any code or result)
Flag continuation breakouts (bull / bear flags), defined mechanically on M5 mid bars (session clock), inside each market's main session (round 1 sessions), 46 MT5 broker.
- **Impulse:** the move from the lowest low to the highest high (bull) of 6 consecutive M5 bars is >= 1.5 x ATR14(M5) and the 6th bar closes in the top quarter of that range.
- **Flag:** the next 6 to 18 bars stay inside a range no taller than 40% of the impulse, and never retrace more than 50% of the impulse.
- **Entry:** a buy stop at the flag's high (ask), live while the flag lasts (up to bar 18 after the impulse) - the first bar that trades through it; bear flags mirrored.
- **Stop:** the flag's low at the entry (R = entry - flag low). Exits (2 cells): F1 target = entry + the impulse's height (the classic "flagpole" target), F2 hold to the session close. Flat at the session close in both (capped 22:55 server). One trade per market at a time; entries until 2 hours before the close.
Random-entry control (a random minute in the same session, random side, same R and exit). Gates (DEV 2022-24, VAL 2025, 2026 non-clean): DEV mean >= +0.05 R and t >= 2.24 (daily NW lag 1; Bonferroni 2); VAL mean > 0 and t >= 1.65; beats its control by >= 0.05 R in DEV and VAL.
Honest prior: about 5%.
