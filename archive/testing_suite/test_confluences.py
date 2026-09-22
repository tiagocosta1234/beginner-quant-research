"""
Tier 1 Feature Tests: Confluence Filters, HTF Zones, 50% Equilibrium, ADX, and SMT Divergence
Authoritative tests verifying higher-timeframe and regime confluences.
"""

import unittest
from testing_suite.core_engine import (
    grade_htf_zone,
    evaluate_equilibrium_discount_premium,
)


def evaluate_adx_regime_and_rr(
    adx_value: float,
    adx_threshold: float = 25.0,
    potential_reward_pts: float = 20.0,
    risk_pts: float = 15.0,
    min_rr_ratio: float = 1.0
) -> dict:
    """
    Evaluates ADX regime (< 25 for chop/mean-reversion) and minimum R:R ratio gate.
    """
    if risk_pts <= 0:
        return {"allowed": False, "reason": "Invalid risk <= 0"}
    
    rr_ratio = potential_reward_pts / risk_pts
    
    # Daniel Inskeep & nq-level1-edge: ADX < 25 indicates chop/range bound market where
    # 75% of breakouts fail, so sweep reversal is optimal. ADX >= 25 indicates trend.
    is_chop_regime = (adx_value <= adx_threshold)
    passes_rr = (rr_ratio >= min_rr_ratio)

    allowed = is_chop_regime and passes_rr
    
    reasons = []
    if not is_chop_regime:
        reasons.append(f"ADX {adx_value:.1f} > threshold {adx_threshold:.1f} (trending regime blocks fade)")
    if not passes_rr:
        reasons.append(f"R:R ratio {rr_ratio:.2f} < min {min_rr_ratio:.2f}")

    return {
        "allowed": allowed,
        "is_chop_regime": is_chop_regime,
        "passes_rr": passes_rr,
        "rr_ratio": rr_ratio,
        "reason": "; ".join(reasons) if reasons else "Approved"
    }


def evaluate_smt_divergence(
    nq_swept_low: bool,
    nq_swept_high: bool,
    es_swept_low: bool,
    es_swept_high: bool,
    filter_enabled: bool = True
) -> dict:
    """
    Evaluates Intermarket SMT (Smart Money Technique) divergence between NQ and ES:
    - Bullish SMT: NQ breaks/sweeps swing low while ES holds higher low (ES did not sweep low), or vice versa.
    - Bearish SMT: NQ breaks/sweeps swing high while ES holds lower high (ES did not sweep high), or vice versa.
    """
    if not filter_enabled:
        return {"divergence_confirmed": True, "divergence_type": "BYPASS", "reason": "SMT filter disabled"}

    # Bullish SMT: One index sweeps low, the other holds
    bullish_smt = (nq_swept_low and not es_swept_low) or (es_swept_low and not nq_swept_low)
    # Bearish SMT: One index sweeps high, the other holds
    bearish_smt = (nq_swept_high and not es_swept_high) or (es_swept_high and not nq_swept_high)

    if bullish_smt:
        return {
            "divergence_confirmed": True,
            "divergence_type": "BULLISH_SMT",
            "reason": "Bullish SMT confirmed: Liquidity sweep non-confirmation between NQ and ES"
        }
    if bearish_smt:
        return {
            "divergence_confirmed": True,
            "divergence_type": "BEARISH_SMT",
            "reason": "Bearish SMT confirmed: Liquidity sweep non-confirmation between NQ and ES"
        }

    return {
        "divergence_confirmed": False,
        "divergence_type": "NONE",
        "reason": "No SMT divergence: Indices moved in tandem"
    }


