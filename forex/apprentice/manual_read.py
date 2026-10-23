"""Learning the trader's read (the trader 22 Oct 2026 ~21:5x: "you read has to learn through experience on how to become my read").
Claude plays the trader's own London days blind on the futures desk (desk.py frame: Databento GC 1-minute, date hidden, prices rebased), makes a call, then sees
the trader's real call for that day and both are scored on the same data. The target is AGREEMENT with the trader (same decision, same side, signal candle within 2 minutes),
not P&L; every disagreement is written into MANUAL_READ.md, and agreement is tracked block by block to see whether the read converges.
the trader's calls: BLIND_LOG_JAN2026.csv (London, Jan 2026, signal candle = 'hhmm', with entry / stop / target; 20 Jan = no trade) and replay_mt5.csv (London rows of
14 Apr - 12 May 2025; 'hm' = entry minute on the server clock, local = server - 2 h, signal = entry - 1 minute; 'risk' / 'rew' = stop / target distances).
Days left out because their charts and outcomes are described in MANUAL_WHY_ENTRIES.md, which Claude read before playing: 2025-04-30, 2025-05-01, 2025-05-05,
2026-01-09, 2026-01-28. Claude also saw the January list of sides / times before playing (not the charts): the dates stay hidden on the desk.
the trader-style bracket suggestion: T = the nearest structural level in the trade direction at least 0.8 ATR away (untouched opposite 1-minute gap near edge,
equal highs / lows = 3+ candle extremes within 0.25 since 00:00, session high / low); stop = D / 0.53 (his target / stop ratio, median 0.53).
Usage: python forex/apprentice/manual_read.py new | scan [--chart] | call L|S HH:MM STOP TARGET "reason" | call none "reason" | reveal | log"""
import sys, os, json, hashlib, datetime as dt
import numpy as np, pandas as pd
import desk as D

HERE = D.HERE; ST = os.path.join(HERE, "state_k"); os.makedirs(ST, exist_ok=True)
LOG = os.path.join(HERE, "MANUAL_READ_LOG.csv"); CALLS = os.path.join(HERE, "MANUAL_CALLS.csv")
EMA12 = os.path.join(D.ROOT, "mt5", "ea_research", "ema12")
SEEN = {"2025-04-30", "2025-05-01", "2025-05-05", "2026-01-09", "2026-01-28"}
DAY0 = pd.Timestamp("2000-01-03")


def build_calls():
    j = pd.read_csv(os.path.join(EMA12, "BLIND_LOG_JAN2026.csv"))
    rows = []
    for r in j.itertuples():
        if r.ses != "London": continue
        if isinstance(r.side, str):
            rows.append({"date": r.date, "side": r.side, "signal": r.hhmm, "stop_d": round(abs(r.entry - r.stop), 3), "tgt_d": round(abs(r.target - r.entry), 3), "src": "jan2026"})
        else:
            rows.append({"date": r.date, "side": "none", "signal": "", "stop_d": np.nan, "tgt_d": np.nan, "src": "jan2026"})
    a = pd.read_csv(os.path.join(EMA12, "replay_mt5.csv"))
    for r in a.itertuples():
        if r.ses != "London": continue
        m = int(r.hm) - 120 - 1
        rows.append({"date": r.day, "side": r.side, "signal": "%02d:%02d" % divmod(m, 60), "stop_d": round(r.risk, 3), "tgt_d": round(r.rew, 3), "src": "aprmay2025"})
    c = pd.DataFrame(rows); c = c[~c["date"].isin(SEEN)].reset_index(drop=True)
    c.to_csv(CALLS, index=False); return c


def cur():
    p = os.path.join(ST, "current.json"); return json.load(open(p)) if os.path.exists(p) else None


def save(c): json.dump(c, open(os.path.join(ST, "current.json"), "w"))


