"""Descriptive: MT5 broker test pass odds of the TREND-PORT daily streams (block bootstrap of 2021-25 daily returns). Not a registered claim."""
import sys, io, contextlib, numpy as np, pandas as pd
src = open("forex/ea_research/trend_port.py").read().split("if DRY:")[0]
g = {"__name__": "m"}; sys.argv = ["x"]
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src, "x", "exec"), g)
run, sig, UNI = g["run"], g["sig"], g["UNI"]
streams = {"NONFX long-only (drift)": run(sig["LONG"], UNI["NONFX"])[0], "ALL long-only (drift)": run(sig["LONG"], UNI["ALL"])[0],
           "NONFX trend 250": run(sig[250], UNI["NONFX"])[0], "NONFX trend COMBO": run(sig["COMBO"], UNI["NONFX"])[0]}
rng = np.random.default_rng(9)
def sim(x, vol_t, days, B=4000, blk=5):
    x = x[(x.index >= "2021-01-04") & (x.index <= "2025-12-31")].to_numpy(); k = vol_t / (x.std() * np.sqrt(252)); x = x * k
    ps = br = 0
    for _ in range(B):
        i = 0; path = []
        while len(path) < days:
            s0 = rng.integers(0, len(x) - blk); path.extend(x[s0:s0 + blk])
        path = np.array(path[:days]); eq = np.cumprod(1 + path)
        hit_day = np.where(path <= -0.025)[0]; hit_floor = np.where(eq <= 0.92)[0]; hit_tgt = np.where(eq >= 1.08)[0]
        b = min(hit_day[0] if len(hit_day) else 999, hit_floor[0] if len(hit_floor) else 999)
        t = hit_tgt[0] if len(hit_tgt) else 999
        if t < b: ps += 1
        elif b < 999: br += 1
    return ps / B * 100, br / B * 100
print("P(pass +8% within N trading days) / P(breach: day <= -2.5% or equity <= -8%) at annualised portfolio vol V")
for name, r in streams.items():
    out = []
    for V in (0.15, 0.25, 0.40):
        p33, b33 = sim(r, V, 33); p55, b55 = sim(r, V, 55)
        out.append(f"V={int(V*100)}%: 33d {p33:.0f}%/{b33:.0f}%, 55d {p55:.0f}%/{b55:.0f}%")
    print(f"{name:26s}", " | ".join(out))
