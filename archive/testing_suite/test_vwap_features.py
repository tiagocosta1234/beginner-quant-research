"""
Tier 1 Feature Tests: VWAP Engine, Level 1 OHLCV, Welford STDV, and Reversal Sweeps
Authoritative tests verifying isolated core mechanics against mathematical specifications.
"""

import unittest
import math
import numpy as np
import pandas as pd
from testing_suite.core_engine import (
    validate_ohlcv_bar,
    calculate_bar_metrics,
    compute_vwap_and_stdv,
    WelfordRunningStats,
    evaluate_sweep_signal,
)


class TestLevel1OHLCVIntegrity(unittest.TestCase):
    """F-01: Level 1 OHLCV Data Geometry & Invariant Rules."""

    def test_l1_valid_bar_geometry(self):
        """Test 1.1: Valid OHLCV bar satisfies all geometrical constraints."""
        valid, msg = validate_ohlcv_bar(open_p=20000.0, high_p=20025.0, low_p=19990.0, close_p=20015.0, volume=150.0)
        self.assertTrue(valid, msg)

    def test_l1_negative_volume_rejected(self):
        """Test 1.2: Negative volume must be strictly rejected."""
        valid, msg = validate_ohlcv_bar(open_p=20000.0, high_p=20010.0, low_p=19995.0, close_p=20005.0, volume=-5.0)
        self.assertFalse(valid)
        self.assertIn("Volume cannot be negative", msg)

    def test_l1_high_lower_than_low_rejected(self):
        """Test 1.3: Bar where High < Low violates core invariants."""
        valid, msg = validate_ohlcv_bar(open_p=20000.0, high_p=19980.0, low_p=20020.0, close_p=20005.0, volume=50.0)
        self.assertFalse(valid)
        self.assertIn("High", msg)

    def test_l1_wick_and_body_ratio_decomposition(self):
        """Test 1.4: Body + Upper Wick + Lower Wick must equal Range, and ratios sum to 1.0."""
        metrics = calculate_bar_metrics(open_p=20000.0, high_p=20040.0, low_p=19980.0, close_p=20020.0)
        total_range = metrics["range"]
        self.assertAlmostEqual(total_range, 60.0, places=4)
        self.assertAlmostEqual(metrics["body"], 20.0, places=4)
        self.assertAlmostEqual(metrics["upper_wick"], 20.0, places=4)
        self.assertAlmostEqual(metrics["lower_wick"], 20.0, places=4)
        
        ratio_sum = metrics["body_ratio"] + metrics["upper_wick_ratio"] + metrics["lower_wick_ratio"]
        self.assertAlmostEqual(ratio_sum, 1.0, places=4)

    def test_l1_zero_range_flat_bar(self):
        """Test 1.5: Flat bar (H == L == O == C) handles division-by-zero safely."""
        metrics = calculate_bar_metrics(open_p=20000.0, high_p=20000.0, low_p=20000.0, close_p=20000.0)
        self.assertEqual(metrics["range"], 0.0)
        self.assertEqual(metrics["body"], 0.0)
        self.assertFalse(np.isnan(metrics["body_ratio"]))
        self.assertFalse(np.isnan(metrics["upper_wick_ratio"]))
        self.assertFalse(np.isnan(metrics["lower_wick_ratio"]))