def frame_for(d, day):
    x = d[(d["lis"] >= day - pd.Timedelta(hours=4)) & (d["lis"] < day + pd.Timedelta(hours=21))].copy().reset_index(drop=True)
    x["ema"] = x["mc"].ewm(span=12, adjust=False).mean()
    tr = np.maximum(x["mh"] - x["ml"], np.maximum((x["mh"] - x["mc"].shift()).abs(), (x["ml"] - x["mc"].shift()).abs()))
    x["atr"] = tr.rolling(14).mean().shift(1); x["vmed"] = x["v"].rolling(60).median().shift(1)
    i6 = int(np.argmax(x["lis"] >= day + pd.Timedelta(hours=6))); base = x["mo"][i6] - 1000.0
    for k in ("mo", "mh", "ml", "mc", "ema"): x[k] = (x[k] - base).round(2)
    x["lis"] = x["lis"] - (day - DAY0)
    return x[["lis", "mo", "mh", "ml", "mc", "v", "ema", "atr", "vmed"]].reset_index(drop=True)


def features(y, i, i0):
    """the trader's stated features for candle i (only candles up to i)"""
    r = y.iloc[i]; atr = r.atr
    body = abs(r.mc - r.mo); up = r.mh - max(r.mo, r.mc); lo = min(r.mo, r.mc) - r.ml
    # v4 (lesson 12, K019): a pin bar's side comes from its rejection wick, not its colour
    pin = "L" if (lo >= atr and lo >= 2 * max(up, body)) else ("S" if (up >= atr and up >= 2 * max(lo, body)) else None)
    L = (pin == "L") if pin else (r.mc > r.mo)
    # v5 (lesson 15, K023): EMA-retest rejection = a wick into the EMA against the 30-minute trend that closes back on the trend side; side from the trend
    e1 = y["ema"][i - 1]; t30 = r.mc - y["mc"][max(0, i - 30)]
    rejS = bool(r.mh >= e1 and r.mc < r.ema and up >= max(body, 0.3 * atr) and t30 < 0)
    rejL = bool(r.ml <= e1 and r.mc > r.ema and lo >= max(body, 0.3 * atr) and t30 > 0)
    if not pin and (rejS or rejL): L = rejL
    cw = up if L else lo
    prev5 = y.iloc[max(0, i - 5):i]
    bos = (r.mc > prev5["mh"].max()) if L else (r.mc < prev5["ml"].min())
    touch = (r.ml <= r.ema <= r.mh) or abs(r.mo - y["ema"][i - 1]) <= 0.3 * atr
    side_ok = (r.mc > r.ema) if L else (r.mc < r.ema)
    w60 = y.iloc[max(0, i - 60):i + 1]
    sweep = (w60["ml"].idxmin() >= i - 6) if L else (w60["mh"].idxmax() >= i - 6)
    before = D.fvgs(y, i - 1)
    rej = [g for g in before if (g[1] == "bear" and not L and r.mh >= g[2] and r.mc < g[2]) or (g[1] == "bull" and L and r.ml <= g[3] and r.mc > g[3])]
    tr30 = r.mc - y["mc"][max(0, i - 30)]
    f = {"side": "L" if L else "S", "body_atr": round(body / atr, 2), "disp": bool(body >= atr and body > up + lo), "small_close_wick": bool(cw <= 0.25 * body),
         "ema_touch": bool(touch), "close_trade_side_of_ema": bool(side_ok), "bos5": bool(bos), "gap_rejection": bool(rej), "sweep60": bool(sweep),
         "with_trend30": bool(tr30 * (1 if L else -1) > 0), "vol_x": round(r.v / r.vmed, 1) if r.vmed == r.vmed and r.vmed > 0 else None}
    # v2 (lesson 4, K007): the close-side wick is what must be small; a long far-side wick is a rejection and is fine
    f["interesting"] = f["disp"] or (body >= 0.6 * atr and cw <= 0.25 * body) or (f["sweep60"] and body >= 0.5 * atr)
    # v3 (lessons 6-11): opening-push bias, mixed pushes, trend strength, first resumption after a pullback
    w = y.iloc[max(0, i - 15):i + 1]
    big = [(D.hm(q.lis), "up" if q.mc > q.mo else "down") for q in w.itertuples() if abs(q.mc - q.mo) >= q.atr]
    dirs = {d for _, d in big}
    f["pushes"] = " ".join("%s %s" % b for b in big) or "none"
    f["mixed"] = len(dirs) > 1
    f["trend30_atr"] = round(tr30 / atr, 1)
    prev = y.iloc[i - 1]; push_dir = big[-1][1] if big else None
    f["resume"] = bool(push_dir and (("up" if L else "down") == push_dir) and ((prev.mc < prev.mo) if L else (prev.mc > prev.mo)))
    f["interesting"] = f["interesting"] or f["resume"]
    # v4 (lessons 12-13): high-volume pin-bar rejection; how extended the candle is from the EMA and how long the run is
    f["pin"] = bool(pin)
    f["ema_reject"] = bool((rejL and L) or (rejS and not L))
    if f["ema_reject"]: f["interesting"] = True
    # v6 (lesson 17, K024): the previous candle tested the 30-minute low / high (equal or a small sweep) and held; this candle goes the held way
    q = y.iloc[i - 1]; w = y.iloc[max(0, i - 31):i - 1]
    lowtest = bool(w["ml"].min() - q.atr <= q.ml <= w["ml"].min() + 0.15 * q.atr and q.mc >= q.ml + 0.4 * q.atr)
    hightest = bool(w["mh"].max() - 0.15 * q.atr <= q.mh <= w["mh"].max() + q.atr and q.mc <= q.mh - 0.4 * q.atr)
    f["held"] = "L" if (lowtest and r.mc > r.mo) else ("S" if (hightest and r.mc < r.mo) else None)
    if f["held"] and (f["held"] == "L") == L: f["interesting"] = True
    # v7 (lesson 18, K028): a candle in the last 5 swept the 60-minute low / high with a rejection wick; this candle turns the other way without a new extreme
    w60b = y.iloc[max(0, i - 60):i - 5]; rec = y.iloc[max(0, i - 5):i]; ps = None
    if len(w60b) and len(rec) and rec["ml"].min() < w60b["ml"].min():
        q = y.loc[rec["ml"].idxmin()]
        if min(q.mo, q.mc) - q.ml >= 0.5 * q.atr and r.mc > r.mo and r.ml > q.ml: ps = "L"
    if len(w60b) and len(rec) and rec["mh"].max() > w60b["mh"].max():
        q = y.loc[rec["mh"].idxmax()]
        if q.mh - max(q.mo, q.mc) >= 0.5 * q.atr and r.mc < r.mo and r.mh < q.mh: ps = "S"
    f["post_sweep"] = ps
    if ps and (ps == "L") == L: f["interesting"] = True
    # v8 (lesson 19, K030 / K015): a bounce stalls under an untouched opposite gap (rejection wick of 0.75 ATR or more in the last 3 candles,
    # its extreme within 1.5 ATR of the gap's near edge); this candle turns away with a lower high / higher low
    st = None; gaps = D.fvgs(y, i)
    for k in range(max(0, i - 3), i):
        q = y.iloc[k]; quw = q.mh - max(q.mo, q.mc); qlw = min(q.mo, q.mc) - q.ml
        if quw >= 0.75 * q.atr and r.mc < r.mo and r.mh <= q.mh and any(g[1] == "bear" and 0 <= g[2] - q.mh <= 1.5 * q.atr for g in gaps): st = "S"
        if qlw >= 0.75 * q.atr and r.mc > r.mo and r.ml >= q.ml and any(g[1] == "bull" and 0 <= q.ml - g[3] <= 1.5 * q.atr for g in gaps): st = "L"
    f["stall_under_gap"] = st
    if st and (st == "L") == L: f["interesting"] = True
    sl, sh = y["ml"][i0:i + 1].min(), y["mh"][i0:i + 1].max()
    f["room_to_extreme_atr"] = round(((r.mc - sl) if not L else (sh - r.mc)) / atr, 1)
    if pin and side_ok: f["interesting"] = True  # lesson 14 (K021): no volume condition; with the trend a normal-volume pin is enough
    f["open_from_ema_atr"] = round(((r.mo - y["ema"][i - 1]) if L else (y["ema"][i - 1] - r.mo)) / atr, 2)
    run = 0
    for k in range(i - 1, max(0, i - 10), -1):
        q = y.iloc[k]
        if (q.mc > q.mo) == L and q.mc != q.mo: run += 1
        else: break
    f["run_before"] = run
    return f


