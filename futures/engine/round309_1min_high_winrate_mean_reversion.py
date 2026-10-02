"""
Round 309 (2026-10-02, PRE-REGISTERED): the trader: "make a 1 minute strategy that achieves a high win rate on the long term" (the ICT stack of Round 308 had a 63% win rate and no edge).
A high win rate comes from the target being nearer than the stop; it pays only if the entry predicts a snap-back. So this round tests the four textbook 1-minute
mean-reversion triggers that the ledger has NOT tested as 1-minute triggers, each with a high-win-rate shape (stop 2 ATR, target 0.5R or 1R), on real data, with costs and a mirrored-bet placebo.

Step 0 (ledger checked first, k = 1973): 1-minute EMA crosses (ledger 3-7), 5-minute Bollinger scalper (24-27, 67-70), STDV fades (52-55, 85-88), round-number / prior-day / opening-range fades
(170-175), volume-spike fade (286-287), VWAP z-score fade on MNQ (Round 120b, live_bot `vwap_zscore`: no edge), POC reversion (289-292: NQ only, 31% win rate), Connors RSI(2) on DAILY bars
(153-160) are all done. NOT tested as 1-minute triggers: consecutive-bar exhaustion, RSI(2) extremes, Bollinger re-entry, VWAP stretch z-score on ES/NQ/GC from 2020.
Honest expectation (stated before the run): a 1-minute stop of 2 ATR is only 2-3 ES points, so costs (1.24 + 2 ticks per micro contract) are about 0.2-0.3R a trade; the trigger would need a gross edge above that.

Data: Databento 1-minute ES, NQ, GC (start-stamped, UTC -> New York), trading days 2020-01-02..2026-09-25, RTH entries only (09:30-15:30 ET), as in Round 308 (same loader). IS < 2025-07-01 <= OOS.

RULES (causal; the signal is read at a 1-minute bar's close i and the entry is that close):
  ATR = mean true range of the last 20 bars. STOP = 2 ATR from the entry. TARGET = 0.5R or 1R (i.e. 1 ATR or 2 ATR). Stop wins a tie on a bar. Exit at the first of stop / target / 60 bars / 15:59 ET (at the close).
  One position at a time; no entry after 15:30 ET. Costs per trade in R = (1.24 + 2 ticks x micro point value) / (stop x micro point value), micro point values ES 5, NQ 2, GC 10.
  F1 EXHAUSTION: the last 6 closes each lower than the one before AND close[i-6] - close[i] >= 2 ATR -> long; mirror for shorts.
  F2 RSI2: Wilder RSI(2) of 1-minute closes < 3 -> long; > 97 -> short.
  F3 BOLLINGER RE-ENTRY: Bollinger(20, 2.5) of closes; the previous close was below the lower band and this close is back above it -> long; mirror at the upper band.
  F4 VWAP STRETCH: z = (close - VWAP since 18:00 ET) / rolling std of (close - VWAP) over 60 bars (>= 30 bars); z <= -3 -> long; z >= +3 -> short.
  8 ledger variants = 4 triggers x targets 0.5R / 1R, pooled over ES + NQ + GC. Per-instrument / per-year tables and the mirrored-bet placebo (same entries, opposite bet) are diagnostics.
  CANDIDATE (idea_harness.test_idea): positive before AND after costs, IS P(edge>0) >= 0.95, OOS P(edge>0) >= 1 - 0.01/k.
  Not widened after the run: no new periods, thresholds, ATR multiples or filters to rescue a failure.

DRY-RUN COUNTS (no P&L read; one RSI2 and one VWAP-z signal per symbol hand-checked against the closes, e.g. ES 2023-01-03 09:30 RSI2 long after six straight lower closes 3886 -> 3878; the exit logic passes a synthetic self-test incl. the mirrored bet):
  trades per instrument at 0.5R / 1R: F1 EXHAUST ES 5,062 / 4,961, NQ 7,400 / 7,186, GC 4,954 / 4,848; F2 RSI2 about 26,700 / 23,000 each; F3 BOLL about 11,700 / 11,500 each; F4 VWAPZ 46,055-59,298 / 28,271-35,545.
POWER: pooled trades are 17,000-142,000 per variant, so the standard error of the mean net R is 0.003-0.008R (OOS 0.01-0.02R): any edge above about +0.03R net is detectable. The binding constraint is not power but cost: about 0.2-0.3R a trade at a 2 ATR stop.
"""
import os, sys, json, time, subprocess
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import idea_harness as H

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(HERE, "..", "data", "databento")
FILES = {"ES": "futures_ES.F_1m.parquet", "NQ": "futures_NQ.F_1m.parquet", "GC": "futures_GC.F_1m.parquet"}
SPEC = {"ES": dict(tick=0.25, pvm=5.0), "NQ": dict(tick=0.25, pvm=2.0), "GC": dict(tick=0.10, pvm=10.0)}
FIRST_DAY = pd.Timestamp("2020-01-02")
RISK, COMM = 300.0, 1.24
ENTRY_SM = (930, 1290)       # 09:30 .. 15:30 ET in minutes after 18:00
FLAT_SM = 1319               # 15:59
MAX_HOLD = 60
FAMS = ["F1_EXHAUST", "F2_RSI2", "F3_BOLL", "F4_VWAPZ"]
TARGETS = [0.5, 1.0]


