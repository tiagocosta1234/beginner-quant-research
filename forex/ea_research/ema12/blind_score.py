"""Scores the blind-replay log (PREREG_BLIND2026.md) on MT5 broker bid/ask: his side vs the mirror trade vs a random side, same minute and same stop/target distances.
python blind_score.py LOG.csv        LOG.csv columns: date, ses (London/NY), side (L/S; empty = no trade), hhmm (chart clock = local, last candle visible when he clicked), entry, stop, target, flag (1 = recognised the day), pre (1 = logged before the result)
python blind_score.py --validate     rebuilds the 30 trades of 14 Apr-12 May 2025 from replay_mt5.csv and must reproduce direction_skill.csv"""
import sys, numpy as np, pandas as pd
def srv_off(date):
    """Minutes from the local clock to the MT5 broker server clock on that date. Fix 26 Oct 2026: the MT5 broker server is New York time + 7 h (it follows
    US daylight saving), so in the US/EU DST gaps (mid-late March, late Oct - early Nov) it is local + 3 h, not + 2 h (v1 used + 2 h always)."""
    t = pd.Timestamp(str(date) + " 12:00")
    ny = t.tz_localize("Europe/London").tz_convert("America/New_York").utcoffset().total_seconds() / 60
    lis = t.tz_localize("Europe/London").utcoffset().total_seconds() / 60
    return int(ny + 7 * 60 - lis)
DATA = "D:/finance/beginner-quant-research/forex/data_mt5/XAUUSD_M1_rates.parquet"; TOL = 1.5; CLOSE_HM = {"London": 19 * 60, "NY": 23 * 60 + 30}   # server clock: 17:00 local / end of day
def load_days(d0, d1):
    lo = int((pd.Timestamp(d0) - pd.Timedelta(days=1)).timestamp()); hi = int((pd.Timestamp(d1) + pd.Timedelta(days=2)).timestamp())
    r = pd.read_parquet(DATA, filters=[("t", ">=", lo), ("t", "<", hi)]).sort_values("t").reset_index(drop=True)
    r["dt"] = pd.to_datetime(r.t, unit="s"); r["day"] = r.dt.dt.date; r["hm"] = r.dt.dt.hour * 60 + r.dt.dt.minute
    z = r.sp <= 0; med = r[~z].sp.median()
    for b, a in (("bo", "ao"), ("bh", "ah"), ("bl", "al"), ("bc", "ac")): r.loc[z, a] = r.loc[z, b] + med
    r["mo"] = (r.bo + r.ao) / 2
    return {k: g.reset_index(drop=True) for k, g in r.groupby("day")}
def run(g, i0, side, risk_, rew_, close_hm):
    """R of one trade: entry at the real quote of minute i0 (long: ask open, short: bid open), exits on the real side of the book, same-minute stop+target = loss, still open at close_hm = marked on the exit side."""
    if side == "L":
        ent = g.ao[i0]; tp, sl = ent + rew_, ent - risk_
        for j in range(i0, len(g)):
            if g.bl[j] <= sl: return -1.0
            if g.bh[j] >= tp: return rew_ / risk_
            if g.hm[j] >= close_hm: return (g.bc[j] - ent) / risk_
        return (g.bc.iloc[-1] - ent) / risk_
    ent = g.bo[i0]; tp, sl = ent - rew_, ent + risk_
    for j in range(i0, len(g)):
        if g.ah[j] >= sl: return -1.0
        if g.al[j] <= tp: return rew_ / risk_
        if g.hm[j] >= close_hm: return (ent - g.ac[j]) / risk_
    return (ent - g.ac.iloc[-1]) / risk_