def manual_bracket(y, i, i0, side):
    r = y.iloc[i]; atr = r.atr; L = side == "L"; c = r.mc
    lv = []
    for g in D.fvgs(y, i):
        if L and g[1] == "bear" and g[2] > c: lv.append((g[2], "%s bear gap" % g[0]))
        if not L and g[1] == "bull" and g[3] < c: lv.append((g[3], "%s bull gap" % g[0]))
    z = y.iloc[max(0, i0 - 360):i + 1]
    ext = z["mh"].values if L else z["ml"].values
    for h in ext:
        if (L and h > c) or (not L and h < c):
            n = int(((ext >= h - 0.25) & (ext <= h + 0.25)).sum())
            if n >= 3: lv.append((h, "equal %s x%d" % ("highs" if L else "lows", n)))
    hi, lo = y["mh"][i0:i + 1].max(), y["ml"][i0:i + 1].min()
    lv.append((hi, "session high") if L else (lo, "session low"))
    # v2 (lesson 3, K006): his targets sit ~2-3 ATR away at a significant level; use the nearest level >= 2 ATR, else the nearest >= 0.8 ATR
    far = sorted([l for l in lv if (l[0] - c if L else c - l[0]) >= 2 * atr], key=lambda l: abs(l[0] - c))
    lv = far or sorted([l for l in lv if (l[0] - c if L else c - l[0]) >= 0.8 * atr], key=lambda l: abs(l[0] - c))
    if not lv: return None
    T, what = lv[0]; Dd = abs(T - c); sd = Dd / 0.53
    return {"T": round(T, 2), "what": what, "D": round(Dd, 2), "stop": round(c - sd if L else c + sd, 2), "target": round(T, 2)}