def load(sym):
    df = pd.read_parquet(os.path.join(DB_DIR, FILES[sym]))
    idx = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    b = pd.DataFrame({"o": df["open"].values, "h": df["high"].values, "l": df["low"].values, "c": df["close"].values, "v": df["volume"].values}, index=idx).sort_index()
    b = b[~b.index.duplicated(keep="first")]
    tday = (b.index + pd.Timedelta(hours=6)).normalize()
    sm = (((b.index.hour * 60 + b.index.minute) - 1080) % 1440).astype(np.int32)
    c = b["c"]
    pc = c.shift(1)
    tr = pd.concat([b["h"] - b["l"], (b["h"] - pc).abs(), (b["l"] - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(20).mean()
    tp = (b["h"] + b["l"] + c) / 3.0
    pv = (tp * b["v"]).groupby(tday).cumsum()
    vv = b["v"].groupby(tday).cumsum()
    vwap = pv / vv.replace(0, np.nan)
    dev = c - vwap
    z = dev / dev.rolling(60, min_periods=30).std()
    ma = c.rolling(20).mean(); sd = c.rolling(20).std()
    lo_b, up_b = ma - 2.5 * sd, ma + 2.5 * sd
    d1 = c.diff()
    gain = d1.clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    loss = (-d1.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    down6 = (d1 < 0).rolling(6).sum() == 6
    up6 = (d1 > 0).rolling(6).sum() == 6
    move6 = c.shift(6) - c
    sig = {
        "F1_EXHAUST": np.where(down6 & (move6 >= 2 * atr), 1, np.where(up6 & (-move6 >= 2 * atr), -1, 0)),
        "F2_RSI2": np.where(rsi < 3, 1, np.where(rsi > 97, -1, 0)),
        "F3_BOLL": np.where((pc < lo_b.shift(1)) & (c > lo_b), 1, np.where((pc > up_b.shift(1)) & (c < up_b), -1, 0)),
        "F4_VWAPZ": np.where(z <= -3, 1, np.where(z >= 3, -1, 0)),
    }
    return dict(ts=b.index.values, h=b["h"].values, l=b["l"].values, c=c.values, sm=sm, tday=tday.values, atr=atr.values, sig=sig)


def run(D, sym, fam, tR, mirror=False):
    tick, pvm = SPEC[sym]["tick"], SPEC[sym]["pvm"]
    h, l, c, sm, atr, td = D["h"], D["l"], D["c"], D["sm"], D["atr"], D["tday"]
    s = D["sig"][fam]
    ok = (s != 0) & (sm >= ENTRY_SM[0]) & (sm <= ENTRY_SM[1]) & ~np.isnan(atr) & (td >= np.datetime64(FIRST_DAY))
    cand = np.flatnonzero(ok)
    rows, free = [], -1
    n = len(c)
    for i in cand:
        if i <= free:
            continue
        d = int(s[i])
        dd = -d if mirror else d
        e = c[i]
        dist = 2.0 * atr[i]
        if dist < 2 * tick:
            continue
        stop, tgt = e - dd * dist, e + dd * tR * dist
        r, ex = None, None
        end = min(i + MAX_HOLD, n - 1)
        for j in range(i + 1, end + 1):
            if td[j] != td[i] or sm[j] > FLAT_SM:
                ex = j - 1
                break
            if (dd == 1 and l[j] <= stop) or (dd == -1 and h[j] >= stop):
                r, ex = -1.0, j
                break
            if (dd == 1 and h[j] >= tgt) or (dd == -1 and l[j] <= tgt):
                r, ex = tR, j
                break
        else:
            ex = end
        if ex is None or ex <= i:
            continue
        if r is None:
            r = dd * (c[ex] - e) / dist
        free = ex
        cost_R = (COMM + 2 * tick * pvm) / (dist * pvm)
        rows.append(dict(sym=sym, tday=pd.Timestamp(td[i]), d=d, entry_ts=pd.Timestamp(D["ts"][i]), exit_ts=pd.Timestamp(D["ts"][ex]), r_gross=float(r), cost_R=float(cost_R),
                         r_net=float(r - cost_R), win_flag=bool(r > 0), tR=tR, dist=float(dist)))
    return rows


def as_trades(rows):
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["entry_ts", "exit_ts", "direction", "contracts", "pnl", "r", "cost"])
    return pd.DataFrame(dict(entry_ts=df["entry_ts"], exit_ts=df["exit_ts"], direction=df["d"], contracts=1, pnl=df["r_net"] * RISK, r=df["r_gross"], cost=df["cost_R"] * RISK))


def summarise(rows):
    if not rows:
        return dict(n=0)
    df = pd.DataFrame(rows)
    be = (1 + df["cost_R"].mean()) / (1 + df["tR"].mean())
    return dict(n=len(df), win=float(df["win_flag"].mean()), gross_R=float(df["r_gross"].mean()), net_R=float(df["r_net"].mean()), cost_R=float(df["cost_R"].mean()), breakeven_win=float(be))


def selftest():
    D = dict(ts=np.arange(8).astype("datetime64[m]"), h=np.array([10, 10.2, 10.3, 11, 11, 11, 11, 11.0]), l=np.array([9.9, 9.9, 10.0, 10.0, 10.0, 10, 10, 10.0]),
             c=np.array([10, 10.1, 10.2, 10.5, 10.5, 10.5, 10.5, 10.5]), sm=np.array([931] * 8, dtype=np.int32), tday=np.array(["2021-03-01"] * 8, dtype="datetime64[ns]"),
             atr=np.array([0.5] * 8), sig={"F": np.array([0, 1, 0, 0, 0, 0, 0, 0])})
    # long at bar1 close 10.1, dist 1.0, stop 9.1, 1R target 11.1: not reached, ends at bar7 close 10.5 -> r = 0.4
    SPEC["XX"] = dict(tick=0.25, pvm=5.0)
    r = run(D, "XX", "F", 1.0)
    assert len(r) == 1 and abs(r[0]["r_gross"] - 0.4) < 1e-9, r
    # 0.5R target: 10.6 not reached either (high 11 reaches it at bar3): r = 0.5
    r = run(D, "XX", "F", 0.5)
    assert abs(r[0]["r_gross"] - 0.5) < 1e-9, r
    # mirror: short from 10.1, stop 11.1 not hit (high 11), target 9.6 not hit: ends at 10.5 -> -0.4
    r = run(D, "XX", "F", 1.0, mirror=True)
    assert abs(r[0]["r_gross"] + 0.4) < 1e-9, r
    print("selftest ok")


def dry_run():
    selftest()
    for sym in FILES:
        D = load(sym)
        print(f"\n{sym}: {len(D['ts'])} bars")
        for fam in FAMS:
            raw = int(((D["sig"][fam] != 0) & (D["tday"] >= np.datetime64(FIRST_DAY))).sum())
            cnt = {tR: len(run(D, sym, fam, tR)) for tR in TARGETS}
            print(f"  {fam:<11} raw signals {raw:>6}  trades after one-position/RTH/entry window: 0.5R {cnt[0.5]}, 1R {cnt[1.0]}")
        # hand-check: first RSI2 and VWAP z signals
        for fam in ("F2_RSI2", "F4_VWAPZ"):
            ii = np.flatnonzero((D["sig"][fam] != 0) & (D["sm"] >= ENTRY_SM[0]) & (D["sm"] <= ENTRY_SM[1]) & (D["tday"] >= np.datetime64("2023-01-01")))[:1]
            for i in ii:
                print(f"  hand-check {sym} {fam} at {pd.Timestamp(D['ts'][i])} dir {D['sig'][fam][i]} close {D['c'][i]:.2f} ATR20 {D['atr'][i]:.3f}; closes i-6..i: {np.round(D['c'][i - 6:i + 1], 2).tolist()}")
    print("\n--dry-run: counts only (trades are resolved for the counts but no P&L is read). Hand-check before the real run.")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    selftest()
    t0 = time.time()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    data = {s: load(s) for s in FILES}
    all_days = sorted(set(pd.Timestamp(t) for s in FILES for t in np.unique(data[s]["tday"]) if pd.Timestamp(t) >= FIRST_DAY))
    kk = H.ledger_count()
    rows_out, results = [], {}
    print(f"ledger k so far {kk}")
    for fam in FAMS:
        for tR in TARGETS:
            kk += 1
            real, mirror = [], []
            for s in FILES:
                real += run(data[s], s, fam, tR)
                mirror += run(data[s], s, fam, tR, mirror=True)
            name = f"1-min mean reversion {fam} (stop 2 ATR20, target {tR}R, max 60 bars, RTH entries), ES+NQ+GC"
            row = H.test_idea(name, as_trades(real), all_days, "MNQ", kk)
            rows_out.append(row)
            H.test_idea("   placebo (mirrored bet)", as_trades(mirror), all_days, "MNQ", kk)
            sr, sm_ = summarise(real), summarise(mirror)
            dfr = pd.DataFrame(real)
            diag = {}
            if len(dfr):
                diag["by_symbol"] = {s: summarise([r for r in real if r["sym"] == s]) for s in FILES}
                diag["by_year"] = {int(y): summarise([r for r in real if r["tday"].year == y]) for y in sorted(set(dfr["tday"].dt.year))}
            print(f"    win rate {sr['win']:.1%} (break-even {sr['breakeven_win']:.1%}, mirror wins {sm_['win']:.1%})  gross {sr['gross_R']:+.3f}R, cost {sr['cost_R']:.3f}R, net {sr['net_R']:+.3f}R | mirror net {sm_['net_R']:+.3f}R", flush=True)
            results[f"{fam}|{tR}"] = dict(real=sr, mirror=sm_, row={k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in row.items() if k != "name"}, diag=diag)
    lr = H.ledger_rows([{**r} for r in rows_out], "Round 309 (pre-registered, the trader's 1-minute high-win-rate mean reversion)", commit, date="2026-10-02")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lr) + "\n")
    out = os.path.join(HERE, "round309_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {out} and {len(lr)} ledger rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
