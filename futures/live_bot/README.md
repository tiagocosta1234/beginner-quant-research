# live_bot — BrokerAPI $250k Freedom Test execution infrastructure

Strategy-agnostic live-trading scaffold for account `ACCOUNT-ID`.
Built 2026-09-18. **Auth/order/event round-trip confirmed against the real
BrokerAPI/BrokerAPI API on the Practice account (2026-09-21/22)** — see the
Verification Checklist at the bottom. The real (non-Practice) account has not
been separately exercised; treat that as its own go-live step, not implied by
the Practice-account confirmation.

## Why it's structured this way

Three concerns are kept strictly separate so a bug in one can't silently break
another:

- **`risk_governor.py`** — enforces Broker's account-survival rules (daily loss
  limit, trailing drawdown floor, consistency cap, session flatten time,
  per-trade position-size cap, consecutive-loss lockout, optional dynamic
  equity-scaled sizing). Has zero network dependency and is fully unit tested
  (`tests/test_risk_governor.py`, 27/27 passing as of this writing) with
  synthetic P&L sequences. This is the one file that should be hardest to get
  wrong, so it's the one most thoroughly tested.
- **`broker_client.py`** — thin wrapper around the `brokerapi-py` SDK
  (github.com/TexasCoding/brokerapi-py, installed as v4.3.1) for auth, bars,
  bracket orders, trailing-stop orders, and flatten-all. Defaults to `dry_run`
  mode, which makes **no network calls whatsoever** — you have to explicitly
  set `BOT_MODE=practice` or `BOT_MODE=live` (and for live, an additional
  confirmation env var) to connect to anything real.
- **`strategy_interface.py`** — the `Strategy` abstract base class any strategy
  plugs into, and two real implementations: **`random_entry_atr_trail_strategy.py`**
  (MNQ, wired up 2026-09-20) and **`support_resistance_bounce_strategy.py`**
  (MGC, wired up 2026-09-20) — read each file's own module docstring before
  using it. Each pairs with one instrument (`BOT_INSTRUMENT`); running both
  together means running two separate bot processes against the same account
  (see "Running both edges together" below). `NoOpStrategy`
  (the default) is a stub that always holds, used only to prove the pipeline
  runs end-to-end. A `Signal` for `ENTER_LONG`/`ENTER_SHORT` sets EITHER
  `stop_loss_price`+`take_profit_price` (a fixed bracket) OR
  `initial_stop_distance_points`+`trail_distance_points` (a trailing-stop exit,
  no fixed target — what the validated strategy uses), plus optionally
  `risk_dollars` (the strategy's own default dollar risk, overridden by
  dynamic sizing when enabled) — `main.py` refuses to place an order without a
  complete pair of one shape or the other, since `RiskGovernor.check_position_size()`
  can't gate a risk it can't see.
- **`main.py`** — wires the three together into a poll loop: evaluate risk →
  flatten if breached → otherwise fetch bars → ask the strategy for a signal →
  resolve sizing (fixed or dynamic) → place an order if risk allows, via
  whichever order shape the signal used. Strategy and sizing policy are both
  selected via env vars (`BOT_STRATEGY`, `BOT_DYNAMIC_SIZING`), both defaulting
  to the safe/inert choice — see the module docstring.

A strategy can never bypass risk governance: `Strategy.on_bar()` only sees bars
and returns a `Signal`; it has no access to the broker or account state, so it
physically cannot place an order or ignore a lockout. Only `main.py` (which
always checks `governor.evaluate()` first) can do that.

## Setup

Run all commands from the repo root (`beginner-quant-research/`), not from inside `live_bot/`
— `main.py` uses absolute `live_bot.*` imports:

```bash
pip install -r live_bot/requirements.txt   # installs brokerapi-py
cp live_bot/.env.example live_bot/.env     # then fill in real values
python live_bot/tests/test_risk_governor.py                        # 27/27, no network needed
python live_bot/tests/test_random_entry_atr_trail_strategy.py      # 8/8, no network needed
python live_bot/tests/test_support_resistance_bounce_strategy.py   # 9/9, no network needed
python live_bot/tests/test_main_integration.py                     # 8/8, no network needed
python -m live_bot.main                     # dry_run by default — safe, no network calls
```

