# DIR8_RESULT: FAIL (23 Oct 2026, local clock in the commit)

Pre-registration `PREREG_DIR8.md` (commits 55191e53 and 4cb4d3c8, Amendment 1 = a column rename after a crash that printed nothing). Output in `DIR8_OUTPUT.txt`, days in `DIR8_DAYS.csv`.
The model: logistic regression on 9 pre-08:00 features (GC overnight / last 30 min / previous day, Asia and previous-day range location, 20-day trend, SI and ES overnight, volatility regime), fit on 2020-22 (605 days), judged on 2023-24 (427 days). Target: the GC 08:00 -> 12:00 direction.

## VAL 2023-24 (one look)
- **Overall:** 228 / 427 hits (53.4%), binomial P 0.088. Always-long would have 240 (56.2%). Mean R +0.126 (t 0.82, P 0.21), carried by the gold uptrend.
- **Long calls:** 287, hit 57.1%, mean R +0.301. The up-rate on those days was 57.1%, the same as all days.
- **Short calls:** 140, hit **45.7%**, mean R **-0.233**. The up-rate on those days was 54.3%.
- **Separation:** long-call days went up 57.1% of the time, short-call days 54.3%. The model barely tells them apart.
- **Bars:**
  - (a) beats always-long: no.
  - (b) shorts work: no.
  - (c) mean R significant: no.
  - **FAIL.** HOLD 2025 not opened.
- **No bar:**
  - The top-half-confidence calls were worse (50.7%, shorts 44.7%).
  - The best single features on VAL were 53.4% (previous day, faded) and 53.2% (20-day trend, faded); the rest 46-52%.
  - Bracket (stop 2S / target 3S): +0.059 R.
- Even in-sample on DEV the fit only reached 52.4%, against always-long's 51.7%.

## What it means
- Nothing known at 08:00 in these 9 measures (gold, silver and S&P overnight action, range location, trend, volatility) separates up mornings from down mornings in a way that holds on new days.
- The only stable fact is gold's upward drift in 2023-24 (56% up mornings). It is a regime, not a signal, and shorting against it lost.
- Same finding as the blind BIAS8 calls: both the human-style read and the model call shorts at about 45%.