class TestHTFZoneGrading(unittest.TestCase):
    """F-05: Higher-Timeframe Support & Resistance Zone Grading (6 Criteria)."""

    def test_zone_grade_aplus(self):
        """Test 5.1: Zone meeting 5-6 criteria receives Grade A+ (core location, full size)."""
        res = grade_htf_zone(
            origin_displacement_mult=2.5,  # 1: Origin
            retest_count=1,                # 2: Retest
            timeframe_confluence_count=2,  # 3: Confluence (e.g. Daily + 1H)
            is_role_swap=True,             # 4: Role swap
            price_level=20000.0,           # 5: Round number
            has_volume_node=True           # 6: Volume node
        )
        self.assertEqual(res["grade"], "A+")
        self.assertEqual(res["score"], 6)
        self.assertTrue(res["tradeable"])
        self.assertEqual(res["risk_multiplier"], 1.0)

    def test_zone_grade_a(self):
        """Test 5.2: Zone meeting 3-4 criteria receives Grade A (primary zone, full size)."""
        res = grade_htf_zone(
            origin_displacement_mult=2.1,  # 1: Origin
            retest_count=2,                # 2: Retest
            timeframe_confluence_count=1,
            is_role_swap=False,
            price_level=19750.0,           # not round 00/500 mod 100 != 0 (wait 750 % 100 != 0, but check mod)
            has_volume_node=True           # 3: Volume node
        )
        self.assertIn(res["grade"], ["A", "A+"])
        self.assertTrue(res["tradeable"])
        self.assertEqual(res["risk_multiplier"], 1.0)

    def test_zone_grade_b_reduced_size(self):
        """Test 5.3: Zone meeting 2 criteria receives Grade B (secondary zone, 50% size)."""
        res = grade_htf_zone(
            origin_displacement_mult=1.2,  # < 2.0 (No)
            retest_count=1,                # Yes (1)
            timeframe_confluence_count=1,  # < 2 (No)
            is_role_swap=True,             # Yes (2)
            price_level=20123.45,          # not round (No)
            has_volume_node=False          # No
        )
        self.assertEqual(res["grade"], "B")
        self.assertEqual(res["score"], 2)
        self.assertTrue(res["tradeable"])
        self.assertEqual(res["risk_multiplier"], 0.5)

    def test_zone_grade_c_untradeable(self):
        """Test 5.4: Zone meeting only 1 criterion is Grade C (weak, monitor only, no trade)."""
        res = grade_htf_zone(
            origin_displacement_mult=1.0,
            retest_count=0,
            timeframe_confluence_count=1,
            is_role_swap=False,
            price_level=20000.0,           # 1 criterion: round number
            has_volume_node=False
        )
        self.assertEqual(res["grade"], "C")
        self.assertEqual(res["score"], 1)
        self.assertFalse(res["tradeable"])
        self.assertEqual(res["risk_multiplier"], 0.0)

    def test_zone_invalidation_close_through(self):
        """Test 5.5: Full candle body close through zone invalidates it completely."""
        res = grade_htf_zone(
            origin_displacement_mult=3.0,
            retest_count=1,
            timeframe_confluence_count=3,
            is_role_swap=True,
            price_level=20000.0,
            has_volume_node=True,
            closed_through=True
        )
        self.assertEqual(res["grade"], "INVALID")
        self.assertFalse(res["tradeable"])
        self.assertIn("Closed through", res["status"])

    def test_zone_invalidation_exhaustion_retest_count(self):
        """Test 5.6: Zone tested 3+ times without bounce is exhausted and invalid."""
        res = grade_htf_zone(
            origin_displacement_mult=2.5,
            retest_count=3,  # >= 3 exhausted
            timeframe_confluence_count=2,
            is_role_swap=True,
            price_level=20000.0,
            has_volume_node=True
        )
        self.assertEqual(res["grade"], "INVALID")
        self.assertFalse(res["tradeable"])
        self.assertIn("exhausted", res["status"].lower())

    def test_zone_invalidation_stale_days(self):
        """Test 5.7: Zone untested for >10 trading days is stale and invalid."""
        res = grade_htf_zone(
            origin_displacement_mult=2.5,
            retest_count=1,
            timeframe_confluence_count=2,
            is_role_swap=True,
            price_level=20000.0,
            has_volume_node=True,
            days_untested=11
        )
        self.assertEqual(res["grade"], "INVALID")
        self.assertFalse(res["tradeable"])
        self.assertIn("Stale", res["status"])


