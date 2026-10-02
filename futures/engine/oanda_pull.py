"""
Download OANDA 1-minute history (bid, ask and mid candles) through OANDA's v20 REST API -- the same feed TradingView's OANDA charts use.

SETUP (you do this yourself; nothing here creates accounts or reads secrets from chat):
  1. Open a free fxTrade Practice (demo) account at oanda.com, log in, and create a personal API token (My Account -> API access / "Manage API Access").
  2. Put it in the project's .env (already gitignored; never commit or paste it):
         OANDA_API_TOKEN=<your token>
         OANDA_ENV=practice            # practice (default) or live; the demo token only works on practice
  3. python futures/engine/oanda_pull.py                       (EUR_USD, XAU_USD, NAS100_USD from 2021-10-01)
     python futures/engine/oanda_pull.py EUR_USD --start 2024-01-01

Output: futures/data/oanda_m1/<INSTRUMENT>_M1.parquet with time (UTC), volume, and bid_/ask_/mid_ open, high, low, close. Complete candles only; the file is resumed from its last
candle, so re-running extends it. Read-only (candles only; no orders, no account data).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE.parent / "data" / "oanda_m1"
HOSTS = {"practice": "https://api-fxpractice.oanda.com", "live": "https://api-fxtrade.oanda.com"}
DEFAULT = ["EUR_USD", "XAU_USD", "NAS100_USD"]
PAGE = 5000


def load_env():
    try:
        from dotenv import load_dotenv
        for p in (ROOT / ".env", HERE.parent / ".env", ROOT / "mt5broker" / ".env"):
            if p.exists():
                load_dotenv(p)
    except ImportError:
        pass


def parse_candles(payload: dict) -> pd.DataFrame:
    rows = []
    for c in payload.get("candles", []):
        if not c.get("complete", True):
            continue
        r = {"time": pd.Timestamp(c["time"]).tz_convert("UTC").tz_localize(None), "volume": int(c.get("volume", 0))}
        for side in ("bid", "ask", "mid"):
            if side in c:
                for k, nm in (("o", "open"), ("h", "high"), ("l", "low"), ("c", "close")):
                    r[f"{side}_{nm}"] = float(c[side][k])
        rows.append(r)
    return pd.DataFrame(rows)


def pull(instrument: str, start: str, session=None, sleep=0.25, max_pages=100000, token=None, env="practice") -> pd.DataFrame:
    import requests
    s = session or requests.Session()
    headers = {"Authorization": f"Bearer {token}", "Accept-Datetime-Format": "RFC3339"} if token else {}
    path = OUT / f"{instrument}_M1.parquet"
    old = pd.read_parquet(path) if path.exists() else pd.DataFrame()
    cur = (old["time"].max() + pd.Timedelta(minutes=1)) if len(old) else pd.Timestamp(start)
    frames, pages, now = [], 0, pd.Timestamp.now(tz="UTC").tz_localize(None)
    while cur < now and pages < max_pages:
        params = {"granularity": "M1", "price": "BAM", "count": PAGE, "from": cur.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")}
        r = s.get(f"{HOSTS[env]}/v3/instruments/{instrument}/candles", params=params, headers=headers, timeout=60)
        if r.status_code == 429:
            time.sleep(5); continue
        if r.status_code != 200:
            raise SystemExit(f"{instrument}: HTTP {r.status_code} {r.text[:200]}")
        df = parse_candles(r.json())
        pages += 1
        if df.empty:
            cur = cur + pd.Timedelta(hours=24 * 5)         # a weekend / holiday stretch with no candles: jump ahead
            continue
        frames.append(df)
        cur = df["time"].max() + pd.Timedelta(minutes=1)
        if pages % 20 == 0:
            print(f"  {instrument}: {cur:%Y-%m-%d} ({pages} pages)", flush=True)
        time.sleep(sleep)
    new = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return pd.concat([old, new], ignore_index=True).drop_duplicates("time").sort_values("time").reset_index(drop=True)


def main(argv=None):
    load_env()
    args = (argv if argv is not None else sys.argv[1:])
    start = "2021-10-01"
    if "--start" in args:
        i = args.index("--start"); start = args[i + 1]; args = args[:i] + args[i + 2:]
    instruments = args or DEFAULT
    token, env = os.getenv("OANDA_API_TOKEN"), os.getenv("OANDA_ENV", "practice")
    if not token:
        raise SystemExit("OANDA_API_TOKEN is not set (see the SETUP note at the top of this file); nothing was downloaded.")
    if env not in HOSTS:
        raise SystemExit("OANDA_ENV must be 'practice' or 'live'")
    OUT.mkdir(parents=True, exist_ok=True)
    for ins in instruments:
        df = pull(ins, start, token=token, env=env)
        df.to_parquet(OUT / f"{ins}_M1.parquet", index=False)
        print(f"{ins}: {len(df)} candles {df['time'].min()} -> {df['time'].max()} saved to {OUT / (ins + '_M1.parquet')}", flush=True)


def selftest():
    """Offline test of the parser and the pagination with a fake API (no network, no token)."""
    import tempfile
    global OUT
    t0 = pd.Timestamp("2021-10-04 00:00:00")
    allc = [{"complete": True, "volume": 5, "time": (t0 + pd.Timedelta(minutes=k)).strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
             "bid": {"o": "1.1", "h": "1.2", "l": "1.0", "c": "1.15"}, "ask": {"o": "1.1001", "h": "1.2001", "l": "1.0001", "c": "1.1501"}, "mid": {"o": "1.10005", "h": "1.20005", "l": "1.00005", "c": "1.15005"}} for k in range(12000)]
    allc[-1]["complete"] = False

    class R:
        def __init__(self, p): self.status_code, self._p, self.text = 200, p, ""
        def json(self): return self._p

    class FakeSession:
        def get(self, url, params=None, headers=None, timeout=None):
            start = pd.Timestamp(params["from"]).tz_convert("UTC").tz_localize(None)
            sel = [c for c in allc if pd.Timestamp(c["time"]).tz_convert("UTC").tz_localize(None) >= start][:params["count"]]
            return R({"candles": sel})

    OUT = Path(tempfile.mkdtemp())
    # pretend "now" is just after the data by patching the loop bound through a tiny start window
    df = pull("TEST_INSTR", "2021-10-04", session=FakeSession(), sleep=0, max_pages=5, token="x")
    assert len(df) == 11999 and df["time"].is_unique and df["bid_close"].iloc[0] == 1.15 and df["ask_close"].iloc[0] > df["bid_close"].iloc[0], len(df)
    assert not (df["time"] == (t0 + pd.Timedelta(minutes=11999))).any(), "the incomplete candle must be dropped"
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        main()