def score(log, days, shift=0, lag=0):
    out = []
    for _, r in log.iterrows():
        g = days[pd.Timestamp(r.date).date()]; hm = int(r.hhmm[:2]) * 60 + int(r.hhmm[3:]) + srv_off(r.date) + lag     # local -> MT5 broker server clock (srv_off); lag 1 = the log holds the signal candle, the entry is the next candle
        i0 = g.index[g.hm >= hm][0]; note = ""
        if pd.notna(r.get("entry")) and abs(g.mo[i0] - r.entry) > TOL:
            near = [i for i in range(max(i0 - 5, 0), min(i0 + 6, len(g)))]; b = min(near, key=lambda i: abs(g.mo[i] - r.entry))
            note = "retimed %+d min (price off by %.2f)" % (b - i0, g.mo[i0] - r.entry) if abs(g.mo[b] - r.entry) <= TOL else "PRICE MISMATCH %.2f" % (g.mo[i0] - r.entry)
            if abs(g.mo[b] - r.entry) <= TOL: i0 = b
        i0 = min(max(i0 + shift, 0), len(g) - 1)
        risk_ = r.risk if "risk" in r and pd.notna(r.risk) else abs(r.entry - r.stop); rew_ = r.rew if "rew" in r and pd.notna(r.rew) else abs(r.target - r.entry)
        ch = CLOSE_HM[r.ses] + srv_off(r.date) - 120; RL, RS = run(g, i0, "L", risk_, rew_, ch), run(g, i0, "S", risk_, rew_, ch)
        out.append(dict(date=r.date, ses=r.ses, side=r.side, flag=int(r.get("flag", 0) or 0), pre=int(r.get("pre", 1)), risk=risk_, R_L=RL, R_S=RS, R_mine=RL if r.side == "L" else RS, R_mirror=RS if r.side == "L" else RL, note=note))
    return pd.DataFrame(out)
def summarize(Z, label, extra_cost=0.0):
    n = len(Z)
    if n < 2: return print("%-34s n %d" % (label, n))
    adj = (extra_cost / Z.risk).to_numpy(); L, S = Z.R_L.to_numpy() - adj, Z.R_S.to_numpy() - adj; mine = np.where(Z.side == "L", L, S); mirror = np.where(Z.side == "L", S, L)
    rng = np.random.default_rng(11); null = np.where(rng.random((200000, n)) < 0.5, L, S).mean(axis=1)
    boot = np.sort([rng.choice(mine, n).mean() for _ in range(4000)])
    print("%-34s n %3d | his side: wins %d mean R %+.3f (t %.2f, 95%% CI %+.2f..%+.2f) | mirror %+.3f | random side %+.3f | excess %+.3f | P(random >= his) %.4f" % (
        label, n, (mine > 0).sum(), mine.mean(), mine.mean() / (mine.std(ddof=1) / np.sqrt(n)), boot[100], boot[3900], mirror.mean(), null.mean(), mine.mean() - null.mean(), (null >= mine.mean()).mean()))
if __name__ == "__main__":
    if "--validate" in sys.argv:
        O = pd.read_csv("replay_mt5.csv"); h = O.hm - 120
        log = pd.DataFrame(dict(date=O.day, ses=O.ses, side=O.side, hhmm=["%02d:%02d" % (x // 60, x % 60) for x in h], entry=np.nan, risk=O.risk, rew=O.rew, flag=0))
        Z = score(log, load_days(O.day.min(), O.day.max())); Q = pd.read_csv("direction_skill.csv")
        print("validation vs direction_skill.csv: R_mine max abs diff %.2e | R_mirror %.2e | mean R his %+.3f mirror %+.3f" % (np.abs(Z.R_mine.to_numpy() - Q.R_mine.to_numpy()).max(), np.abs(Z.R_mirror.to_numpy() - Q.R_mirror.to_numpy()).max(), Z.R_mine.mean(), Z.R_mirror.mean()))
        summarize(Z, "30 trades Apr-May 2025 (all)"); [summarize(Z[Z.ses == s], "  " + s) for s in ("London", "NY")]
    else:
        log = pd.read_csv(sys.argv[1], dtype={"hhmm": str}); print("rows %d, no-trade days %d" % (len(log), (~log.side.isin(["L", "S"])).sum())); log = log[log.side.isin(["L", "S"])]
        days = load_days(log.date.min(), log.date.max()); Z = score(log, days, lag=1)
        print(Z[Z.note != ""][["date", "ses", "note"]].to_string(index=False) if (Z.note != "").any() else "all entry minutes match the logged prices")
        P = Z[(Z.flag == 0) & (Z.pre == 1)]; L_ = P[P.ses == "London"]; print("excluded from the primary: %d flagged, %d logged after the result" % ((Z.flag == 1).sum(), (Z.pre == 0).sum()))
        summarize(L_, "PRIMARY London, flagged days out"); summarize(Z[Z.ses == "London"], "London, all days"); summarize(P[P.ses == "NY"], "NY (secondary), flagged out")
        summarize(L_, "London, extra cost 0.30 USD", 0.30)
        keep = log[(log.ses == "London") & (log.get("flag", 0) == 0) & (log.get("pre", 1) == 1)]
        for s_ in (-1, 1): summarize(score(keep, days, s_, lag=1), "London, entry shifted %+d min" % s_)
