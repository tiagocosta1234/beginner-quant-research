import pandas as pd
from mt5broker.tester_report_check import check


def test_daily_loss_breach_and_best_day():
    deals = pd.DataFrame({"time": ["2026-09-24 10:00", "2026-09-25 10:00", "2026-09-26 10:00"],
                          "profit": [-3500.0, 2000.0, 1000.0]})
    r = check(deals)
    assert r["worst_day_pct"] == -0.035 and not r["daily_limit_ok"]
    assert r["max_loss_ok"]
    assert r["best_day_rule_ok"] is False   # net -500: no positive total


def test_clean_run():
    deals = pd.DataFrame({"time": ["2026-09-24 10:00", "2026-09-25 10:00", "2026-09-26 10:00"],
                          "profit": [1000.0, 1000.0, 1000.0], "commission": [-10.0] * 3})
    r = check(deals)
    assert r["daily_limit_ok"] and r["best_day_rule_ok"] and abs(r["net"] - 2970.0) < 1e-9