def cmd_new():
    c = cur()
    if c and not c.get("revealed"): sys.exit("day %s still open" % c["id"])
    calls = build_calls() if not os.path.exists(CALLS) else pd.read_csv(CALLS)
    done = set(pd.read_csv(LOG)["date"]) if os.path.exists(LOG) else set()
    order = [calls["date"][k] for k in np.random.default_rng(20261023).permutation(len(calls))]
    d = D.raw()
    for date in order:
        if date in done: continue
        y = frame_for(d, pd.Timestamp(date))
        y.to_parquet(os.path.join(ST, "day.parquet"))
        n = len(done) + 1
        save({"id": "K%03d" % n, "date": date}); print("new day K%03d (one of the trader's London days; date hidden). Next: scan --chart" % n); return
    sys.exit("all of the trader's days played")


def cmd_scan(chart):
    c = cur()
    if not c or c.get("call"): sys.exit("no open, uncalled day")
    y = pd.read_parquet(os.path.join(ST, "day.parquet")); i0 = int(np.argmax(y["lis"] >= DAY0 + pd.Timedelta(hours=6)))
    start = 7 * 60 + 59
    if c.get("shown_until"): ph, pm = map(int, c["shown_until"].split(":")); start = ph * 60 + pm + 1
    if chart and not c.get("shown_until"):
        i = int(np.where(y["lis"] == DAY0 + pd.Timedelta(minutes=start - 1))[0][0])
        png = os.path.join(ST, "%s_0758.png" % c["id"]); D.chart(y, max(i0, i - 150), i, png, "%s up to 07:58" % c["id"]); print("context chart to 07:58: %s" % png)
    for m in range(start, 8 * 60 + 15):
        hit = np.where(y["lis"] == DAY0 + pd.Timedelta(minutes=m))[0]
        if not len(hit): continue
        i = int(hit[0]); c["shown_until"] = "%02d:%02d" % divmod(m, 60); f = features(y, i, i0)
        if not f["interesting"]: continue
        save(c)
        print("time   open     high     low      close    EMA12    ATR  body/ATR close-EMA vol")
        for k in range(max(0, i - 9), i + 1):
            r = y.iloc[k]
            print("%s %8.2f %8.2f %8.2f %8.2f %8.2f %5.2f %5.2f %+6.2f %5.0f" % (D.hm(r.lis), r.mo, r.mh, r.ml, r.mc, r.ema, r.atr, abs(r.mc - r.mo) / r.atr, r.mc - r.ema, r.v))
        b = manual_bracket(y, i, i0, f["side"])
        print("CANDIDATE %s %s | %s" % (c["shown_until"], "LONG" if f["side"] == "L" else "SHORT", ", ".join("%s=%s" % (k, v) for k, v in f.items() if k not in ("side", "interesting", "pushes"))))
        print("pushes (>= 1 ATR candles, last 15 min): %s" % f["pushes"])
        if f["room_to_extreme_atr"] <= 1.0 and D.hm(y["lis"][i]) < "08:00":
            print("WARNING (lesson 18): this trade runs into the session %s %.1f ATR away before the 08:00 candle; the open often sweeps it and turns" % ("low" if f["side"] == "S" else "high", f["room_to_extreme_atr"]))
        print("the trader-style bracket: %s" % ("T %.2f (%s), D %.2f, stop %.2f, target %.2f" % (b["T"], b["what"], b["D"], b["stop"], b["target"]) if b else "no level >= 0.8 ATR"))
        print("context: session %.2f-%.2f; 30-min change %+.2f; untouched gaps: %s" % (y["ml"][i0:i + 1].min(), y["mh"][i0:i + 1].max(), y["mc"][i] - y["mc"][max(0, i - 30)],
              "; ".join("%s %s %.2f-%.2f" % g for g in D.fvgs(y, i)[-5:]) or "none"))
        return
    c["shown_until"] = "08:14"; save(c); print("no candidate candle up to 08:14")


