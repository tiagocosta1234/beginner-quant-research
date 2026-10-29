# futures/_archive

The first wave of futures work (July to September 2026), kept as it was.

- `NinjaTrader_Strategies_Backup/`, `pre_campaign_ninjatrader_pinescript/`: NinjaScript (C#)
  strategies and TradingView Pine indicators from before the round-by-round engine existed.
- Root scripts: early backtests (VWAP, PO3, anomaly, momentum), a genetic walk-forward optimiser
  (`genetic_wfo.py`), an ML filter (`ml_brain.py`) and plotting helpers.
- `testing_suite/`: adversarial and boundary tests for the early simulator, including oil stress
  "challenger" scenarios.
- `data_and_results/`: small result tables and parameter files from these experiments.
- `graphify-out/`: an automatically generated knowledge graph of the code base at the time.

None of these ideas survived the stricter testing used later; see `../engine/INDEX.md`.