## Running both edges together (Round 31/33/34 — INVALIDATED 2026-09-20, do not use these numbers)

**The $245/$650 sizing below, and every probability number that came with it,
was based on a confirmed backtest bug (a "phantom-touch" fill in the MGC
signal generator that credited entries at an idealized price the market never
actually offered — see `futures/docs/EDGE_AUDIT_2026-09-20.md`).
The bug is now fixed. Re-running Round 34's sizing sweep with the fix in place
gives dramatically worse numbers: at the old $245/$650 point, success drops
from the previously-reported 87.8% to 11.7%, and ruin rises from 3.8% to
58.8%. A full sweep from 0.5x to 4.5x of the original individually-safe sizes
found NO point with a favorable success/ruin tradeoff — ruin exceeds success
at every single size tested, including the smallest. Do not deploy at $245/
$650, or any of the sizes this section used to recommend, until this is
re-derived. See `futures/docs/EDGE_AUDIT_2026-09-20.md` for the
current numbers and status.**

Original (now invalidated) text, kept for history: Round 31 found that running
MNQ and MGC together, sized well above each edge's own individually-safe level
($75/$200), gave dramatically better odds of reaching the account's profit
target before the real 2026-10-30 withdrawal deadline than staying at those "safe"
sizes. Round 34 refined this to MNQ $245/trade, MGC $650/trade. That
conclusion no longer holds with the fixed fill logic.

To run both (mechanically, once a real sizing recommendation exists): two
separate `python -m live_bot.main` processes against the same account, one
with `BOT_INSTRUMENT=MNQ BOT_STRATEGY=random_entry_atr_trail`, the other with
`BOT_INSTRUMENT=MGC BOT_STRATEGY=support_resistance_bounce`, each with its own
`AccountConfig.max_single_trade_risk`. This file does not orchestrate
multi-instrument trading within one process.

### MNQ-only, time-of-day-filtered, $1500/trade configuration (discussed 2026-09-20/21)

A specific launch spec was discussed and partly implemented: MNQ only (MGC/VWAP-Z/busted-FVG
disabled — the latter two were research-only and were never wired into live_bot to begin with),
Round 39's time-of-day filter on, $1500/trade, a single-loss daily circuit breaker, plain ATR
trailing exit (no partials — Round 55 tested a partial-profit/runner variant and found it
significantly *hurts* this edge, since the edge's value comes from letting the full position run).

```bash
BOT_MODE=practice BOT_INSTRUMENT=MNQ BOT_STRATEGY=random_entry_atr_trail \
BOT_TOD_FILTER=1 MAX_SINGLE_TRADE_RISK=1500 CONSECUTIVE_LOSS_LIMIT=1 \
python -m live_bot.main
```

**Before running this for real, two things are still unresolved, not just theoretically but
concretely:**
1. **The claimed "Broker micro-to-mini 10:1 ratio contract limit" is unverified.** It is not
   documented anywhere in `Knowledge_Base/BROKERAPI_API_REFERENCE.md` or elsewhere in this repo.
   At $1500/trade this strategy averages ~22 MNQ contracts per trade (real 15m-ATR-derived stop
   distances vary, so any individual trade could be higher or lower) — confirm the account's real
   per-instrument position limit before assuming that size is unconditionally fine.
2. **Even at $1500/trade this is still a net-unfavorable bet, just a much closer one than anything
   else found in this campaign.** Round 34/38/53-style Monte Carlo on this exact configuration:
   P(success) 29.8%→38.0%, P(ruin) 38.4%→41.3% across the 20→27 day windows — the closest
   success/ruin ratio (~1.1:1) found anywhere tonight, versus 3-4x ruin-dominance everywhere else,
   but ruin still exceeds success at every point checked. This is a real, informed trade-off, not
   a solved problem.

Getting a BrokerAPI API key: BrokerAPI platform → Settings → API
(`brokerapi.com/settings?tab=api`), or `dashboard.brokerapi.com`. Requires an
active BrokerAPI API subscription (~$14.50/mo with the Broker discount code
`broker`, per Knowledge_Base/BROKERAPI_API_REFERENCE.md).

## Modes

| `BOT_MODE` | Network calls? | Account touched |
|---|---|---|
| `dry_run` (default) | None | None |
| `practice` | Yes | BrokerAPI Practice account (same API surface, zero real-money risk) |
| `live` | Yes | Whatever `BROKERAPI_ACCOUNT_NAME` resolves to — **also requires `BOT_CONFIRM_LIVE=I_UNDERSTAND_THIS_IS_REAL_MONEY`** |

**Do not set `BOT_MODE=live` until every item below is checked off.**

## History caches and the daily updater (2026-09-30)

Two strategies need more history than the broker's live 1-minute window (~22 sessions):
the bracket bot's Round 244 POC filter (`daily_history.py`, one OHLC row per session) and
the Combined bot's meta-model (`session_history.py`, profile + POC-trade outcome per
session). Each starts from a Databento seed in `data/` and appends completed sessions to
`state/`. The bots append while they run; `update_history.py` does it once a day
without them, so a stretch with no bot running can't leave a hole (the broker keeps
1-minute history for the active contract only, ~2 months).