def cmd_call(a):
    c = cur()
    if not c or c.get("call"): sys.exit("no open, uncalled day")
    if a[0].lower() == "none": call = {"side": "none", "reason": " ".join(a[1:])}
    else:
        if a[1] != c.get("shown_until"): sys.exit("call on the candle just shown (%s)" % c.get("shown_until"))
        call = {"side": a[0].upper(), "signal": a[1], "stop": float(a[2]), "target": float(a[3]), "reason": " ".join(a[4:])}
    call["pc_time"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"); call["sha256"] = hashlib.sha256(json.dumps(call, sort_keys=True).encode()).hexdigest()
    c["call"] = call; save(c); print("locked %s: %s" % (call["sha256"][:16], json.dumps(call)))


def cmd_reveal():
    c = cur()
    if not c or not c.get("call") or c.get("revealed"): sys.exit("nothing to reveal")
    y = pd.read_parquet(os.path.join(ST, "day.parquet")); i0 = int(np.argmax(y["lis"] >= DAY0 + pd.Timedelta(hours=6)))
    k = pd.read_csv(CALLS); k = k[k["date"] == c["date"]].iloc[0]; me = c["call"]
    mine = D.simulate(y, me["side"], me["signal"], me["stop"], me["target"]) if me["side"] != "none" else None
    his = None
    if k["side"] != "none":
        hit = np.where(y["lis"] == DAY0 + pd.Timedelta(hours=int(k["signal"][:2]), minutes=int(k["signal"][3:])))[0]
        if len(hit):
            cl = y["mc"][int(hit[0])]; L = k["side"] == "L"
            his = D.simulate(y, k["side"], k["signal"], cl - k["stop_d"] if L else cl + k["stop_d"], cl + k["tgt_d"] if L else cl - k["tgt_d"])
    agree_trade = (me["side"] == "none") == (k["side"] == "none")
    agree_side = bool(agree_trade and me["side"] != "none" and me["side"] == k["side"])
    dmin = None
    if agree_side:
        dmin = abs((int(me["signal"][:2]) * 60 + int(me["signal"][3:])) - (int(k["signal"][:2]) * 60 + int(k["signal"][3:])))
    row = {"id": c["id"], "date": c["date"], "src": k["src"], "my_side": me["side"], "my_signal": me.get("signal", ""), "my_R": mine["R"] if mine else 0.0,
           "manual_side": k["side"], "manual_signal": k["signal"] if k["side"] != "none" else "", "manual_R_on_gc": his["R"] if his else 0.0,
           "agree_trade": agree_trade, "agree_side": agree_side, "minutes_apart": dmin, "agree_full": bool(agree_side and dmin is not None and dmin <= 2),
           "my_reason": me["reason"], "sha256": me["sha256"]}
    pd.DataFrame([row]).to_csv(LOG, mode="a", header=not os.path.exists(LOG), index=False)
    i12 = int(np.where(y["lis"] <= DAY0 + pd.Timedelta(hours=10))[0].max())
    marks = []
    if mine: marks += [(me["stop"], "my stop", "#ef5350"), (me["target"], "my target", "#26a69a")]
    png = os.path.join(ST, "%s_reveal.png" % c["id"]); D.chart(y, max(i0, i12 - 240), i12, png, "%s revealed: me %s %s | the trader %s %s" % (
        c["id"], me["side"], me.get("signal", ""), k["side"], k["signal"] if k["side"] != "none" else ""), marks)
    c["revealed"] = True; save(c)
    print("%s (%s, %s): ME %s %s -> %s | MANUAL %s %s (stop %.2f, target %.2f) -> %s | agree trade %s, side %s, minutes apart %s, FULL %s | chart %s" % (
        c["id"], c["date"], k["src"], me["side"], me.get("signal", ""), ("%s %+.2f R" % (mine["result"], mine["R"])) if mine else "no trade",
        k["side"], k["signal"] if k["side"] != "none" else "", k["stop_d"] if k["side"] != "none" else 0, k["tgt_d"] if k["side"] != "none" else 0,
        ("%s %+.2f R" % (his["result"], his["R"])) if his else "no trade", agree_trade, agree_side, dmin, row["agree_full"], png))


def cmd_log():
    g = pd.read_csv(LOG)
    print(g[["id", "date", "my_side", "my_signal", "manual_side", "manual_signal", "agree_side", "minutes_apart", "agree_full", "my_R", "manual_R_on_gc"]].to_string(index=False))
    for b0 in range(0, len(g), 10):
        b = g.iloc[b0:b0 + 10]
        print("block %d-%d: agree trade %d/%d, side %d/%d, full %d/%d; my R %+.2f, the trader R on GC %+.2f" % (b0 + 1, b0 + len(b), b.agree_trade.sum(), len(b), b.agree_side.sum(), len(b),
              b.agree_full.sum(), len(b), b.my_R.sum(), b.manual_R_on_gc.sum()))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"new": cmd_new, "scan": lambda: cmd_scan("--chart" in a), "call": lambda: cmd_call(a[1:]), "reveal": cmd_reveal, "log": cmd_log}[a[0]]()
