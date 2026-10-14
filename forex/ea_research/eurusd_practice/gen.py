import sys, json, numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from pathlib import Path
OUT = Path("D:/finance/scratch/eurusd_practice"); rnd = int(sys.argv[1]); n = int(sys.argv[2])
d = pd.read_parquet("forex/data_mt5/EURUSD_M1_rates.parquet", columns=["t","bo","bh","bl","bc","ao","ac"]).sort_values("t")
d["dt"] = pd.to_datetime(d.t, unit="s"); d = d.set_index("dt"); mid = lambda a,b: (a+b)/2
d["o"]=(d.bo+d.ao)/2; d["c"]=(d.bc+d.ac)/2; d["h"]=d.bh+(d.ao-d.bo)/2; d["l"]=d.bl+(d.ao-d.bo)/2
ag = dict(o="first", h="max", l="min", c="last")
H1 = d.resample("1h").agg(ag).dropna(); D1 = d.resample("1D").agg(ag).dropna(); D1 = D1[D1.index.dayofweek < 5]
rng = np.random.default_rng(1000 + rnd)
cand = H1.index[(H1.index >= "2022-03-01") & (H1.index < "2025-12-20") & (H1.index.hour == 10) & (H1.index.dayofweek < 5)]
picks = rng.choice(len(cand), n, replace=False); meta = {}
def candles(ax, df, w):
    x = np.arange(len(df))
    for i,(o,h,l,c) in enumerate(zip(df.o,df.h,df.l,df.c)):
        col = "#1a7f37" if c>=o else "#cf222e"; ax.plot([i,i],[l,h],color=col,lw=0.8); ax.add_patch(plt.Rectangle((i-w/2,min(o,c)),w,max(abs(c-o),1e-5),color=col))
    ax.set_xlim(-1,len(df)+1)
for k,pi in enumerate(picks, 1):
    t0 = cand[pi]; h = H1[H1.index < t0].iloc[-120:]            # bars strictly before the decision hour: last bar is 09:00
    dd = D1[D1.index < t0.normalize()].iloc[-70:]
    fig,(a1,a2) = plt.subplots(1,2,figsize=(17,6.5),gridspec_kw={"width_ratios":[1,1.5]})
    candles(a1,dd,0.7); e20=dd.c.ewm(span=20).mean().values; e50=dd.c.ewm(span=50).mean().values; a1.plot(e20,color="#0969da",lw=1,label="EMA20"); a1.plot(e50,color="#bf8700",lw=1,label="EMA50"); a1.set_title("EURUSD Daily (last 70 sessions)"); a1.legend(loc="upper left"); a1.grid(alpha=.25)
    allh = H1[H1.index < t0].iloc[-170:]; e20h=allh.c.ewm(span=20).mean().iloc[-120:].values; e50h=allh.c.ewm(span=50).mean().iloc[-120:].values
    candles(a2,h,0.7); a2.plot(e20h,color="#0969da",lw=1,label="EMA20"); a2.plot(e50h,color="#bf8700",lw=1,label="EMA50")
    pdh,pdl = dd.h.iloc[-1], dd.l.iloc[-1]; a2.axhline(pdh,ls="--",color="gray",lw=.8); a2.axhline(pdl,ls="--",color="gray",lw=.8)
    a2.set_title(f"Case {rnd}.{k}  H1 (last 120 bars; dashed = prior-day high/low)  decision at next bar open"); a2.legend(loc="upper left"); a2.grid(alpha=.25)
    a2.text(0.99,0.02,f"last close {h.c.iloc[-1]:.5f}   ATR14(H1) {(h.h-h.l).rolling(14).mean().iloc[-1]*1e4:.1f} pips",transform=a2.transAxes,ha="right",fontsize=9)
    fig.tight_layout(); fig.savefig(OUT/f"case_{rnd}_{k}.png",dpi=70); plt.close(fig)
    meta[f"{rnd}.{k}"] = {"t0": str(t0), "entry_ref": float(h.c.iloc[-1])}
json.dump(meta, open(OUT/f"meta_{rnd}.json","w"))
print("made", n)
