"""Check an MT5 Strategy Tester deal list against the MT5 1-Step rules.

    python forex/early_mt5/tester_report_check.py deals.csv [--initial 100000]

`deals.csv`: one row per closed deal with columns `time` (tester server time, parsed as Europe/Prague wall time),
`profit`, and optionally `commission` and `swap` (net = profit + commission + swap). Export from the tester's
Results tab ("Export to CSV") or write the three columns by hand. Closed-trade accounting only: an intraday
equity dip that recovered before the close of the deal is not visible here (needs the tester's equity curve).

Reports per MT5 broker day (CE(S)T): net P&L, worst day vs the 3% daily-loss limit, end-of-day balance drawdown vs the
10% limit, and the Best Day rule (best day <= 50% of the total profit).
"""
import argparse
import pandas as pd

DAILY_LIMIT, MAX_LIMIT, BEST_DAY_SHARE = 0.03, 0.10, 0.50


def check(deals: pd.DataFrame, initial: float = 100_000.0) -> dict:
    d = deals.copy()
    d["net"] = d["profit"] + d.get("commission", 0) + d.get("swap", 0)
    d["day"] = pd.to_datetime(d["time"]).dt.date
    daily = d.groupby("day")["net"].sum()
    bal = initial + daily.cumsum()
    start = bal.shift(1, fill_value=initial)
    daily_pct = daily / start
    eod_dd = (bal.cummax() - bal) / bal.cummax()
    total = float(daily.sum())
    best = float(daily.max())
    return {
        "days": len(daily), "trades": len(d), "net": total, "return_pct": total / initial,
        "worst_day": float(daily.min()), "worst_day_pct": float(daily_pct.min()), "worst_day_date": str(daily_pct.idxmin()),
        "daily_limit_ok": bool(daily_pct.min() > -DAILY_LIMIT),
        "max_eod_drawdown_pct": float(eod_dd.max()), "max_loss_ok": bool(bal.min() > initial * (1 - MAX_LIMIT)),
        "best_day": best, "best_day_share": best / total if total > 0 else None,
        "best_day_rule_ok": bool(total > 0 and best <= BEST_DAY_SHARE * total),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv"); ap.add_argument("--initial", type=float, default=100_000.0)
    a = ap.parse_args()
    r = check(pd.read_csv(a.csv), a.initial)
    for k, v in r.items():
        print(f"{k:24} {v:.4f}" if isinstance(v, float) else f"{k:24} {v}")


if __name__ == "__main__":
    main()
