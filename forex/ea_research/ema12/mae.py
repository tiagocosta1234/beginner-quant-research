exec(open("replay.py").read().split("out = []")[0])
def sim_ba2(g, i0, side, risk_, rew_):
    if side == "L":
        ent = g.ao[i0]; tp = ent + rew_; sl = ent - risk_; worst = 0.0
        for j in range(i0, min(i0+400, len(g))):
            worst = max(worst, ent - g.bl[j])
            htp = g.bh[j] >= tp; hsl = g.bl[j] <= sl
            if hsl: return "L", min(worst/risk_, 1.0), j - i0
            if htp: return "W", min(worst/risk_, 1.0), j - i0
    else:
        ent = g.bo[i0]; tp = ent - rew_; sl = ent + risk_; worst = 0.0
        for j in range(i0, min(i0+400, len(g))):
            worst = max(worst, g.ah[j] - ent)
            htp = g.al[j] <= tp; hsl = g.ah[j] >= sl
            if hsl: return "L", min(worst/risk_, 1.0), j - i0
            if htp: return "W", min(worst/risk_, 1.0), j - i0
    return None, 1.0, None
rows_ = []
for k in range(len(D)):
    day = assign[k]; g = days[day]; lo, hi = WIN[ses[k]]
    mins = [i for i in g.index[(g.hm >= lo) & (g.hm <= hi)] if abs(g.mo[i] - E[k]) <= TOL]
    best = min(mins, key=lambda i: abs(g.mo[i] - E[k]))
    r, mae, dur = sim_ba2(g, best, d[k], risk[k], rew[k])
    rows_.append((k+1, r, rew[k]/risk[k], mae, dur))
M = pd.DataFrame(rows_, columns=["k", "res", "rr", "mae_R", "dur_min"])
print(M.round(2).to_string(index=False))
print("wins", (M.res == "W").sum(), "| MAE of winners (R): mean %.2f max %.2f | duration winners (min): median %.0f max %.0f" % (M[M.res=="W"].mae_R.mean(), M[M.res=="W"].mae_R.max(), M[M.res=="W"].dur_min.median(), M[M.res=="W"].dur_min.max()))
M.to_csv("mae_mt5.csv", index=False)
