# Data

No market data is included. The bars used in this research came from licensed sources (a CME
futures data vendor, broker MT5 history and platform exports) whose terms do not allow
redistribution. What the repo does include is derived results: trade lists, equity curves,
result tables and the text outputs of each test.

## Running the scripts

Most scripts read their inputs from a local `data/` folder (ignored by git) and write their
outputs next to themselves. Paths in older scripts were rewritten from absolute local paths to
`data/...`, so expect to adjust a path or two. Typical inputs:

| used for | what to supply |
|---|---|
| futures research (`futures/engine`, `futures/london_open_gold`) | CME 1-minute OHLCV bars (GC/MGC, NQ/MNQ, ES/MES, SI) in UTC, one file or parquet per symbol |
| forex research (`forex/ea_research`, `forex/apprentice`) | MT5 M1 bid/ask bars per symbol, exported from the terminal |
| live bot history caches (`futures/live_bot`) | a daily RTH OHLC seed and a session seed, built with the engine's seed builders |

Market data needs care: continuous futures series jump at each roll, CFD prices differ from
futures by the basis, and MT5 server clocks are not UTC. Every one of these caused at least one
bug during the project (see [methods.md](methods.md)).
