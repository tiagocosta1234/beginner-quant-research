"""Mechanical 12 EMA session-open rule on MT5 M1 bid/ask (PREREG_EMA12.md). python ema12_test.py --dry-run | --run | --hold TRIALNAME"""
import sys, datetime as dt, numpy as np, pandas as pd
from zoneinfo import ZoneInfo
LON, NYC, ATH = ZoneInfo("Europe/London"), ZoneInfo("America/New_York"), ZoneInfo("Europe/Athens")
DEV_END, VAL_END = pd.Timestamp("2024-12-31"), pd.Timestamp("2025-12-31")
MARKETS = ("XAUUSD", "NSDQ")
def open_min(day, sess):
    t = dt.datetime(day.year, day.month, day.day, 8, 0, tzinfo=LON) if sess == "London" else dt.datetime(day.year, day.month, day.day, 9, 30, tzinfo=NYC)
    a = t.astimezone(ATH); return a.hour * 60 + a.minute
def load(m, last_day=None):
    d = pd.read_parquet(f"forex/data_mt5/{m}_M1_rates.parquet").sort_values("t").reset_index(drop=True)
    d["dt"] = pd.to_datetime(d.t, unit="s"); d["day"] = d.dt.dt.date; d["hm"] = d.dt.dt.hour * 60 + d.dt.dt.minute; d["yr"] = d.dt.dt.year
    if last_day is not None: d = d[d.dt <= pd.Timestamp(last_day) + pd.Timedelta(days=1)].reset_index(drop=True)
    med = d[d.sp > 0].groupby("yr").sp.median()
    z = d.sp <= 0
    for b, a in (("bo", "ao"), ("bh", "ah"), ("bl", "al"), ("bc", "ac")): d.loc[z, a] = d.loc[z, b] + d.loc[z, "yr"].map(med)
    d["mid"] = (d.bc + d.ac) / 2; d["mh"] = (d.bh + d.ah) / 2; d["ml"] = (d.bl + d.al) / 2
    d["ema"] = d.mid.ewm(span=12, adjust=False).mean(); d["atr"] = (d.mh - d.ml).rolling(14).mean()
    return d
def signals(d, sess, stop, upto_day=None, filt="F0"):
    """one entry per day: dict(day, i_sig, e, side, entry, risk). Uses only bars <= signal bar for the decision."""
    A = {k: d[k].to_numpy() for k in ("hm", "mid", "ema", "atr", "mh", "ml", "bo", "ao")}; days = d.day.to_numpy(); out = []
    first = {}
    for i, dy in enumerate(days):
        first.setdefault(dy, i)
    for dy, i_first in first.items():
        if dy.weekday() >= 5 or (upto_day is not None and dy > upto_day): continue
        om = open_min(dy, sess); i = i_first
        while i < len(days) and days[i] == dy and A["hm"][i] < om: i += 1
        for t in range(i, len(days)):
            if days[t] != dy or A["hm"][t] > om + 14: break
            if t < 15 or np.isnan(A["atr"][t]): continue
            s_now = np.sign(A["mid"][t] - A["ema"][t]); s_prev = np.sign(A["mid"][t-1] - A["ema"][t-1])
            if s_now == 0 or s_now == s_prev: continue
            if filt == "F30" and s_now != np.sign(A["mid"][t] - A["mid"][t-30]): continue
            e = t + 1
            if e >= len(days) or days[e] != dy or A["hm"][e] - A["hm"][t] > 2: break
            entry = A["ao"][e] if s_now > 0 else A["bo"][e]
            if stop == "ATR25": risk = 2.5 * A["atr"][t]
            else:
                sw = (entry - A["ml"][t-14:t+1].min()) if s_now > 0 else (A["mh"][t-14:t+1].max() - entry)
                risk = max(sw, A["atr"][t])
            if risk > 0: out.append(dict(day=dy, t=t, e=e, side=int(s_now), entry=entry, risk=risk))
            break
    return out
def simulate(d, sig, r, max_bars=60):
    bh, bl, bc, ah, al, ac = (d[k].to_numpy() for k in ("bh", "bl", "bc", "ah", "al", "ac")); res = []
    for s in sig:
        e, side, entry, risk = s["e"], s["side"], s["entry"], s["risk"]
        tp = entry + side * r * risk; sl = entry - side * risk; R = None
        for j in range(e, min(e + max_bars, len(bh))):
            if side > 0: htp, hsl = bh[j] >= tp, bl[j] <= sl
            else: htp, hsl = al[j] <= tp, ah[j] >= sl
            if hsl: R = -1.0; break
            if htp: R = r; break
        if R is None:
            j = min(e + max_bars, len(bh)) - 1
            R = side * ((bc[j] if side > 0 else ac[j]) - entry) / risk * (1 if side > 0 else 1)
            if side < 0: R = (entry - ac[j]) / risk
        res.append(dict(day=pd.Timestamp(s["day"]), side=side, R=R, risk=risk))
    return pd.DataFrame(res)
