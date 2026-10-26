"""MGC blind replay (the trader 26 Oct 2026: "build it bro"). A local, blind-by-construction replay of gold futures 1-minute data for the
registered extension windows of PREREG_BLIND2026 (Amendment 8) and for unscored practice days.

- Data: Databento GC continuous 1m (= the MGC price), local clock.
- The SERVER holds the cursor (the last visible minute) and never returns a bar after it, so the browser cannot see the future.
- Protocol (PREREG_BLIND2026 steps 3-6, Amendment 7): bias before 08:00 (required), at most one trade, market entry while the last visible
  candle is 07:59-08:14, the trade is written to the log BEFORE any later bar exists on the client; reaching 08:15 with no trade = a
  no-trade day; registered days run in calendar order with no skipping and no going back; stop and target are never moved.
- Result shown on GC futures (spot_vs_futures.py convention): fill at the next minute's open, one tick worse; stop exits one tick worse;
  target at its price; stop and target in the same minute = stop; still open at 17:00 local = closed at that minute's close.
  The registered primary (MT5 broker spot bid/ask) is scored separately by blind_score.py.
- Practice days are drawn from 2019-07-01..2023-10-31 only (before extension window 1), so practice can never show a price from after a
  scored day.

Usage: C:/Python314/python.exe server.py   then open http://127.0.0.1:8611   (start_replay.bat does both)."""
import csv, hashlib, json, os, random, threading, time, datetime as dt
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); EMA12 = os.path.dirname(HERE)
DATA = "D:/finance/beginner-quant-research/futures/data/databento/futures_GC.F_1m.parquet"
PORT = 8611
LOG = os.path.join(EMA12, "BLIND_LOG_EXTRA_FUT.csv")            # the registered log (blind_score.py format + price_source)
RES = os.path.join(EMA12, "BLIND_RESULTS_EXTRA_FUT.csv")        # futures outcome of each registered trade (secondary, Amendment 8)
PLOG = os.path.join(EMA12, "PRACTICE_REPLAY_LOG.csv")           # practice days (never scored)
EVENTS = os.path.join(EMA12, "replay_events.jsonl")             # audit trail: every start / bias / trade / no-trade / result / reveal
STATE = os.path.join(HERE, "replay_state.json")
WINDOWS = [("slow read 2024-25", os.path.join(EMA12, "BLIND_SLOW_2024_25.csv"))]   # PREREG_SLOW_READ (Claude-filter schedule is complete)
LOG = os.path.join(EMA12, "BLIND_LOG_SLOW.csv")                 # each test keeps its own logs (earlier logs stay as they are)
RES = os.path.join(EMA12, "BLIND_RESULTS_SLOW.csv")
FILTER_MODE = False                                             # PREREG_CLAUDE_FILTER only: a placed trade ended the day with no result
PACE_SECONDS = 180                                              # PREREG_SLOW_READ rule 2: no decision on a scored day before 3 minutes
V2_MIN_STOP, V2_RR, V2_CHASE = 5.0, (1.0, 1.5), 3.0             # PREREG_READ_V2 rules 1-3 (noise = median 1m range 07:00-07:59)
SANDBOX = os.environ.get("REPLAY_SANDBOX")                     # testing only: logs and state go to this folder, never to the real ones
if SANDBOX:
    import shutil
    os.makedirs(SANDBOX, exist_ok=True)
    for _p in (LOG, RES):
        if os.path.exists(_p) and not os.path.exists(os.path.join(SANDBOX, os.path.basename(_p))): shutil.copy(_p, SANDBOX)
    LOG, RES, PLOG, EVENTS, STATE = (os.path.join(SANDBOX, os.path.basename(p)) for p in (LOG, RES, PLOG, EVENTS, STATE))
    PORT = int(os.environ.get("REPLAY_PORT", "8612"))
    PACE_SECONDS = int(os.environ.get("REPLAY_PACE", PACE_SECONDS))                     # a short pace so the lock can be tested quickly
    if os.environ.get("REPLAY_SCHEDULE"): WINDOWS = [("sandbox", os.environ["REPLAY_SCHEDULE"])]   # test days, never the scored ones
