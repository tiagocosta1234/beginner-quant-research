"""SDS constraints: the lessons of this research as records the system can check (DESIGN.md, piece 2).
Each lesson: id, date, text, binds (engine names or "*"), and an optional `check(engine_spec, source_text) -> list of problems` that the verifier runs on the engine's source.
Adding a lesson here is how the system 'learns'; adding one triggers the regression step (re-run of the engines it binds) in loop.py."""
from __future__ import annotations

import re

# server hours (Athens clock of the MT5 broker server) around the 17:00 New York rollover: no decision, entry or exit
ROLLOVER_HOURS = (23, 0)
MT5_ONLY_BANNED_FEATURES = ("vix", "skew", "curve_chg", "dxy_chg", "fng", "stab_chg", "fund_btc", "cot_", "s_nfp", "s_cpi", "s_unr", "s_fomc", "x_ES", "x_NQ")   # series the MT5 does not offer
SEALS = {"slow families (rules, regime, ML, new info)": "2026-01-01..2026-09-30 unread", "HF tick family": "2026-08-16..2026-10-13 unread"}
FLOORS = {"net_bp_floor_slow": 3.0, "min_clusters": 20, "bh_q": 0.05, "placebo_worlds": 3, "placebo_max_passes": 0}
FORBIDDEN_IMPORTS = ("order_send", "order_check", "Buy(", "Sell(", "PositionOpen", "OrderSend", "MetaTrader5.order")      # the research package never places orders


def _has(src, pat): return re.search(pat, src) is not None


def check_rollover(spec, src):
    ok = _has(src, r"isin\([^)]*\(23, ?0\)\)") or _has(src, r"\(h == 23\)") or "ROLLOVER" in src or _has(src, r"hour.*23.*0")
    return [] if ok or spec.get("rollover_exempt") else ["no visible rollover-hour (server 23 and 0) exclusion in the engine source"]


def check_no_orders(spec, src): return [f"order function referenced: {p}" for p in FORBIDDEN_IMPORTS if p in src]


def check_tick_clock(spec, src): return ["tick/rates epoch treated as UTC (unit='ms', utc=True): the MT5 API epoch is the SERVER clock"] if re.search(r"unit=.ms.,\s*utc=True", src) else []


def check_calibration_hook(spec, src): return [] if (_has(src, r"--placebo") or _has(src, r"placebo")) else ["engine has no placebo mode: it cannot be calibrated"]


LESSONS = [
    dict(id="L01", date="2026-10-13", text="No decision, entry or exit at server hours 23 and 0: the rollover spread artefact moves the bid predictably (IC +0.52 / +0.40 there, ~0 elsewhere).", binds="*", check=check_rollover),
    dict(id="L02", date="2026-10-13", text="Test excess over random timing (same market, side, horizon, grid), never 'mean > 0': drift makes any long rule 'significant'.", binds="*", check=None),
    dict(id="L03", date="2026-10-13", text="An adaptive search needs an explore / confirm split; the false-discovery control applies only to rules confirmed on data the search never saw.", binds="freeform", check=None),
    dict(id="L04", date="2026-10-13", text="Gross returns must not contain spread at the exit bar (bid-to-bid); cost avoidance by hour is not timing skill.", binds="freeform", check=None),
    dict(id="L05", date="2026-10-13", text="Few clusters: Student t with G-1 degrees of freedom and the sqrt(G/(G-1)) correction.", binds="*", check=None),
    dict(id="L06", date="2026-10-13", text="One entry per horizon per market: persistent signals must not be counted as many independent trades.", binds="*", check=None),
    dict(id="L07", date="2026-10-13", text="Every engine must have a placebo mode and be calibrated (0 passing cells in fresh worlds) before its real result is read.", binds="*", check=check_calibration_hook),
    dict(id="L08", date="2026-10-13", text="Passive limit orders do not earn the spread on an MT5 dealer-model account (a buy limit fills when the ASK reaches it).", binds="hf", check=None),
    dict(id="L09", date="2026-10-13", text="Only MT5-native information is deployable (prices, spreads, tick_volume, other symbols, MT5 economic calendar); external series are research-only.", binds="*", check=None),
    dict(id="L10", date="2026-10-13", text="Total open stop-risk must be capped in the MT5 broker environment (flat risk per trade on correlated signals breaches the account).", binds="freeform", check=None),
    dict(id="L12", date="2026-10-13", text="The placebo gate has a nominal false-failure rate (~5% per world); use the sequential rule (0 of 3, else at most 1 of 10), never 'any pass = broken'.", binds="*", check=None),
    dict(id="L13", date="2026-10-13", text="MT5 Python API times (ticks, rates) are on the SERVER clock (Europe/Athens, naive), the MT5 calendar is UTC: convert before aligning; verify any clock with the daily spread peak (server hour 0).", binds="*", check=check_tick_clock),
    dict(id="L11", date="2026-10-13", text="The research package never places orders and never arms Algo Trading; live changes are proposals for the trader's hand.", binds="*", check=check_no_orders),
]


def audit_engine(spec, src):
    """Run every lesson check that binds the engine; returns {lesson_id: [problems]} for the ones that fail."""
    bad = {}
    for L in LESSONS:
        if L["check"] is None or not (L["binds"] == "*" or L["binds"] == spec.get("family")): continue
        p = L["check"](spec, src)
        if p: bad[L["id"]] = p
    return bad
