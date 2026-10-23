"""Apprentice trading desk (the trader 22 Oct 2026 ~20:4x: "here's the twist, instead of the trader being me, you're the apprentice trader"; ~21:0x: "switch it up
bro you got this" = move the desk to gold futures).
Claude trades the trader's London 12 EMA setup blind on COMEX gold futures 1-minute bars with volume (Databento GC continuous front month, UTC,
futures/data/databento/futures_GC.F_1m.parquet; MGC = 1/10 GC at the same price). The desk shows only candles up to the asked minute (one minute at a
time from 07:59), with the date hidden and prices rebased (06:00 local open = 1000.0); each call is written with its PC time and a SHA-256 before `reveal`.
Days: weekdays Sep-Nov 2024 in a fixed shuffled order (seed 20261022), skipping days with a contract-roll jump (a minute-to-minute jump > $8 between 06:00 and
20:00 local) and days already seen; never the reserved data (2026 Feb-Sep, Jan 2026, Apr-May 2025, 28 Nov - 27 Dec 2023, 28 Feb - 29 Mar 2025).
Rules traded (rules card + the trader's refinements, S1 bracket): signal = a 1m candle that closes through the EMA 12 (previous close on the other side), body bigger than
its larger wick and not small, close not inside an untouched FVG remainder; entry at the next candle's open, entry minute 08:00-08:15 local, one trade a day;
target level T = an untouched FVG edge or session high / low in the trade direction; S1: D = distance entry -> T, stop 2D away, target 2D away (1:1).
Costs (futures, no bid / ask in the data): entry 1 tick (0.1) worse than the open; a stop fills 1 tick through; a target fills only if traded 1 tick through;
commission 0.15 points a round turn (about $1.50 per MGC, assumed); flat at 20:00 local. Paper only: nothing here touches an account.
Usage:
  python forex/apprentice/desk.py new                      next unseen day
  python forex/apprentice/desk.py show 07:59 [--chart]     candles up to that local minute (one minute at a time from 07:59 until the call)
  python forex/apprentice/desk.py call L|S HH:MM STOP TARGET GRADE "reason"   signal candle time (07:59-08:14); entry = next candle open
  python forex/apprentice/desk.py call none "reason"       no trade today
  python forex/apprentice/desk.py reveal                   simulate and score in R, chart to 12:00
  python forex/apprentice/desk.py log                      every day so far"""
import sys, os, json, hashlib, datetime as dt
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
STATE = os.path.join(HERE, "state"); os.makedirs(STATE, exist_ok=True)
LOG = os.path.join(HERE, "APPRENTICE_LOG_GC.csv")
OLD_LOG = os.path.join(HERE, "APPRENTICE_LOG.csv")      # day D001, played on MT5 CFD prices before the switch
SRC = os.path.join(ROOT, "futures", "data", "databento", "futures_GC.F_1m.parquet")
TICK, COMM = 0.1, 0.15


def raw():
    d = pd.read_parquet(SRC).sort_values("ts").reset_index(drop=True)
    d["lis"] = d["ts"].dt.tz_convert("Europe/London").dt.tz_localize(None)
    return d.rename(columns={"open": "mo", "high": "mh", "low": "ml", "close": "mc", "volume": "v"})


def pool():
    days = [d for d in pd.bdate_range("2024-09-02", "2024-11-29")]
    rng = np.random.default_rng(20261022)
    return [str(x.date()) for x in rng.permutation(days)]


def cur():
    p = os.path.join(STATE, "current.json")
    return json.load(open(p)) if os.path.exists(p) else None


def save(c): json.dump(c, open(os.path.join(STATE, "current.json"), "w"))


def hm(ts): return ts.strftime("%H:%M")


def frame(c):
    y = pd.read_parquet(os.path.join(STATE, "%s.parquet" % c["id"]))
    return y


