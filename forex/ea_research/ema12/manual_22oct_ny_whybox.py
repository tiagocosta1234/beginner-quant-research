"""the trader 22 Oct ~15:30: "can you understand the setup i draw, why i would have taken it? this is literally one of the best 12 ema setups".
Reads the 1m bars (with tick volume) of his OANDA:XAUUSD chart and tests what makes the 14:31 displacement + 14:32 continuation short stand out: size of the displacement candle against the last 120 candles, its tick volume,
the EMA 12 against the bearish gap the move leaves (14:30-14:32 candles), how deep the 14:32 pullback was, and whether price ever came back to the EMA / gap after his entry. Hindsight, read-only (TradingView on CDP 9333)."""
import json, urllib.request, websocket, datetime as dt
from zoneinfo import ZoneInfo
LIS = ZoneInfo("Europe/London")


def page():
    for t in json.load(urllib.request.urlopen("http://localhost:9333/json")):
        if t.get("type") == "page" and "tradingview.com/chart" in t.get("url", ""): return t["webSocketDebuggerUrl"]


ws = websocket.create_connection(page(), timeout=15, suppress_origin=True)
JS = """(function(){var b=window.TradingViewApi._activeChartWidgetWV.value()._chartWidget.model().mainSeries().bars();var r=[];var e=b.lastIndex();var s=Math.max(b.firstIndex(),e-3000);for(var i=s;i<=e;i++){var v=b.valueAt(i);if(v)r.push([v[0],v[1],v[2],v[3],v[4],v[5]||0]);}return r;})()"""
ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": JS, "returnByValue": True}}))
while True:
    m = json.loads(ws.recv())
    if m.get("id") == 1: B = m["result"]["result"]["value"]; break
T = [x[0] for x in B]; O = [x[1] for x in B]; H = [x[2] for x in B]; L = [x[3] for x in B]; C = [x[4] for x in B]; V = [x[5] for x in B]
hm = lambda ts: dt.datetime.fromtimestamp(ts, LIS).strftime("%H:%M")
a = 2 / 13; EMA = []
for i, x in enumerate(C): EMA.append(x if i == 0 else a * x + (1 - a) * EMA[-1])
TR = [H[i] - L[i] if i == 0 else max(H[i] - L[i], abs(H[i] - C[i-1]), abs(L[i] - C[i-1])) for i in range(len(B))]
ATR = [sum(TR[max(0, i-13):i+1]) / len(TR[max(0, i-13):i+1]) for i in range(len(B))]
idx = {hm(t): i for i, t in enumerate(T)}
print("bars loaded: %d, from %s to %s (local)" % (len(B), dt.datetime.fromtimestamp(T[0], LIS).strftime("%a %d %b %H:%M"), hm(T[-1])))
print()
print("time   open      close     EMA12     vs EMA        body/ATR  tick vol")
for k in range(idx["14:20"], idx["14:38"] + 1):
    print("%s  %.3f  %.3f  %.3f  %+6.2f (close)  %5.2f    %d" % (hm(T[k]), O[k], C[k], EMA[k], C[k] - EMA[k], abs(C[k] - O[k]) / ATR[k], V[k]))
j31, j32, j30 = idx["14:31"], idx["14:32"], idx["14:30"]
look = range(j31 - 120, j31)
bodies = sorted((abs(C[k] - O[k]) for k in look), reverse=True)
vols = sorted((V[k] for k in look), reverse=True)
print()
print("-- the 14:31 displacement candle against the 120 candles before it:")
print("   body %.3f pts: rank %d of 121 by body size (the largest before it was %.3f); tick volume %d: rank %d of 121 (median before it %d)" % (
    abs(C[j31] - O[j31]), 1 + sum(1 for b in bodies if b > abs(C[j31] - O[j31])), bodies[0], V[j31], 1 + sum(1 for v in vols if v > V[j31]), sorted(vols)[len(vols) // 2]))
print("   the 14:30 white candle: body %.3f pts rank %d, tick volume %d rank %d" % (abs(C[j30] - O[j30]), 1 + sum(1 for b in bodies if b > abs(C[j30] - O[j30])), V[j30], 1 + sum(1 for v in vols if v > V[j30])))
gap_lo, gap_hi = H[j32], L[j30]
print()
print("-- the bearish gap the displacement leaves (14:30-14:32 candles): %.3f..%.3f (%.2f pts); EMA12 at the 14:32 close %.3f is %s the gap; the 14:32 high %.3f is the gap's bottom edge" % (
    gap_lo, gap_hi, gap_hi - gap_lo, EMA[j32], "INSIDE" if gap_lo <= EMA[j32] <= gap_hi else "outside", H[j32]))
body31 = O[j31] - C[j31]
print("-- the 14:32 pullback retraced %.0f%% of the 14:31 body (high %.3f against the 14:31 close %.3f and open %.3f); the 14:32 candle closed at %.0f%% of its range" % (
    100 * (H[j32] - C[j31]) / body31, H[j32], C[j31], O[j31], 100 * (C[j32] - L[j32]) / (H[j32] - L[j32])))
after = range(idx["14:33"], len(B))
print("-- after the 14:32 close (entry 4073.555): highest high %.3f at %s (EMA 12 then %.3f); first candle with a high >= the gap bottom %.3f: %s; first candle with a high >= the EMA of that moment: %s" % (
    max(H[k] for k in after), hm(T[max(after, key=lambda k: H[k])]), EMA[max(after, key=lambda k: H[k])], gap_lo,
    next((hm(T[k]) for k in after if H[k] >= gap_lo), "none"), next((hm(T[k]) + " (high %.3f, EMA %.3f)" % (H[k], EMA[k]) for k in after if H[k] >= EMA[k]), "none")))
print("-- lowest low after the entry: %.3f at %s (target 4062.906)" % (min(L[k] for k in after), hm(T[min(after, key=lambda k: L[k])])))
print("-- the day so far: high %.3f at %s; swing highs of the last two hours (13:48 4091.84, 14:17 4080.80, 14:30 4080.82) are lower highs: %s" % (
    max(H[idx["08:00"]:j32 + 1]) if "08:00" in idx else max(H), hm(T[max(range(idx.get("08:00", 0), j32 + 1), key=lambda k: H[k])]), "yes" if H[j30] < H[idx["13:48"]] else "no"))
