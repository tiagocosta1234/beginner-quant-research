# live_bot

A small, strategy-agnostic scaffold for trading one futures instrument automatically, built in
September 2026 while testing intraday ideas on micro futures (MNQ, MGC). It ran on a practice
(simulated) account only. The broker adapter is not included: `broker_client.py` is an abstract
interface plus a `DryRunBroker` that never touches the network.

## How it is structured

Three concerns are kept apart so a bug in one cannot silently break another:

- **`risk_governor.py`**: self-imposed risk limits (daily loss limit, trailing maximum drawdown,
  best-day share, session flatten time, per-trade risk cap, consecutive-loss and losing-day
  lockouts, optional equity-scaled sizing). No network dependency; the most heavily tested file.
- **`broker_client.py`**: the `BrokerClient` interface (connect, bars, bracket and trailing-stop
  orders, flatten, balance, fills) with the contract each method must meet, `DryRunBroker`, and
  `create_broker()`. Plug a real broker in by subclassing `BrokerClient`.
- **`strategy_interface.py`**: the `Strategy` base class and `Signal`. A strategy only sees bars
  and returns a signal; it cannot reach the broker or the account, so it cannot bypass the risk
  limits. Signals are either a fixed bracket (stop + target) or a trailing stop.
- **`main.py`**: the poll loop: evaluate risk, flatten if a limit is breached, otherwise fetch
  bars, ask the strategy for a signal, size it, and place the order if the risk check allows.

Strategies included (each file's docstring explains the rule and its test history):
`disciplined_bracket_strategy.py`, `combined_strategy.py`, `cisd_trend_strategy.py`,
`ote_fvg_strategy.py`, `random_entry_atr_trail_strategy.py`,
`support_resistance_bounce_strategy.py`, `vwap_zscore_strategy.py`, `manual_strategy.py`.
None of them showed a lasting edge once tested out of sample; see the repo's docs.

## Running it

Run from the `futures/` folder (imports are `live_bot.*`):

```bash
pip install -r live_bot/requirements.txt
python live_bot/tests/test_risk_governor.py      # each test file runs on its own, no network
python -m live_bot.main                          # dry_run by default: no network calls
```

| `BOT_MODE` | Network | Needs |
|---|---|---|
| `dry_run` (default) | none | nothing |
| `practice` | yes | your own `BrokerClient` subclass |
| `live` | yes | your adapter **and** `BOT_CONFIRM_LIVE=I_UNDERSTAND_THIS_IS_REAL_MONEY` |

Other settings come from environment variables: `BOT_STRATEGY`, `BOT_INSTRUMENT`,
`BOT_TIMEFRAMES`, `BOT_INITIAL_DAYS`, `BOT_DYNAMIC_SIZING`, and the `BRACKET_*` sizing values.

## History caches

Two strategies need more history than a broker's live 1-minute window: the bracket bot's POC
filter (`daily_history.py`, one OHLC row per session) and the combined bot's meta-model
(`session_history.py`). Each starts from a seed file in `data/` (not included; build it from
your own data) and appends completed sessions to `state/`. `update_history.py` does the same
once a day without the bot running; `register_history_updater.ps1` schedules it on Windows.

## Lessons this code encodes

- Take the balance from the broker's real-time account events, never from a login snapshot.
- Filter positions to your own contract; one bot once flattened a manual trade on another
  instrument because the SDK returned every position on the account.
- Refuse a trade whose own worst case would cross the daily stop; a circuit breaker can only
  act between trades.
- Reconcile the tracked balance with the broker's every poll, and stop on a mismatch.
