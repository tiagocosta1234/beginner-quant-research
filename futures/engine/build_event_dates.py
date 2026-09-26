"""
Builds data/events/treasury_coupon_auctions.csv: every auction (new issues and
reopenings) of nominal Treasury notes/bonds with >= 4 years to maturity, 2000-2026,
from the TreasuryDirect securities API; TIPS and floating-rate notes excluded.

Builds data/events/fomc_statement_dates.csv: the day each SCHEDULED FOMC meeting
ended (the statement day), 2000-2026, from federalreserve.gov (the current
calendar page for 2021+, fomchistorical{year}.htm before that). Unscheduled
meetings, cancelled meetings, conference calls and notation votes are excluded.
"""
import os, re, sys, time, urllib.request
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "events", "fomc_statement_dates.csv")
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"], 1)}
ABBR = {m[:3]: i for m, i in MONTHS.items()}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")


def end_date(year, month_txt, days_txt):
    month_txt, days_txt = month_txt.strip(), days_txt.strip().rstrip("*").strip()
    months = [ABBR[m[:3]] for m in re.split(r"[/-]", month_txt)]
    last_day = int(re.findall(r"\d+", days_txt)[-1])
    return pd.Timestamp(year, months[-1], last_day)


def current_page():
    s = get("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
    out = []
    parts = re.split(r'<h4><a id="\d+">(\d{4}) FOMC Meetings</a></h4>', s)
    for year, blk in zip(parts[1::2], parts[2::2]):
        for row in re.findall(r'fomc-meeting__month[^>]*>\s*<strong>([^<]+)</strong>.*?fomc-meeting__date[^>]*>([^<]+)<', blk, re.S):
            if any(w in row[1].lower() for w in ("unscheduled", "notation", "cancel")):
                continue
            out.append(end_date(int(year), *row))
    return out


def historical(year):
    s = get(f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm")
    out = []
    for h in re.findall(r"<h5[^>]*>([^<]*Meeting[^<]*)</h5>", s):
        low = h.lower()
        if "unscheduled" in low or "conference call" in low or "notation" in low or "cancel" in low:
            continue
        head = h.replace("&nbsp;", " ").split("Meeting")[0]
        months = [ABBR[w[:3]] for w in re.findall(r"[A-Za-z]+", head) if w[:3] in ABBR]
        days = re.findall(r"\d+", head)
        if months and days:  # the statement comes on the meeting's last day
            out.append(pd.Timestamp(year, months[-1], int(days[-1])))
    return out


def dedupe(dates):
    """Two 'meetings' within 3 days (e.g. 2003-09-15/16) are one; keep the later."""
    out = []
    for d in sorted(set(dates)):
        if out and (d - out[-1]).days <= 3:
            out[-1] = d
        else:
            out.append(d)
    return out


def treasury_auctions(first=2000, last=2026):
    import json
    rows = []
    for kind in ["Note", "Bond"]:
        for y in range(first, last + 1):
            url = (f"https://www.treasurydirect.gov/TA_WS/securities/search?type={kind}&format=json"
                   f"&startDate=01/01/{y}&endDate=12/31/{y}")
            for x in json.loads(get(url)):
                years = int(re.match(r"(\d+)-Year", x["securityTerm"]).group(1)) if "-Year" in x["securityTerm"] else 0
                if x.get("tips") == "No" and x.get("floatingRate") == "No" and years >= 4 and x.get("auctionDate"):
                    rows.append((pd.Timestamp(x["auctionDate"][:10]), x["securityTerm"], x.get("reopening")))
            time.sleep(0.2)
    df = pd.DataFrame(rows, columns=["date", "term", "reopening"]).drop_duplicates().sort_values("date")
    df = df[(df["date"] >= f"{first}-01-01") & (df["date"] <= f"{last}-12-31")]
    df.to_csv(os.path.join(HERE, "..", "data", "events", "treasury_coupon_auctions.csv"), index=False)
    return df


if __name__ == "__main__" and "--treasury" in sys.argv:
    df = treasury_auctions()
    print(len(df), "auctions;", df.groupby(df["date"].dt.year).size().to_dict())
    raise SystemExit


if __name__ == "__main__":
    dates = current_page()
    for y in range(2000, 2021):
        if y not in {d.year for d in dates}:
            dates += historical(y)
            time.sleep(0.5)
    s = pd.Series(dedupe(dates), name="date")
    s = s[(s >= "2000-01-01") & (s <= "2026-12-31")]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    s.to_csv(OUT, index=False)
    print(s.groupby(s.dt.year).size().to_dict())