def fvgs(y, upto):
    """untouched remainders of 3-candle gaps formed from 06:00 up to candle `upto`, as of that candle"""
    out = []
    for k in range(2, upto + 1):
        if y["lis"][k] < pd.Timestamp("2000-01-03 06:00"): continue      # only gaps formed from 06:00 on the (hidden) day
        if y["ml"][k] > y["mh"][k - 2]: lo, hi, kind = y["mh"][k - 2], y["ml"][k], "bull"
        elif y["mh"][k] < y["ml"][k - 2]: lo, hi, kind = y["mh"][k], y["ml"][k - 2], "bear"
        else: continue
        for j in range(k + 1, upto + 1):
            if kind == "bull": hi = min(hi, max(lo, y["ml"][j]))
            else: lo = max(lo, min(hi, y["mh"][j]))
            if hi - lo <= 1e-9: break
        if hi - lo > 1e-9: out.append((hm(y["lis"][k]), kind, round(lo, 2), round(hi, 2)))
    return out


def chart(y, i0, i1, path, title, marks=()):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    z = y.iloc[i0:i1 + 1]
    fig, (ax, av) = plt.subplots(2, 1, figsize=(16, 8), dpi=90, sharex=True, gridspec_kw={"height_ratios": [4, 1]})
    for k, r in enumerate(z.itertuples()):
        col = "#26a69a" if r.mc >= r.mo else "#ef5350"
        ax.vlines(k, r.ml, r.mh, color=col, lw=0.8)
        ax.add_patch(plt.Rectangle((k - 0.35, min(r.mo, r.mc)), 0.7, max(abs(r.mc - r.mo), 0.02), color=col))
        av.bar(k, r.v, color=col, width=0.7)
    ax.plot(range(len(z)), z["ema"].values, color="#ffb300", lw=1.2, label="EMA 12")
    ticks = [k for k, t in enumerate(z["lis"]) if t.minute % 15 == 0]
    av.set_xticks(ticks); av.set_xticklabels([hm(z["lis"].iloc[k]) for k in ticks], fontsize=8)
    for k, t in enumerate(z["lis"]):
        if t.hour == 8 and t.minute == 0: ax.axvline(k, color="#5c6bc0", ls="--", lw=1); av.axvline(k, color="#5c6bc0", ls="--", lw=1)
    for p, lab, col in marks: ax.axhline(p, color=col, ls=":", lw=1.2); ax.text(len(z) + 0.5, p, lab, color=col, fontsize=8, va="center")
    ax.set_title(title); ax.grid(alpha=0.15); ax.legend(loc="upper left"); av.set_ylabel("volume")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def seen():
    s = set()
    for f in (LOG, OLD_LOG):
        if os.path.exists(f): s |= set(pd.read_csv(f)["date"])
    return s


def cmd_new():
    c = cur()
    if c and not c.get("revealed"): sys.exit("day %s is still open: call and reveal it first" % c["id"])
    d = raw(); used = seen()
    n = len(pd.read_csv(LOG)) if os.path.exists(LOG) else 0
    for date in pool():
        if date in used: continue
        day0 = pd.Timestamp(date)
        x = d[(d["lis"] >= day0 - pd.Timedelta(hours=4)) & (d["lis"] < day0 + pd.Timedelta(hours=21))].copy().reset_index(drop=True)
        w = x[(x["lis"] >= day0 + pd.Timedelta(hours=6)) & (x["lis"] < day0 + pd.Timedelta(hours=20))]
        if len(w[w["lis"] < day0 + pd.Timedelta(hours=8, minutes=16)]) < 120: continue
        if (w["mo"] - w["mc"].shift()).abs().max() > 8: continue          # contract roll inside the day
        x["ema"] = x["mc"].ewm(span=12, adjust=False).mean()
        tr = np.maximum(x["mh"] - x["ml"], np.maximum((x["mh"] - x["mc"].shift()).abs(), (x["ml"] - x["mc"].shift()).abs()))
        x["atr"] = tr.rolling(14).mean().shift(1)
        x["vmed"] = x["v"].rolling(60).median().shift(1)
        i6 = int(np.argmax(x["lis"] >= day0 + pd.Timedelta(hours=6)))
        base = x["mo"][i6] - 1000.0
        for k in ("mo", "mh", "ml", "mc", "ema"): x[k] = (x[k] - base).round(2)
        x["lis"] = x["lis"] - (day0 - pd.Timestamp("2000-01-03"))       # hide the date: every day becomes 3 Jan 2000
        did = "F%03d" % (n + 1)
        x[["lis", "mo", "mh", "ml", "mc", "v", "ema", "atr", "vmed"]].to_parquet(os.path.join(STATE, "%s.parquet" % did))
        save({"id": did, "date": date, "i6": i6})
        print("new day %s (gold futures, date hidden, 06:00 local open rebased to 1000.0). Next: show 07:59 --chart" % did); return
    sys.exit("pool used up")


