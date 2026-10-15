# Pre-registration BRK-HOURS (breakout day, round 25; written 2026-10-15 13:39 local, local clock, before any code or result)
Question: at which hour of the day do breakouts carry information, market class by market class? (Every earlier round used each market's main-session open.)
Clock: MT5 broker server time (= London + 2 h all year). For every server hour h = 1..20, every market (46) and every day: box = the bid high/low of [h:00, h+1:00); one-cancels-other stop orders at the box (buy at ask >= high, sell at bid <= low), live (h+1:00, h+3:00); first fill wins; stop at the other side of the box; R = entry - stop >= 2 spreads at the fill; hold to min(h+7:00, 22:55) server. No entry, decision or exit in server hours 23 / 0 (rule L-rollover).
Random-entry control: a random minute of the order window, random side, same R, same exit.
Cells: 20 hours x 5 classes (fx, index, metal, energy, crypto) = 100. Statistic per cell: mean net R a trade; t = Newey-West (lag 1) t of the daily class mean.
Gates (DEV 2022-24, VAL 2025, 2026 non-clean report only): 1. DEV mean >= +0.05 R and t >= 3.48 (Bonferroni 100, one-sided 2.5%). 2. VAL mean > 0 and t >= 1.65. 3. Beats its control by >= 0.05 R in DEV and in VAL.
Output also: heat maps of net R and of breakout information (net minus control) by hour x class for DEV / VAL / 2026 (chart for the trader).
Honest prior: about 5% that any cell passes; the map is the main product.
