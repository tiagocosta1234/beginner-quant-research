"""Direction-skill test: same entry minute, same stop/target distances, MT5 broker bid/ask; his direction vs the mirror trade vs random directions. Descriptive on 30 trades (14 Apr-12 May 2025)."""
exec(open("replay.py").read().split("out = []")[0])
def run_dir(g, i, side, risk_, rew_):
    r, ent = sim_ba(g, i, side, risk_, rew_, True)
    return rew_/risk_ if r == "W" else -1.0
rows = []
for k in range(len(D)):
    day = assign[k]; g = days[day]; lo, hi = WIN[ses[k]]
    mins = [i for i in g.index[(g.hm >= lo) & (g.hm <= hi)] if abs(g.mo[i] - E[k]) <= TOL]
    best = min(mins, key=lambda i: abs(g.mo[i] - E[k]))
    for shift in (0,):
        i = best + shift
        rl = run_dir(g, i, "L", risk[k], rew[k]); rs = run_dir(g, i, "S", risk[k], rew[k])
        rows.append(dict(k=k+1, mine=d[k], R_L=rl, R_S=rs, R_mine=rl if d[k] == "L" else rs, R_mirror=rs if d[k] == "L" else rl))
Z = pd.DataFrame(rows)
print("30 trades: his direction mean R %+.3f (wins %d) | mirror trade mean R %+.3f (wins %d) | always long %+.3f | always short %+.3f" % (
    Z.R_mine.mean(), (Z.R_mine > 0).sum(), Z.R_mirror.mean(), (Z.R_mirror > 0).sum(), Z.R_L.mean(), Z.R_S.mean()))
both_win = int(((Z.R_mine > 0) & (Z.R_mirror > 0)).sum()); mine_only = int(((Z.R_mine > 0) & (Z.R_mirror < 0)).sum()); mirror_only = int(((Z.R_mine < 0) & (Z.R_mirror > 0)).sum()); both_lose = int(((Z.R_mine < 0) & (Z.R_mirror < 0)).sum())
print("both directions win: %d | only his: %d | only the mirror: %d | both lose: %d" % (both_win, mine_only, mirror_only, both_lose))
rng = np.random.default_rng(11); L = Z.R_L.to_numpy(); S = Z.R_S.to_numpy(); obs = Z.R_mine.mean()
null = np.array([np.where(rng.random(len(Z)) < 0.5, L, S).mean() for _ in range(200000)])
print("random direction on the same 30 entries: mean R %.3f (5%%-95%% %.3f..%.3f); P(random >= his %+.3f) = %.4f" % (null.mean(), np.quantile(null, .05), np.quantile(null, .95), obs, (null >= obs).mean()))
# keep his long/short split (11 L / 19 S): shuffle which trades are long
mine = (Z.mine == "L").to_numpy(); nl = mine.sum()
null2 = []
for _ in range(100000):
    p = rng.permutation(len(Z)); isL = np.zeros(len(Z), bool); isL[p[:nl]] = True; null2.append(np.where(isL, L, S).mean())
null2 = np.array(null2); print("random assignment keeping his 11 long / 19 short: mean R %.3f; P(>= his) = %.4f" % (null2.mean(), (null2 >= obs).mean()))
print("sign test on trades where the two directions differ: his wins %d vs mirror wins %d (n %d)" % (mine_only, mirror_only, mine_only + mirror_only))
from math import comb
n = mine_only + mirror_only
if n: print("  one-sided binomial p = %.4f" % sum(comb(n, i) for i in range(mine_only, n + 1)) / 2**n if False else "  one-sided binomial p = %.4f" % (sum(comb(n, i) for i in range(mine_only, n + 1)) / 2**n))
Z.to_csv("direction_skill.csv", index=False)

# ---- can a simple momentum rule reproduce the direction at his entry minutes?
rules = {}
for k in range(len(D)):
    day = assign[k]; g = days[day]; lo, hi = WIN[ses[k]]
    mins = [i for i in g.index[(g.hm >= lo) & (g.hm <= hi)] if abs(g.mo[i] - E[k]) <= TOL]; i = min(mins, key=lambda j: abs(g.mo[j] - E[k]))
    om = lo; i_open = g.index[g.hm >= om][0]
    sg = lambda v: 1 if v > 0 else -1
    rules.setdefault("momentum prev 30 min", []).append(sg(g.mo[i] - g.mo[i-30])); rules.setdefault("momentum since session open", []).append(sg(g.mo[i] - g.mo[max(i_open-1, 0)]))
    rules.setdefault("price vs mean of last 12 min", []).append(sg(g.mo[i] - g.mo[max(i-12, 0):i].mean()))
print("\nmean R at HIS entry minutes with a simple direction rule instead of his (MT5 broker bid/ask):")
for name, sides in rules.items():
    R = np.array([Z.R_L[k] if sides[k] > 0 else Z.R_S[k] for k in range(len(Z))]); agree = int(sum((sides[k] > 0) == (Z.mine[k] == "L") for k in range(len(Z))))
    print("  %-30s mean R %+.3f | wins %d/30 | agrees with his direction on %d" % (name, R.mean(), (R > 0).sum(), agree))
