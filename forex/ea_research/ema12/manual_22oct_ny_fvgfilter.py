"""Hindsight replay of the 22 Oct NY window (entry 14:30:00-14:45:59 local) on the trader's OANDA bid chart WITH the extra filter 'no entry inside a 1-minute FVG'. Read-only.
Entry = open of the candle after the setup candle (no call delay) +0.55 spread for a long (ask), bid for a short. Setup = the demo rules (cross of EMA12, body > bigger wick, body >= 1 ATR14).
Card target = nearest level >= 1 ATR beyond the entry: near edge of a gap in the trade direction that is OPEN, or a swing high/low (2 bars each side, closed bars) not yet exceeded. Stop = 2 x target distance, S1 TP = stop distance.
'Inside' definitions: A = entry within a gap that is still OPEN (not fully traded through by closed candles up to the entry); B = within a gap never touched since it formed; C = within ANY gap formed in the last 60 closed candles, filled or not."""
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

import csv
with open("MANUAL_22OCT_NY_BARS.csv", "w", newline="") as f:   # the bars this run used (OANDA:XAUUSD 1m bid, epoch UTC), so the numbers can be re-checked without the chart
    w = csv.writer(f); w.writerow(["time_utc", "open", "high", "low", "close"]); w.writerows(B)
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

rows = []
for j in range(len(B)):
    lab = dt.datetime.fromtimestamp(T[j], LIS)
    if not (lab.hour == 14 and 29 <= lab.minute <= 44): continue
    body = C[j] - O[j]; upw = H[j] - max(O[j], C[j]); lwr = min(O[j], C[j]) - L[j]
    cross = (O[j] < EMA[j] < C[j]) or (O[j] > EMA[j] > C[j])
    setup = cross and abs(body) > max(upw, lwr) and abs(body) >= ATR[j]
    print("%s candle: o %.3f c %.3f ema %.3f body/atr %.2f cross %s -> %s" % (hm(T[j]), O[j], C[j], EMA[j], abs(body) / ATR[j], cross, "SETUP" if setup else "no"))
    if not setup: continue
    side = "L" if body > 0 else "S"; e = j + 1
    entry = O[e] + (SPR if side == "L" else 0.0)
    insd = {d: inside(j, entry, d) for d in "ABC"}
    cd = card(j, side, entry)
    print("   %s at the %s open: entry %.3f; inside an FVG: A(open) %s | B(untouched) %s | C(any, 60 bars) %s" % (
        "LONG" if side == "L" else "SHORT", hm(T[e]), entry, "YES " + str(insd["A"]) if insd["A"] else "no", "YES " + str(insd["B"]) if insd["B"] else "no", ("YES %d gaps" % len(insd["C"])) if insd["C"] else "no"))
    if cd:
        dist, name, lv = cd; stop = 2 * dist; sl = entry - stop if side == "L" else entry + stop; tp = entry + stop if side == "L" else entry - stop
        lots = BUDGET / (stop * 100)
        res, tt = outcome(j, side, entry, sl, tp)
        print("   card target: %s at %.3f (%.2f pts) -> stop %.2f pts (SL %.3f), S1 TP %.3f, lots %.2f (min of 3.1) | hindsight: %s %s" % (name, lv, dist, stop, sl, tp, min(lots, 3.1), res, hm(tt) if tt else ""))
    else:
        print("   no level >= 1 ATR beyond the entry that is still standing -> the card gives no target")

print()
print("Which gaps sit behind the 'inside' readings (A = gap still open, B = never touched, C = any gap of the last 60 candles):")
idx = {hm(t): i for i, t in enumerate(T)}
for lab, j, price in (("long entry, 14:31 open + spread", idx["14:30"], O[idx["14:30"] + 1] + SPR), ("short entry, 14:32 open", idx["14:31"], O[idx["14:31"] + 1]), ("the DEMO entry 4074.73 at 14:32:56 (closed candles to 14:31)", idx["14:31"], 4074.73)):
    print(lab, "%.3f" % price)
    for d in "ABC": print("  ", d, inside(j, price, d))
n = 0; cnt = {"A": 0, "B": 0, "C": 0}
for j in range(80, len(B) - 2):
    n += 1
    for d in "ABC":
        if inside(j, O[j + 1], d): cnt[d] += 1
print("share of candle opens that sit inside a 1m FVG, %d opens over the loaded history:" % n, {d: "%.0f%%" % (100 * cnt[d] / n) for d in cnt})
