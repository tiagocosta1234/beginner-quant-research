"""
Measure real execution slippage on the MT5 FREE TRIAL (demo) account: a few minimum-lot market round trips per symbol, each
closed straight away. Run only on the trader's explicit request (2026-10-01: "run a few trades on the free trial and understand if the
slippage is actually what you have in mind").

  python -m forex.slippage_probe US100.cash XAUUSD EURUSD --trips 6

Guards (the script stops, sends nothing, if any fails): the terminal is attached to the account in forex/.env (forex.data_pull.attach),
MT5 itself reports the account as DEMO (not real, not contest), the terminal allows algorithmic trading, the symbol is fully
tradable and quoting right now. Size is the symbol's minimum volume; every position it opens is closed within seconds and a final
check confirms none remains. No credentials are used or stored: it attaches to the session the terminal is already logged into.

For each round trip it records the quote at the moment of sending (bid, ask), the filled price (from the deal history), the entry
and exit slippage against that quote (positive = worse for us), the commission / fee on the deals, and the delay between the last
quote and the fill. Output: forex/specs/slippage_probe_<date>.json (prices only, no account identifiers).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np

from forex.data_pull import attach

HERE = Path(__file__).resolve().parent
MAGIC = 260101


def fill_mode(mt5, info):
    fm = info.filling_mode
    if fm & 2:
        return mt5.ORDER_FILLING_IOC
    if fm & 1:
        return mt5.ORDER_FILLING_FOK
    return mt5.ORDER_FILLING_RETURN


def deal_of(mt5, res, position=None, want_entry=0):
    """The filled deal. Market-order results often carry deal = 0 / price = 0 on this server, so look the deal up by position
    id in the history (entry 0 = in, 1 = out); a first run that used the result's own price recorded zeros."""
    for _ in range(30):
        if position:
            ds = [d for d in (mt5.history_deals_get(position=position) or []) if d.entry == want_entry]
            if ds:
                return ds[-1]
        elif res.deal:
            d = mt5.history_deals_get(ticket=res.deal)
            if d:
                return d[0]
        time.sleep(0.2)
    return None


