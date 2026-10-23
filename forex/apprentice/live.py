"""Live London window for the apprentice (paper only; the trader 22 Oct 2026: "then we'll trade tomorro's london session"). Reads the 1-minute bars of the chart open in
TradingView Desktop (CDP port 9333, read-only) every few seconds, and for each candle that closes between 07:59 and 08:14 local applies the same card,
rubric and S1 bracket as desk.py (setup_at). Prints every cross; on the first card-valid A / B setup it prints the call (entry at the next open, S1 stop and
target in chart prices), appends it to LIVE_LOG.csv with the PC time before any outcome is known, and exits, so a background run wakes Claude. Exits with
"no setup" after the 08:14 candle closes. Volume is the chart's (tick volume on OANDA:XAUUSD). Nothing here places an order.
Usage: python forex/apprentice/live.py              live (run from ~07:55 local)
       python forex/apprentice/live.py --replay      the same logic on today's 07:59-08:14 candles already on the chart (a test)"""
import sys, os, json, time, datetime as dt, urllib.request
import numpy as np, pandas as pd
from zoneinfo import ZoneInfo
import desk as D

LIS = ZoneInfo("Europe/London"); LOG = os.path.join(D.HERE, "LIVE_LOG.csv")
JS = ("(function(){var w=window.TradingViewApi._activeChartWidgetWV.value();var m=w._chartWidget.model();var b=m.mainSeries().bars();var r=[];"
      "var e=b.lastIndex();var s=Math.max(b.firstIndex(),e-1500);for(var i=s;i<=e;i++){var v=b.valueAt(i);if(v)r.push([v[0],v[1],v[2],v[3],v[4],v[5]||0]);}"
      "return {sym:w.symbol(),res:w.resolution(),bars:r};})()")


def fetch():
    import websocket
    page = next(t["webSocketDebuggerUrl"] for t in json.load(urllib.request.urlopen("http://localhost:9333/json"))
                if t.get("type") == "page" and "tradingview.com/chart" in t.get("url", ""))
    ws = websocket.create_connection(page, timeout=15, suppress_origin=True)
    ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": JS, "returnByValue": True}}))
    while True:
        m = json.loads(ws.recv())
        if m.get("id") == 1: ws.close(); return m["result"]["result"]["value"]


def frame(bars, day):
    x = pd.DataFrame(bars, columns=["t", "mo", "mh", "ml", "mc", "v"])
    x["lis"] = pd.to_datetime(x["t"], unit="s", utc=True).dt.tz_convert(LIS).dt.tz_localize(None)
    x["ema"] = x["mc"].ewm(span=12, adjust=False).mean()
    tr = np.maximum(x["mh"] - x["ml"], np.maximum((x["mh"] - x["mc"].shift()).abs(), (x["ml"] - x["mc"].shift()).abs()))
    x["atr"] = tr.rolling(14).mean().shift(1); x["vmed"] = x["v"].rolling(60).median().shift(1)
    x["lis"] = x["lis"] - (pd.Timestamp(day) - pd.Timestamp("2000-01-03"))      # desk.py works on a 3 Jan 2000 clock
    return x[["lis", "mo", "mh", "ml", "mc", "v", "ema", "atr", "vmed"]].reset_index(drop=True)


def main(replay):
    day = dt.datetime.now(LIS).date(); seen = set(); day0 = pd.Timestamp("2000-01-03")
    while True:
        got = fetch(); now = dt.datetime.now(LIS).replace(tzinfo=None)
        if got["res"] not in ("1", "1m"): print("chart resolution is %s, switch it to 1 minute" % got["res"])
        y = frame(got["bars"], day); i6 = int(np.argmax(y["lis"] >= day0 + pd.Timedelta(hours=6)))
        for m in range(7 * 60 + 59, 8 * 60 + 15):
            ts = day0 + pd.Timedelta(minutes=m)
            closed = replay or (pd.Timestamp(day) + pd.Timedelta(minutes=m + 1) <= pd.Timestamp(now))
            hit = np.where(y["lis"] == ts)[0]
            if m in seen or not closed or not len(hit): continue
            seen.add(m); s = D.setup_at(y, int(hit[0]), i6)
            if s is None: continue
            if not s["valid"]:
                print("%s %s cross fails: %s" % (s["time"], s["side"], ", ".join([k for k, v in s["card"].items() if not v] + ([] if s["s1"] else ["no S1 level"])))); continue
            line = "%s %s grade %s | rubric %s | S1 T %.2f (%s) stop %.2f target %.2f" % (s["time"], "LONG" if s["side"] == "L" else "SHORT", s["grade"],
                   ", ".join("%s %s" % (k, "Y" if v else "n") for k, v in s["rubric"].items()), s["s1"]["T"], s["s1"]["what"], s["s1"]["stop"], s["s1"]["target"])
            print(line)
            if s["grade"] in ("A", "B"):
                pd.DataFrame([{"date": str(day), "symbol": got["sym"], "time": s["time"], "side": s["side"], "grade": s["grade"], "stop": s["s1"]["stop"],
                               "target": s["s1"]["target"], "pc_time": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "replay": replay}]).to_csv(LOG, mode="a", header=not os.path.exists(LOG), index=False)
                print("CALL (paper): %s %s at the next open, stop %.2f, target %.2f, one trade, bracket attached" % ("BUY" if s["side"] == "L" else "SELL", got["sym"], s["s1"]["stop"], s["s1"]["target"]))
                return
        if replay or now >= pd.Timestamp(day).to_pydatetime().replace(hour=8, minute=15, second=5): print("no A / B setup in 07:59-08:14"); return
        time.sleep(3)


if __name__ == "__main__":
    main("--replay" in sys.argv)
