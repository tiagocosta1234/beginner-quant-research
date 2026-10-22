"""the trader 22 Oct ~15:15, after the 'final setup' replay: "that white candle isnt strong, big wick above the close, analyze the box i just draw now and understand the confluences".
His box on his OANDA:XAUUSD 1m chart (read from the chart, hard-coded below): short_position KSGE3H at 14:32 (the 14:32 candle's close) price 4073.555, stop and target 10.649 pts each side (1:1); rectangle HlLN0j 13:02-14:41, 4061.790-4062.915.
Checks each confluence against the bars (hindsight, read-only; needs TradingView on CDP 9333 scrolled back so the series holds about 2,300 one-minute bars)."""
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
idx = {hm(t): i for i, t in enumerate(T)}
print("bars loaded: %d, from %s to %s (local)" % (len(B), dt.datetime.fromtimestamp(T[0], LIS).strftime("%a %d %b %H:%M"), hm(T[-1])))
E, D = 4073.555, 10.649; SL, TP = E + D, E - D
print("BOX: short entry %.3f (14:32 close), SL %.3f, TP %.3f (%.3f pts each side); rectangle 4061.790..4062.915" % (E, SL, TP, D))


def candle(lab):
    j = idx[lab]; rng = H[j] - L[j]; body = C[j] - O[j]; up = H[j] - max(O[j], C[j])
    print("%s o %.3f h %.3f l %.3f c %.3f | body %+.3f = %.2f ATR | upper wick %.3f (%.0f%% of the body, %.0f%% of the range), lower wick %.3f | close at %.0f%% of the range | EMA12 %.3f ATR14 %.2f" % (
        lab, O[j], H[j], L[j], C[j], body, abs(body) / ATR[j], up, 100 * up / abs(body), 100 * up / rng, min(O[j], C[j]) - L[j], 100 * (C[j] - L[j]) / rng, EMA[j], ATR[j]))


print()
print("-- the three candles"); candle("14:30"); candle("14:31"); candle("14:32")
j30 = idx["14:30"]
print()
print("-- highs within 0.5 pts of the 14:30 high %.3f in the 90 candles before it:" % H[j30], [(hm(T[k]), H[k]) for k in range(j30 - 90, j30) if abs(H[k] - H[j30]) <= 0.5])
print("   highest high of the 90 candles before 14:30: %s %.3f; SL %.3f is %.2f pts above the 14:30 high" % (hm(T[max(range(j30 - 90, j30), key=lambda k: H[k])]), max(H[j30 - 90:j30]), SL, SL - H[j30]))
j = idx["14:32"]


def remainder(lo, hi, rng):
    """gap interval [lo, hi] minus the union of the candle ranges (low, high) in rng."""
    parts = [(lo, hi)]
    for l, h in rng:
        nxt = []
        for p, q in parts:
            if h < p or l > q: nxt.append((p, q)); continue
            if l > p: nxt.append((p, l))
            if h < q: nxt.append((h, q))
        parts = nxt
    return [(p, q) for p, q in parts if q - p > 1e-9]


print()
print("-- untouched remainders of 1m gaps below the entry as of the 14:32 close (nearest first):")
below = []
for k in range(2, j + 1):
    g = ("bull", H[k-2], L[k]) if L[k] > H[k-2] else (("bear", H[k], L[k-2]) if H[k] < L[k-2] else None)
    if not g: continue
    kd, lo, hi = g
    for p, q in remainder(lo, hi, [(L[x], H[x]) for x in range(k + 1, j + 1)]):
        if q < E: below.append((E - q, kd, hm(T[k-2]) + "-" + hm(T[k]), p, q))
for d, kd, nm, p, q in sorted(below)[:5]:
    print("   %s gap %s untouched %.3f..%.3f: its top edge is %.2f pts below the entry (%.2f ATR)" % (kd, nm, p, q, d, d / ATR[j]))
rem = remainder(4073.655, 4076.035, [(L[x], H[x]) for x in range(idx["13:37"] + 1, idx["14:31"])])
c31, c32 = C[idx["14:31"]], C[idx["14:32"]]
print()
print("-- the 13:35-13:37 bullish gap: untouched part before the 14:31 candle %s; 14:31 close %.3f inside it: %s; 14:32 close %.3f inside it: %s" % (
    ["%.3f..%.3f" % r for r in rem], c31, any(p <= c31 <= q for p, q in rem), c32, any(p <= c32 <= q for p, q in rem)))
print()
print("-- hindsight outcomes of the short from %.3f (a short exits at the ask = bid + %.2f; entry candle 14:33; risk budget USD %d):" % (E, SPR, BUDGET))


def run(sl, tp):
    for x in range(idx["14:33"], len(B)):
        if H[x] + SPR >= sl: return "STOP in the %s candle" % hm(T[x])
        if L[x] + SPR <= tp: return "TARGET in the %s candle" % hm(T[x])
    return "still open at %s" % hm(T[-1])


dc = 2 * D
for name, sl, tp, rr in (("as drawn (stop = target distance)", SL, TP, 1.0), ("rules card (stop twice the target distance, 0.5 R)", E + dc, TP, 0.5), ("S1 (card stop, 1.0 R target)", E + dc, E - dc, 1.0)):
    stop = sl - E; lots = BUDGET / (stop * 100)
    print("   %s: SL %.3f TP %.3f, lots %.2f -> %s (about %+.0f USD at the target)" % (name, sl, tp, min(lots, 3.1), run(sl, tp), rr * BUDGET))