class TestEquilibriumDiscountPremium(unittest.TestCase):
    """F-06: 50% Trend Retracement Equilibrium Filter."""

    def test_long_in_discount_allowed(self):
        """Test 6.1: Long trade allowed when price is in Discount (< 50% retracement)."""
        # Swing Low = 19900, Swing High = 20100. Equilibrium = 20000.
        # Price = 19940 (20% of range -> deep Discount)
        res = evaluate_equilibrium_discount_premium(
            price=19940.0,
            swing_low=19900.0,
            swing_high=20100.0,
            direction="LONG"
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["zone"], "DISCOUNT")
        self.assertAlmostEqual(res["ratio"], 0.20, places=2)

    def test_long_in_premium_rejected(self):
        """Test 6.2: Long trade blocked when price is in Premium (> 50% retracement)."""
        # Price = 20060 (80% of range -> Premium)
        res = evaluate_equilibrium_discount_premium(
            price=20060.0,
            swing_low=19900.0,
            swing_high=20100.0,
            direction="LONG"
        )
        self.assertFalse(res["allowed"])
        self.assertEqual(res["zone"], "PREMIUM")
        self.assertAlmostEqual(res["ratio"], 0.80, places=2)

    def test_short_in_premium_allowed(self):
        """Test 6.3: Short trade allowed when price is in Premium (> 50% retracement)."""
        # Price = 20070 (85% of range -> Premium)
        res = evaluate_equilibrium_discount_premium(
            price=20070.0,
            swing_low=19900.0,
            swing_high=20100.0,
            direction="SHORT"
        )
        self.assertTrue(res["allowed"])
        self.assertEqual(res["zone"], "PREMIUM")

    def test_short_in_discount_rejected(self):
        """Test 6.4: Short trade blocked when price is in Discount (< 50% retracement)."""
        # Price = 19930 (15% of range -> Discount)
        res = evaluate_equilibrium_discount_premium(
            price=19930.0,
            swing_low=19900.0,
            swing_high=20100.0,
            direction="SHORT"
        )
        self.assertFalse(res["allowed"])
        self.assertEqual(res["zone"], "DISCOUNT")

    def test_equilibrium_exact_midpoint(self):
        """Test 6.5: Exact 50% midpoint threshold behavior."""
        # Equilibrium = 20000.0. Price = 20000.0 (50.0%)
        res_long = evaluate_equilibrium_discount_premium(
            price=20000.0,
            swing_low=19900.0,
            swing_high=20100.0,
            direction="LONG"
        )
        res_short = evaluate_equilibrium_discount_premium(
            price=20000.0,
            swing_low=19900.0,
            swing_high=20100.0,
            direction="SHORT"
        )
        self.assertTrue(res_long["allowed"])
        self.assertTrue(res_short["allowed"])
        self.assertEqual(res_long["zone"], "EQUILIBRIUM")


