"""
Read-only MT5 connection check for the MT5 broker account in forex/early_mt5/.env. Sends NO orders.

  python -m mt5broker.mt5_check

Logs in through the local MetaTrader 5 terminal, prints the account's server, currency,
leverage, balance/equity and trade mode (demo/real), and saves the real contract specs of
the symbols we research (contract size, tick value, lot min/step, spread, swap long/short,
triple-swap day, stop level, trading sessions) to forex/early_mt5/specs/symbol_specs_<date>.json --
replacing the swap/spread ASSUMPTIONS Round 248 had to make. Also reports how much M1
history the terminal serves for US100.cash.

Credentials come only from forex/early_mt5/.env (gitignored): MT5BROKER_MT5_LOGIN, MT5BROKER_MT5_PASSWORD,
MT5BROKER_MT5_SERVER, optional MT5BROKER_MT5_TERMINAL (path to terminal64.exe). They are never
printed; the login is shown masked.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYMBOLS = ("US100.cash", "US500.cash", "US30.cash", "GER40.cash", "XAUUSD")
SPEC_FIELDS = ("description", "currency_base", "currency_profit", "digits", "point", "trade_contract_size",
               "trade_tick_size", "trade_tick_value", "volume_min", "volume_step", "volume_max", "spread",
               "spread_float", "swap_mode", "swap_long", "swap_short", "swap_rollover3days", "trade_stops_level",
               "trade_freeze_level", "margin_initial", "trade_mode", "trade_calc_mode")
SWAP_MODES = {0: "disabled", 1: "points", 2: "base currency", 3: "margin currency", 4: "deposit currency",
              5: "% of current price (annual)", 6: "% of open price (annual)", 7: "reopen at close", 8: "reopen at bid"}
WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env")
    login, password, server = os.getenv("MT5BROKER_MT5_LOGIN"), os.getenv("MT5BROKER_MT5_PASSWORD"), os.getenv("MT5BROKER_MT5_SERVER")
    if not (login and password and server):
        print("forex/early_mt5/.env is missing MT5BROKER_MT5_LOGIN / MT5BROKER_MT5_PASSWORD / MT5BROKER_MT5_SERVER (see forex/early_mt5/.env.example)")
        return 2
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("The MetaTrader5 Python package is not installed (pip install MetaTrader5).")
        return 2
    kwargs = dict(login=int(login), password=password, server=server, timeout=60_000)
    terminal = os.getenv("MT5BROKER_MT5_TERMINAL")
    if terminal:
        kwargs["path"] = terminal
    if not mt5.initialize(**kwargs):
        print(f"MT5 initialize failed: {mt5.last_error()}")
        return 1
    try:
        acc = mt5.account_info()
        masked = "*" * (len(login) - 3) + login[-3:]
        mode = {0: "DEMO", 1: "CONTEST", 2: "REAL"}.get(acc.trade_mode, acc.trade_mode)
        print(f"Account {masked} on {acc.server} ({mode}), {acc.currency}, leverage 1:{acc.leverage}, "
              f"balance {acc.balance:,.2f}, equity {acc.equity:,.2f}, trade allowed {acc.trade_allowed}")
        specs = {"checked_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                 "server": acc.server, "account_currency": acc.currency, "leverage": acc.leverage, "symbols": {}}
        for sym in SYMBOLS:
            if not mt5.symbol_select(sym, True):
                print(f"  {sym}: not available on this server")
                continue
            info, tick = mt5.symbol_info(sym), mt5.symbol_info_tick(sym)
            rec = {f: getattr(info, f, None) for f in SPEC_FIELDS}
            rec["swap_mode_name"] = SWAP_MODES.get(rec["swap_mode"], rec["swap_mode"])
            rec["triple_swap_day"] = WEEKDAYS[rec["swap_rollover3days"]] if rec["swap_rollover3days"] is not None else None
            if tick is not None:
                rec.update(bid=tick.bid, ask=tick.ask, spread_now=round(tick.ask - tick.bid, info.digits),
                           tick_time_utc=dt.datetime.fromtimestamp(tick.time, dt.timezone.utc).isoformat())
            specs["symbols"][sym] = rec
            print(f"  {sym}: contract {rec['trade_contract_size']}, tick {rec['trade_tick_size']} = "
                  f"{rec['trade_tick_value']} {acc.currency}, lots {rec['volume_min']}/{rec['volume_step']}.."
                  f"{rec['volume_max']}, spread {rec['spread']} pts (now {rec.get('spread_now')}), "
                  f"swap long {rec['swap_long']} / short {rec['swap_short']} ({rec['swap_mode_name']}), "
                  f"triple on {rec['triple_swap_day']}")
        rates = mt5.copy_rates_from_pos("US100.cash", mt5.TIMEFRAME_M1, 0, 100_000)
        if rates is not None and len(rates):
            first = dt.datetime.fromtimestamp(int(rates[0]["time"]), dt.timezone.utc)
            print(f"  US100.cash M1 history served: {len(rates):,} bars back to {first:%Y-%m-%d %H:%M} UTC (server time)")
            specs["us100_m1_bars"] = {"count": int(len(rates)), "first_utc": first.isoformat()}
        out = HERE / "specs" / f"symbol_specs_{dt.date.today():%Y%m%d}.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(specs, indent=1, default=str))
        print(f"Saved {out.relative_to(HERE.parent)}")
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
