# Batch test of the MQL5 CodeBase Expert Advisors (Round 347)

Every MT5 Expert Advisor published in the MQL5 CodeBase (1,659 on 2026-10-04) was downloaded and filtered by
`build_manifest.py` (trading EAs only; no DLL imports, no network calls, no crypto). 1,326 trading EAs were kept and 1,220 of them compile cleanly (checked offline with MetaEditor build 6238; the runner skips the other 106). The kept EAs are in
`sources.zip` with their symbol and timeframe in `manifest.csv`. Your second PC runs them in the MetaTrader 5
Strategy Tester on the MT5 broker demo account's own data; Claude then scores them with `analyze_reports.py` against
the 70% bar (pass the 1-Step within 30 calendar days in 70% of starts, in 2021-23 AND in 2024-26).

## On the second PC (PowerShell, in the repo folder)

```powershell
git fetch origin
git status                              # commit or stash anything of yours first
git reset --hard origin/master-h8gqs1   # once: the branch history was rewritten on 2026-10-04 (authorship) and 2026-10-05 (commit messages); later just git pull
.\.venv\Scripts\Activate.ps1
pip install lxml
# close every MetaTrader 5 window first, then a 3-EA check:
python -m forex.ea_batch.run_batch --limit 3
# if those three print "compiled=True deals=..." run everything (resumable: Ctrl+C and rerun, finished EAs are skipped):
python -m forex.ea_batch.run_batch
# when done (or any time, partial results are fine):
git add -f forex/ea_batch/results
git commit -m "EA batch results"
git push
```

- The tester never trades the account. The config sets `AllowLiveTrading=0` and `AllowDllImport=0`.
- Each EA gets at most 15 minutes (`--timeout`), then the terminal is closed and the next one starts.
- Expect roughly 0.5-3 minutes per EA (history for each symbol downloads once, the first time): about 1-2 days for all 1,220.
  The order is a fixed random shuffle, so a partial run is a fair sample. Commit results whenever you want an interim analysis.
- If the terminal is not in `C:\Program Files\MetaTrader 5`, set `$env:MT5BROKER_MT5_TERMINAL` to the full path of `terminal64.exe`.
- Leave the second PC plugged in with sleep turned off; it can run overnight.

## Or in a Claude Code cloud session (no second PC needed)

the trader agreed (2026-10-05) to let Claude log the MT5 broker demo account into a cloud MT5. Add `MT5BROKER_MT5_LOGIN`, `MT5BROKER_MT5_PASSWORD`
and `MT5BROKER_MT5_SERVER` (server name exactly as MT5 shows it) as environment variables in the cloud environment's settings, start a
new session, and ask Claude to run:

```bash
bash forex/ea_batch/cloud_setup.sh                 # Wine + MetaTrader 5 (+ MT5 broker's server list), ~10 minutes
pip install pandas pyarrow lxml numpy
git lfs pull --include="forex/data/*"              # MT5 broker's own M1 bars: the tester's data in the cloud
python forex/ea_batch/cloud_run.py --limit 3       # check: at least one EA must make deals
nohup python forex/ea_batch/cloud_run.py --workers 6 > /root/ea_batch_run.log 2>&1 &   # the rest, 6 terminals at once (own Wine prefix each), resumable
nohup bash forex/ea_batch/cloud_babysit.sh > /root/ea_babysit.log 2>&1 &              # trims runaway logs, commits + pushes results every 20 EAs
bash forex/ea_batch/analyze_view.sh                # the pre-registered analyze_reports.py, unchanged, minus zero-deal files it cannot read
```

The password is written only to a one-off login config inside the Wine prefix, deleted after the terminal remembers the account,
and never printed or committed. Use a demo or free-trial account, never the paid test.

**The cloud runs the tester offline (2026-10-05).** The cloud container cannot log in to MT5 broker: its outbound port 443 goes through an
egress gateway that terminates TLS (non-TLS bytes get `426 Upgrade Required`, the session proxy resets non-TLS CONNECT tunnels, other
ports are closed), and MT5's trade protocol is not TLS. The terminal reaches MT5 broker-Demo and logs `connection to MT5 broker-Demo lost`.
The tester does not need the connection, only an account named in its config. So `cloud_run.py` builds custom symbols
`<SYMBOL>_MT5BROKER` (`ImportMT5BROKER.mq5`) from `forex/data/<SYMBOL>_M1_ticks_full.parquet` (MT5 broker's own ticks aggregated to M1 bid OHLC with the
per-minute spread, 2021-09-20..2026-10-02) and tests on those with the pre-registered model 1 (1-minute OHLC). How this differs from the second PC route:
- 9 symbols have MT5 broker M1 data in the repo (EURUSD, GBPUSD, AUDUSD, USDJPY, USDCHF, USDCAD, XAUUSD, US30.cash, US100.cash): 1,076 of
  the 1,220 compiling EAs. The 144 on GBPJPY, EURJPY, NZDUSD, XAGUSD and JP225.cash are skipped (status note).
- No commission. FX swaps are 0; gold and index swaps are MT5 broker's 2026-10-01 values. Margin is in USD.
- An EA that hard-codes a real symbol name (`"EURUSD"`) finds no data there and makes no deals.
- The EA's own indicators are compiled into `MQL5\Indicators` (where `iCustom` looks); 539 EAs ship one. `run_batch.py` does not do this yet.

Cloud gotchas (2026-10-05 run): each worker prefix is ~3.1-3.6 GB and the session's writable disk is ~20 GB, so 6 workers fit only after
deleting the npm / bun / pip download caches and the MT5 broker installer's own terminal folder in each clone. Each test spends ~35 s
waiting for a trade-server sync that never comes (then tests anyway), so workers are mostly idle and scale almost linearly. Stop
processes with `wineserver -k` per prefix (`WINEPREFIX=...`) and `pgrep -f "[c]loud_run.py"`: an unbracketed `pkill -f cloud_run.py`
also matches the shell that runs it.

## Confirmation runs in real ticks (second PC only)

The batch above used the 1-minute OHLC model (fast). To confirm a lead, run it in the tester's real-tick model on the logged-in second PC terminal:

```powershell
python -m forex.ea_batch.run_batch --only 77871,17147 --model 4 --results forex/ea_batch/results_realtick
```

`--model 4` = every tick based on real ticks; `--results` keeps these out of the batch results. Pre-register the round first (see
`Knowledge_Base/HANDOFF_LOCAL_AGENT_2026-10-05.md`, task 3).
