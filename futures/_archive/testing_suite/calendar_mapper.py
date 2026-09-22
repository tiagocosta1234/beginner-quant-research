import datetime

start = datetime.date(2026, 8, 31)
end = datetime.date(2026, 12, 31)

holidays = {
    datetime.date(2026, 9, 7): "Labor Day (MARKET CLOSED)",
    datetime.date(2026, 11, 26): "Thanksgiving Day (MARKET CLOSED)",
    datetime.date(2026, 12, 25): "Christmas Day (MARKET CLOSED)",
}

half_days = {
    datetime.date(2026, 11, 27): "Black Friday (Early Close 13:00 EST)",
    datetime.date(2026, 12, 24): "Christmas Eve (Early Close 13:00 EST)",
    datetime.date(2026, 12, 31): "New Year's Eve (Holiday Liquidity Drain)",
}

bank_holidays = {
    datetime.date(2026, 10, 12): "Columbus Day (Bond Markets Closed, Equities Open, Low RVOL)",
    datetime.date(2026, 11, 11): "Veterans Day (Bond Markets Closed, Equities Open, Subdued Volume)",
}

fomc_days = {
    datetime.date(2026, 9, 16): "FOMC Rate Decision & Press Conf (14:00 EST)",
    datetime.date(2026, 11, 4): "FOMC Rate Decision & Press Conf (14:00 EST)",
    datetime.date(2026, 12, 16): "FOMC Rate Decision + Summary of Econ Projections (14:00 EST)",
}

nfp_days = {
    datetime.date(2026, 9, 4): "NFP Non-Farm Payrolls (08:30 EST)",
    datetime.date(2026, 10, 2): "NFP Non-Farm Payrolls (08:30 EST)",
    datetime.date(2026, 11, 6): "NFP Non-Farm Payrolls (08:30 EST)",
    datetime.date(2026, 12, 4): "NFP Non-Farm Payrolls (08:30 EST)",
}

cpi_days = {
    datetime.date(2026, 9, 11): "CPI Inflation Release (08:30 EST)",
    datetime.date(2026, 10, 14): "CPI Inflation Release (08:30 EST)",
    datetime.date(2026, 11, 12): "CPI Inflation Release (08:30 EST)",
    datetime.date(2026, 12, 10): "CPI Inflation Release (08:30 EST)",
}

total_trading_days = 0
weeks_summary = []

for w in range(1, 19):
    mon = start + datetime.timedelta(days=7 * (w - 1))
    fri = min(mon + datetime.timedelta(days=4), end)
    
    t_days = 0
    events = []
    curr = mon
    while curr <= fri:
        day_str = curr.strftime("%a %b %d")
        if curr in holidays:
            events.append(f"[{day_str}] {holidays[curr]}")
        else:
            t_days += 1
            if curr in half_days:
                events.append(f"[{day_str}] {half_days[curr]}")
            if curr in bank_holidays:
                events.append(f"[{day_str}] {bank_holidays[curr]}")
            if curr in fomc_days:
                events.append(f"[{day_str}] {fomc_days[curr]}")
            if curr in nfp_days:
                events.append(f"[{day_str}] {nfp_days[curr]}")
            if curr in cpi_days:
                events.append(f"[{day_str}] {cpi_days[curr]}")
        curr += datetime.timedelta(days=1)
    
    total_trading_days += t_days
    ev_str = " | ".join(events) if events else "Standard Trading Week (No macro blackouts)"
    weeks_summary.append((w, mon.strftime("%Y-%m-%d"), fri.strftime("%Y-%m-%d"), t_days, ev_str))
    print(f"Week {w:02d} ({mon.strftime('%b %d')} - {fri.strftime('%b %d, %Y')}): {t_days} Trading Days | {ev_str}")

print(f"\nTotal Active Trading Sessions across 18 Weeks: {total_trading_days} Days")
