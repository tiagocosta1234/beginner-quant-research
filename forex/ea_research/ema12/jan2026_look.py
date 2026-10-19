"""January 2026 descriptive look at the two failed mechanical 12 EMA rules (PREREG_JAN2026.md). python jan2026_look.py --dry-run | --run
Only rows with time < 2026-02-01 are ever read from the MT5 broker files (read-time filter): February onward stays sealed."""
import sys, numpy as np, pandas as pd
CUT = int(pd.Timestamp("2026-02-01").timestamp())   # MT5 'time' is the server clock stored as epoch seconds
_read = pd.read_parquet
pd.read_parquet = lambda p, *a, **k: _read(p, *a, filters=[("t", "<", CUT)], **k)
import ema12_test as E, manualrule_test as K
JAN0, JAN1 = pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-31")
D = {m: K.prep(m, "2026-01-31") for m in E.MARKETS}; A = {m: K.arrays(D[m]) for m in E.MARKETS}
for m in E.MARKETS: assert D[m].dt.max() < pd.Timestamp("2026-02-01") + pd.Timedelta(seconds=1), "data past January was read"
mode = sys.argv[1] if len(sys.argv) > 1 else "--dry-run"
jan = lambda x: x[(x.day >= JAN0) & (x.day <= JAN1)]
if mode == "--dry-run":
    for m in E.MARKETS:
        print(m, "rows", len(D[m]), "last bar", D[m].dt.max())
        for s in ("London", "NY"):
            days = sorted({dy for dy, hm in zip(D[m].day, D[m].hm) if JAN0 <= pd.Timestamp(dy) <= JAN1 and pd.Timestamp(dy).weekday() < 5 and E.open_min(dy, s) <= hm <= E.open_min(dy, s) + 14})
            sg_e = [z for z in E.signals(D[m], s, "ATR25") if JAN0 <= pd.Timestamp(z["day"]) <= JAN1]
            sg_k = [z for z in K.signals(D[m], A[m], s, "K1") if JAN0 <= pd.Timestamp(z["day"]) <= JAN1]
            print("  %-6s weekday sessions with bars in the first 15 min: %d | EMA12 ATR25 F0 signals: %d | MANUALRULE K1 trades: %d" % (s, len(days), len(sg_e), len(sg_k)))
elif mode == "--run":
    prev_e = pd.read_csv("EMA12_TRIALS.csv"); prev_k = pd.read_csv("MANUALRULE_TRIALS.csv"); rows = []; cache = {}
    for (m, s, st, r, f) in E.TRIALS:
        if (m, s, st, f) not in cache: cache[(m, s, st, f)] = E.signals(D[m], s, st, filt=f)
        x = jan(E.simulate(D[m], cache[(m, s, st, f)], r)); a = E.stats(x)
        p = prev_e[(prev_e.market == m) & (prev_e.sess == s) & (prev_e.stop == st) & (prev_e.r == r) & (prev_e.filt == f)].iloc[0]
        rows.append(dict(rule="EMA12", market=m, sess=s, variant="%s r%s %s" % (st, r, f), n=a["n"], wins=int((x.R > 0).sum()), meanR=a["meanR"], t=a["t"], dev_R=p.dev_R, val_R=p.val_R))
    for (m, s, v) in K.TRIALS:
        x = jan(K.simulate(D[m], K.signals(D[m], A[m], s, v))); a = E.stats(x)
        p = prev_k[(prev_k.market == m) & (prev_k.sess == s) & (prev_k["var"] == v)].iloc[0]
        rows.append(dict(rule="MANUALRULE", market=m, sess=s, variant=v, n=a["n"], wins=int((x.R > 0).sum()), meanR=a["meanR"], t=a["t"], dev_R=p.dev_R, val_R=p.val_R))
    T = pd.DataFrame(rows); pd.set_option("display.width", 250); print(T.round(3).to_string(index=False)); T.to_csv("JAN2026_TRIALS.csv", index=False)
    print("\n--- pooled (descriptive; n per trial is about 20, so one trial's mean R has a standard error near 0.18)")
    for lab, g in (("MANUALRULE gold", T[(T.rule == "MANUALRULE") & (T.market == "XAUUSD")]), ("MANUALRULE gold K1 London+NY", T[(T.rule == "MANUALRULE") & (T.market == "XAUUSD") & (T.variant == "K1")]),
                   ("EMA12 gold", T[(T.rule == "EMA12") & (T.market == "XAUUSD")]), ("MANUALRULE Nasdaq", T[(T.rule == "MANUALRULE") & (T.market == "NSDQ")]), ("EMA12 Nasdaq", T[(T.rule == "EMA12") & (T.market == "NSDQ")]), ("all 44 trials", T)):
        print("%-28s trials %2d | mean of trial means: Jan 2026 %+.3f | DEV 2022-24 %+.3f | VAL 2025 %+.3f | trials with Jan mean R > 0: %d" % (lab, len(g), g.meanR.mean(), g.dev_R.mean(), g.val_R.mean(), int((g.meanR > 0).sum())))
    for s in ("London", "NY"):
        g = T[(T.rule == "MANUALRULE") & (T.market == "XAUUSD") & (T.sess == s)]
        print("MANUALRULE gold %-6s K1/K2/K3 Jan: n %s, wins %s, mean R %s" % (s, g.n.tolist(), g.wins.tolist(), g.meanR.round(3).tolist()))
