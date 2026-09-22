---
type: community
cohesion: 1.00
members: 3
---

# Trade Analysis

**Cohesion:** 1.00 - tightly connected
**Members:** 3 nodes

## Members
- [[analyze_trades.py]] - code - analyze_trades.py
- [[main()]] - code - analyze_trades.py
- [[parse_currency()]] - code - analyze_trades.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Trade_Analysis
SORT file.name ASC
```
