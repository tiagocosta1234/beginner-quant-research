# Batch test of the MQL5 CodeBase Expert Advisors (Round 347)

Every MT5 Expert Advisor published in the MQL5 CodeBase (1,659 on 2026-10-04) was downloaded and filtered by
`build_manifest.py` (trading EAs only; no DLL imports, no network calls, no crypto). The kept EAs are in
`sources.zip` with their symbol and timeframe in `manifest.csv`. Your second PC runs them in the MetaTrader 5
Strategy Tester on the MT5 broker demo account's own data; Claude then scores them with `analyze_reports.py` against
the 70% bar (pass the 1-Step within 30 calendar days in 70% of starts, in 2021-23 AND in 2024-26).

## On the second PC (PowerShell, in the repo folder)

```powershell
git pull origin master-h8gqs1
.\.venv\Scripts\Activate.ps1
pip install lxml
# close every MetaTrader 5 window first, then a 3-EA check:
python -m mt5broker.ea_batch.run_batch --limit 3
# if those three print "compiled=True deals=..." run everything (resumable: Ctrl+C and rerun, finished EAs are skipped):
python -m mt5broker.ea_batch.run_batch
# when done (or any time, partial results are fine):
git add -f forex/early_mt5/ea_batch/results
git commit -m "EA batch results"
git push
```

- The tester never trades the account. The config sets `AllowLiveTrading=0` and `AllowDllImport=0`.
- Each EA gets at most 15 minutes (`--timeout`), then the terminal is closed and the next one starts.
- Expect roughly 0.5-3 minutes per EA (history for each symbol downloads once, the first time).
- If the terminal is not in `C:\Program Files\MetaTrader 5`, set `$env:MT5BROKER_MT5_TERMINAL` to the full path of `terminal64.exe`.
- Leave the second PC plugged in with sleep turned off; it can run overnight.