```
python -m live_bot.update_history --dry-run   # what would be added; writes nothing
python -m live_bot.update_history             # update both caches
```

Read-only against the broker (login + bar history). Log: `logs/update_history.log`;
last run and contract: `state/history_updater.json`. Exit 2 means a hole the broker
can no longer fill: rebuild the seeds with `futures/engine/build_daily_rth_seed.py`
and `build_session_seed.py` from fresh Databento data. `register_history_updater.ps1`
schedules it daily at 22:30 local. A session counts as complete when the feed covers it
from 09:30 to at least 12:59, so the 13:00 ET early-close holidays are kept, as in the
seeds. At a contract roll the caches carry the same price jump the Databento seed has
at every roll; the updater logs the contract change.

## What's confirmed vs. what still needs a real API key

Confirmed today (see Knowledge_Base/BROKERAPI_API_REFERENCE.md for full research):
- The BrokerAPI API *can* trade Test/test accounts (Broker's own help
  docs), not just live ones — only *Live* Live accounts are blocked from API
  trading.
- A Practice account exists with an identical API surface for pre-live testing.
- Method signatures in `broker_client.py` were taken from `brokerapi_py`'s
  actual installed source via `inspect.signature`, not guessed.

**Fixed in code since (2026-09-19), but still needs a real API key to verify end-to-end:**
- **Item 8 (governor seeding)** — `main.py` now reads `ACCOUNT_STARTING_BALANCE` /
  `ACCOUNT_STARTING_HWM` from the environment (defaulting to the real known values,
  $245,815.38 / $250,877.88, not the $250k-fresh-start config defaults), and in
  practice/live mode overrides the balance with `broker.get_account_balance()`
  (reads `client.account_info.balance`, populated at auth — no extra network call).
  The dry-run smoke test now correctly reports a **$4,937.50** buffer. The
  high-water-mark still has no live-API equivalent (BrokerAPI's `Account` model
  doesn't expose trading history) and must still be kept accurate by hand.
- **Item 10 (unrealized P&L blindness)** — `RiskGovernor` now has
  `update_unrealized_pnl()` / `current_equity()` / `daily_total_pnl()`, and both the
  DLL and trailing-drawdown checks include floating P&L, not just realized. `main.py`
  polls `broker.get_unrealized_pnl()` every loop iteration (same 30s cadence as bar
  fetches) and feeds it in. This resolves the question raised in the original item 10
  by taking the conservative assumption either way: even if Broker only evaluates
  these thresholds EOD-settled, checking real-time floating P&L too can only make the
  bot *more* cautious, never less. 4 new unit tests cover this
  (`test_unrealized_loss_alone_triggers_daily_loss_limit` etc., 13/13 passing).
  `get_unrealized_pnl()`'s implementation was built from `calculate_position_pnl()`
  after discovering via `inspect.getsource(Position)` that the SDK's own
  `client/trading.py` docstring example (`pos.unrealizedPnl`) references a field that
  doesn't actually exist on the `Position` model — a reminder to verify every SDK
  usage against source, not docstrings/examples, the same way item 4 below already
  had to.
- **Per-trade position-size cap + consecutive-loss lockout (2026-09-19)** —
  `RiskGovernor` had no gate on a single trade's size, and no automatic response
  to a losing streak within a day; both were added after reviewing this
  account's Notion "Live Trading Journal" (93 discretionary trades, Jan-Jun
  2026), which found position-size variance — not signal quality — caused most
  of the account's real historical damage (at least 9 separate blown
  live/eval accounts, several explicitly self-diagnosed as oversized or
  "accidental" risk in the moment). `check_position_size(proposed_risk_dollars)`
  rejects any new entry whose risk exceeds `AccountConfig.max_single_trade_risk`
  (default $700, raised from $600 on 2026-09-20 to fit Round 34's refined
  $650 MGC sizing — see "Running both edges together" above) **or** the
  drawdown buffer actually remaining right now,
  whichever is smaller — the buffer check matters on its own because it shrinks
  over time and a trade sized within the fixed cap can still be large enough,
  late in a drawdown, to breach the floor outright. `consecutive_loss_limit`
  (default 2) locks out new entries after that many realized losses in a row in
  one day (a breakeven fill neither extends nor resets the streak), automating
  a discipline the same journal shows was sometimes self-imposed and sometimes
  not. Both wired into `main.py`'s order-placement path — see the
  `strategy_interface.py` bullet above for the new `Signal.risk_dollars`
  requirement this depends on. 8 unit tests cover this
  (`test_position_size_*`, `test_consecutive_losses_*`).
