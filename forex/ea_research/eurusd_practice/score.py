import sys, json, numpy as np, pandas as pd
rnd = sys.argv[1]; calls = json.load(open(f"calls_{rnd}.json")); meta = json.load(open(f"meta_{rnd}.json"))
d = pd.read_parquet("D:/finance/beginner-quant-research/forex/data_mt5/EURUSD_M1_rates.parquet", columns=["t","bo","bh","bl","bc","ao","ah","al","ac"]).sort_values("t")
d["dt"] = pd.to_datetime(d.t, unit="s"); d = d.set_index("dt")
H = d.resample("1h").agg(dict(bo="first", bh="max", bl="min", bc="last", ao="first", ah="max", al="min", ac="last")).dropna()
tot = []; print("case side  result   R   bars  note")
for k, (side, sl, tp, why) in calls.items():
    t0 = pd.Timestamp(meta[k]["t0"]); f = H[H.index >= t0].iloc[:24]
    if side == "F":
        r_dir = (f.bc.iloc[-1] - f.bo.iloc[0]) * 1e4; print(f"{k:5s} FLAT  (market moved {r_dir:+.1f} pips over 24h; would a {'long' if r_dir>0 else 'short'} have worked)"); continue
    pip = 1e-4; res = None
    if side == "L":
        e = f.ao.iloc[0]; s, t = e - sl * pip, e + tp * pip
        for i, (_, r) in enumerate(f.iterrows()):
            if r.bl <= s: res = (-sl - 0.0, i + 1); break
            if r.bh >= t: res = (tp, i + 1); break
        if res is None: res = ((f.bc.iloc[-1] - e) / pip, 24)
    else:
        e = f.bo.iloc[0]; s, t = e + sl * pip, e - tp * pip
        for i, (_, r) in enumerate(f.iterrows()):
            if r.ah >= s: res = (-sl, i + 1); break
            if r.al <= t: res = (tp, i + 1); break
        if res is None: res = ((e - f.ac.iloc[-1]) / pip, 24)
    pips, bars = res; R = pips / sl; tot.append(R); print(f"{k:5s} {side}  {pips:+6.1f}p {R:+5.2f}R {bars:3d}  {why[:50]}")
print(f"trades {len(tot)}  net {sum(tot):+.2f}R  mean {np.mean(tot):+.2f}R  winners {sum(r>0 for r in tot)}/{len(tot)}")