class TestExtendedSessionVWAP(unittest.TestCase):
    """F-02: Extended Session VWAP with 18:00 EST Reset."""

    def test_vwap_session_reset_at_1800(self):
        """Test 2.1: Transition across 18:00 EST resets cumulative VWAP."""
        data = {
            "Timestamp": ["20260611 175800", "20260611 175900", "20260611 180000", "20260611 180100"],
            "TimeOfDay": [1758, 1759, 1800, 1801],
            "Open": [20000.0, 20010.0, 20100.0, 20105.0],
            "High": [20010.0, 20020.0, 20110.0, 20115.0],
            "Low": [19995.0, 20005.0, 20095.0, 20100.0],
            "Close": [20005.0, 20015.0, 20105.0, 20110.0],
            "Volume": [100, 100, 50, 50]
        }
        df = pd.DataFrame(data)
        res = compute_vwap_and_stdv(df)
        
        # Session 1: 17:58 and 17:59
        tp_0 = (20010.0 + 19995.0 + 20005.0) / 3.0  # 20003.333
        tp_1 = (20020.0 + 20005.0 + 20015.0) / 3.0  # 20013.333
        expected_vwap_1 = (tp_0 * 100 + tp_1 * 100) / 200.0
        self.assertAlmostEqual(res.loc[1, 'VWAP'], expected_vwap_1, places=3)
        
        # Session 2 resets at 18:00: bar 2 VWAP must equal TypicalPrice of bar 2
        tp_2 = (20110.0 + 20095.0 + 20105.0) / 3.0  # 20103.333
        self.assertAlmostEqual(res.loc[2, 'VWAP'], tp_2, places=3)
        self.assertEqual(res.loc[2, 'SessionID'], 2)

    def test_vwap_volume_weighting_accuracy(self):
        """Test 2.2: VWAP accurately weights heavy volume bars over low volume bars."""
        data = {
            "TimeOfDay": [1800, 1801],
            "Open": [20000.0, 20100.0],
            "High": [20000.0, 20100.0],
            "Low": [20000.0, 20100.0],
            "Close": [20000.0, 20100.0],
            "Volume": [900, 100]  # 90% weight at 20000, 10% weight at 20100
        }
        df = pd.DataFrame(data)
        res = compute_vwap_and_stdv(df)
        # Expected: (20000 * 900 + 20100 * 100) / 1000 = 20010.0
        self.assertAlmostEqual(res.loc[1, 'VWAP'], 20010.0, places=4)

    def test_vwap_multi_session_isolation(self):
        """Test 2.3: Data from prior session does not contaminate new session VWAP."""
        data = {
            "TimeOfDay": [1700, 1759, 1800, 1830],
            "Open": [10000.0, 10000.0, 20000.0, 20000.0],
            "High": [10000.0, 10000.0, 20000.0, 20000.0],
            "Low": [10000.0, 10000.0, 20000.0, 20000.0],
            "Close": [10000.0, 10000.0, 20000.0, 20000.0],
            "Volume": [10000, 10000, 10, 10]
        }
        df = pd.DataFrame(data)
        res = compute_vwap_and_stdv(df)
        # In new session (bars 2 & 3), price is 20000.0. VWAP must be exactly 20000.0
        self.assertAlmostEqual(res.loc[2, 'VWAP'], 20000.0, places=4)
        self.assertAlmostEqual(res.loc[3, 'VWAP'], 20000.0, places=4)

    def test_vwap_monotonic_volume_accumulation(self):
        """Test 2.4: Cumulative volume is strictly non-decreasing within each session."""
        data = {
            "TimeOfDay": [1800, 1805, 1810, 1815],
            "Open": [20000.0] * 4,
            "High": [20010.0] * 4,
            "Low": [19990.0] * 4,
            "Close": [20005.0] * 4,
            "Volume": [50, 75, 120, 30]
        }
        df = pd.DataFrame(data)
        res = compute_vwap_and_stdv(df)
        cum_vols = res['CumVol'].values
        for j in range(1, len(cum_vols)):
            self.assertGreaterEqual(cum_vols[j], cum_vols[j - 1])

    def test_vwap_zero_volume_bar_stability(self):
        """Test 2.5: Zero-volume bar does not cause NaN or division by zero."""
        data = {
            "TimeOfDay": [1800, 1801, 1802],
            "Open": [20000.0, 20005.0, 20010.0],
            "High": [20010.0, 20005.0, 20015.0],
            "Low": [19995.0, 20005.0, 20005.0],
            "Close": [20005.0, 20005.0, 20010.0],
            "Volume": [100, 0, 50]  # Zero volume on middle bar
        }
        df = pd.DataFrame(data)
        res = compute_vwap_and_stdv(df)
        self.assertFalse(res['VWAP'].isna().any())
        # Middle bar with 0 volume should hold prior cumulative VWAP
        self.assertAlmostEqual(res.loc[1, 'VWAP'], res.loc[0, 'VWAP'], places=4)


