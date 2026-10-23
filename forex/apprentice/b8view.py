"""Compact viewer for PREREG_BIAS8 (token saver; bias8.py and its measures are unchanged).
Shows a SUBSET of what `bias8.py show` shows (still nothing at or after 08:00) and a one-line reveal.
  python b8view.py show                       compact pre-08:00 view of the open day
  python b8view.py go L|S CONF "reason"       lock the call, one-line reveal, open + show the next day"""
import os, sys, contextlib, io
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bias8 as B

H = B.H


def show():
    c = B.load_cur(); day = pd.Timestamp(c["date"])
    x = pd.read_parquet(os.path.join(B.ST, "day.parquet")); x = x[x["lis"] < day + H(8)]
    base, lv = B.pre(x, day); p = B.prev_wd(day)
    pv = x[(x["lis"] >= p + H(8)) & (x["lis"] < p + H(22))]
    print("%s S=%.2f | prev o %.1f h %.1f l %.1f c %.1f | asia o %.1f h %.1f l %.1f | 07:30 o %.1f" % (
        c["id"], lv["S"], lv["prev_open0800"], lv["prev_hi"], lv["prev_lo"], lv["prev_close"], lv["asia_open"], lv["asia_hi"], lv["asia_lo"], lv["o0730"]))
    q = B.bars(x, p + H(14), p + H(22), "60min")
    print("prev 14-21h c:", " ".join("%.1f" % (v - base) for v in q["mc"]))
    q = B.bars(x, day, day + H(7, 45), "30min")
    print("30m o/h/l/c v:")
    print("\n".join("%s %.1f %.1f %.1f %.1f %d" % (t.strftime("%H:%M"), r.mo - base, r.mh - base, r.ml - base, r.mc - base, r.v) for t, r in q.iterrows()))
    q = B.bars(x, day + H(7, 45), day + H(8), "5min")
    print("5m 07:45-59:", " | ".join("%.1f %.1f %.1f %.1f %d" % (r.mo - base, r.mh - base, r.ml - base, r.mc - base, r.v) for _, r in q.iterrows()))


def go(a):
    with contextlib.redirect_stdout(io.StringIO()): B.cmd_call(a)
    c = B.load_cur(); day = pd.Timestamp(c["date"]); x = pd.read_parquet(os.path.join(B.ST, "day.parquet"))
    base, lv = B.pre(x[x["lis"] < day + H(8)], day); S = lv["S"]; mv = B.outcome(x, day); side = a[0].upper()
    ok = (mv > 0 and side == "L") or (mv < 0 and side == "S")
    r = {T: B.sim(x, day, side, S, T, "12:00") for T in B.TGTS}
    w = x[(x["lis"] >= day + H(8)) & (x["lis"] < day + H(12))]
    print("%s %s -> %+.1fR %s | 12:00 " % (c["id"], side, mv / S, "OK" if ok else "x") + " ".join("%.1f:%s%+.2f" % (T, v[0][0], v[1] / S) for T, v in r.items())
          + " | 08-12 hi %+.1fR lo %+.1fR" % ((w["mh"].max() - w["mo"].iloc[0]) / S, (w["ml"].min() - w["mo"].iloc[0]) / S))
    c["revealed"] = True; B.json.dump(c, open(B.CUR, "w"))
    with contextlib.redirect_stdout(io.StringIO()):
        try: B.cmd_new()
        except SystemExit: print("done"); return
    show()


if __name__ == "__main__":
    a = sys.argv[1:]
    show() if a and a[0] == "show" else go(a[1:]) if a and a[0] == "go" else sys.exit(__doc__)
