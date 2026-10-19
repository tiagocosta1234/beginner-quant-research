"""the trader's described 12 EMA + FVG rule (PREREG_MANUALRULE.md). python manualrule_test.py --dry-run | --run | --hold"""
import sys, numpy as np, pandas as pd
from ema12_test import load, open_min, stats, DEV_END, VAL_END, MARKETS
def prep(m, last_day):
    d = load(m, last_day=last_day); d["mo"] = (d.bo + d.ao) / 2; return d
def arrays(d): return {k: d[k].to_numpy() for k in ("hm", "mid", "mo", "mh", "ml", "ema", "atr", "bo", "ao")}
def find_target(A, t, side, entry, atr_t, variant):
    best = None
    for c in range(max(t - 90, 2), t + 1):
        a = c - 2
        if side > 0:
            if not (A["ml"][a] > A["mh"][c]): continue
            near, far = A["mh"][c], A["ml"][a]
            if c < t and A["mh"][c + 1:t + 1].max() >= far: continue
        else:
            if not (A["mh"][a] < A["ml"][c]): continue
            near, far = A["ml"][c], A["mh"][a]
            if c < t and A["ml"][c + 1:t + 1].min() <= far: continue
        dn = (near - entry) * side
        if dn < 0.5 * atr_t: continue
        size = abs(far - near)
        lvl = near if variant == "K2" else far if variant == "K3" else (far if size <= 1.5 * atr_t else (near + far) / 2)
        if best is None or dn < best[0]: best = (dn, lvl)
    return None if best is None else best[1]
def signals(d, A, sess, variant, upto_day=None):
    days = d.day.to_numpy(); out = []; first = {}
    for i, dy in enumerate(days): first.setdefault(dy, i)
    for dy, i_first in first.items():
        if dy.weekday() >= 5 or (upto_day is not None and dy > upto_day): continue
        om = open_min(dy, sess); i = i_first
        while i < len(days) and days[i] == dy and A["hm"][i] < om: i += 1
        for t in range(i, len(days)):
            if days[t] != dy or A["hm"][t] > om + 14: break
            if t < 100 or np.isnan(A["atr"][t - 1]): continue
            o, c, h, l, e_ = A["mo"][t], A["mid"][t], A["mh"][t], A["ml"][t], A["ema"][t]
            if not ((o - e_) * (c - e_) < 0): continue
            side = 1 if c > e_ else -1; body = abs(c - o)
            if not (body > max(h - max(o, c), min(o, c) - l) and body >= 0.5 * A["atr"][t - 1]): continue
            e = t + 1
            if e >= len(days) or days[e] != dy or A["hm"][e] - A["hm"][t] > 2: break
            entry = A["ao"][e] if side > 0 else A["bo"][e]
            tgt = find_target(A, t, side, entry, A["atr"][t - 1], variant)
            if tgt is None: continue
            dist = abs(tgt - entry)
            if dist <= 0: continue
            out.append(dict(day=dy, t=t, e=e, side=side, entry=entry, d=dist)); break
    return out
def simulate(d, sig, max_bars=60):
    bh, bl, bc, ah, al, ac = (d[k].to_numpy() for k in ("bh", "bl", "bc", "ah", "al", "ac")); res = []
    for s in sig:
        e, side, entry, dist = s["e"], s["side"], s["entry"], s["d"]; tp = entry + side * dist; sl = entry - side * 2 * dist; R = None
        for j in range(e, min(e + max_bars, len(bh))):
            if side > 0: htp, hsl = bh[j] >= tp, bl[j] <= sl
            else: htp, hsl = al[j] <= tp, ah[j] >= sl
            if hsl: R = -1.0; break
            if htp: R = 0.5; break
        if R is None:
            j = min(e + max_bars, len(bh)) - 1; R = ((bc[j] - entry) if side > 0 else (entry - ac[j])) / (2 * dist)
        res.append(dict(day=pd.Timestamp(s["day"]), side=side, R=R, d=dist))
    return pd.DataFrame(res)