class TestWelfordSTDVCalculation(unittest.TestCase):
    """F-03: Incremental Welford STDV and Multi-Band Scaling."""

    def test_welford_incremental_vs_sample_variance(self):
        """Test 3.1: Welford running stats matches numpy variance."""
        values = [20010.5, 20025.0, 19995.25, 20040.0, 20015.75, 20030.0]
        welford = WelfordRunningStats()
        for v in values:
            welford.update(v)
            
        np_var = np.var(values, ddof=0)
        np_sample_var = np.var(values, ddof=1)
        
        self.assertAlmostEqual(welford.variance, np_var, places=6)
        self.assertAlmostEqual(welford.sample_variance, np_sample_var, places=6)

    def test_welford_stdv_bands_symmetry(self):
        """Test 3.2: Upper and Lower STDV bands are strictly symmetric around VWAP."""
        data = {
            "TimeOfDay": [1800, 1805, 1810],
            "Open": [20000.0, 20020.0, 19980.0],
            "High": [20030.0, 20040.0, 20000.0],
            "Low": [19990.0, 20010.0, 19970.0],
            "Close": [20020.0, 20030.0, 19985.0],
            "Volume": [100, 150, 200]
        }
        df = pd.DataFrame(data)
        res = compute_vwap_and_stdv(df)
        
        for k in range(len(res)):
            vwap = res.loc[k, 'VWAP']
            up1 = res.loc[k, 'Band_Upper_1']
            lo1 = res.loc[k, 'Band_Lower_1']
            self.assertAlmostEqual(up1 - vwap, vwap - lo1, places=5)

    def test_welford_multi_band_multiplier_scaling(self):
        """Test 3.3: 2-sigma and 3-sigma bands scale exactly 2x and 3x relative to 1-sigma."""
        data = {
            "TimeOfDay": [1800, 1801, 1802],
            "Open": [20000.0, 20050.0, 19950.0],
            "High": [20060.0, 20070.0, 19960.0],
            "Low": [19990.0, 20040.0, 19940.0],
            "Close": [20050.0, 20060.0, 19955.0],
            "Volume": [100, 100, 100]
        }
        df = pd.DataFrame(data)
        res = compute_vwap_and_stdv(df)
        
        last_row = res.iloc[-1]
        stdv = last_row['STDV']
        self.assertGreater(stdv, 0.0)
        self.assertAlmostEqual(last_row['Band_Upper_2'] - last_row['VWAP'], 2.0 * stdv, places=5)
        self.assertAlmostEqual(last_row['Band_Upper_3'] - last_row['VWAP'], 3.0 * stdv, places=5)
        self.assertAlmostEqual(last_row['VWAP'] - last_row['Band_Lower_2'], 2.0 * stdv, places=5)
        self.assertAlmostEqual(last_row['VWAP'] - last_row['Band_Lower_3'], 3.0 * stdv, places=5)

    def test_welford_zero_variance_flat_series(self):
        """Test 3.4: Constant price series yields STDV = 0 and equal bands."""
        data = {
            "TimeOfDay": [1800, 1801, 1802],
            "Open": [20000.0, 20000.0, 20000.0],
            "High": [20000.0, 20000.0, 20000.0],
            "Low": [20000.0, 20000.0, 20000.0],
            "Close": [20000.0, 20000.0, 20000.0],
            "Volume": [50, 50, 50]
        }
        df = pd.DataFrame(data)
        res = compute_vwap_and_stdv(df)
        self.assertAlmostEqual(res.iloc[-1]['STDV'], 0.0, places=6)
        self.assertAlmostEqual(res.iloc[-1]['Band_Upper_1'], 20000.0, places=6)
        self.assertAlmostEqual(res.iloc[-1]['Band_Lower_1'], 20000.0, places=6)

    def test_welford_large_numbers_numerical_stability(self):
        """Test 3.5: Numerical stability when prices are centered at high values (~30,000 NQ)."""
        welford = WelfordRunningStats()
        for i in range(1000):
            # Price oscillating between 29,990 and 30,010
            p = 30000.0 + 10.0 * math.sin(i * 0.1)
            welford.update(p)
        self.assertAlmostEqual(welford.mean, 30000.0, delta=1.0)
        self.assertGreater(welford.variance, 0.0)
        self.assertFalse(math.isnan(welford.std_dev))