def cmd_show(until, want_chart):
    c = cur()
    if not c or c.get("revealed"): sys.exit("no open day: run new")
    hh, mm = map(int, until.split(":"))
    if (hh, mm) > (8, 14) and not c.get("call"): sys.exit("the last signal candle is 08:14: call first")
    if c.get("shown_until") and not c.get("call") and (hh, mm) >= (7, 59):
        ph, pm = map(int, c["shown_until"].split(":"))
        nxt = max(ph * 60 + pm, 7 * 60 + 58) + 1
        if hh * 60 + mm > nxt: sys.exit("one minute at a time from 07:59: next is %02d:%02d" % divmod(nxt, 60))
    y = frame(c); day0 = pd.Timestamp("2000-01-03")
    i6 = int(np.argmax(y["lis"] >= day0 + pd.Timedelta(hours=6)))
    i1 = int(np.where(y["lis"] <= day0 + pd.Timedelta(hours=hh, minutes=mm))[0].max())
    c["shown_until"] = until; save(c)
    if want_chart:
        png = os.path.join(STATE, "%s_%s.png" % (c["id"], until.replace(":", "")))
        chart(y, max(i6, i1 - 150), i1, png, "%s up to %s local (gold futures, rebased)" % (c["id"], until)); print("chart: %s" % png)
    r0 = max(0, i1 - (14 if want_chart else 1))
    print("time   open     high     low      close    EMA12    ATR   body/ATR close-EMA  vol (60m median)")
    for k in range(r0, i1 + 1):
        r = y.iloc[k]
        print("%s  %7.2f  %7.2f  %7.2f  %7.2f  %7.2f  %4.2f  %5.2f  %+6.2f   %5.0f (%.0f)" % (hm(r.lis), r.mo, r.mh, r.ml, r.mc, r.ema, r.atr, abs(r.mc - r.mo) / r.atr, r.mc - r.ema, r.v, r.vmed))
    g = fvgs(y, i1)
    print("06:00-%s high %.2f low %.2f | untouched FVG remainders: %s" % (until, y["mh"][i6:i1 + 1].max(), y["ml"][i6:i1 + 1].min(), "; ".join("%s %s %.2f-%.2f" % t for t in g[-7:]) or "none"))


SHADOW = os.path.join(HERE, "APPRENTICE_SHADOW_GC.csv")   # card-valid setups that were skipped, scored after the reveal


def is_cross(y, i):
    a, b = y["mc"][i - 1] - y["ema"][i - 1], y["mc"][i] - y["ema"][i]
    return "L" if (a <= 0 < b) else "S" if (a >= 0 > b) else None


