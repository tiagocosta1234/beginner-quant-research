---
type: "explain"
date: "2026-08-01T13:25:23.563533+00:00"
question: "Why does _15m_eval_3 connect Community 1 to Community 0, Community 9, Community 10, Community 5?"
contributor: "graphify"
source_nodes: ["_15m_eval_3"]
---

# Q: Why does _15m_eval_3 connect Community 1 to Community 0, Community 9, Community 10, Community 5?

## Answer

The node _15m_eval_3 acts as a central hub (15 connections). It bridges Community 1 (its own internal state like BPR, FVG, LiquidityPool, TrackFVGs) to Community 0 (NinjaTrader Core) by inheriting from Strategy. It also bridges to other communities by referencing shared primitives (double, int, bool) and indicators (ATR) that are used across the entire codebase.

## Source Nodes

- _15m_eval_3