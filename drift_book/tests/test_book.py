"""Tests on made-up prices, no network:  python -m pytest drift_book"""
import numpy as np
import pandas as pd
import pytest

from drift_book import book, data


def prices(n=400, seed=0, drift=(0.0004, 0.0002, -0.0003), vol=(0.01, 0.02, 0.01)):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    r = rng.normal(drift, vol, size=(n, len(drift)))
    return pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=idx, columns=list("ABC")[: len(drift)])


def test_no_weights_before_warm_up():
    assert book.target_weights(prices(n=book.SMA_DAYS - 1)).sum() == 0


def test_weights_sum_to_one_without_filter_and_favour_low_volatility():
    w = book.target_weights(prices(), trend_filter=False)
    assert w.sum() == pytest.approx(1.0)
    assert w["A"] > w["B"]  # B is twice as volatile


def test_trend_filter_drops_markets_below_their_average():
    p = prices()
    p["C"] = np.linspace(200, 100, len(p))  # falling steadily
    w = book.target_weights(p)
    assert w["C"] == 0 and w.sum() < 1


def test_weights_only_use_the_past():
    p = prices(n=600)
    cut = p.index[450]
    changed = p.copy()
    changed.loc[changed.index > cut] *= 3  # rewrite the future
    a = book.target_weights(p.loc[:cut])
    b = book.target_weights(changed.loc[:cut])
    pd.testing.assert_series_equal(a, b)


def test_rebalances_on_the_last_trading_day_of_each_week():
    idx = pd.DatetimeIndex(["2024-01-01", "2024-01-03", "2024-01-05", "2024-01-08", "2024-01-11"])
    assert list(book.last_day_of(idx, "W")) == [pd.Timestamp("2024-01-05"), pd.Timestamp("2024-01-11")]


def test_first_rebalance_pays_the_trading_cost_on_what_it_buys():
    idx = pd.bdate_range("2020-01-01", periods=300)
    p = pd.DataFrame({"A": np.linspace(100, 110, 300), "B": np.linspace(110, 100, 300)}, index=idx)  # A up, B down
    cash = pd.Series(0.0, index=idx)
    out = book.backtest(p, cash, book.Costs(trade_bps=10))
    first = out.trading[out.trading > 0].index[0]
    w = book.target_weights(p.loc[:first])
    assert w["B"] == 0
    assert out.trading[first] == pytest.approx(w.sum() * 10 / 1e4)
    assert out.swap.sum() > 0  # the markup is charged even with a zero cash rate
    assert (out.cfd_swap <= out.swap_free).all() and (out.futures <= out.swap_free).all()


def test_swap_is_charged_for_calendar_days_so_weekends_cost_three_nights():
    p = prices(n=300)
    cash = pd.Series(0.05, index=p.index)
    out = book.backtest(p, cash, book.Costs(trade_bps=0, swap_markup=0.0))
    held = out[out.exposure.shift(1) > 0]
    monday = held[held.index.weekday == 0].iloc[0]
    tuesday = held[held.index.weekday == 1].iloc[0]
    per_night = 0.05 / 365
    prev_exp = out.exposure.shift(1)
    assert monday.swap == pytest.approx(prev_exp[monday.name] * 3 * per_night)
    assert tuesday.swap == pytest.approx(prev_exp[tuesday.name] * per_night)


def test_to_usd_uses_the_last_known_rate():
    local = pd.Series([10.0, 10.0, 10.0], index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]))
    fx = pd.Series([1.1, 1.2], index=pd.to_datetime(["2024-01-02", "2024-01-04"]))
    assert list(data.to_usd(local, fx, "mul")) == pytest.approx([11.0, 11.0, 12.0])
    assert list(data.to_usd(local, fx, "div")) == pytest.approx([10 / 1.1, 10 / 1.1, 10 / 1.2])


def test_stats_on_a_known_series():
    r = pd.Series([0.1, -0.5, 0.0], index=pd.bdate_range("2024-01-01", periods=3))
    assert book.stats(r)["max_dd"] == pytest.approx(-0.5)
