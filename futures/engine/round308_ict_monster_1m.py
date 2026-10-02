"""
Round 308 (2026-10-02, PRE-REGISTERED): the trader asked for "a 1 minute ICT monstrous strategy that achieves a high win rate on the long term".
Built as ONE stacked ICT model on 1-minute bars and tested on real data, with the win rate reported next to what a coin flip with the same
stop/target geometry would win. A high win rate is easy to engineer (a wide stop and a small target); the question is whether the net
expectancy after costs is positive.

Step 0 (ledger checked first, k = 1965): ICT pieces tested already, all "no edge": Judas swing (Rounds 125, ledger 28-31), plain and filtered
FVG retests at 5/15/60 min (Rounds 150, 153, 189: 184-205, 328-338), order-block retests, Silver Bullet (Round 159: 201-205), their inversions
(Round 160: 206-218), OTE sweep-reclaim (Round 76), prior-day high/low first-touch fade (Round 147). NOT tested: the STACK on 1-minute bars
(liquidity sweep of Asia / London / prior-day levels, then a displacement market-structure shift that leaves a fair value gap, then a limit entry
at the gap's midpoint, stop beyond the sweep), with a high-win-rate target grid, on ES/NQ/GC from 2020. Honest expectation: the pieces found no edge
alone, so the stack will mostly buy a smaller trade count; it is tested because the trader asked, not because the odds look better.

Data: Databento 1-minute ES, NQ, GC (continuous front month, start-stamped bars, UTC converted to New York time), trading days from 2020-01-02 to 2026-09-25
(the trader's scope rule: nothing earlier than 2020). Split: IS < 2025-07-01 <= OOS (idea_harness convention).

RULES (all causal; every bar close is the decision point and entries are limit orders filled on LATER bars):
  Day: 18:00 ET starts the trading day (idea_harness convention). Levels known before they are used:
    Asia range = 18:00-02:00 ET high/low; London range = 02:00-05:00 ET high/low (used only in the NY window); prior-day RTH (09:30-16:00) high/low (PDH/PDL)
    and its midpoint.
  Windows (one setup at most per window per day): London kill zone 02:00-05:00 ET; NY AM kill zone 08:30-11:00 ET.
  SWEEP: a bar's low trades below a sell-side level (Asia low, PDL, London low in the NY window) by more than one tick (long setup); mirror for highs (short).
    The sweep extreme S is the lowest low since the breach; the setup dies 45 bars after the breach.
  MSS + FVG (at a bar close i after the sweep low): close[i] > the highest high of the 10 bars up to and including the sweep-low bar AND close[i] > the swept level
    (reclaimed) AND low[i] > high[i-2] (bullish fair value gap over bars i-2..i) AND the body of bar i or i-1 >= 1.5 x the mean body of the 20 bars before it (displacement).
    Mirror for shorts.
  ENTRY: limit at the gap midpoint ((high[i-2] + low[i]) / 2), filled on the first bar j in i+1..i+20 that trades one tick through it (a bar that fills and also
    reaches the stop counts as a loss). STOP: S -/+ 2 ticks. Skip if the stop distance < 4 ticks or > 0.4% of price.
  EXIT: stop, or the target below, whichever is touched first (stop wins a tie on a bar); flat at the close of the 15:59 ET bar. One position at a time (a setup whose
    fill comes while a position is open is dropped).
  MODELS: BASE = all of the above. PD = BASE plus the ICT premium/discount filter: longs only below the prior-day RTH midpoint, shorts only above it.
  TARGETS (the high-win-rate grid): 0.5R, 1R, 2R, and DRAW = the nearest opposing liquidity level (Asia / London / PDH-PDL) at least 1R away (no trade if none).
  8 ledger variants = 2 models x 4 targets, pooled over ES + NQ + GC (per-instrument and per-year tables are diagnostics, not ledger rows).
  COSTS: per trade in R = (1.24 + 2 ticks x micro point value) / (stop distance x micro point value) (micro-contract equivalent: MES $5/pt, MNQ $2/pt, MGC $10/pt),
    i.e. the repo's commission + 2 ticks round trip. P&L is in R, shown as dollars at the repo's $300 risk for the ledger.
  PLACEBO (mirrored): the SAME fills, the opposite bet (stop and target reflected about the entry), same costs. A real ICT edge must beat its mirror; a pure geometry
    win rate shows up in both.
  CANDIDATE (idea_harness.test_idea): positive before AND after costs, IS P(edge>0) >= 0.95, OOS P(edge>0) >= 1 - 0.01/k.
  Pass-speed gate screen (step 0 of the loop): a 0.5R-1R scalp can only reach a daily Sharpe near 0.5 with a real edge of about +0.1R net a trade at about one trade a day;
    stated before the run.

DRY-RUN COUNTS (no P&L inspected; three setups per symbol hand-checked against the bars, e.g. ES 2020-05-07 NY short after a PDH sweep: high[i] 2877.25 < low[i-2] 2879.50, gap midpoint 2878.375, displacement body 4.25 pts; the walk() fill/stop/target/flat logic passes a synthetic self-test):
  setups (both directions, both windows, 2020-01-02..2026-09-25): ES 1,519, NQ 1,516, GC 1,521 (about one per trading day per instrument, 62% sell-side-sweep-in-NY / 38% London mix);
  BASE trades after the one-position rule: ES ~980, NQ ~1,030, GC ~955 (pooled ~2,970); PD (premium/discount) ~2,220 pooled; DRAW target has ~3-5% fewer.
POWER: pooled BASE standard error of the mean net R is about 1/sqrt(2970) = 0.018R in total but only about 0.045R in the OOS slice (~500 trades since 2025-07), so an edge smaller than about +0.10R net a trade cannot be told from zero out of sample; stated before the run.
Fixed by this pre-registration: nothing is re-tuned after the run; if the stack fails, the variants are not widened (no new levels, windows, gaps, retrace depths) to rescue it.
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
RISK = 300.0
COMM = 1.24
WINDOWS = {"LON": (480, 660), "NY": (870, 1020)}   # minutes after 18:00 ET: 02:00-05:00, 08:30-11:00
FLAT_SM = 1319                                      # the 15:59 ET bar
ASIA = (0, 480)
RTH = (930, 1320)
SWEEP_LIFE = 45
SWING_BACK = 10
FILL_BARS = 20
MIN_TICKS = 4
MAX_PCT = 0.004
DISP = 1.5
TARGETS = ["0.5R", "1R", "2R", "DRAW"]
MODELS = ["BASE", "PD"]
OOS_START = pd.Timestamp("2025-07-01")


def load(sym):
    df = pd.read_parquet(os.path.join(DB_DIR, FILES[sym]))
    idx = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    b = pd.DataFrame({"o": df["open"].values, "h": df["high"].values, "l": df["low"].values, "c": df["close"].values}, index=idx).sort_index()
    b = b[~b.index.duplicated(keep="first")]
    tday = (b.index + pd.Timedelta(hours=6)).normalize()
    mod = b.index.hour * 60 + b.index.minute
    sm = ((mod - 1080) % 1440).astype(np.int32)
    body = np.abs(b["c"].values - b["o"].values)
    bm = pd.Series(body).rolling(20).mean().shift(1).values
    return dict(ts=b.index.values, o=b["o"].values, h=b["h"].values, l=b["l"].values, c=b["c"].values, sm=sm, tday=tday.values, body=body, bm=bm)


def day_slices(D):
    t = D["tday"]
    cut = np.flatnonzero(np.r_[True, t[1:] != t[:-1]])
    ends = np.r_[cut[1:], len(t)]
    return list(zip(cut, ends))


def find_setups(D, sym, verbose=False):
    """All setups (both models are filtered from this list)."""
    tick = SPEC[sym]["tick"]
    h, l, c, sm, body, bm = D["h"], D["l"], D["c"], D["sm"], D["body"], D["bm"]
    sl = day_slices(D)
    out = []
    prev_pdh = prev_pdl = None
    for k, (a, b) in enumerate(sl):
        tday = pd.Timestamp(D["tday"][a])
        if b - a < 600:
            continue
        s = sm[a:b]
        m_asia = (s >= ASIA[0]) & (s < ASIA[1])
        m_rth = (s >= RTH[0]) & (s < RTH[1])
        pdh, pdl = prev_pdh, prev_pdl
        if m_rth.sum() > 100:
            prev_pdh, prev_pdl = float(h[a:b][m_rth].max()), float(l[a:b][m_rth].min())
        if tday < FIRST_DAY or pdh is None or m_asia.sum() < 60:
            continue
        asia_hi, asia_lo = float(h[a:b][m_asia].max()), float(l[a:b][m_asia].min())
        m_lon = (s >= WINDOWS["LON"][0]) & (s < WINDOWS["LON"][1])
        lon_hi = float(h[a:b][m_lon].max()) if m_lon.sum() > 60 else None
        lon_lo = float(l[a:b][m_lon].min()) if m_lon.sum() > 60 else None
        mid = (pdh + pdl) / 2.0
        flat_i = a + int(np.flatnonzero(s <= FLAT_SM)[-1])
        for wn, (w0, w1) in WINDOWS.items():
            idx_w = a + np.flatnonzero((s >= w0) & (s < w1))
            if len(idx_w) < 30:
                continue
            if wn == "LON":
                lows = [("ASIA_L", asia_lo), ("PDL", pdl)]; highs = [("ASIA_H", asia_hi), ("PDH", pdh)]
            else:
                lows = [("ASIA_L", asia_lo), ("PDL", pdl)] + ([("LON_L", lon_lo)] if lon_lo is not None else [])
                highs = [("ASIA_H", asia_hi), ("PDH", pdh)] + ([("LON_H", lon_hi)] if lon_hi is not None else [])
            st = {1: None, -1: None}
            used = {1: set(), -1: set()}
            found = None
            for i in idx_w:
                for d in (1, -1):
                    lv = lows if d == 1 else highs
                    z = st[d]
                    if z is None:
                        if d == 1:
                            cand = [(nm, L) for nm, L in lv if nm not in used[d] and l[i] < L - tick]
                            if cand:
                                nm, L = max(cand, key=lambda x: x[1])
                                st[d] = dict(nm=nm, L=L, bi=i, si=i, S=l[i], swing=float(h[max(a, i - SWING_BACK):i + 1].max()))
                        else:
                            cand = [(nm, L) for nm, L in lv if nm not in used[d] and h[i] > L + tick]
                            if cand:
                                nm, L = min(cand, key=lambda x: x[1])
                                st[d] = dict(nm=nm, L=L, bi=i, si=i, S=h[i], swing=float(l[max(a, i - SWING_BACK):i + 1].min()))
                        continue
                    if i - z["bi"] > SWEEP_LIFE:
                        used[d].add(z["nm"]); st[d] = None
                        continue
                    if d == 1 and l[i] < z["S"]:
                        z["S"], z["si"] = l[i], i
                        z["swing"] = float(h[max(a, i - SWING_BACK):i + 1].max())
                        continue
                    if d == -1 and h[i] > z["S"]:
                        z["S"], z["si"] = h[i], i
                        z["swing"] = float(l[max(a, i - SWING_BACK):i + 1].min())
                        continue
                    if i <= z["si"] or i - 2 < a:
                        continue
                    disp = (not np.isnan(bm[i])) and max(body[i], body[i - 1]) >= DISP * bm[i]
                    if d == 1:
                        ok = c[i] > z["swing"] and c[i] > z["L"] and l[i] > h[i - 2] and disp
                        gap_lo, gap_hi = h[i - 2], l[i]
                    else:
                        ok = c[i] < z["swing"] and c[i] < z["L"] and h[i] < l[i - 2] and disp
                        gap_lo, gap_hi = h[i], l[i - 2]
                    if ok:
                        e = (gap_lo + gap_hi) / 2.0
                        stop = z["S"] - 2 * tick if d == 1 else z["S"] + 2 * tick
                        dist = abs(e - stop)
                        found = dict(sym=sym, tday=tday, win=wn, d=d, i=int(i), e=float(e), stop=float(stop), dist=float(dist), level=z["nm"],
                                     pd_ok=bool((d == 1 and e < mid) or (d == -1 and e > mid)), flat_i=int(flat_i),
                                     draw=[v for v in ([asia_hi, pdh] + ([lon_hi] if (wn == "NY" and lon_hi is not None) else [])) if v is not None] if d == 1
                                     else [v for v in ([asia_lo, pdl] + ([lon_lo] if (wn == "NY" and lon_lo is not None) else [])) if v is not None])
                        break
                if found:
                    break
            if found and found["dist"] >= MIN_TICKS * tick and found["dist"] <= MAX_PCT * c[found["i"]]:
                out.append(found)
    return out


def walk(D, sym, su, target_R, mirror):
    """One setup, one target multiple. Returns (fill_i, exit_i, gross_R, win) or None."""
    tick = SPEC[sym]["tick"]
    h, l, c = D["h"], D["l"], D["c"]
    d, e, dist, flat = su["d"], su["e"], su["dist"], su["flat_i"]
    fill = None
    for j in range(su["i"] + 1, min(su["i"] + FILL_BARS, flat - 1) + 1):
        if (d == 1 and l[j] <= e - tick) or (d == -1 and h[j] >= e + tick):
            fill = j
            break
    if fill is None:
        return None
    dd = -d if mirror else d
    stop = e - dd * dist
    tgt = e + dd * target_R * dist
    # fill bar: a bar that fills and reaches the (real or mirrored) stop counts as a loss
    j = fill
    if (dd == 1 and l[j] <= stop) or (dd == -1 and h[j] >= stop):
        return fill, j, -1.0, False
    for j in range(fill + 1, flat + 1):
        if (dd == 1 and l[j] <= stop) or (dd == -1 and h[j] >= stop):
            return fill, j, -1.0, False
        if (dd == 1 and h[j] >= tgt) or (dd == -1 and l[j] <= tgt):
            return fill, j, float(target_R), True
    r = dd * (c[flat] - e) / dist
    return fill, flat, float(r), bool(r > 0)


def target_for(su, label):
    if label == "DRAW":
        d, e, dist = su["d"], su["e"], su["dist"]
        cands = [v for v in su["draw"] if (v - e) * d >= dist]
        if not cands:
            return None
        v = min(cands, key=lambda x: abs(x - e))
        return abs(v - e) / dist
    return {"0.5R": 0.5, "1R": 1.0, "2R": 2.0}[label]


def run_variant(D, sym, setups, model, label, mirror=False):
    tick, pvm = SPEC[sym]["tick"], SPEC[sym]["pvm"]
    rows, free = [], -1
    for su in sorted(setups, key=lambda x: x["i"]):
        if model == "PD" and not su["pd_ok"]:
            continue
        tR = target_for(su, label)
        if tR is None:
            continue
        w = walk(D, sym, su, tR, mirror)
        if w is None:
            continue
        fill, ex, r, win = w
        if fill <= free:
            continue          # a position is open
        free = ex
        cost_R = (COMM + 2 * tick * pvm) / (su["dist"] * pvm)
        rows.append(dict(sym=sym, tday=su["tday"], win=su["win"], d=su["d"], level=su["level"], entry_ts=pd.Timestamp(D["ts"][fill]), exit_ts=pd.Timestamp(D["ts"][ex]),
                         r_gross=r, cost_R=cost_R, r_net=r - cost_R, win_flag=win, tR=tR, dist=su["dist"]))
    return rows


def as_trades(rows):
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["entry_ts", "exit_ts", "direction", "contracts", "pnl", "r", "cost"])
    return pd.DataFrame(dict(entry_ts=df["entry_ts"], exit_ts=df["exit_ts"], direction=df["d"], contracts=1, pnl=df["r_net"] * RISK, r=df["r_gross"], cost=df["cost_R"] * RISK))


def selftest():
    """Synthetic walk checks: long fill + target, long fill + stop, fill-bar stop = loss, expiry, mirror."""
    tick = SPEC["ES"]["tick"]
    def mk(hh, ll, cc):
        n = len(hh)
        return dict(h=np.array(hh, float), l=np.array(ll, float), c=np.array(cc, float), ts=np.arange(n).astype("datetime64[m]"))
    su = dict(d=1, e=100.0, dist=2.0, i=0, flat_i=9)
    # bar1 trades down through 100 (fill), bar2 reaches 102 (1R target = 102)
    D = mk([101, 100.5, 102.5, 103, 103, 103, 103, 103, 103, 103], [100.5, 99.5, 100.5, 102, 102, 102, 102, 102, 102, 102], [100.7, 100, 102, 102.5, 102.5, 102.5, 102.5, 102.5, 102.5, 102.5])
    assert walk(D, "ES", su, 1.0, False) == (1, 2, 1.0, True), walk(D, "ES", su, 1.0, False)
    # mirrored: short from 100, stop 102: bar2 high 102.5 >= 102 -> loss
    assert walk(D, "ES", su, 1.0, True) == (1, 2, -1.0, False)
    # fill bar also reaches the stop (98): loss
    D2 = mk([101, 100.5, 100.5, 100, 100, 100, 100, 100, 100, 100], [100.5, 97.5, 99, 99, 99, 99, 99, 99, 99, 99], [100.7, 99, 99.5, 99.5, 99.5, 99.5, 99.5, 99.5, 99.5, 99.5])
    assert walk(D2, "ES", su, 1.0, False) == (1, 1, -1.0, False)
    # never reaches the entry within the fill window: no trade
    D3 = mk([101] * 10, [100.5] * 10, [100.8] * 10)
    assert walk(D3, "ES", su, 1.0, False) is None
    # flat at the close: long fills, drifts, ends at c[flat]
    D4 = mk([101, 100.5, 101, 101, 101, 101, 101, 101, 101, 101], [100.5, 99.5, 100.2, 100.2, 100.2, 100.2, 100.2, 100.2, 100.2, 100.2], [100.7, 100, 100.6, 100.6, 100.6, 100.6, 100.6, 100.6, 100.6, 100.6])
    res = walk(D4, "ES", su, 2.0, False)
    assert res[1] == 9 and abs(res[2] - 0.3) < 1e-9, res
    print("selftest ok")


def summarise(rows, label=""):
    if not rows:
        return dict(n=0)
    df = pd.DataFrame(rows)
    be = (1 + df["cost_R"].mean()) / (1 + df["tR"].mean())
    return dict(n=len(df), win=float(df["win_flag"].mean()), gross_R=float(df["r_gross"].mean()), net_R=float(df["r_net"].mean()), cost_R=float(df["cost_R"].mean()), breakeven_win=float(be))


def dry_run():
    selftest()
    t0 = time.time()
    for sym in FILES:
        D = load(sym)
        su = find_setups(D, sym)
        df = pd.DataFrame(su)
        print(f"\n{sym}: {len(D['ts'])} bars, loaded+scanned in {time.time() - t0:.0f}s; setups {len(df)}")
        print(df.groupby(["win", "d"]).size().unstack().to_string())
        print("PD-ok share:", round(float(df["pd_ok"].mean()), 3), " per year:", df.groupby(df["tday"].dt.year).size().to_dict())
        print("median stop distance:", round(float(df["dist"].median()), 2), " levels:", df["level"].value_counts().to_dict())
        for model in MODELS:
            for lb in TARGETS:
                rows = run_variant(D, sym, su, model, lb)
                s = summarise(rows)
                print(f"  {model:<4} {lb:<5} trades {s['n']}")
        # hand-check: three setups printed with their bars
        for k in (50, len(su) // 2, len(su) - 5):
            x = su[k]
            i = x["i"]
            print(f"  hand-check {sym} {x['tday'].date()} {x['win']} d={x['d']} sweep of {x['level']}: signal bar {pd.Timestamp(D['ts'][i])} entry {x['e']:.2f} stop {x['stop']:.2f} dist {x['dist']:.2f}")
            print("    bars i-3..i+1 (o h l c):", [(round(float(D['o'][j]), 2), round(float(D['h'][j]), 2), round(float(D['l'][j]), 2), round(float(D['c'][j]), 2)) for j in range(i - 3, i + 2)])
    print("\n--dry-run: counts only, no P&L logged. Hand-check the three setups per symbol before the real run.")


def main():
    if "--dry-run" in sys.argv:
        dry_run(); return
    selftest()
    t0 = time.time()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    data = {s: load(s) for s in FILES}
    setups = {s: find_setups(data[s], s) for s in FILES}
    all_days = sorted(set(pd.Timestamp(x["tday"]) for s in FILES for x in setups[s]) | set(pd.Timestamp(t) for s in FILES for t in np.unique(data[s]["tday"]) if pd.Timestamp(t) >= FIRST_DAY))
    k0 = H.ledger_count()
    ledger_rows_, results, kk = [], {}, k0
    print(f"ledger k so far {k0}; setups: " + ", ".join(f"{s} {len(setups[s])}" for s in FILES))
    for model in MODELS:
        for lb in TARGETS:
            kk += 1
            real, mirror = [], []
            for s in FILES:
                real += run_variant(data[s], s, setups[s], model, lb)
                mirror += run_variant(data[s], s, setups[s], model, lb, mirror=True)
            name = f"ICT monster 1-min [{model}: sweep -> MSS+FVG -> limit at FVG midpoint], target {lb}, ES+NQ+GC, flat 15:59 ET"
            row = H.test_idea(name, as_trades(real), all_days, "MNQ", kk)
            ledger_rows_.append(row)
            mrow = H.test_idea("   placebo (mirrored bet)", as_trades(mirror), all_days, "MNQ", kk)
            sr, sm_ = summarise(real), summarise(mirror)
            # by instrument, by year, by window, by direction (diagnostics)
            dfr = pd.DataFrame(real)
            diag = {}
            if len(dfr):
                diag["by_symbol"] = {s: summarise([r for r in real if r["sym"] == s]) for s in FILES}
                diag["by_year"] = {int(y): summarise([r for r in real if r["tday"].year == y]) for y in sorted(set(dfr["tday"].dt.year))}
                diag["by_window"] = {w: summarise([r for r in real if r["win"] == w]) for w in WINDOWS}
                diag["by_dir"] = {str(d): summarise([r for r in real if r["d"] == d]) for d in (1, -1)}
                diag["by_level"] = {lv: summarise([r for r in real if r["level"] == lv]) for lv in sorted(set(dfr["level"]))}
            print(f"    win rate {sr['win']:.1%} (break-even {sr['breakeven_win']:.1%}, mirror wins {sm_['win']:.1%})  gross {sr['gross_R']:+.3f}R, cost {sr['cost_R']:.3f}R, net {sr['net_R']:+.3f}R | mirror net {sm_['net_R']:+.3f}R", flush=True)
            results[f"{model}|{lb}"] = dict(real=sr, mirror=sm_, row={k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in row.items() if k != "name"}, diag=diag)
    lr = H.ledger_rows([{**r} for r in ledger_rows_], "Round 308 (pre-registered, the trader's 1-minute ICT monster)", commit, date="2026-10-02")
    with open(H.LEDGER, "a", encoding="utf-8") as f:
        f.write("\n".join(lr) + "\n")
    out = os.path.join(HERE, "round308_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"wrote {out} and {len(lr)} ledger rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
