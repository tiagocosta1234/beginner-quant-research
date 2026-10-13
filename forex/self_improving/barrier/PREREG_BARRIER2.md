# Pre-registration v2: the position stays open until it hits +X or -X (written 2026-10-13, before the v2 labels were computed)
the trader: "o sistema deve continuar a operar até atingir um dos limites". v1 (BARRIER_RESULT.md, 0/8) used an 8-hour window and trades that hit neither barrier lost on average, so its mean R was dragged below zero. v2 is the exact game asked for: a trade ends ONLY at +X (win, R=+1) or -X (loss, R=-1).
Changes from PREREG_BARRIER.md, everything else identical (features, models, windows, grid, floors, Bonferroni, placebo gate):
1. Window up to 480 bars (5 days) instead of 32; if neither barrier is touched in 5 days (reported, expected rare) the trade exits at the bid (ask) close with R = pnl/X.
2. Barrier checks are skipped in server hours 23 and 0 (the rollover quote artefact, see lessons); the position stays open and exposed through them, and weekend gaps count as the real price jump.
3. Rows whose resolution falls after the end of their window (A, B, VAL) get no label, so no label of one window is built from prices of the next.
4. Barrier widths k in {2, 4} one-hour volatilities (wider barriers dilute the spread, which at k=1 is ~5% of X); cells: 4 classes x 2 widths = 8, Bonferroni 0.05/8, pass needs VAL mean R >= +0.20 with >= 100 trades, >= 20 weekly clusters, excess p < 0.05/8.
Not modelled: swap / carry for the days a trade is held (a cost on gold longs and some FX); the mean holding time is reported so it can be added if any cell passes. Calibration: placebo worlds 111, 112, 113 must pass 0 cells each (sequential rule).
Expectation: with no timeouts the hit rate of a no-edge system is 50% minus the spread over X; reaching 60% still needs +0.2 R per trade. Most likely no passing cell.