TRIALS = [(m, s, v) for m in MARKETS for s in ("London", "NY") for v in ("K1", "K2", "K3")]
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--dry-run"
    D = {m: prep(m, None if mode == "--hold" else "2025-12-31") for m in MARKETS}; A = {m: arrays(D[m]) for m in MARKETS}
    if mode == "--dry-run":
        for m in MARKETS:
            for s in ("London", "NY"):
                sg = pd.DataFrame(signals(D[m], A[m], s, "K1")); sg["yr"] = pd.to_datetime(sg.day).dt.year
                print(m, s, "K1 trades per year:", sg.groupby("yr").size().to_dict(), "| long share %.0f%% | median target distance %.2f" % (100 * (sg.side > 0).mean(), sg.d.median()))
        rng = np.random.default_rng(9); bad = tested = 0
        for m in MARKETS:
            for s in ("London", "NY"):
                for v in ("K1", "K2", "K3"):
                    full = signals(D[m], A[m], s, v)
                    for k in rng.choice(len(full), min(25, len(full)), replace=False):
                        x = full[k]; cut = D[m].iloc[: x["e"] + 1].copy(); y = [z for z in signals(cut, arrays(cut), s, v) if z["day"] == x["day"]]; tested += 1
                        if not (y and y[0]["e"] == x["e"] and y[0]["side"] == x["side"] and abs(y[0]["d"] - x["d"]) < 1e-9): bad += 1
        print("truncation test: %d trades recomputed with the future cut, %d mismatches" % (tested, bad))
        O = pd.read_csv("replay_mt5.csv"); fire = same = 0
        for _, r_ in O.iterrows():
            sg = [z for z in signals(D["XAUUSD"], A["XAUUSD"], r_.ses if r_.ses == "London" else "NY", "K1") if pd.Timestamp(z["day"]) == pd.Timestamp(r_.day)]
            if sg: fire += 1; same += (sg[0]["side"] > 0) == (r_.side == "L")
        print("the trader's 30 gold session-days: the rule trades on %d, same direction on %d" % (fire, same))
        g = D["XAUUSD"]; sg = signals(g, A["XAUUSD"], "London", "K1")[60:63]
        for z in sg:
            t = z["t"]; print("hand check", z["day"], g.dt[t].time(), "open %.2f close %.2f ema %.2f body %.2f atr %.2f -> side %d entry %.2f target dist %.2f stop dist %.2f" % (A["XAUUSD"]["mo"][t], A["XAUUSD"]["mid"][t], A["XAUUSD"]["ema"][t], abs(A["XAUUSD"]["mid"][t] - A["XAUUSD"]["mo"][t]), A["XAUUSD"]["atr"][t-1], z["side"], z["entry"], z["d"], 2 * z["d"]))
    elif mode == "--run":
        rows = []; cache = {}
        for (m, s, v) in TRIALS:
            x = simulate(D[m], signals(D[m], A[m], s, v)); x = x[x.day >= pd.Timestamp("2022-01-01")]
            dev = x[x.day <= DEV_END]; val = x[(x.day > DEV_END) & (x.day <= VAL_END)]; a, b = stats(dev), stats(val)
            rows.append(dict(market=m, sess=s, var=v, dev_n=a["n"], dev_R=a["meanR"], dev_t=a["t"], dev_win=a["win"], dev_pf=a["pf"], val_n=b["n"], val_R=b["meanR"], val_t=b["t"], val_win=b["win"],
                             y22=x[x.day.dt.year == 2022].R.mean(), y23=x[x.day.dt.year == 2023].R.mean(), y24=x[x.day.dt.year == 2024].R.mean(), med_d=x.d.median()))
        T = pd.DataFrame(rows); T["cand"] = (T.dev_n >= 200) & (T.dev_R >= 0.05) & (T.dev_t >= 2.87) & (T.val_R > 0) & (T.val_t >= 1.65)
        pd.set_option("display.width", 250); print(T.round(3).to_string(index=False)); T.to_csv("MANUALRULE_TRIALS.csv", index=False); print("\ncandidates:", int(T.cand.sum()), "of", len(T))