LOG_HDR = ["date", "ses", "side", "hhmm", "entry", "stop", "target", "flag", "pre", "price_source"]
RES_HDR = ["date", "side", "hhmm", "entry", "stop", "target", "fill", "stop_px", "target_px", "exit", "exit_time", "outcome", "R",
           "micros_750", "usd_750", "bias", "logged_at"]
PLOG_HDR = ["date", "bias", "recognised", "side", "hhmm", "entry", "stop", "target", "fill", "exit", "exit_time", "outcome", "R",
            "usd_750", "logged_at"]
TICK, USD, RISK_USD, FEE, MAX_MICROS = 0.1, 10.0, 750.0, 1.92, 50
HIST_DAYS = {1: 2, 5: 6, 15: 15, 60: 40}
PRACTICE_FROM, PRACTICE_TO = "2026-01-02", "2026-07-24"           # PREREG_READ_V2: a period he has already replayed (no new leak)
MONTHS = dict(zip("FGHJKMNQUVXZ", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]))
LOCK = threading.RLock()

print("loading GC 1m ...", flush=True)
_d = pd.read_parquet(DATA, columns=["ts", "symbol", "open", "high", "low", "close", "volume"]).drop_duplicates("ts").sort_values("ts")
_d.index = pd.DatetimeIndex(_d.ts.dt.tz_convert("Europe/London").dt.tz_localize(None))
DF = _d[~_d.index.duplicated()][["symbol", "open", "high", "low", "close", "volume"]]
del _d
IDX = DF.index
EPOCH = IDX.values.astype("datetime64[s]").astype(np.int64)      # local wall clock as epoch seconds: the chart axis reads local time
O, H, L, C = (DF[c].to_numpy() for c in ("open", "high", "low", "close"))
_t = IDX[(IDX.hour == 8) & (IDX.minute < 15)]
OPEN_DAYS = set(pd.Series(1, index=_t).groupby(_t.normalize()).size().loc[lambda s: s >= 10].index.strftime("%Y-%m-%d"))
print("loaded %d bars %s .. %s" % (len(DF), IDX[0], IDX[-1]), flush=True)


class ApiError(Exception):
    pass


def now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def event(**kw):
    with open(EVENTS, "a", encoding="utf-8") as f:
        f.write(json.dumps({"pc_time": now(), **kw}) + "\n")


def rows(path):
    if not os.path.exists(path): return []
    with open(path, newline="", encoding="utf-8") as f: return list(csv.DictReader(f))


def append(path, header, row):
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new: w.writerow(header)
        w.writerow(row)
    return hashlib.sha256(",".join(str(x) for x in row).encode()).hexdigest()


def blank():
    return {"mode": None, "day": None, "window": None, "cursor": None, "phase": "idle", "bias": None, "recognised": False, "trade": None}


def load_state():
    try:
        with open(STATE, encoding="utf-8") as f: return json.load(f)
    except Exception:
        return blank()


ST = load_state()


def save():
    with open(STATE, "w", encoding="utf-8") as f: json.dump(ST, f, indent=1)


def window_days():
    out = []
    for name, path in WINDOWS:
        for r in rows(path): out.append((r.get("set") or name, r["date"]))
    return out


def next_registered():
    done = {r["date"] for r in rows(LOG)}
    for name, d in window_days():
        if d not in done: return name, d
    return None, None


def cur_idx():
    return int(IDX.searchsorted(pd.Timestamp(ST["cursor"]), side="right") - 1)


def hm(ts):
    return ts.hour * 60 + ts.minute


def in_window():
    if ST["phase"] != "open" or not ST["cursor"]: return False
    c = IDX[cur_idx()]
    return c.strftime("%Y-%m-%d") == ST["day"] and 7 * 60 + 59 <= hm(c) <= 8 * 60 + 14


def noise():
    """Median 1-minute range 07:00-07:59 of the day (all before 08:00, so known at the 07:59 bias)."""
    D = pd.Timestamp(ST["day"]); w = DF.loc[D + pd.Timedelta(hours=7):D + pd.Timedelta(hours=7, minutes=59)]
    return float((w.high - w.low).median()) if len(w) else float("nan")


def chase_moves(ci):
    """Move over the last 5 minutes (close of the last visible candle minus the close 5 minutes earlier), in noise units, up and down."""
    k = int(IDX.searchsorted(IDX[ci] - pd.Timedelta(minutes=5)))
    nz = noise(); mv = float(C[ci] - C[k]) if k < ci else 0.0
    return (mv / nz if nz > 0 else 0.0)