- **A real strategy + trailing-stop order flow + dynamic sizing (2026-09-20)**
  — item 8 below is resolved. `random_entry_atr_trail_strategy.py` implements
  the one edge validated in `futures/docs/EDGE_VALIDATION_RESULTS.md`
  Rounds 19-26 (random daily entry timing/direction, ATR-based stop that only
  ever trails tighter, no fixed target — read that file's module docstring for
  why the entry is genuinely random and that's not a placeholder). Since a
  trailing-stop exit has no fixed target, `place_bracket_order` can't express
  it (it requires both a stop AND a target) — added
  `broker_client.place_market_entry_with_trailing_stop()` (plain market entry
  + a separate native `place_trailing_stop_order` call) and a second `Signal`
  shape (`initial_stop_distance_points`/`trail_distance_points`) for it.
  `risk_governor.py` gained opt-in dynamic, equity-scaled sizing
  (`DynamicSizingConfig`, `compute_dynamic_risk()`) — Round 26 found this
  changes the shape of the risk/reward trade-off, not just its size: at the
  best fixed-dollar sizing (Round 25), simulated probability of reaching the
  account's profit target before the deadline was ~24% against ~66% probability
  of blowing the account first; at Round 26's best dynamic rule, those become
  ~21%/~12% — the first configuration across the whole campaign where success
  is more likely than ruin, though still far from safe. Neither the strategy
  nor dynamic sizing is the default — `main.py` still defaults to
  `NoOpStrategy` and fixed sizing; both are opt-in via `BOT_STRATEGY` /
  `BOT_DYNAMIC_SIZING` env vars, deliberately, since switching either on is a
  real risk decision this code should not make silently. 8 new unit tests
  (`tests/test_random_entry_atr_trail_strategy.py`) plus 6 more for dynamic
  sizing in `test_risk_governor.py` (27/27 passing there now). While building
  this, found and fixed a real bug before it shipped: the strategy's daily
  entry-timing counter was initially counting `on_bar()` *poll calls*, not
  actual elapsed 1-minute bars — harmless-looking until the mismatch between
  `main.py`'s 30-second poll cadence and 1-minute bars would have desynced the
  random-entry trigger from the session position the backtest's timing was
  actually based on. Caught by the test suite before it ever ran against real
  data.
- **Integration test for the signal → sizing → order wiring (2026-09-20)** —
  every piece above was unit-tested in isolation (the strategy alone, the
  governor alone), but the WIRING between them inside `main.py` never was,
  until `tests/test_main_integration.py` (8 tests, a `FakeBroker` standing in
  for the network). Exactly this seam is where the poll-count bug hid. Also
  required extracting the order-placement logic out of `run()`'s loop into a
  standalone `handle_entry_signal()` function so it could be tested without a
  real event loop/connection — behavior unchanged, `run()` just calls it now.
  Covers: correct contract-count math for both fixed and dynamic sizing,
  bracket vs. trailing-stop order routing, refusing to trade over an existing
  position, refusing an over-cap risk, refusing an incomplete signal, and —
  the one that matters most — **immediately flattening if a trailing-stop
  placement fails after the entry already filled**, so a position is never
  left open with no protective stop. 48/48 tests passing across all four files
  in this directory now.

**Still unconfirmed / do not skip:**
1. **Real auth round-trip** — `BrokerAPI.from_env()` / `TradingSuite.create()`
   has never been called with a real API key in this session. First thing to
   test once a key exists — this would also be the first real test of the item-8/10
   fixes above (`get_account_balance()`, `get_unrealized_pnl()`), which are
   verified against SDK source but not yet against a live connection.
2. **Consistency cap %** — `risk_governor.AccountConfig.consistency_cap_pct`
   defaults to 0.50 (the stricter of two candidates found in research; the trader's
   dashboard reportedly shows 55%). Verify the real number on the BrokerAPI
   dashboard and update the default before going live — this number directly
   gates how much profit the bot is allowed to book on a good day.
3. **Static lock HWM** — `AccountConfig.static_lock_hwm` defaults to `None`
   (floor trails forever, the conservative assumption). If this $250k Freedom
   Test product has a static-lock mechanic like the $50k Broker product
   documented elsewhere in this repo, find the real lock level and set it —
   otherwise the bot may be more conservative than necessary, holding size back
   near a floor that's actually already locked.
4. **`Order/place` bracket schema gotcha** — per
   Knowledge_Base/BROKERAPI_API_REFERENCE.md, bracket order fields are silently
   rejected unless the account has **"Auto OCO Brackets"** enabled in Broker
   account settings (default is "Position Brackets"). Check/enable this before
   the first practice-account order, or `place_bracket_order` calls may fail or
   behave unexpectedly.
5. **Rate limits** — BrokerAPI's own server-side limit still isn't documented
   anywhere found, but the SDK's self-imposed CLIENT-side throttle is now
   confirmed via source (`brokerapi_py/models.py`): `BrokerAPIConfig.requests_per_minute`
   defaults to **60/min**, enforced by `RateLimiter` inside `client/base.py` —
   `TradingSuite.create()` uses this by default unless overridden via
   `BROKERAPI_REQUESTS_PER_MINUTE`. `main.py`'s 30s poll cadence makes at most 2
   calls per cycle (`get_bars` + `get_unrealized_pnl`) — about 4 requests/minute
   — comfortably under the SDK's own default throttle, so the cadence is safe
   against at least this limit. Still unconfirmed: whether BrokerAPI's real
   server-side limit is looser or stricter than the SDK's client-side default.
6. **Real-time event handling** — still not wired, but now de-risked while waiting
   for a real connection: (a) `BrokerClient.on()` had a real bug, found and fixed
   2026-09-20 by reading the installed SDK source rather than guessing —
   `TradingSuite.on()` is a coroutine function (verified via
   `inspect.iscoroutinefunction`), and the previous `on()` called it without
   `await` from a plain `def`, so any subscription would have silently never
   fired; nothing in this repo called `broker.on()` yet, so this had zero blast
   radius so far, but would have been a real live-mode bug the first time it was
   used. (b) The `ORDER_FILLED` payload shape is now confirmed via SDK source
   (`order_manager/tracking.py`), not guessed: `Event.data` is
   `{"order": Order, "order_id": ..., "old_status": ..., "new_status": ...}`,
   where `Order` (per `brokerapi_py.models`) has `filledPrice`, `fillVolume`,
   `side`, `size`, `contractId`. Still NOT wired: actually calling
   `governor.record_fill()` from this event requires matching an ENTRY fill
   against its corresponding EXIT fill (by `order_id`/`contractId`) to compute a
   realized P&L delta — the event fires on every fill, not just closes, and
   getting that matching wrong risks silently double-counting or missing P&L,
   which is worse than the current polling fallback. Deliberately left as a task
   for once a live connection exists to test against, not implemented blind.
   The unrealized-P&L gap (item 10) is still covered by polling in the meantime
   (see above), so `daily_realized_pnl`/`current_balance` still won't update from
   real trades in practice/live mode until this is done.
7. ~~`contract_id` resolution~~ — **already done, this note was stale**: `main.py`'s
   `handle_entry_signal()` calls `broker.get_contract_id()` before every order
   placement (verified by re-reading the code 2026-09-20), which itself reads
   `TradingSuite`'s own connect-time resolution (`InstrumentContext.instrument_info.id`)
   rather than a separate lookup. Nothing left to do here.
8. ~~A validated strategy~~ — **done, 2026-09-20, now two**: `random_entry_atr_trail_strategy.py`
   (MNQ) and `support_resistance_bounce_strategy.py` (MGC) are both real
   implementations, opt-in via `BOT_STRATEGY=random_entry_atr_trail` /
   `support_resistance_bounce` (see the "Fixed in code since" and "Running both
   edges together" sections above). Read each file's module docstring and
   `EDGE_VALIDATION_RESULTS.md`'s Round 31 section before enabling either —
   "validated" here means each edge is real and its risk/reward was rigorously
   quantified, NOT that success is likely: Round 31's own best combined finding
   is 83.4% probability of reaching the profit target before the real
   2026-10-30 withdrawal deadline at 3x each edge's individually-safe sizing
   (against 3.8% probability of blowing the account first), not a guarantee.
   What's genuinely still open: neither code path has ever run against a real
   API key (see item 1) — `trail_price`'s units question (item 10 below) is now
   resolved via source, not just item 1's live-key gap.
9. **`get_unrealized_pnl()`'s single-instrument assumption** — assumes
   `instrument_ctx.positions.get_all_positions()` only returns this instrument's
   positions, not other instruments also open under the same suite. Fine for the
   current single-instrument config; re-verify before ever configuring more than
   one instrument at once.
10. ~~`place_trailing_stop_order`'s `trail_price` units~~ — **resolved 2026-09-20,
    via SDK source, no live key needed**: `order_manager/core.py`'s `place_order()`
    passes `trail_price` through the identical `align_price_to_tick_size()` call
    used for `limit_price`/`stop_price` — a dollar amount would never be
    tick-size-aligned, so it must be PRICE POINTS, confirming
    `place_market_entry_with_trailing_stop()`'s existing assumption was already
    correct. A real fill on the Practice account is still worth doing to be
    fully certain, but this is no longer an open, unverified guess.

## Third-party dependency note

`brokerapi-py` is not an official Broker/BrokerAPI library. It's a
well-structured, actively maintained third-party SDK (production-ready per its
own versioning), but it's handling real order placement for real money — worth
a closer read of its own source for anything safety-critical before fully
trusting it, the same way you'd want for any dependency in this position.