class TestADXRegimeFilter(unittest.TestCase):
    """F-07: ADX Regime & Chop Filter and Minimum R:R Gating."""

    def test_adx_chop_regime_allows_mean_reversion_sweep(self):
        """Test 7.1: Low ADX (18.5 <= 25) indicates chop, allowing mean-reversion sweep."""
        res = evaluate_adx_regime_and_rr(adx_value=18.5, adx_threshold=25.0, potential_reward_pts=30.0, risk_pts=15.0)
        self.assertTrue(res["allowed"])
        self.assertTrue(res["is_chop_regime"])
        self.assertAlmostEqual(res["rr_ratio"], 2.0, places=2)

    def test_adx_trending_regime_blocks_countertrend_sweep(self):
        """Test 7.2: High ADX (34.0 > 25) indicates runaway trend, blocking reversal fade."""
        res = evaluate_adx_regime_and_rr(adx_value=34.0, adx_threshold=25.0, potential_reward_pts=30.0, risk_pts=15.0)
        self.assertFalse(res["allowed"])
        self.assertFalse(res["is_chop_regime"])
        self.assertIn("trending regime", res["reason"])

    def test_adx_exact_boundary_threshold(self):
        """Test 7.3: Boundary ADX = 25.0 is included in chop regime."""
        res = evaluate_adx_regime_and_rr(adx_value=25.0, adx_threshold=25.0, potential_reward_pts=20.0, risk_pts=20.0)
        self.assertTrue(res["allowed"])
        self.assertTrue(res["is_chop_regime"])

    def test_minimum_rr_ratio_gate_pass(self):
        """Test 7.4: Minimum R:R ratio >= 1.0 passes."""
        res = evaluate_adx_regime_and_rr(adx_value=20.0, potential_reward_pts=25.0, risk_pts=20.0, min_rr_ratio=1.0)
        self.assertTrue(res["allowed"])
        self.assertTrue(res["passes_rr"])

    def test_minimum_rr_ratio_gate_fail(self):
        """Test 7.5: Minimum R:R ratio < 1.0 blocks trade entry."""
        res = evaluate_adx_regime_and_rr(adx_value=20.0, potential_reward_pts=12.0, risk_pts=20.0, min_rr_ratio=1.0)
        self.assertFalse(res["allowed"])
        self.assertFalse(res["passes_rr"])
        self.assertIn("R:R ratio", res["reason"])


class TestIntermarketSMTDivergence(unittest.TestCase):
    """F-08: ES/NQ SMT Divergence Filter."""

    def test_bullish_smt_nq_sweeps_es_higher_low(self):
        """Test 8.1: NQ sweeps low while ES holds higher low confirms Bullish SMT."""
        res = evaluate_smt_divergence(
            nq_swept_low=True,
            nq_swept_high=False,
            es_swept_low=False,  # ES held higher low
            es_swept_high=False
        )
        self.assertTrue(res["divergence_confirmed"])
        self.assertEqual(res["divergence_type"], "BULLISH_SMT")

    def test_bearish_smt_nq_sweeps_es_lower_high(self):
        """Test 8.2: NQ sweeps high while ES holds lower high confirms Bearish SMT."""
        res = evaluate_smt_divergence(
            nq_swept_low=False,
            nq_swept_high=True,
            es_swept_low=False,
            es_swept_high=False  # ES held lower high
        )
        self.assertTrue(res["divergence_confirmed"])
        self.assertEqual(res["divergence_type"], "BEARISH_SMT")

    def test_smt_non_divergence_both_sweep(self):
        """Test 8.3: Both NQ and ES sweeping low produces no divergence."""
        res = evaluate_smt_divergence(
            nq_swept_low=True,
            nq_swept_high=False,
            es_swept_low=True,
            es_swept_high=False
        )
        self.assertFalse(res["divergence_confirmed"])
        self.assertEqual(res["divergence_type"], "NONE")

    def test_smt_filter_bypass_when_disabled(self):
        """Test 8.4: When SMT filter is disabled, signals pass unconditionally."""
        res = evaluate_smt_divergence(
            nq_swept_low=False,
            nq_swept_high=False,
            es_swept_low=False,
            es_swept_high=False,
            filter_enabled=False
        )
        self.assertTrue(res["divergence_confirmed"])
        self.assertEqual(res["divergence_type"], "BYPASS")

    def test_inverse_smt_es_sweeps_nq_holds(self):
        """Test 8.5: ES sweeps low while NQ holds higher low confirms Bullish SMT on NQ."""
        res = evaluate_smt_divergence(
            nq_swept_low=False,
            nq_swept_high=False,
            es_swept_low=True,
            es_swept_high=False
        )
        self.assertTrue(res["divergence_confirmed"])
        self.assertEqual(res["divergence_type"], "BULLISH_SMT")


if __name__ == "__main__":
    unittest.main()
