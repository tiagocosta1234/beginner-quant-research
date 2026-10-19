exec(open("match.py").read().split("# chronological DP")[0])
import datetime
assign = """2025-04-14 2025-04-14 2025-04-15 2025-04-15 2025-04-16 2025-04-16 2025-04-17 2025-04-17 2025-04-21 2025-04-21 2025-04-22 2025-04-23 2025-04-24 2025-04-25 2025-04-25 2025-04-28 2025-04-29 2025-04-30 2025-04-30 2025-05-01 2025-05-02 2025-05-05 2025-05-05 2025-05-06 2025-05-06 2025-05-07 2025-05-08 2025-05-09 2025-05-09 2025-05-12""".split()
assign = [datetime.date.fromisoformat(x) for x in assign]
def sim_ba(g, i0, side, risk_, rew_, pessimistic=True):
    # entry at the real quote of that minute (long: ask open; short: bid open); exits on the real side of the book
    if side == "L":
        ent = g.ao[i0]; tp = ent + rew_; sl = ent - risk_
        for j in range(i0, min(i0+400, len(g))):
            htp = g.bh[j] >= tp; hsl = g.bl[j] <= sl
            if htp and hsl: return ("L" if pessimistic else "W"), ent
            if htp: return "W", ent
            if hsl: return "L", ent
    else:
        ent = g.bo[i0]; tp = ent - rew_; sl = ent + risk_
        for j in range(i0, min(i0+400, len(g))):
            htp = g.al[j] <= tp; hsl = g.ah[j] >= sl
            if htp and hsl: return ("L" if pessimistic else "W"), ent
            if htp: return "W", ent
            if hsl: return "L", ent
    return None, ent
out = []
for k in range(len(D)):
    day = assign[k]; g = days[day]; lo, hi = WIN[ses[k]]
    mins = [i for i in g.index[(g.hm >= lo) & (g.hm <= hi)] if abs(g.mo[i] - E[k]) <= TOL]
    best = min(mins, key=lambda i: abs(g.mo[i] - E[k]))
    r, ent = sim_ba(g, best, d[k], risk[k], rew[k], True)
    ro, _ = sim_ba(g, best, d[k], risk[k], rew[k], False)
    # robustness: every candidate minute of that day
    allr = [sim_ba(g, i, d[k], risk[k], rew[k], True)[0] for i in mins]
    out.append(dict(k=k+1, day=day, hm=int(g.hm[best]), side=d[k], ses=ses[k], rec="W" if win[k] else "L", ba=r, ba_opt=ro, frac_win_minutes=np.mean([x == "W" for x in allr]), spr=float(g.sp[best]), risk=risk[k], rew=rew[k], rr=rew[k]/risk[k], dE=g.mo[best]-E[k]))
O = pd.DataFrame(out)
pd.set_option("display.width", 200)
print(O[["k","day","hm","ses","side","rec","ba","ba_opt","frac_win_minutes","spr","risk","rew","dE"]].round(2).to_string(index=False))
for lab, col in (("pessimistic (same-minute SL+TP counts as loss)", "ba"), ("optimistic (counts as win)", "ba_opt")):
    w = (O[col] == "W"); R = np.where(w, O.rr, -1.0)
    print("%s: wins %d/30 (%.1f%%), sum R %.2f, mean R %.3f, t %.2f" % (lab, w.sum(), 100*w.mean(), R.sum(), R.mean(), R.mean()/(R.std(ddof=1)/np.sqrt(len(R)))))
print("recorded: wins 25/30, sum R 8.10, mean R 0.270")
print("changed from win to loss:", O[(O.rec == "W") & (O.ba == "L")].k.tolist(), "| loss to win:", O[(O.rec == "L") & (O.ba == "W")].k.tolist())
print("spread at entry minute: mean %.3f median %.3f" % (O.spr.mean(), O.spr.median()))
O.to_csv("replay_mt5.csv", index=False)
