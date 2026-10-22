"""the trader 22 Oct 14:5x: "even if the gap is mitigated you cant use a close that's still on the rest of the area that hasnt been touched". A 1-minute FVG is consumed by price from the side it is approached;
what no wick has traded into since the gap formed is its UNTOUCHED remainder (gap interval minus the union of the high-low ranges of the candles after its 3rd candle and BEFORE the setup candle).
Rule tested: the CLOSE of the setup candle must not lie inside the untouched remainder of any gap. Hindsight, read-only, OANDA bid chart (needs TradingView on CDP 9333).
Caveat: only gaps inside the loaded bars are seen (the span is printed first; the chart was scrolled back so that about 2,250 one-minute bars were loaded)."""


import json, urllib.request, websocket, datetime as dt
from zoneinfo import ZoneInfo
LIS = ZoneInfo("Europe/London"); SPR = 0.55; BUDGET = 832.0
def page():
    for t in json.load(urllib.request.urlopen("http://localhost:9333/json")):
        if t.get("type") == "page" and "tradingview.com/chart" in t.get("url", ""): return t["webSocketDebuggerUrl"]
ws = websocket.create_connection(page(), timeout=15, suppress_origin=True)
JS = """(function(){var b=window.TradingViewApi._activeChartWidgetWV.value()._chartWidget.model().mainSeries().bars();var r=[];var e=b.lastIndex();var s=Math.max(b.firstIndex(),e-3000);for(var i=s;i<=e;i++){var v=b.valueAt(i);if(v)r.push([v[0],v[1],v[2],v[3],v[4]]);}return r;})()"""
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
print("bars loaded: %d, from %s to %s (local)" % (len(B), dt.datetime.fromtimestamp(T[0], LIS).strftime("%a %d %b %H:%M"), hm(T[-1])))
def remainder(lo, hi, rng):
    """gap interval [lo, hi] minus the union of the candle ranges in rng (list of (low, high)); returns the untouched sub-intervals."""
    parts = [(lo, hi)]
    for l, h in rng:
        nxt = []
        for a, b in parts:
            if h < a or l > b: nxt.append((a, b)); continue
            if l > a: nxt.append((a, l))
            if h < b: nxt.append((h, b))
        parts = nxt
    return [(a, b) for a, b in parts if b - a > 1e-9]
def gaps(j):
    out = []
    for k in range(2, j + 1):
        if L[k] > H[k-2]: out.append(("bull", H[k-2], L[k], k))
        elif H[k] < L[k-2]: out.append(("bear", H[k], L[k-2], k))
    return out
def bad_close(j):
    """gaps whose untouched remainder (touched by candles k+1..j-1 only) contains the close of candle j"""
    res = []
    for kd, lo, hi, k in gaps(j):
        rem = remainder(lo, hi, [(L[x], H[x]) for x in range(k + 1, j)])
        if any(a <= C[j] <= b for a, b in rem): res.append((kd, hm(T[k-2]) + "-" + hm(T[k]), lo, hi, rem))
    return res
for lab in ("14:30", "14:31"):
    j = idx[lab]
    print("%s candle (%s) close %.3f" % (lab, "long" if C[j] > O[j] else "short", C[j]))
    inside = [(kd, lo, hi, k) for kd, lo, hi, k in gaps(j) if lo <= C[j] <= hi]
    for kd, lo, hi, k in inside:
        rem = remainder(lo, hi, [(L[x], H[x]) for x in range(k + 1, j)])
        print("   in %s gap %s-%s %.3f..%.3f | untouched before the candle: %s" % (kd, hm(T[k-2]), hm(T[k]), lo, hi, ["%.3f..%.3f" % r for r in rem] or "nothing (fully touched)"))
    bc = bad_close(j)
    print("   -> close inside an untouched remainder: %s" % ("YES " + str([(b[0], b[1]) for b in bc]) if bc else "no, the setup passes"))
n = bad = 0
for j in range(80, len(B)):
    n += 1; bad += 1 if bad_close(j) else 0
print("share of candle closes on the loaded chart that sit in an untouched gap remainder: %d of %d (%.0f%%)" % (bad, n, 100 * bad / n))
