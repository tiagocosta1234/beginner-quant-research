"""Exploratory breakdown of the finished PREREG_READ_TEST (written 23 Oct 2026 ~00:5x, after the one scored look). Not evidence: 93 trades split many ways.
Per trade: R and mirror R (same entry, same distances, other side) on GC with desk costs, grouped by setup family (from the locked reason text),
signal time, side against the 30-minute trend, and pool.
Usage: python forex/apprentice/read_test_breakdown.py"""
import os, sys, re
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D, manual_read as K, manual_read_baselines as B

HERE = os.path.dirname(os.path.abspath(__file__))
FAMILIES = [("pin", r"\bpin\b"), ("held level", r"held|double bottom|triple bottom|base"), ("sweep", r"swe(e)?pt|sweep"),
            ("stall under gap / end of bounce", r"stall|end of the bounce|tagged|double top"), ("EMA-retest rejection", r"EMA-retest|hammer|wick into the EMA|wick under the EMA"),
            ("first decisive push", r"first decisive push|decisive push|opening push|breaks the session|break"), ("resumption", r"resumption|resum"),
            ("false break / undone", r"false break|undid|undone")]


def main():
    t = pd.read_csv(os.path.join(HERE, "READ_TEST_CALLS.csv")); d = D.raw(); rows = []
    for r in t.itertuples():
        if r.side not in ("L", "S"): continue
        y = K.frame_for(d, pd.Timestamp(r.date)); i = B.idx(y, r.signal); cl = y["mc"][i]
        a, b = B.pair(y, r.side, r.signal, abs(cl - r.stop), abs(r.target - cl))
        t30 = y["mc"][i] - y["mc"][i - 30]
        rows.append({"id": r.id, "pool": r.pool, "side": r.side, "signal": r.signal, "R": a, "mirror": b, "reason": r.reason,
                     "with_trend30": (t30 > 0) == (r.side == "L"), "early": r.signal <= "08:02"})
    g = pd.DataFrame(rows); g["edge"] = (g.R - g.mirror) / 2
    out = ["all: n %d, mean R %+.3f, excess %+.3f, wins %d" % (len(g), g.R.mean(), g.edge.mean(), (g.R > 0).sum())]
    for name, pat in FAMILIES:
        m = g.reason.str.contains(pat, flags=re.I, regex=True)
        if m.sum(): out.append("%-32s n %2d  mean R %+.3f  excess %+.3f  wins %d/%d" % (name, m.sum(), g.R[m].mean(), g.edge[m].mean(), (g.R[m] > 0).sum(), m.sum()))
    for lab, m in (("signal 07:59-08:02", g.early), ("signal 08:03 or later", ~g.early), ("with the 30-min trend", g.with_trend30), ("against the 30-min trend", ~g.with_trend30),
                   ("long", g.side == "L"), ("short", g.side == "S")):
        out.append("%-32s n %2d  mean R %+.3f  excess %+.3f  wins %d/%d" % (lab, m.sum(), g.R[m].mean(), g.edge[m].mean(), (g.R[m] > 0).sum(), m.sum()))
    txt = "\n".join(out); print(txt)
    open(os.path.join(HERE, "READ_TEST_BREAKDOWN_OUTPUT.txt"), "w").write(txt + "\n")
    g.to_csv(os.path.join(HERE, "READ_TEST_TRADES.csv"), index=False)


if __name__ == "__main__":
    main()
