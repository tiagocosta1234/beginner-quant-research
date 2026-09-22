# Self-Improving AI Bridge Architecture
**Status:** Initialization Phase
**Objective:** Replace hardcoded C# trading rules with a self-optimizing Machine Learning (ML) model that dynamically adapts to market regimes.

## Phase 1: Data Extraction (The Senses)
The AI cannot learn without seeing the market. We must extract high-resolution 1-minute OHLCV data from NinjaTrader 8.
*   **Required Data:** Time, Open, High, Low, Close, Volume.
*   **Engineered Features (DNA):** 
    *   Wick-to-Body Ratios (to detect rejection/sweeps)
    *   Volatility (ATR)
    *   Momentum (ADX)
    *   Distance from session boundaries (Asian High/Low).

## Phase 2: Python Machine Learning Engine (The Brain)
A Python environment will ingest the NinjaTrader data and simulate millions of trading permutations.
*   **Algorithm Type:** Deep Q-Learning (DQN) or Genetic Algorithm (GA).
*   **Reward Function:** +1 for every dollar of profit, -2 for every dollar of drawdown (heavily penalizing risk to protect the 50k Broker evaluation limit).
*   **Output:** The Python engine generates an `optimal_weights.json` file containing the best mathematical parameters for the current market regime.

## Phase 3: C# Execution Bridge (The Hands)
`ManualCustomBot.cs` will be stripped of its rigid logic. Instead, it will be programmed to:
1.  Read `optimal_weights.json` on startup.
2.  Apply the AI's chosen parameters for the day.
3.  Execute trades purely based on the AI's dynamically generated threshold.

## Next Immediate Step
We need raw 1-minute historical data to train the initial Python brain.
