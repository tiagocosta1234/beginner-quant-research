"""Exploratory breakdown of the finished PREREG_READ_TEST2 (read v9; written 23 Oct 2026 ~08:5x, after the one scored look). Not evidence: 47 trades split many ways.
Per trade: R and mirror R (same entry, same distances, other side) on GC with desk costs, grouped by setup family (from the locked reason text),
signal time, side and pool; also the no-trade days' naive 08:00 trend trade, to see what passing cost or saved.
Usage: python forex/apprentice/read_test2_breakdown.py"""
import os, sys, re
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desk as D, manual_read as K, manual_read_baselines as B
from read_test2 import bracket

HERE = os.path.dirname(os.path.abspath(__file__))
FAMILIES = [("resumption / flag", r"resumption|flag"), ("break of a high / low / base", r"break|breakout|new session low"),
            ("failed bounce / rollover", r"failed|rollover|rolls over|capped"), ("reclaim / engulfing", r"reclaim|engulfing"),
            ("sweep and reversal", r"sweep")]


def main():
    t = pd.read_csv(os.path.join(HERE, "READ_TEST2_CALLS.csv")); d = D.raw(); rows, skip = [], []
    for r in t.itertuples():
        y = K.frame_for(d, pd.Timestamp(r.date))
        if r.side not in ("L", "S"):
            i0 = int(np.argmax(y["lis"] >= K.DAY0 + pd.Timedelta(hours=6))); i8 = B.idx(y, "08:00")
            s = "L" if y["mc"][i8] > y["mc"][i8 - 30] else "S"; st, tg, _ = bracket(y, i8, i0, s); c8 = y["mc"][i8]
            try: skip.append(B.pair(y, s, "08:00", abs(c8 - st), abs(tg - c8))[0])
            except TypeError: pass
            continue
        i = B.idx(y, r.signal); cl = y["mc"][i]
        a, b = B.pair(y, r.side, r.signal, abs(cl - r.stop), abs(r.target - cl))
        rows.append({"id": r.id, "pool": r.pool, "side": r.side, "signal": r.signal, "R": a, "mirror": b, "reason": r.reason, "early": r.signal <= "08:05"})
    g = pd.DataFrame(rows); g["edge"] = (g.R - g.mirror) / 2
    line = lambda lab, m: "%-32s n %2d  mean R %+.3f  excess %+.3f  wins %d/%d" % (lab, m.sum(), g.R[m].mean(), g.edge[m].mean(), (g.R[m] > 0).sum(), m.sum())
    out = ["all: n %d, mean R %+.3f, excess %+.3f, wins %d" % (len(g), g.R.mean(), g.edge.mean(), (g.R > 0).sum())]
    for name, pat in FAMILIES:
        m = g.reason.str.contains(pat, flags=re.I, regex=True)
        if m.sum(): out.append(line(name, m))
    for lab, m in (("signal 08:02-08:05", g.early), ("signal 08:06 or later", ~g.early), ("long", g.side == "L"), ("short", g.side == "S"),
                   ("pool A (2022)", g.pool == "A"), ("pool B (Jan-May 2024)", g.pool == "B")):
        out.append(line(lab, m))
    out.append("no-trade days (%d): the naive 08:00 trend trade would have made mean R %+.3f (wins %d/%d)" % (len(skip), np.mean(skip), sum(x > 0 for x in skip), len(skip)))
    txt = "\n".join(out); print(txt)
    open(os.path.join(HERE, "READ_TEST2_BREAKDOWN_OUTPUT.txt"), "w").write(txt + "\n")
    g.to_csv(os.path.join(HERE, "READ_TEST2_TRADES.csv"), index=False)


if __name__ == "__main__":
    main()