def setup_at(y, i, i6):
    """card checks, the 4-point rubric and the S1 suggestion for the cross candle i (uses candles up to i only)"""
    side = is_cross(y, i)
    if side is None: return None
    r = y.iloc[i]; L = side == "L"; atr = r.atr
    body = abs(r.mc - r.mo); wick = max(r.mh - max(r.mo, r.mc), min(r.mo, r.mc) - r.ml)
    before = fvgs(y, i - 1)                                   # untouched remainders before the signal candle
    inside = [g for g in before if g[2] < r.mc < g[3]]
    card = {"colour": bool((r.mc > r.mo) if L else (r.mc < r.mo)), "body>wick": bool(body > wick), "not small": bool(body >= 0.6 * atr), "close outside gaps": not inside}
    k30 = max(i6, i - 30)
    crosses = sum(1 for j in range(max(i6 + 1, i - 10), i) if is_cross(y, j))
    rub = {"trend": bool((y["ema"][i] - y["ema"][k30]) * (1 if L else -1) > 0), "body>=1ATR": bool(body >= atr), "volume>=median": bool(r.v >= r.vmed), "not chop": crosses <= 2}
    n = sum(rub.values()); grade = "A" if n == 4 else "B" if n == 3 else "C"
    after = fvgs(y, i)                                        # levels as they stand after the signal candle
    hi, lo = y["mh"][i6:i + 1].max(), y["ml"][i6:i + 1].min()
    if L: levels = [(g[2], "%s bear gap" % g[0]) for g in after if g[1] == "bear" and g[2] > r.mc] + ([(hi, "session high")] if hi > r.mc else [])
    else: levels = [(g[3], "%s bull gap" % g[0]) for g in after if g[1] == "bull" and g[3] < r.mc] + ([(lo, "session low")] if lo < r.mc else [])
    levels = sorted([l for l in levels if abs(l[0] - r.mc) >= atr], key=lambda l: abs(l[0] - r.mc))
    s1 = None
    if levels:
        T, what = levels[0]; Dd = abs(T - r.mc)
        s1 = {"T": round(T, 2), "what": what, "D": round(Dd, 2), "stop": round(r.mc - 2 * Dd if L else r.mc + 2 * Dd, 2), "target": round(r.mc + 2 * Dd if L else r.mc - 2 * Dd, 2)}
    return {"time": hm(r.lis), "side": side, "card": card, "valid": bool(all(card.values()) and s1 is not None), "inside": inside, "rubric": rub, "crosses10": crosses,
            "grade": grade, "s1": s1, "body_atr": round(body / atr, 2), "vol": int(r.v), "vmed": int(r.vmed) if r.vmed == r.vmed else 0}


def simulate(y, side, sig, stop, tgt):
    day0 = pd.Timestamp("2000-01-03"); sh, sm = map(int, sig.split(":"))
    ke = int(np.where(y["lis"] == day0 + pd.Timedelta(hours=sh, minutes=sm))[0][0]) + 1
    L = side == "L"; entry = y["mo"][ke] + (TICK if L else -TICK)
    risk = (entry - stop) if L else (stop - entry)
    if risk <= 0 or (tgt - entry if L else entry - tgt) <= 0: return None
    res, ex, et = "flat 20:00", None, None
    for k in range(ke, len(y)):
        if y["lis"][k] >= day0 + pd.Timedelta(hours=20): ex, et = y["mo"][k], hm(y["lis"][k]); break
        if (L and y["ml"][k] <= stop) or (not L and y["mh"][k] >= stop): res, ex, et = "stop", stop - TICK if L else stop + TICK, hm(y["lis"][k]); break
        if (L and y["mh"][k] >= tgt + TICK) or (not L and y["ml"][k] <= tgt - TICK): res, ex, et = "target", tgt, hm(y["lis"][k]); break
    if ex is None: ex, et = y["mc"].iloc[-1], hm(y["lis"].iloc[-1])
    return {"entry": round(entry, 2), "exit": round(ex, 2), "exit_time": et, "result": res, "R": round((((ex - entry) if L else (entry - ex)) - COMM) / risk, 3)}


