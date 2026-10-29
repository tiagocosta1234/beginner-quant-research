# drift_book: the one result I can rerun from scratch

The only idea in this repo that passed every pre-registered test was a slow "drift book" (see
[docs/swap-costs.md](../docs/swap-costs.md)). The original test used broker data that I can't share, so
nobody else could check it. This folder rebuilds it on free daily data with one command, and adds a
decade the original research never looked at.

```
pip install -r requirements.txt
python -m drift_book            # downloads about 1 MB of daily closes once, then runs in a few seconds
python -m pytest drift_book     # tests on made-up prices, no network
```

Output: [results/RESULTS.md](results/RESULTS.md) and [results/equity.png](results/equity.png).

## The rules

Five markets: S&P 500, Nasdaq-100, DAX, Nikkei 225 and gold (GLD), all in USD.

1. At the last close of each week, weight each market by 1 / its 60-day volatility.
2. Only hold a market while it is above its 200-day average (the "trend filter"). Its share is not given
   to the others, so the book is partly in cash.
3. Hold until the next week. Pay 2 basis points on everything traded.

`no filter (D1)` is the same book without step 2, as a yardstick.

The book is run three times, once for each way of paying to hold a position overnight:

| column | what it means |
|---|---|
| `swap_free` | only trading costs, like the swap-free MT5 account the original test used |
| `cfd_swap` | a normal CFD account: cash rate + 2.5% a year on the position, every night (weekends count 3) |
| `futures` | the cash rate that is built into a futures price, plus a roll every quarter |

## What it shows

![equity](results/equity.png)

- **Holding cost matters as much as I thought.** Over 2010 to now the same trades make about 7.6% a
  year swap-free, 6.2% on futures and 4.3% on a CFD account. On a normal CFD account the swap eats almost
  half of it.
- **The trend filter doesn't add return, it cuts the drawdown.** Without it the book makes more (11.6%
  vs 7.6% a year) with a slightly better Sharpe (0.97 vs 0.87), but its worst drawdown is twice as deep
  (-25% vs -14%). That matches what the original research found: "the 200-day filter mainly trims the
  2022 drawdown".
- **The new decade (2010-19) is weaker:** 4.9% a year, Sharpe 0.63. It is still positive, which is what you'd
  expect from a risk premium (being paid for holding stocks and gold), not from a clever signal.
- **2026 so far is weaker here than in the original test** (+4.8% a year vs about +13%). The free data is not the
  same as broker CFD prices (see below), so I trust the direction more than the exact numbers.

## How this differs from the original

- Index levels and an ETF instead of the broker's CFD quotes. Index levels leave out dividends, so
  the stock markets look a bit worse than holding them really is.
- Daily closes instead of 1-minute bars. The original decided at 18:00 server time; here the decision
  is the week's last close, and markets close at different hours (Tokyo closes before New York opens).
- No 25% no-trade band on rebalancing, and the costs are simple flat numbers, not real spreads.

## What I would not claim

- The five markets were picked in 2026, by someone who knew US tech stocks and gold had a great decade.
  The 2010-19 test is new data but not a new choice of markets, so it is less independent than it looks.
- One Sharpe-0.9 strategy is not a business. It lost money in 2022, and it is basically "be long stocks
  and gold, sized sensibly".
- Yahoo's chart endpoint is free but unofficial. If it changes, `data.py` is the only file to fix.

## Files

| file | what it does |
|---|---|
| `data.py` | downloads and caches the closes (in `data/drift_book/`, not committed), converts to USD |
| `book.py` | weights, weekly rebalancing, the three cost models, summary stats |
| `__main__.py` | runs both books over the periods and writes the results |
| `tests/test_book.py` | no look-ahead, weights, filter, costs, weekend swap, currency conversion |
