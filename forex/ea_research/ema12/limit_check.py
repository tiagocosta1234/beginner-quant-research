"""Limit entry at the chart price instead of a market order, on the trader's 30 dated gold trades (MT5 broker bid/ask, Apr-May 2025 spread ~0.28).
Chart price = the bid. Buy limit fills when the ASK trades down to it; sell limit fills when the BID trades up to it. TP/SL keep the same USD distances from the limit price. Exits on the real side of the book, stop first if both fall in one bar."""
exec(open("replay.py").read().split("out = []")[0])
def run(K, side, i, L, risk_, rew_, g):
    for j in range(i, min(i + K + 1, len(g))):
        filled = (g.al[j] <= L) if side == "L" else (g.bh[j] >= L)
        if filled:
            if side == "L": tp, sl = L + rew_, L - risk_
            else: tp, sl = L - rew_, L + risk_
            for q in range(j, min(j + 400, len(g))):
                if side == "L": htp, hsl = g.bh[q] >= tp, g.bl[q] <= sl
                else: htp, hsl = g.al[q] <= tp, g.ah[q] >= sl
                if hsl: return True, -1.0, j - i
                if htp: return True, rew_ / risk_, j - i
            return True, 0.0, j - i
    return False, 0.0, None
rows = []
for k in range(len(D)):
    day = assign[k]; g = days[day]; lo, hi = WIN[ses[k]]
    mins = [i for i in g.index[(g.hm >= lo) & (g.hm <= hi)] if abs(g.mo[i] - E[k]) <= TOL]; i = min(mins, key=lambda j: abs(g.mo[j] - E[k]))
    L = g.bo[i]                                                       # the chart (bid) price at the entry minute
    mk, ent = sim_ba(g, i, d[k], risk[k], rew[k], True)               # market entry baseline
    Rm = rew[k] / risk[k] if mk == "W" else -1.0
    rec = dict(k=k + 1, side=d[k], R_market=Rm)
    for K in (0, 3, 10):
        f, R, delay = run(K, d[k], i, L, risk[k], rew[k], g); rec[f"filled{K}"] = f; rec[f"R{K}"] = R; rec[f"delay{K}"] = delay
    rows.append(rec)
Z = pd.DataFrame(rows); pd.set_option("display.width", 200)
print("market entry (baseline, spread ~0.28): mean R %+.3f over 30 trades (24 wins)" % Z.R_market.mean())
for K in (0, 3, 10):
    f = Z[f"filled{K}"]; R = Z[f"R{K}"]
    print("limit at the chart price, valid %2d min: filled %2d/30 | mean R of filled %+.3f (wins %d of %d) | mean R per signal (unfilled = 0): %+.3f" % (K, f.sum(), R[f].mean(), (R[f] > 0).sum(), f.sum(), R.mean()))
for K in (10,):
    sub = Z[Z[f"filled{K}"]]; un = Z[~Z[f"filled{K}"]]
    print("\nwith 10 min: by side, filled share: long %d/%d, short %d/%d" % (sub[sub.side == "L"].shape[0], (Z.side == "L").sum(), sub[sub.side == "S"].shape[0], (Z.side == "S").sum()))
    print("trades that never filled: %d, and as market entries they would have returned %+.3f R each (wins %d of %d)" % (len(un), un.R_market.mean() if len(un) else float('nan'), (un.R_market > 0).sum(), len(un)))