def contract(sym, ts):
    """The Databento file is the continuous front month ('GC.F'), so the label is generic; a dated symbol like 'GCZ3' gets its month."""
    try:
        y = ts.year
        while y % 10 != int(sym[-1]): y += 1
        return "GC %s %d (= MGC)" % (MONTHS[sym[2]], y)
    except Exception:
        return "GC front month (= MGC price)"


# ---------------------------------------------------------------- actions
def start(mode):
    if ST["phase"] in ("bias", "open", "trade"): raise ApiError("finish the current day first")       # "logged" days are finished
    if mode == "registered":
        w, d = next_registered()
        if not d: raise ApiError("both extension windows are done")
        if d not in OPEN_DAYS: raise ApiError("no futures data at 08:00 on %s: tell Claude (needs a decision, not a skip)" % d)
    else:
        seen = {r["date"] for r in rows(PLOG)}
        pool = sorted(x for x in OPEN_DAYS if PRACTICE_FROM <= x <= PRACTICE_TO and x not in seen and pd.Timestamp(x).weekday() < 5)
        if not pool: raise ApiError("practice pool is empty")
        d = random.SystemRandom().choice(pool); w = "practice"
    c = IDX[IDX.searchsorted(pd.Timestamp(d + " 07:59"), side="right") - 1]
    ST.clear(); ST.update(blank()); ST.update(mode=mode, day=d, window=w, cursor=str(c), phase="bias", started_at=time.time())
    save(); event(event="start_day", mode=mode, window=w, day=d, cursor=str(c))


def pace_left():
    """Seconds until a decision is accepted on a scored day (0 on practice days)."""
    if ST.get("mode") != "registered": return 0.0
    return max(0.0, PACE_SECONDS - (time.time() - ST.get("started_at", 0)))


