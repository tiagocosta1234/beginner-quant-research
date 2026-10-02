"""
Round 310 (2026-10-02, PRE-REGISTERED): the trader: "try other ways to make it profitable" (after Round 309: four 1-minute mean-reversion triggers had 63-67% win rates at a 0.5R target, zero gross
edge, and lost 0.11-0.19R a trade to costs). This round tests a FIXED, SMALL list of changes, each with a stated reason, on the two triggers that were least bad / most frequent
(F1 exhaustion: gross +0.011R vs mirror -0.004R; F4 VWAP-stretch z: the highest-frequency trigger). The selection of F1 and F4 is made AFTER seeing Round 309 and is disclosed; F2 and F3 are dropped
(gross -0.01 to +0.01R with a mirror of the same size).

A change "helps" only if (a) its net R is positive and (b) it passes the ledger's candidate rule at the NEW k. Skill = gross R of the real bet minus gross R of the mirrored bet (independent of costs); it is
reported for every variant. Win rate alone proves nothing (the mirror has the same one).

Step 0 (ledger k = 1981): every trigger here was tested in Round 309 (ledger 1974-1981) and failed; this round changes ONE thing at a time from that baseline (and one stack), it does not add new triggers.
Honest expectation (before the run): Round 309's gross edge was zero, so cutting costs (wider stops) can at best reduce the loss to a small negative number; only a change that creates skill
(a more extreme trigger, a regime filter) can make it profitable, and with ~14 variants a lucky false positive is likely unless the candidate bar (1 - 0.01/k, k about 1995) is respected.

Data and mechanics: identical to Round 309 (Databento 1-minute ES, NQ, GC, 2020-01-02..2026-09-25, RTH entries 09:30-15:30 ET, one position at a time, flat 15:59 ET, costs (1.24 + 2 ticks) per micro
contract in R, target 0.5R, mirrored-bet placebo, IS < 2025-07-01 <= OOS). ATR = mean true range of 20 bars; the base stop is 2 ATR20 with a 60-bar max hold.

CHANGES (each applied alone to the baseline, for each trigger), 7 changes x 2 triggers = 14 ledger variants:
  W1 WIDER STOP 1: stop 4 ATR, max hold 120 bars (cost per trade roughly halves).
  W2 WIDER STOP 2: stop 8 ATR, max hold 240 bars (cost roughly a quarter).
  W3 EXTREME TRIGGER: F1 drop over 6 bars >= 4 ATR (baseline 2); F4 |z| >= 5 (baseline 3). Rarer, bigger stretch.
  W4 MIDDAY ONLY: entries 11:30-14:00 ET (the low-volume lull, when ranges mean-revert).
  W5 VOLUME CLIMAX: the signal bar's volume >= 3 x the mean of the previous 20 bars (capitulation / exhaustion volume).
  W6 WITH THE TREND: longs only when the close is above its 390-bar EMA (about one RTH session), shorts only below (buy dips in an uptrend; the daily dip-reversal edge is the only confirmed edge in this repo).
  W7 STACK: W3 + W5 + W6 together with stop 4 ATR / 120 bars.
  Trigger definitions as in Round 309: F1 = six consecutive lower (higher) closes and a 6-bar drop (rise) >= X ATR -> long (short); F4 = z of (close - VWAP since 18:00 ET) over a 60-bar rolling
  std <= -Z (>= +Z) -> long (short).
  Not widened after the run: no new thresholds, windows or ATR multiples to rescue a failure.

DRY-RUN COUNTS (no P&L read; the filter logic passes a synthetic self-test): trades per instrument ES / NQ / GC.
  F1: W1 4,482 / 6,319 / 4,427; W2 3,235 / 4,091 / 3,058; W3 1,252 / 1,650 / 1,613; W4 2,023 / 3,029 / 1,896; W5 370 / 478 / 723; W6 1,421 / 2,198 / 1,705; W7 29 / 44 / 58.
  F4: W1 16,196 / 16,832 / 19,156; W2 6,309 / 6,489 / 6,286; W3 26,219 / 28,540 / 40,375; W4 20,563 / 21,312 / 26,877; W5 4,339 / 4,309 / 9,781; W6 131 / 138 / 1,769; W7 5 / 12 / 107.
UNDERPOWERED (stated before the run): F1 W5 (about 1,570 pooled), F1 W7 (131 pooled), F4 W6 (about 2,040, mostly gold: a stretch below VWAP while above the 390-bar EMA is rare) and F4 W7 (124 pooled) cannot
  show an edge smaller than about +0.1R net; their verdicts are "not enough trades", not "no edge". Others have 4,000-90,000 pooled trades (standard error 0.004-0.015R).
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
ENTRY_SM = (930, 1290)
MIDDAY_SM = (1050, 1200)     # 11:30-14:00 ET
FLAT_SM = 1319
TR = 0.5
CHANGES = {
    "W1_stop4": dict(stopm=4.0, hold=120),
    "W2_stop8": dict(stopm=8.0, hold=240),
    "W3_extreme": dict(extreme=True),
    "W4_midday": dict(midday=True),
    "W5_volclimax": dict(vol=True),
    "W6_withtrend": dict(trend=True),
    "W7_stack": dict(stopm=4.0, hold=120, extreme=True, vol=True, trend=True),
}
TRIGGERS = ["F1", "F4"]


def load(sym):
    df = pd.read_parquet(os.path.join(DB_DIR, FILES[sym]))
    idx = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    b = pd.DataFrame({"o": df["open"].values, "h": df["high"].values, "l": df["low"].values, "c": df["close"].values, "v": df["volume"].values}, index=idx).sort_index()
    b = b[~b.index.duplicated(keep="first")]
    tday = (b.index + pd.Timedelta(hours=6)).normalize()
    sm = (((b.index.hour * 60 + b.index.minute) - 1080) % 1440).astype(np.int32)
    c = b["c"]; pc = c.shift(1)
    tr = pd.concat([b["h"] - b["l"], (b["h"] - pc).abs(), (b["l"] - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(20).mean()
    tp = (b["h"] + b["l"] + c) / 3.0
    pv = (tp * b["v"]).groupby(tday).cumsum()
    vv = b["v"].groupby(tday).cumsum()
    vwap = pv / vv.replace(0, np.nan)
    dev = c - vwap
    z = (dev / dev.rolling(60, min_periods=30).std()).values
    d1 = c.diff()
    down6 = ((d1 < 0).rolling(6).sum() == 6).values
    up6 = ((d1 > 0).rolling(6).sum() == 6).values
    move6 = (c.shift(6) - c).values
    a = atr.values
    volx = (b["v"] / b["v"].rolling(20).mean().shift(1)).values
    ema = c.ewm(span=390, adjust=False).mean().values
    cv = c.values
    sig = {}
    for nm, X in (("F1", 2.0), ("F1x", 4.0)):
        sig[nm] = np.where(down6 & (move6 >= X * a), 1, np.where(up6 & (-move6 >= X * a), -1, 0))
    for nm, Z in (("F4", 3.0), ("F4x", 5.0)):
        sig[nm] = np.where(z <= -Z, 1, np.where(z >= Z, -1, 0))
    return dict(ts=b.index.values, h=b["h"].values, l=b["l"].values, c=cv, sm=sm, tday=tday.values, atr=a, volx=volx, ema=ema, sig=sig)


def run(D, sym, trig, chg, mirror=False):
    p = CHANGES[chg]
    tick, pvm = SPEC[sym]["tick"], SPEC[sym]["pvm"]
    h, l, c, sm, atr, td = D["h"], D["l"], D["c"], D["sm"], D["atr"], D["tday"]
    s = D["sig"][trig + ("x" if p.get("extreme") else "")]
    lo, hi = MIDDAY_SM if p.get("midday") else ENTRY_SM
    ok = (s != 0) & (sm >= lo) & (sm <= (hi if p.get("midday") else ENTRY_SM[1])) & ~np.isnan(atr) & (td >= np.datetime64(FIRST_DAY))
    if p.get("vol"):
        ok &= D["volx"] >= 3.0
    if p.get("trend"):
        ok &= ((s == 1) & (c > D["ema"])) | ((s == -1) & (c < D["ema"]))
    stopm, hold = p.get("stopm", 2.0), p.get("hold", 60)
    rows, free, n = [], -1, len(c)
    for i in np.flatnonzero(ok):
        if i <= free:
            continue
        d = int(s[i]); dd = -d if mirror else d
        e = c[i]; dist = stopm * atr[i]
        if dist < 2 * tick:
            continue
        stop, tgt = e - dd * dist, e + dd * TR * dist
        r = ex = None
        end = min(i + hold, n - 1)
        for j in range(i + 1, end + 1):
            if td[j] != td[i] or sm[j] > FLAT_SM:
                ex = j - 1
                break
            if (dd == 1 and l[j] <= stop) or (dd == -1 and h[j] >= stop):
                r, ex = -1.0, j
                break
            if (dd == 1 and h[j] >= tgt) or (dd == -1 and l[j] <= tgt):
                r, ex = TR, j
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
                         r_net=float(r - cost_R), win_flag=bool(r > 0), tR=TR, dist=float(dist)))
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
    return dict(n=len(df), win=float(df["win_flag"].mean()), gross_R=float(df["r_gross"].mean()), net_R=float(df["r_net"].mean()), cost_R=float(df["cost_R"].mean()),
                breakeven_win=float((1 + df["cost_R"].mean()) / (1 + TR)))


def selftest():
    SPEC["XX"] = dict(tick=0.25, pvm=5.0)
    n = 8
    D = dict(ts=np.arange(n).astype("datetime64[m]"), h=np.array([10, 10.2, 10.3, 11, 11, 11, 11, 11.0]), l=np.array([9.9, 9.9, 10.0, 10.0, 10.0, 10, 10, 10.0]),
             c=np.array([10, 10.1, 10.2, 10.5, 10.5, 10.5, 10.5, 10.5]), sm=np.array([1100] * n, dtype=np.int32), tday=np.array(["2021-03-01"] * n, dtype="datetime64[ns]"),
             atr=np.array([0.5] * n), volx=np.array([4.0] * n), ema=np.array([9.0] * n), sig={"F1": np.array([0, 1, 0, 0, 0, 0, 0, 0]), "F1x": np.array([0] * n)})
    r = run(D, "XX", "F1", "W6_withtrend")           # c 10.1 > ema 9 -> long allowed; 0.5R target 10.6 reached at bar3
    assert len(r) == 1 and abs(r[0]["r_gross"] - 0.5) < 1e-9, r
    D["ema"] = np.array([12.0] * n)
    assert len(run(D, "XX", "F1", "W6_withtrend")) == 0     # below the EMA: long refused
    D["volx"] = np.array([1.0] * n)
    assert len(run(D, "XX", "F1", "W5_volclimax")) == 0
    D["sm"] = np.array([1000] * n, dtype=np.int32)
    assert len(run(D, "XX", "F1", "W4_midday")) == 0         # 11:00-ish entry outside 11:30-14:00 -> no trade
    print("selftest ok")


def dry_run():
    selftest()
    for sym in FILES:
        D = load(sym)
        print(f"\n{sym}")
        for trig in TRIGGERS:
            print("  " + trig + ": " + ", ".join(f"{chg} {len(run(D, sym, trig, chg))}" for chg in CHANGES))
    print("\n--dry-run: counts only (trades are resolved for the counts but no P&L is read).")


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
    for trig in TRIGGERS:
        for chg in CHANGES:
            kk += 1
            real, mirror = [], []
            for s in FILES:
                real += run(data[s], s, trig, chg)
                mirror += run(data[s], s, trig, chg, mirror=True)
            name = f"1-min fade {trig} + change {chg} (target 0.5R, flat 15:59 ET), ES+NQ+GC"
            row = H.test_idea(name, as_trades(real), all_days, "MNQ", kk)
            rows_out.append(row)
            H.test_idea("   placebo (mirrored bet)", as_trades(mirror), all_days, "MNQ", kk)
            sr, sm_ = summarise(real), summarise(mirror)
            skill = sr.get("gross_R", float("nan")) - sm_.get("gross_R", float("nan"))
            dfr = pd.DataFrame(real)
            diag = {}
            if len(dfr):
                diag["by_symbol"] = {s: summarise([r for r in real if r["sym"] == s]) for s in FILES}
                diag["by_year"] = {int(y): summarise([r for r in real if r["tday"].year == y]) for y in sorted(set(dfr["tday"].dt.year))}
            print(f"    win rate {sr['win']:.1%} (break-even {sr['breakeven_win']:.1%}, mirror wins {sm_['win']:.1%})  gross {sr['gross_R']:+.3f}R, cost {sr['cost_R']:.3f}R, net {sr['net_R']:+.3f}R | mirror gross {sm_['gross_R']:+.3f}R | skill {skill:+.3f}R", flush=True)
            results[f"{trig}|{chg}"] = dict(real=sr, mirror=sm_, skill=skill, row={k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in row.items() if k != "name"}, diag=diag)
    lr = H.ledger_rows([{**r} for r in rows_out], "Round 310 (pre-registered, ways to make the 1-minute fades profitable)", commit, date="2026-10-02")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lr) + "\n")
    out = os.path.join(HERE, "round310_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {out} and {len(lr)} ledger rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