def send(mt5, symbol, info, side, volume, tick, position=None):
    req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": volume,
           "type": mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL,
           "price": tick.ask if side == "buy" else tick.bid, "deviation": 100, "magic": MAGIC,
           "comment": "slippage probe", "type_time": mt5.ORDER_TIME_GTC, "type_filling": fill_mode(mt5, info)}
    if position is not None:
        req["position"] = position
    res = mt5.order_send(req)
    return req, res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="+")
    ap.add_argument("--trips", type=int, default=6)
    ap.add_argument("--hold", type=float, default=3.0)
    ap.add_argument("--gap", type=float, default=5.0)
    a = ap.parse_args()
    mt5 = attach()
    out = {"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "trips": []}
    try:
        acc = mt5.account_info()
        if acc.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise SystemExit(f"STOP: MT5 reports this account's trade mode as {acc.trade_mode}, not DEMO. Nothing was sent.")
        if not mt5.terminal_info().trade_allowed:
            raise SystemExit("STOP: algorithmic trading is switched off in the terminal (the Algo Trading button). Enable it and re-run. Nothing was sent.")
        out["account_mode"] = "DEMO"
        for sym in a.symbols:
            mt5.symbol_select(sym, True)
            info = mt5.symbol_info(sym)
            tick = mt5.symbol_info_tick(sym)
            if info is None or tick is None or info.trade_mode != mt5.SYMBOL_TRADE_MODE_FULL or time.time() - tick.time > 30 + 3 * 3600:
                print(f"{sym}: not tradable / not quoting now -- skipped")
                continue
            vol = info.volume_min
            for i in range(a.trips):
                side = "buy" if i % 2 == 0 else "sell"
                t0 = mt5.symbol_info_tick(sym)
                req, res = send(mt5, sym, info, side, vol, t0)
                row = dict(symbol=sym, side=side, volume=vol, bid0=t0.bid, ask0=t0.ask, retcode_open=res.retcode if res else None)
                if res is None or res.retcode != mt5.TRADE_RETCODE_DONE:
                    row["comment"] = getattr(res, "comment", "no result")
                    out["trips"].append(row)
                    print(f"{sym} {side}: open failed {row['retcode_open']} {row.get('comment')}")
                    time.sleep(a.gap)
                    continue
                d_open = None
                time.sleep(a.hold)
                pos = [p for p in (mt5.positions_get(symbol=sym) or []) if p.magic == MAGIC]
                if not pos:
                    row["comment"] = "position not found after open"
                    out["trips"].append(row)
                    continue
                d_open = deal_of(mt5, res, position=pos[0].ticket, want_entry=0)
                row.update(fill_open=float(d_open.price if d_open else pos[0].price_open), commission_open=float(d_open.commission) if d_open else None,
                           fee_open=float(d_open.fee) if d_open else None, delay_open_ms=int(d_open.time_msc - t0.time_msc) if d_open else None)
                t1 = mt5.symbol_info_tick(sym)
                cside = "sell" if side == "buy" else "buy"
                req2, res2 = send(mt5, sym, info, cside, vol, t1, position=pos[0].ticket)
                row.update(bid1=t1.bid, ask1=t1.ask, retcode_close=res2.retcode if res2 else None)
                if res2 is not None and res2.retcode == mt5.TRADE_RETCODE_DONE:
                    d_close = deal_of(mt5, res2, position=pos[0].ticket, want_entry=1)
                    row.update(fill_close=float(d_close.price if d_close else res2.price), commission_close=float(d_close.commission) if d_close else None,
                               fee_close=float(d_close.fee) if d_close else None, profit=float(d_close.profit) if d_close else None,
                               swap=float(d_close.swap) if d_close else None, delay_close_ms=int(d_close.time_msc - t1.time_msc) if d_close else None)
                    sp0, sp1 = t0.ask - t0.bid, t1.ask - t1.bid
                    e_slip = (row["fill_open"] - t0.ask) if side == "buy" else (t0.bid - row["fill_open"])
                    x_slip = (t1.bid - row["fill_close"]) if side == "buy" else (row["fill_close"] - t1.ask)
                    row.update(spread_open=sp0, spread_close=sp1, entry_slip=e_slip, exit_slip=x_slip,
                               roundtrip_cost_price=(row["fill_open"] - row["fill_close"]) if side == "buy" else (row["fill_close"] - row["fill_open"]))
                else:
                    row["comment"] = getattr(res2, "comment", "no result")
                out["trips"].append(row)
                print(f"{sym:10s} {side:4s} spread {row.get('spread_open', float('nan')):.5g}  entry slip {row.get('entry_slip', float('nan')):+.5g}  "
                      f"exit slip {row.get('exit_slip', float('nan')):+.5g}  delay {row.get('delay_open_ms')}/{row.get('delay_close_ms')} ms", flush=True)
                time.sleep(a.gap)
    finally:
        left = [p for p in (mt5.positions_get() or []) if p.magic == MAGIC]
        for p in left:                                         # safety net: close anything this script opened
            info = mt5.symbol_info(p.symbol); tk = mt5.symbol_info_tick(p.symbol)
            send(mt5, p.symbol, info, "sell" if p.type == 0 else "buy", p.volume, tk, position=p.ticket)
        left2 = [p for p in (mt5.positions_get() or []) if p.magic == MAGIC]
        out["positions_left_open"] = len(left2)
        print(f"positions left open by this script: {len(left2)}")
        mt5.shutdown()
    path = HERE / "specs" / f"slippage_probe_{dt.date.today():%Y%m%d}_{dt.datetime.now():%H%M}.json"
    path.write_text(json.dumps(out, indent=1))
    ok = [t for t in out["trips"] if "entry_slip" in t]
    for s in sorted({t["symbol"] for t in ok}):
        r = [t for t in ok if t["symbol"] == s]
        sp = np.median([t["spread_open"] for t in r])
        print(f"\n{s}: {len(r)} round trips | median quoted spread {sp:.5g} | entry slippage median {np.median([t['entry_slip'] for t in r]):+.5g} "
              f"(max {max(t['entry_slip'] for t in r):+.5g}) | exit slippage median {np.median([t['exit_slip'] for t in r]):+.5g} | "
              f"round-trip cost median {np.median([t['roundtrip_cost_price'] for t in r]):.5g} = {np.median([t['roundtrip_cost_price'] for t in r]) / sp:.2f} x spread | "
              f"commission+fee per round trip median {np.median([(t.get('commission_open') or 0) + (t.get('commission_close') or 0) + (t.get('fee_open') or 0) + (t.get('fee_close') or 0) for t in r]):.4g}")
    print(f"saved {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
