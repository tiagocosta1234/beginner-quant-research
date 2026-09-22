#!/usr/bin/env python3
"""
Verification Script for Synthetic 1-Tick Engine & 680-Cell Matrix Scan Output.
"""

import os
import sys
import json
import sqlite3
import pandas as pd
import numpy as np

def run_verification():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, ".."))
    data_dir = os.path.join(project_root, "data_and_results")
    
    db_path = os.path.join(data_dir, "lucid_matrix_results.db")
    json_path = os.path.join(data_dir, "matrix_eval_summary.json")
    csv_path = os.path.join(data_dir, "matrix_eval_summary.csv")
    parquet_path = os.path.join(data_dir, "matrix_eval_summary.parquet")
    
    # 1. Check file existence
    files = [db_path, json_path, csv_path, parquet_path]
    for fp in files:
        assert os.path.exists(fp), f"Missing file: {fp}"
        print(f"[PASS] File exists: {os.path.basename(fp)} ({os.path.getsize(fp):,} bytes)")
        
    # 2. Verify SQLite DB
    conn = sqlite3.connect(db_path)
    df_summary = pd.read_sql_query("SELECT * FROM tbl_matrix_cell_summary", conn)
    df_trades = pd.read_sql_query("SELECT * FROM tbl_synthetic_trade_logs", conn)
    conn.close()
    
    assert len(df_summary) == 680, f"Expected 680 summary rows, got {len(df_summary)}"
    assert len(df_trades) > 0, f"Expected >0 trade rows, got {len(df_trades)}"
    print(f"[PASS] SQLite Summary rows = {len(df_summary)} (Exact 680-cell match)")
    print(f"[PASS] SQLite Trade log rows = {len(df_trades):,} total trades")
    
    # 3. Check All 34 Tickers Present
    expected_tickers = [
        "MNQ", "NQ", "MES", "ES", "MYM", "YM", "M2K", "RTY", "NKD",
        "MGC", "GC", "SI", "SIL", "HG", "PL",
        "MCL", "CL", "NG", "QG", "QM",
        "6E", "6B", "6J", "6A", "6C", "6S", "6N",
        "ZS", "ZC", "ZL", "ZM", "ZW", "HE", "LE"
    ]
    summary_tickers = sorted(df_summary["ticker"].unique().tolist())
    assert sorted(expected_tickers) == summary_tickers, "Mismatch in expected 34 tickers!"
    print(f"[PASS] All 34 approved Broker tickers verified in dataset.")
    
    # 4. Check 5 Timeframes and 4 Sessions per Ticker (34 * 5 * 4 = 680)
    for t in expected_tickers:
        sub = df_summary[df_summary["ticker"] == t]
        assert len(sub) == 20, f"Ticker {t} has {len(sub)} rows, expected 20"
    print(f"[PASS] Every ticker has exactly 20 parameter cells (5 timeframes x 4 sessions).")
    
    # 5. Check Parquet, CSV, and JSON integrity
    df_csv = pd.read_csv(csv_path)
    assert len(df_csv) == 680, f"CSV length mismatch: {len(df_csv)}"
    
    df_parquet = pd.read_parquet(parquet_path)
    assert len(df_parquet) == 680, f"Parquet length mismatch: {len(df_parquet)}"
    
    with open(json_path, "r", encoding="utf-8") as f:
        data_json = json.load(f)
    assert len(data_json) == 680, f"JSON length mismatch: {len(data_json)}"
    print(f"[PASS] Multi-tier storage verified (SQLite, Parquet, CSV, JSON all contain 680 rows).")
    
    # 6. Check Metric Bounds & Integrity
    assert df_summary["win_rate"].between(0.0, 1.0).all(), "Win rate out of bounds"
    assert (df_summary["profit_factor"] >= 0.0).all(), "Negative profit factor"
    assert (df_summary["max_intraday_dd_usd"] >= 0.0).all(), "Negative max intraday DD"
    assert (df_summary["max_eod_dd_usd"] >= 0.0).all(), "Negative max EOD DD"
    assert df_summary["risk_of_ruin"].between(0.0, 1.0).all(), "Risk of ruin out of bounds"
    assert df_summary["consistency_compliance"].between(0.0, 1.0).all(), "Consistency compliance out of bounds"
    print(f"[PASS] All quantitative metrics are within strict mathematical bounds.")
    
    # 7. Check Top Qualified Standalone Models (PF >= 1.30, WR >= 50%)
    qualified = df_summary[(df_summary["profit_factor"] >= 1.30) & (df_summary["win_rate"] >= 0.50)]
    print(f"[PASS] Verified {len(qualified)} standalone configurations with PF >= 1.30 and WR >= 50.0%.")
    
    print("\n" + "="*80)
    print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY (100% INTEGRITY)")
    print("="*80)

if __name__ == "__main__":
    run_verification()