class TestFalseBreakoutSweepDetection(unittest.TestCase):
    """F-04: Daniel Inskeep False Breakout Sweep Reversal Engine."""

    def test_sweep_bullish_reclaim_valid(self):
        """Test 4.1: Valid bullish sweep of ONL triggers LONG signal."""
        # ONL = 20000, Low sweeps down to 19992 (8 pts depth), closes back at 20006, Open 20000, VWAP at 20035
        # Range = 20008 - 19992 = 16 pts. Lower wick = 20000 - 19992 = 8 pts (ratio = 0.50 >= 0.40)
        sig = evaluate_sweep_signal(
            open_p=20000.0,
            high_p=20008.0,
            low_p=19992.0,
            close_p=20006.0,
            onh=20080.0,
            onl=20000.0,
            vwap=20035.0,
            min_sweep_depth=2.0,
            max_sweep_depth=25.0,
            min_wick_ratio=0.40,
            min_target_dist=15.0
        )
        self.assertTrue(sig["is_signal"])
        self.assertEqual(sig["direction"], "LONG")
        self.assertEqual(sig["entry_price"], 20006.0)
        self.assertEqual(sig["stop_loss"], 19991.0)  # low - 1.0 pt
        self.assertEqual(sig["risk_pts"], 15.0)

    def test_sweep_bearish_rejection_valid(self):
        """Test 4.2: Valid bearish sweep of ONH triggers SHORT signal."""
        # ONH = 20050, High sweeps up to 20060 (10 pts depth), closes at 20042, Open 20048, VWAP at 20010
        sig = evaluate_sweep_signal(
            open_p=20048.0,
            high_p=20060.0,
            low_p=20040.0,
            close_p=20042.0,
            onh=20050.0,
            onl=19970.0,
            vwap=20010.0,
            min_sweep_depth=2.0,
            max_sweep_depth=25.0,
            min_wick_ratio=0.40,
            min_target_dist=15.0
        )
        self.assertTrue(sig["is_signal"])
        self.assertEqual(sig["direction"], "SHORT")
        self.assertEqual(sig["entry_price"], 20042.0)
        self.assertEqual(sig["stop_loss"], 20061.0)  # high + 1.0 pt
        self.assertEqual(sig["risk_pts"], 19.0)

    def test_sweep_rejected_shallow_depth(self):
        """Test 4.3: Sweep depth < 2.0 pts fails to trigger (insufficient liquidity grab)."""
        sig = evaluate_sweep_signal(
            open_p=19999.0,
            high_p=20005.0,
            low_p=19999.0,  # only 1.0 pt below ONL 20000.0
            close_p=20003.0,
            onh=20080.0,
            onl=20000.0,
            vwap=20040.0,
            min_sweep_depth=2.0
        )
        self.assertFalse(sig["is_signal"])
        self.assertIn("depth", sig["reason"].lower())

    def test_sweep_rejected_excessive_depth(self):
        """Test 4.4: Sweep depth > 25.0 pts fails to trigger (runaway trend breakdown)."""
        sig = evaluate_sweep_signal(
            open_p=19980.0,
            high_p=20005.0,
            low_p=19965.0,  # 35 pts below ONL 20000.0 (> 25 pt limit)
            close_p=20002.0,
            onh=20080.0,
            onl=20000.0,
            vwap=20040.0,
            max_sweep_depth=25.0
        )
        self.assertFalse(sig["is_signal"])
        self.assertIn("max", sig["reason"].lower())

    def test_sweep_rejected_insufficient_wick_ratio(self):
        """Test 4.5: Rejection wick ratio < 0.40 fails to qualify as a wick rejection."""
        # Range = 20015 - 19995 = 20 pts. Lower wick = min(O,C) - L = 19998 - 19995 = 3 pts (ratio = 3/20 = 0.15 < 0.40)
        sig = evaluate_sweep_signal(
            open_p=19998.0,
            high_p=20015.0,
            low_p=19995.0,
            close_p=20012.0,
            onh=20080.0,
            onl=20000.0,
            vwap=20050.0,
            min_sweep_depth=2.0,
            min_wick_ratio=0.40
        )
        self.assertFalse(sig["is_signal"])
        self.assertIn("wick ratio", sig["reason"].lower())

    def test_sweep_rejected_insufficient_target_distance(self):
        """Test 4.6: Distance to VWAP < 15 pts fails minimum profit target requirement."""
        sig = evaluate_sweep_signal(
            open_p=20000.0,
            high_p=20008.0,
            low_p=19992.0,
            close_p=20006.0,
            onh=20080.0,
            onl=20000.0,
            vwap=20015.0,  # target dist = 20015 - 20006 = 9 pts < 15.0
            min_sweep_depth=2.0,
            min_target_dist=15.0
        )
        self.assertFalse(sig["is_signal"])
        self.assertIn("target distance", sig["reason"].lower())


if __name__ == "__main__":
    unittest.main()