def cmd_next(want_chart):
    """advance minute by minute (blind) to the next EMA-cross candle in 07:59-08:14 that passes the card and has an S1 level; list the crosses passed over"""
    c = cur()
    if not c or c.get("revealed") or c.get("call"): sys.exit("no open, uncalled day")
    y = frame(c); day0 = pd.Timestamp("2000-01-03")
    i6 = int(np.argmax(y["lis"] >= day0 + pd.Timedelta(hours=6)))
    start = 7 * 60 + 59
    if c.get("shown_until"):
        ph, pm = map(int, c["shown_until"].split(":")); start = max(start, ph * 60 + pm + 1)
        if c.get("pending"):                                  # the setup shown last time was passed over: shadow it
            c.setdefault("skipped", []).append(c.pop("pending"))
    notes = []
    for m in range(start, 8 * 60 + 15):
        i = int(np.where(y["lis"] == day0 + pd.Timedelta(minutes=m))[0][0])
        s = setup_at(y, i, i6)
        c["shown_until"] = "%02d:%02d" % divmod(m, 60)
        if s is None: continue
        if not s["valid"]:
            why = [k for k, v in s["card"].items() if not v] + ([] if s["s1"] else ["no S1 level >= 1 ATR"])
            notes.append("%s %s cross fails: %s" % (s["time"], s["side"], ", ".join(why))); continue
        c["pending"] = s; save(c)
        for n in notes: print("  passed over: " + n)
        r0 = max(0, i - 11)
        print("time   open     high     low      close    EMA12    ATR   body/ATR close-EMA  vol (60m median)")
        for k in range(r0, i + 1):
            r = y.iloc[k]
            print("%s  %7.2f  %7.2f  %7.2f  %7.2f  %7.2f  %4.2f  %5.2f  %+6.2f   %5.0f (%.0f)" % (hm(r.lis), r.mo, r.mh, r.ml, r.mc, r.ema, r.atr, abs(r.mc - r.mo) / r.atr, r.mc - r.ema, r.v, r.vmed))
        ch = {mins: round(y["mc"][i] - y["mc"][max(0, i - mins)], 2) for mins in (30, 60, 120)}
        print("CROSS %s %s | rubric %s -> grade %s | S1: T %.2f (%s), D %.2f, stop %.2f, target %.2f" % (
            s["time"], "LONG" if s["side"] == "L" else "SHORT", ", ".join("%s %s" % (k, "Y" if v else "n") for k, v in s["rubric"].items()), s["grade"],
            s["s1"]["T"], s["s1"]["what"], s["s1"]["D"], s["s1"]["stop"], s["s1"]["target"]))
        print("context: close change 30/60/120 min %+.2f / %+.2f / %+.2f; session %.2f-%.2f; crosses in the prior 10 min %d; untouched gaps now: %s" % (
            ch[30], ch[60], ch[120], y["ml"][i6:i + 1].min(), y["mh"][i6:i + 1].max(), s["crosses10"], "; ".join("%s %s %.2f-%.2f" % g for g in fvgs(y, i)[-6:]) or "none"))
        if want_chart:
            png = os.path.join(STATE, "%s_%s.png" % (c["id"], s["time"].replace(":", ""))); chart(y, max(i6, i - 150), i, png, "%s up to %s" % (c["id"], s["time"])); print("chart: %s" % png)
        return
    c.pop("pending", None); save(c)
    for n in notes: print("  passed over: " + n)
    print("no valid setup in the window (07:59-08:14 shown). Next: call none")


def cmd_call(args):
    c = cur()
    if not c or c.get("revealed"): sys.exit("no open day")
    if c.get("call"): sys.exit("already called")
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if args[0].lower() == "none":
        call = {"side": "none", "reason": " ".join(args[1:]), "pc_time": now, "shown_until": c.get("shown_until")}
    else:
        side, sig, stop, tgt, grade = args[0].upper(), args[1], float(args[2]), float(args[3]), args[4].upper()
        sh, sm = map(int, sig.split(":"))
        if not ((7, 59) <= (sh, sm) <= (8, 14)): sys.exit("signal candle must be 07:59-08:14")
        if tuple(map(int, c["shown_until"].split(":"))) != (sh, sm): sys.exit("call on the candle just shown (%s), not %s" % (c["shown_until"], sig))
        call = {"side": side, "signal": sig, "stop": stop, "target": tgt, "grade": grade, "reason": " ".join(args[5:]), "pc_time": now}
    call["sha256"] = hashlib.sha256(json.dumps(call, sort_keys=True).encode()).hexdigest()
    c["call"] = call; save(c)
    print("call locked %s: %s" % (call["sha256"][:16], json.dumps(call)))


