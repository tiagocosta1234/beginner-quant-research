"""Baselines for the the trader-read imitation (written 22 Oct 2026 ~22:4x, after all 33 of the trader's days were played).
(1) Agreement: would a naive rule match the trader's calls as often as the learned read? Every naive rule trades the 08:00 candle; the side is the 08:00 candle's
    colour, the 30-minute trend at 08:00, or the move since 06:00. Agreement = same side and the trader's signal 07:58-08:02 (the learned read's "full match").
(2) P&L on GC (desk costs): each trade against its mirror (same signal candle, same stop / target distances, other side). Under "the side carries no
    information" each trade's R and mirror R are exchangeable: sign-flip test of mean R, 20,000 draws. Done for my calls, the trader's calls and the naive
    30-minute-trend rule with the v2 the trader-style bracket.
My calls' stops / targets come from state_k/my_calls_recovered.csv (recovered by sha256 from the session transcripts; the log kept only R).
Usage: python forex/apprentice/manual_read_baselines.py"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D, manual_read as K

HERE = os.path.dirname(os.path.abspath(__file__))


def idx(y, hm):
    return int(np.where(y["lis"] == K.DAY0 + pd.Timedelta(hours=int(hm[:2]), minutes=int(hm[3:])))[0][0])


def pair(y, side, sig, sd, td):
    """R of the trade and of its mirror, both with the same distances from the signal close"""
    c = y["mc"][idx(y, sig)]; L = side == "L"
    a = D.simulate(y, side, sig, c - sd if L else c + sd, c + td if L else c - td)["R"]
    b = D.simulate(y, "S" if L else "L", sig, c + sd if L else c - sd, c - td if L else c + td)["R"]
    return a, b


def signflip(r, m, n=20000, seed=7):
    r, m = np.asarray(r), np.asarray(m); obs = r.mean()
    pick = np.random.default_rng(seed).integers(0, 2, size=(n, len(r))).astype(bool)
    null = np.where(pick, r, m).mean(axis=1)
    return obs, m.mean(), (r - m).mean() / 2, float((null >= obs - 1e-12).mean())


def main():
    g = pd.read_csv(K.LOG); mine = pd.read_csv(os.path.join(HERE, "state_k", "my_calls_recovered.csv")).set_index("id")
    calls = pd.read_csv(K.CALLS).set_index("date"); d = D.raw()
    agree, P = [], {"me": ([], []), "manual": ([], []), "naive_trend30": ([], [])}
    for r in g.itertuples():
        y = K.frame_for(d, pd.Timestamp(r.date)); i0 = int(np.argmax(y["lis"] >= K.DAY0 + pd.Timedelta(hours=6))); i8 = idx(y, "08:00"); q = y.iloc[i8]
        rule = {"colour_0800": "L" if q.mc > q.mo else "S", "trend30_0800": "L" if q.mc > y["mc"][i8 - 30] else "S", "since0600_0800": "L" if q.mc > y["mo"][i0] else "S"}
        k = calls.loc[r.date]; ok_time = k["side"] != "none" and k["signal"][:2] == "08" and int(k["signal"][3:]) <= 2 or (k["side"] != "none" and k["signal"] in ("07:58", "07:59"))
        agree.append({"id": r.id, **{n: bool(ok_time and k["side"] == s) for n, s in rule.items()}})
        c = mine.loc[r.id]
        if c["side"] in ("L", "S"):
            cl = y["mc"][idx(y, c["signal"])]
            a, b = pair(y, c["side"], c["signal"], abs(cl - c["stop"]), abs(c["target"] - cl)); P["me"][0].append(a); P["me"][1].append(b)
        if k["side"] != "none":
            a, b = pair(y, k["side"], k["signal"], k["stop_d"], k["tgt_d"]); P["manual"][0].append(a); P["manual"][1].append(b)
        s = rule["trend30_0800"]; br = K.manual_bracket(y, i8, i0, s)
        td = br["D"] if br else 2.5 * q.atr
        a, b = pair(y, s, "08:00", td / 0.53, td); P["naive_trend30"][0].append(a); P["naive_trend30"][1].append(b)
    t = pd.DataFrame(agree)
    print("(1) agreement with the trader (same side, his signal 07:58-08:02), %d days:" % len(t))
    print("    learned read, full match (side + within 2 minutes of my own signal): %d" % g.agree_full.sum())
    for n in ("colour_0800", "trend30_0800", "since0600_0800"):
        print("    naive %-15s %d   (days 16-33: %d of 18; learned read %d)" % (n, t[n].sum(), t[n].iloc[15:].sum(), g.agree_full.iloc[15:].sum()))
    print("(2) P&L on GC, mean R per trade vs the mirror (same entry and distances, other side); sign-flip P = chance a random side does at least as well:")
    for n, (a, b) in P.items():
        obs, mir, exc, p = signflip(a, b)
        print("    %-14s n %2d  mean R %+.3f  mirror %+.3f  excess over a random side %+.3f  wins %d / %d  P %.3f" % (n, len(a), obs, mir, exc, sum(x > 0 for x in a), len(a), p))


if __name__ == "__main__":
    main()
