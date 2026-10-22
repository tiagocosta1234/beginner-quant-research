"""the trader 22 Oct 14:5x: "the close cant be inside an unfilled gap". Tests the CLOSE of each valid NY setup candle (14:30 long, 14:31 short) of the 22 Oct window against 1-minute FVGs under four ways of saying "unfilled":
wick-before (no wick fully traded through the gap before the candle), wick-incl (same, counting the setup candle's own wick), close-based (no candle up to and including the setup candle closed beyond the far edge), never-touched-before.
Hindsight, read-only, OANDA bid chart (needs TradingView on CDP 9333; the bars it used are saved to MANUAL_22OCT_NY_BARS.csv by manual_22oct_ny_fvgfilter.py)."""

import json, urllib.request, websocket, datetime as dt
from zoneinfo import ZoneInfo
LIS = ZoneInfo("Europe/London"); SPR = 0.55; BUDGET = 832.0
def page():
    for t in json.load(urllib.request.urlopen("http://localhost:9333/json")):
        if t.get("type") == "page" and "tradingview.com/chart" in t.get("url", ""): return t["webSocketDebuggerUrl"]
ws = websocket.create_connection(page(), timeout=15, suppress_origin=True)
JS = """(function(){var b=window.TradingViewApi._activeChartWidgetWV.value()._chartWidget.model().mainSeries().bars();var r=[];var e=b.lastIndex();var s=Math.max(b.firstIndex(),e-500);for(var i=s;i<=e;i++){var v=b.valueAt(i);if(v)r.push([v[0],v[1],v[2],v[3],v[4]]);}return r;})()"""
ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": JS, "returnByValue": True}}))
while True:
    m = json.loads(ws.recv())
    if m.get("id") == 1: B = m["result"]["result"]["value"]; break

T = [x[0] for x in B]; O = [x[1] for x in B]; H = [x[2] for x in B]; L = [x[3] for x in B]; C = [x[4] for x in B]
hm = lambda ts: dt.datetime.fromtimestamp(ts, LIS).strftime("%H:%M")
a = 2 / 13; EMA = []
for i, x in enumerate(C): EMA.append(x if i == 0 else a * x + (1 - a) * EMA[-1])
TR = [H[i] - L[i] if i == 0 else max(H[i] - L[i], abs(H[i] - C[i-1]), abs(L[i] - C[i-1])) for i in range(len(B))]
ATR = [sum(TR[max(0, i-13):i+1]) / len(TR[max(0, i-13):i+1]) for i in range(len(B))]

def gaps_at(j):
    """FVGs formed by closed candles <= index j: (kind, lo, hi, formed_idx, fully_filled_by_j, touched_by_j)."""
    out = []
    for k in range(2, j + 1):
        g = None
        if L[k] > H[k-2]: g = ("bull", H[k-2], L[k])
        elif H[k] < L[k-2]: g = ("bear", H[k], L[k-2])
        if not g: continue
        kind, lo, hi = g
        later = range(k + 1, j + 1)
        full = any((L[x] <= lo) if kind == "bull" else (H[x] >= hi) for x in later)
        touched = any((L[x] <= hi) if kind == "bull" else (H[x] >= lo) for x in later)
        out.append((kind, lo, hi, k, full, touched))
    return out

def inside(j, price, d):
    res = []
    for kind, lo, hi, k, full, touched in gaps_at(j):
        if not (lo <= price <= hi): continue
        if d == "A" and not full: res.append((kind, lo, hi, hm(T[k-2]) + "-" + hm(T[k])))
        if d == "B" and not touched: res.append((kind, lo, hi, hm(T[k-2]) + "-" + hm(T[k])))
        if d == "C" and j - k <= 60: res.append((kind, lo, hi, hm(T[k-2]) + "-" + hm(T[k])))
    return res

def card(j, side, entry):
    atr = ATR[j]; cands = []
    for kind, lo, hi, k, full, touched in gaps_at(j):
        if full: continue
        if side == "L" and kind == "bear": cands.append(("bear FVG near edge %s-%s" % (hm(T[k-2]), hm(T[k])), lo))
        if side == "S" and kind == "bull": cands.append(("bull FVG near edge %s-%s" % (hm(T[k-2]), hm(T[k])), hi))
    for k in range(max(2, j - 60), j - 1):
        if side == "L" and H[k] == max(H[k-2:k+3]) and max(H[k+1:j+1]) < H[k]: cands.append(("swing high %s" % hm(T[k]), H[k]))
        if side == "S" and L[k] == min(L[k-2:k+3]) and min(L[k+1:j+1]) > L[k]: cands.append(("swing low %s" % hm(T[k]), L[k]))
    ok = sorted(((abs(lv - entry), n, lv) for n, lv in cands if ((lv - entry) if side == "L" else (entry - lv)) >= atr))
    return ok[0] if ok else None

def outcome(j, side, entry, sl, tp):
    for x in range(j + 1, len(B)):   # j+1 = the entry candle: its low/high before the fill are unknown, so start checking from it anyway (conservative-neutral)
        if side == "L":
            if L[x] <= sl: return "STOP", T[x]
            if H[x] >= tp: return "TARGET", T[x]
        else:
            if H[x] + SPR >= sl: return "STOP", T[x]
            if L[x] + SPR <= tp: return "TARGET", T[x]
    return "open", None


idx = {hm(t): i for i, t in enumerate(T)}
def gaps(j):
    out = []
    for k in range(2, j + 1):
        if L[k] > H[k-2]: out.append(("bull", H[k-2], L[k], k))
        elif H[k] < L[k-2]: out.append(("bear", H[k], L[k-2], k))
    return out
def status(kind, lo, hi, k, j):
    bef = range(k + 1, j); inc = range(k + 1, j + 1)
    wick = lambda r: any((L[x] <= lo) if kind == "bull" else (H[x] >= hi) for x in r)
    clos = any((C[x] < lo) if kind == "bull" else (C[x] > hi) for x in inc)
    touch = any((L[x] <= hi) if kind == "bull" else (H[x] >= lo) for x in bef)
    return wick(bef), wick(inc), clos, touch
for lab in ("14:30", "14:31"):
    j = idx[lab]; c = C[j]
    print("%s candle (%s) close %.3f" % (lab, "long" if C[j] > O[j] else "short", c))
    hit = [(kd, lo, hi, k) for kd, lo, hi, k in gaps(j) if lo <= c <= hi]
    if not hit: print("   close is inside no 1m gap"); continue
    for kd, lo, hi, k in hit:
        wb, wi, cl, tb = status(kd, lo, hi, k, j)
        print("   %s gap %s-%s %.3f..%.3f | UNFILLED under: wick-before %s, wick-incl %s, close-based %s, never-touched-before %s" % (kd, hm(T[k-2]), hm(T[k]), lo, hi, not wb, not wi, not cl, not tb))