def cmd_reveal():
    c = cur()
    if not c or not c.get("call") or c.get("revealed"): sys.exit("nothing to reveal")
    call = c["call"]; y = frame(c); day0 = pd.Timestamp("2000-01-03")
    row = {"day_id": c["id"], "date": c["date"], "side": call["side"], "grade": call.get("grade", ""), "reason": call["reason"], "pc_time": call["pc_time"], "sha256": call["sha256"]}
    i6 = int(np.argmax(y["lis"] >= day0 + pd.Timedelta(hours=6))); i12 = int(np.where(y["lis"] <= day0 + pd.Timedelta(hours=12))[0].max())
    marks = []
    if call["side"] == "none":
        row.update(entry="", stop="", target="", exit="", exit_time="", R=0.0, result="no trade")
    else:
        sim = simulate(y, call["side"], call["signal"], call["stop"], call["target"])
        if sim is None: sys.exit("stop / target on the wrong side of the entry")
        row.update(entry=sim["entry"], stop=call["stop"], target=call["target"], exit=sim["exit"], exit_time=sim["exit_time"], R=sim["R"], result=sim["result"])
        marks = [(sim["entry"], "entry", "#90a4ae"), (call["stop"], "stop", "#ef5350"), (call["target"], "target", "#26a69a")]
    skipped = c.get("skipped", []) + ([c["pending"]] if c.get("pending") and call["side"] == "none" else [])
    for s in skipped:                                         # shadow: the S1 suggestion of every card-valid setup passed over
        sim = simulate(y, s["side"], s["time"], s["s1"]["stop"], s["s1"]["target"])
        if sim is None: continue
        pd.DataFrame([{"day_id": c["id"], "date": c["date"], "time": s["time"], "side": s["side"], "grade": s["grade"], **sim}]).to_csv(SHADOW, mode="a", header=not os.path.exists(SHADOW), index=False)
        print("  shadow %s %s (%s): %s %+.3f R" % (s["time"], s["side"], s["grade"], sim["result"], sim["R"]))
    png = os.path.join(STATE, "%s_reveal.png" % c["id"])
    chart(y, i6, i12, png, "%s revealed (to 12:00 local)" % c["id"], marks)
    pd.DataFrame([row]).to_csv(LOG, mode="a", header=not os.path.exists(LOG), index=False)
    c["revealed"] = True; save(c)
    print("%s (%s): %s -> %s at %s, R %+.3f | chart: %s" % (c["id"], c["date"], call["side"], row["result"], row["exit_time"], row["R"], png))


def cmd_log():
    for f, lab in ((OLD_LOG, "MT5 CFD (before the switch)"), (LOG, "gold futures")):
        if not os.path.exists(f): continue
        g = pd.read_csv(f); t = g[g["side"] != "none"]
        print("== %s ==" % lab)
        print(g[["day_id", "date", "side", "grade", "entry", "stop", "target", "result", "R"]].to_string(index=False))
        if len(t): print("trades %d of %d days, wins %d, mean R %+.3f, sum R %+.2f; by grade: %s" % (len(t), len(g), (t["R"] > 0).sum(), t["R"].mean(), t["R"].sum(),
                         ", ".join("%s %+.2f (n %d)" % (k, v["R"].mean(), len(v)) for k, v in t.groupby("grade"))))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"new": lambda: cmd_new(), "show": lambda: cmd_show(a[1], "--chart" in a), "next": lambda: cmd_next("--chart" in a), "call": lambda: cmd_call(a[1:]),
     "reveal": lambda: cmd_reveal(), "log": lambda: cmd_log()}[a[0]]()