def need_pace(what):
    left = pace_left()
    if left > 0: raise ApiError("pace: %s unlocks %d:%02d after the day starts (%d s left). Read the chart." % (what, PACE_SECONDS // 60, PACE_SECONDS % 60, int(left) + 1))


def secs():
    return int(time.time() - ST.get("started_at", time.time()))


def set_bias(bias, recognised):
    if ST["phase"] != "bias": raise ApiError("the bias is set at 07:59, before the first step")
    if bias not in ("long", "short", "neutral"): raise ApiError("bias must be long, short or neutral")
    ST.update(bias=bias, recognised=bool(recognised), phase="open"); save()
    event(event="bias", day=ST["day"], mode=ST["mode"], bias=bias, recognised=bool(recognised), cursor=ST["cursor"])


def log_notrade(reason):
    flag = "1" if ST["recognised"] else "0"
    if ST["mode"] == "registered":
        sha = append(LOG, LOG_HDR, [ST["day"], "London", "", "", "", "", "", flag, "1", "GC"])
    else:
        sha = append(PLOG, PLOG_HDR, [ST["day"], ST["bias"], int(ST["recognised"]), "", "", "", "", "", "", "", "", "no trade", "", "", now()])
    ST["phase"] = "notrade"; ST["trade"] = None
    event(event="no_trade", day=ST["day"], mode=ST["mode"], reason=reason, cursor=ST["cursor"], sha256=sha, secs=secs())


def place(side, stop, target):
    if ST["phase"] != "open": raise ApiError("no trade can be placed now")
    if not in_window(): raise ApiError("entries only while the last visible candle is 07:59-08:14")
    need_pace("a trade")
    if side not in ("L", "S"): raise ApiError("side must be L or S")
    ci = cur_idx(); sd = 1 if side == "L" else -1; entry = round(float(C[ci]), 2)
    try: stop, target = round(float(stop), 2), round(float(target), 2)
    except Exception: raise ApiError("stop and target must be prices")
    if not (sd * (entry - stop) > 0 and sd * (target - entry) > 0):
        raise ApiError("a %s needs stop %s entry %.2f and target %s it" % ("long" if sd > 0 else "short", "below" if sd > 0 else "above", entry, "above" if sd > 0 else "below"))
    nz = noise(); sdist, tdist = abs(entry - stop), abs(target - entry)          # PREREG_READ_V2 rules 1-3
    if sdist < V2_MIN_STOP * nz - 1e-9:
        raise ApiError("v2: stop %.1f pt is inside the noise; minimum is %.1f pt (5 x %.2f)" % (sdist, V2_MIN_STOP * nz, nz))
    if not (V2_RR[0] - 0.005 <= tdist / sdist <= V2_RR[1] + 0.005):
        raise ApiError("v2: target must be 1.0R to 1.5R (now %.2fR)" % (tdist / sdist))
    if sd * chase_moves(ci) > V2_CHASE:
        raise ApiError("v2: no chase: price already moved %.1f x noise your way in the last 5 minutes (limit 3)" % (sd * chase_moves(ci)))
    hhmm = IDX[ci].strftime("%H:%M"); flag = "1" if ST["recognised"] else "0"
    t = dict(side=side, sd=sd, entry=entry, stop=stop, target=target, hhmm=hhmm, sdist=round(abs(entry - stop), 4), tdist=round(abs(target - entry), 4),
             t0=int(EPOCH[ci]), placed=now(), fill=None, fill_epoch=None, stop_px=None, target_px=None, exit=None, exit_time=None, exit_epoch=None,
             outcome=None, R=None)
    if ST["mode"] == "registered":
        t["sha256"] = append(LOG, LOG_HDR, [ST["day"], "London", side, hhmm, "%.2f" % entry, "%.2f" % stop, "%.2f" % target, flag, "1", "GC"])
    ST["trade"] = t; ST["phase"] = "logged" if (FILTER_MODE and ST["mode"] == "registered") else "trade"; save()
    event(event="trade", day=ST["day"], mode=ST["mode"], side=side, hhmm=hhmm, entry=entry, stop=stop, target=target, recognised=ST["recognised"],
          sha256=t.get("sha256"), outcome_hidden=ST["phase"] == "logged", secs=secs())


def close_trade(ci, outcome, exit_px):
    t = ST["trade"]; R = t["sd"] * (exit_px - t["fill"]) / t["sdist"]
    micros = int(min(MAX_MICROS, RISK_USD // (t["sdist"] * USD))) if t["sdist"] > 0 else 0
    usd = micros * (R * t["sdist"] * USD) - micros * FEE
    t.update(exit=round(exit_px, 2), exit_time=IDX[ci].strftime("%H:%M"), exit_epoch=int(EPOCH[ci]), outcome=outcome, R=round(R, 3), micros=micros, usd=round(usd, 2))
    ST["phase"] = "closed"
    if ST["mode"] == "registered":
        append(RES, RES_HDR, [ST["day"], t["side"], t["hhmm"], t["entry"], t["stop"], t["target"], t["fill"], t["stop_px"], t["target_px"], t["exit"],
                              t["exit_time"], outcome, "%.3f" % R, micros, "%.2f" % usd, ST["bias"], now()])
    else:
        append(PLOG, PLOG_HDR, [ST["day"], ST["bias"], int(ST["recognised"]), t["side"], t["hhmm"], t["entry"], t["stop"], t["target"], t["fill"],
                                t["exit"], t["exit_time"], outcome, "%.3f" % R, "%.2f" % usd, now()])
    event(event="result", day=ST["day"], mode=ST["mode"], outcome=outcome, R=round(R, 3), exit=t["exit"], exit_time=t["exit_time"], fill=t["fill"])


def check_exit(ci):
    t = ST["trade"]; sd = t["sd"]
    if t["fill"] is None:                                            # this minute is the fill minute: market order at its open, one tick worse
        t["fill"] = round(float(O[ci]) + sd * TICK, 2); t["fill_epoch"] = int(EPOCH[ci])
        t["stop_px"] = round(t["fill"] - sd * t["sdist"], 2); t["target_px"] = round(t["fill"] + sd * t["tdist"], 2)
    hi, lo = float(H[ci]), float(L[ci])
    if (lo <= t["stop_px"]) if sd > 0 else (hi >= t["stop_px"]): return close_trade(ci, "SL", t["stop_px"] - sd * TICK)
    if (hi >= t["target_px"]) if sd > 0 else (lo <= t["target_px"]): return close_trade(ci, "TP", t["target_px"])
    if hm(IDX[ci]) >= 17 * 60: return close_trade(ci, "17:00", float(C[ci]))


def step(n, until_close=False):
    if ST["phase"] == "idle": raise ApiError("start a day first")
    if ST["phase"] == "bias": raise ApiError("lock your bias first")
    if ST["phase"] == "logged": raise ApiError("trade logged: the outcome stays hidden until Claude's take/skip calls are locked; start the next day")
    day_end = pd.Timestamp(ST["day"] + " 22:00"); ci = cur_idx()
    if ST["phase"] == "open" and 7 * 60 + 59 <= hm(IDX[ci]) <= 8 * 60 + 13 and (int(n) > 1 or until_close):
        raise ApiError("v2: one minute at a time in the entry window (07:59-08:14)")              # PREREG_READ_V2 rule 4
    for _ in range(max(1, min(int(n), 900))):
        if ci + 1 >= len(IDX) or IDX[ci + 1] >= day_end: break
        if ST["phase"] == "open" and hm(IDX[ci + 1]) >= 8 * 60 + 15 and pace_left() > 0:
            save(); need_pace("stepping past 08:14 (= no trade)")
        ci += 1; ST["cursor"] = str(IDX[ci])
        if ST["phase"] == "trade": check_exit(ci)
        elif ST["phase"] == "open" and hm(IDX[ci]) >= 8 * 60 + 15: log_notrade("08:15 reached with no trade")
        if until_close and ST["phase"] != "trade": break
    save()


def reveal():
    if ST["phase"] not in ("closed", "notrade"): raise ApiError("the rest of the day opens after the trade is closed (or a no-trade day)")
    end = IDX[IDX.searchsorted(pd.Timestamp(ST["day"] + " 22:00")) - 1]
    if end > IDX[cur_idx()]: ST["cursor"] = str(end)
    save(); event(event="reveal", day=ST["day"], mode=ST["mode"])


def skip_practice():
    if ST["mode"] != "practice" or ST["phase"] not in ("bias", "open"): raise ApiError("only an untraded practice day can be skipped")
    append(PLOG, PLOG_HDR, [ST["day"], ST["bias"] or "", int(ST["recognised"]), "", "", "", "", "", "", "", "", "skipped", "", "", now()])
    event(event="skip_practice", day=ST["day"]); ST.clear(); ST.update(blank()); save()


# ---------------------------------------------------------------- reads
def bars(tf, since):
    if not ST["cursor"]: return {"bars": [], "ema": [], "levels": []}
    ci = cur_idx(); a = int(IDX.searchsorted(pd.Timestamp(ST["day"]) - pd.Timedelta(days=HIST_DAYS[tf])))
    sub = DF.iloc[a:ci + 1]                                           # NOTHING after the cursor
    if tf > 1:
        sub = sub.resample("%dmin" % tf, label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna(subset=["open"])
    ema = sub.close.ewm(span=12, adjust=False).mean().to_numpy()
    ep = sub.index.values.astype("datetime64[s]").astype(np.int64)
    m = ep >= int(since) if since else np.ones(len(ep), bool)
    b = [{"time": int(t), "open": float(o), "high": float(h), "low": float(l), "close": float(c)}
         for t, o, h, l, c in zip(ep[m], sub.open.to_numpy()[m], sub.high.to_numpy()[m], sub.low.to_numpy()[m], sub.close.to_numpy()[m])]
    e = [{"time": int(t), "value": round(float(v), 3)} for t, v in zip(ep[m], ema[m])]
    out = {"bars": b, "ema": e}
    if not since: out["levels"] = levels()
    return out


def levels():
    D = pd.Timestamp(ST["day"]); cur = IDX[cur_idx()]; out = []
    asia = DF.loc[D:min(cur, D + pd.Timedelta(hours=6, minutes=59))]
    if len(asia):
        out += [{"price": float(asia.high.max()), "title": "Asia H", "color": "#ff9800"}, {"price": float(asia.low.min()), "title": "Asia L", "color": "#ff9800"}]
    k = int(IDX.searchsorted(D)) - 1
    if k >= 0:
        pdate = IDX[k].normalize(); prev = DF.loc[pdate:D - pd.Timedelta(minutes=1)]
        out += [{"price": float(prev.high.max()), "title": "PDH", "color": "#ab47bc"}, {"price": float(prev.low.min()), "title": "PDL", "color": "#ab47bc"}]
    return out


def summary(path, kind):
    R = [float(r["R"]) for r in rows(path) if r.get("R")]
    return {"n": len(R), "wins": sum(1 for x in R if x > 0), "sumR": round(sum(R), 2), "meanR": round(sum(R) / len(R), 3) if R else None, "kind": kind}


def state():
    s = json.loads(json.dumps(ST))
    if ST["cursor"]:
        ci = cur_idx(); c = IDX[ci]
        s.update(cursor_hm=c.strftime("%H:%M"), cursor_epoch=int(EPOCH[ci]), last_close=float(C[ci]), contract=contract(DF.symbol.iloc[ci], c),
                 day_label=pd.Timestamp(ST["day"]).strftime("%a %d %b %Y"))
    s["in_window"] = in_window()
    s["pace"] = {"min": PACE_SECONDS, "left": round(pace_left(), 1)} if ST["phase"] in ("bias", "open") and ST.get("mode") == "registered" else None
    if ST["cursor"]:
        nz = noise(); s["v2"] = {"noise": round(nz, 3), "min_stop": round(V2_MIN_STOP * nz, 2), "rr": V2_RR, "chase": round(chase_moves(cur_idx()), 2),
                                 "chase_limit": V2_CHASE, "window_lock": ST["phase"] == "open" and 7 * 60 + 59 <= hm(IDX[cur_idx()]) <= 8 * 60 + 13}
    done = {r["date"] for r in rows(LOG)}; prog = []
    for name, path in WINDOWS:
        ds = [r["date"] for r in rows(path)]; prog.append({"window": name, "done": sum(1 for d in ds if d in done), "total": len(ds)})
    s["progress"] = prog; s["next_registered"] = next_registered()[1]
    s["registered_summary"] = summary(RES, "futures"); s["practice_summary"] = summary(PLOG, "practice")
    s["recent"] = [{"date": r["date"], "side": r["side"], "R": r["R"], "outcome": r["outcome"]} for r in rows(RES)[-8:]]
    if ST["phase"] in ("bias", "open") and s.get("trade"): s["trade"] = None
    return s


# ---------------------------------------------------------------- http
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        try:
            if u.path in ("/", "/index.html"):
                with open(os.path.join(HERE, "index.html"), "rb") as f: return self.send(200, f.read(), "text/html; charset=utf-8")
            if u.path == "/lwc.js":
                with open(os.path.join(HERE, "lwc.js"), "rb") as f: return self.send(200, f.read(), "application/javascript")
            with LOCK:
                if u.path == "/api/state": return self.send(200, state())
                if u.path == "/api/bars":
                    tf = int(q.get("tf", ["1"])[0])
                    if tf not in HIST_DAYS: raise ApiError("tf must be 1, 5, 15 or 60")
                    return self.send(200, bars(tf, q.get("since", [None])[0]))
            self.send(404, {"error": "not found"})
        except ApiError as e:
            self.send(400, {"error": str(e)})
        except Exception as e:
            self.send(500, {"error": "server error: %r" % e})

    def do_POST(self):
        u = urlparse(self.path)
        try:
            n = int(self.headers.get("Content-Length") or 0); body = json.loads(self.rfile.read(n) or b"{}")
            with LOCK:
                if u.path == "/api/start": start(body.get("mode"))
                elif u.path == "/api/bias": set_bias(body.get("bias"), body.get("recognised"))
                elif u.path == "/api/step": step(body.get("n", 1), bool(body.get("until_close")))
                elif u.path == "/api/trade": place(body.get("side"), body.get("stop"), body.get("target"))
                elif u.path == "/api/notrade":
                    if ST["phase"] != "open": raise ApiError("no-trade is declared while the day is open")
                    need_pace("no trade")
                    log_notrade("no setup (the trader)"); save()
                elif u.path == "/api/reveal": reveal()
                elif u.path == "/api/skip": skip_practice()
                else: return self.send(404, {"error": "not found"})
                return self.send(200, state())
        except ApiError as e:
            self.send(400, {"error": str(e)})
        except Exception as e:
            self.send(500, {"error": "server error: %r" % e})


if __name__ == "__main__":
    print("MGC blind replay on http://127.0.0.1:%d" % PORT, flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
