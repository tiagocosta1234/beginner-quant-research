"""SIMULATION (22 Oct, the trader: 'whats the best and fastest version'): the same MT5 broker account model as manual_s1_pass_sim.py (start 95,472.14, pass 108,000, floor 92,000, +2,000 a day cap, one S1 trade a weekday with probability 0.95,
dollar risk capped by 3.1 lots), now comparing SIZING POLICIES instead of one risk number: fixed USD 500 .. 2,000, and a dynamic rule risk = min(2,000, k x cushion above the floor, what is still needed to pass), floor 250.
Sizing is a choice, not a data-mined edge, so it is legitimate to rank; the outcome scenarios are the same as before (S1 as recorded is in-sample optimistic). Best = highest pass probability; fastest = lowest mean business days to pass among the policies within 1 point of the best pass probability.
Second block: which target ratio (0.53 as logged / 0.75 / 1.0 = S1 / 1.5) is fastest at the same policy - post-hoc, same 50 trades. python -B manual_s1_policy_scan.py > MANUAL_S1_POLICY_SCAN_OUTPUT.txt"""
import sys, io, contextlib, numpy as np, pandas as pd
sys.dont_write_bytecode = True
with contextlib.redirect_stdout(io.StringIO()):
    import manual_fixed_bracket as K
    base, z75, z15 = K.trades(), K.trades_own(0.75), K.trades_own(1.5)
Z = K.Zown; R1 = Z.R_mine.to_numpy(float); ST = Z.risk.to_numpy(float); JAN = (Z.per != "Apr-May 2025").to_numpy()
START, TARGET, FLOOR, DAYCAP, CAPLOTS, P_TRADE, H, N = 95472.14, 108000.0, 92000.0, 2000.0, 3.1, 0.95, 260, 20000
rng = np.random.default_rng(7)
def fixed(x): return lambda bal: np.full(len(bal), float(x))
def dyn(k): return lambda bal: np.clip(np.minimum(k * (bal - FLOOR), TARGET - bal), 250.0, 2000.0)
def sim(draw, policy):
    bal = np.full(N, START); alive = np.ones(N, bool); done = np.full(N, np.nan); out = np.zeros(N, int)
    for d in range(1, H + 1):
        tr = alive & (rng.random(N) < P_TRADE); r, st = draw(N); risk = policy(bal)
        if policy.__name__ == "<lambda>" and False: pass
        usd = np.minimum(r * np.minimum(risk, CAPLOTS * 100 * st), DAYCAP)
        bal = np.where(tr, bal + usd, bal); passed = alive & (bal >= TARGET); br = alive & ~passed & (bal <= FLOOR)
        done[passed | br] = d; out[passed] = 1; out[br] = 2; alive &= ~(passed | br)
        if not alive.any(): break
    ps = out == 1
    return 100 * ps.mean(), 100 * (out == 2).mean(), (done[ps].mean() if ps.any() else np.nan), (np.median(done[ps]) if ps.any() else np.nan)
def boot(R, S, mask):
    idx = np.flatnonzero(mask); return lambda n: (lambda k: (R[k], S[k]))(rng.choice(idx, n))
def wr(p): return lambda n: (lambda k, w: (np.where(w, 1.0, -1.0) - 0.48 / ST[k], ST[k]))(rng.integers(0, len(ST), n), rng.random(n) < p)
POL = [("fixed 500", fixed(500)), ("fixed 750", fixed(750)), ("fixed 1,000", fixed(1000)), ("fixed 1,250", fixed(1250)), ("fixed 1,500", fixed(1500)), ("fixed 2,000", fixed(2000)),
       ("dynamic k=0.25", dyn(0.25)), ("dynamic k=0.35", dyn(0.35)), ("dynamic k=0.50", dyn(0.50)), ("dynamic k=0.70", dyn(0.70))]
SC = [("S1 as recorded (mean R %+.2f)" % R1.mean(), boot(R1, ST, np.ones(len(R1), bool))), ("S1, Jan 2026 blind only (%+.2f)" % R1[JAN].mean(), boot(R1, ST, JAN)),
      ("true win rate 65%% at 1:1 (about %+.2f)" % (0.30 - np.mean(0.48 / ST)), wr(0.65)), ("true win rate 60%% at 1:1 (about %+.2f)" % (0.20 - np.mean(0.48 / ST)), wr(0.60))]
print("start %.2f, pass %.0f, floor %.0f, one trade a weekday with probability %.2f, margin cap %.1f lots, %d paths, horizon %d business days\n" % (START, TARGET, FLOOR, P_TRADE, CAPLOTS, N, H))
for lab, draw in SC:
    rows = [(nm,) + sim(draw, p) for nm, p in POL]; best = max(r[1] for r in rows); near = [r for r in rows if r[1] >= best - 1.0]; fast = min(near, key=lambda r: r[3])
    print("=== %s ===" % lab); print("  %-16s %7s %7s %10s %10s" % ("policy", "pass%", "breach%", "mean days", "median"))
    for r in rows: print("  %-16s %7.1f %7.1f %10.1f %10.1f%s" % (r + ("   <- best pass" if r[1] == best else "   <- fastest within 1 pt of best" if r is fast and r[1] != best else "",)))
    print()
print("=== which target ratio, same entries and stops, policy fixed 1,000 and dynamic k=0.35 (post-hoc, all 50 trades, as recorded) ===")
for lab, G in (("0.53 as logged", base), ("0.75", z75), ("1.0 = S1", Z), ("1.5", z15)):
    Rg = G.R_mine.to_numpy(float); Sg = G.risk.to_numpy(float); d = boot(Rg, Sg, np.ones(len(Rg), bool))
    for nm, p in (("fixed 1,000", fixed(1000)), ("dynamic k=0.35", dyn(0.35))):
        a = sim(d, p); print("  target/stop %-15s mean R %+.3f | %-15s pass %5.1f%% breach %5.1f%% mean days %5.1f" % (lab, Rg.mean(), nm, a[0], a[1], a[2]))
