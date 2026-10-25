"""Score the trader's blind-replay trades on Databento GC futures (independent of the chart he traded on).
Input: PHASE3_LOG.csv (session,date,signal_candle_open_local,side,stop_pts,target_pts,target_type,...).
Entry = close of the 1-minute signal candle +/- 0.1 point slippage. Stop/target = logged DISTANCES from that entry,
so the CFD-vs-futures price gap cancels. Same engine and costs as edge_lab. Mirror baseline = same distances, opposite side."""
import sys, math
import numpy as np, pandas as pd

LOG = sys.argv[1] if len(sys.argv) > 1 else "PHASE3_LOG.csv"
SL, THRU, COMM, PV = 0.1, 0.1, 1.2, 10.0
df = pd.read_parquet("D:/finance/beginner-quant-research/futures/data/databento/futures_GC.F_1m.parquet").sort_values("ts").reset_index(drop=True)
loc = df.ts.dt.tz_convert("Europe/London").dt.tz_localize(None)
T = ((loc - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).to_numpy(np.int64)
O, H, L, C = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
N = len(T)


def sim(i, side, risk, tgt_pts, end_t):
    entry = C[i] + SL * side
    stop = entry - side * risk
    tgt = entry + side * tgt_pts
    for j in range(i + 1, N):
        if T[j] >= end_t:
            ex = C[j] - SL * side
            break
        if side == 1:
            if O[j] <= stop:
                ex = O[j] - SL
                break
            if L[j] <= stop:
                ex = stop - SL
                break
            if H[j] >= tgt + THRU:
                ex = tgt
                break
        else:
            if O[j] >= stop:
                ex = O[j] + SL
                break
            if H[j] >= stop:
                ex = stop + SL
                break
            if L[j] <= tgt - THRU:
                ex = tgt
                break
    else:
        return None
    return (ex - entry) * side / risk - COMM / (risk * PV)


log = pd.read_csv(LOG)
rows, skipped = [], []
for _, r in log.iterrows():
    if str(r.get("logged_before_result", "")).strip().lower() not in ("yes", "y", "true", "1"):
        skipped.append((r["date"], "not marked logged before result"))
        continue
    try:
        d = pd.Timestamp(r["date"])
        h, m = str(r["signal_candle_open_local"]).split(":")
        t = int((d + pd.Timedelta(hours=int(h), minutes=int(m)) - pd.Timestamp("1970-01-01")).total_seconds())
        i = int(np.searchsorted(T, t))
        if i >= N or T[i] != t:
            skipped.append((r["date"], "no 1m bar at that local time"))
            continue
        if not (8 * 60 <= int(h) * 60 + int(m) <= 8 * 60 + 15):
            skipped.append((r["date"], "signal candle outside 08:00-08:15"))
            continue
        side = 1 if str(r["side"]).strip().upper().startswith("L") else -1
        stop_pts, tgt_pts = float(r["stop_pts"]), float(r["target_pts"])
        risk = stop_pts + SL  # stop distance measured from the slipped entry
        end_t = int((d + pd.Timedelta(hours=17) - pd.Timestamp("1970-01-01")).total_seconds())
        a = sim(i, side, risk, tgt_pts, end_t)
        b = sim(i, -side, risk, tgt_pts, end_t)
        if a is None or b is None:
            skipped.append((r["date"], "data ended"))
            continue
        rows.append((int(r["session"]), d, side, str(r.get("target_type", "")), a, b, tgt_pts / stop_pts))
    except Exception as e:  # keep scoring the rest; report the row
        skipped.append((r.get("date"), f"error {e}"))

print(f"scored {len(rows)} trades; skipped {len(skipped)}")
for s in skipped[:15]:
    print("  skipped:", s)
if not rows:
    sys.exit(0)
A = np.array([x[4] for x in rows])
M = np.array([x[5] for x in rows])
n = len(A)
rng = np.random.default_rng(20261026)
means = np.where(rng.random((20000, n)) < 0.5, A, M).mean(axis=1)
p = float((means >= A.mean()).mean())
se = A.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
print(f"\nALL: n={n} win={100 * (A > 0).mean():.0f}% meanR={A.mean():+.3f} (SE {se:.3f}) | mirror {M.mean():+.3f} | random-side mean {means.mean():+.3f} P={p:.4f}")
for lab, sel in (("longs", [x[2] == 1 for x in rows]), ("shorts", [x[2] == -1 for x in rows])):
    sel = np.array(sel)
    if sel.sum():
        print(f"  {lab}: n={sel.sum()} meanR={A[sel].mean():+.3f}")
for tt in sorted({x[3] for x in rows}):
    sel = np.array([x[3] == tt for x in rows])
    print(f"  target type {tt or '-'}: n={sel.sum()} meanR={A[sel].mean():+.3f}")
for s in sorted({x[0] for x in rows}):
    sel = np.array([x[0] == s for x in rows])
    print(f"  session {s}: n={sel.sum()} meanR={A[sel].mean():+.3f}")
print("  planned RR median %.2f" % np.median([x[6] for x in rows]))
gate = n >= 80 and A.mean() >= 0.15 and p <= 0.05 and all(A[np.array([x[2] == d_ for x in rows])].mean() >= 0 for d_ in (1, -1) if sum(1 for x in rows if x[2] == d_) >= 10)
print(f"\nGATE (n>=80, mean>=+0.15, random-side P<=0.05, both sides >=0): {'PASS' if gate else 'not yet / fail'}")