def stats(x):
    if len(x) < 2: return dict(n=len(x), meanR=np.nan, t=np.nan, win=np.nan, pf=np.nan)
    w, l = x.R[x.R > 0].sum(), -x.R[x.R < 0].sum()
    return dict(n=len(x), meanR=x.R.mean(), t=x.R.mean() / (x.R.std(ddof=1) / np.sqrt(len(x))), win=100 * (x.R > 0).mean(), pf=w / l if l else np.inf)
TRIALS = [(m, s, st, r, f) for m in MARKETS for s in ("London", "NY") for st in ("ATR25", "SW15") for r in (0.525, 1.0) for f in ("F0", "F30")]
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--dry-run"
    D = {m: load(m, last_day=None if mode == "--hold" else "2025-12-31") for m in MARKETS}
    if mode == "--dry-run":
        for m in MARKETS:
            for s in ("London", "NY"):
                sg = pd.DataFrame(signals(D[m], s, "ATR25"))
                sg["yr"] = pd.to_datetime(sg.day).dt.year
                print(m, s, "signals per year:", sg.groupby("yr").size().to_dict(), "| long share %.0f%% | median risk %.2f" % (100 * (sg.side > 0).mean(), sg.risk.median()))
        # truncation test: decision unchanged when everything after the entry bar's open is cut
        rng = np.random.default_rng(5); bad = 0; tested = 0
        for m in MARKETS:
            for s in ("London", "NY"):
                for stp, f in (("ATR25", "F0"), ("SW15", "F0"), ("ATR25", "F30"), ("SW15", "F30")):
                    full = signals(D[m], s, stp, filt=f)
                    for k in rng.choice(len(full), 40, replace=False):
                        x = full[k]; cut = D[m].iloc[: x["e"] + 1].copy()
                        y = [z for z in signals(cut, s, stp, filt=f) if z["day"] == x["day"]]
                        tested += 1
                        if not (y and y[0]["e"] == x["e"] and y[0]["side"] == x["side"] and abs(y[0]["risk"] - x["risk"]) < 1e-9): bad += 1
        print("truncation test: %d sessions re-computed with future cut, %d mismatches" % (tested, bad))
        # the trader's 30 gold session-days: does the rule fire in his direction? (direction only, no P&L)
        O = pd.read_csv("replay_mt5.csv"); hit = same = 0
        for _, r_ in O.iterrows():
            sg = [z for z in signals(D["XAUUSD"], r_.ses if r_.ses == "London" else "NY", "ATR25") if pd.Timestamp(z["day"]) == pd.Timestamp(r_.day)]
            if sg: hit += 1; same += (sg[0]["side"] > 0) == (r_.side == "L")
        print("the trader's 30 gold session-days: rule fires on %d, same direction on %d" % (hit, same))
        # hand check of three signals
        g = D["XAUUSD"]; sg = signals(g, "London", "ATR25")[100:103]
        for z in sg: print("hand check XAU London", z["day"], "bar", g.dt[z["t"]].time(), "mid", round(g.mid[z["t"]], 2), "ema", round(g.ema[z["t"]], 2), "-> side", z["side"], "entry bar", g.dt[z["e"]].time(), "entry", round(z["entry"], 2), "risk", round(z["risk"], 2))
    elif mode == "--run":
        rows = []
        cache = {}
        for (m, s, st, r, f) in TRIALS:
            if (m, s, st, f) not in cache: cache[(m, s, st, f)] = signals(D[m], s, st, filt=f)
            x = simulate(D[m], cache[(m, s, st, f)], r)
            x = x[x.day >= pd.Timestamp("2022-01-01")]
            dev = x[x.day <= DEV_END]; val = x[(x.day > DEV_END) & (x.day <= VAL_END)]
            a, b = stats(dev), stats(val)
            rows.append(dict(market=m, sess=s, stop=st, r=r, filt=f, dev_n=a["n"], dev_R=a["meanR"], dev_t=a["t"], dev_win=a["win"], dev_pf=a["pf"], val_n=b["n"], val_R=b["meanR"], val_t=b["t"], val_win=b["win"],
                             y22=x[x.day.dt.year == 2022].R.mean(), y23=x[x.day.dt.year == 2023].R.mean(), y24=x[x.day.dt.year == 2024].R.mean()))
        T = pd.DataFrame(rows); T["cand"] = (T.dev_n >= 300) & (T.dev_R >= 0.05) & (T.dev_t >= 3.16) & (T.val_R > 0) & (T.val_t >= 1.65)
        pd.set_option("display.width", 250); print(T.round(3).to_string(index=False)); T.to_csv("EMA12_TRIALS.csv", index=False)
        print("\ncandidates:", int(T.cand.sum()), "of", len(T))
