#!/usr/bin/env python3
"""
E2E Test Runner for Optimized VWAP Sweep Reversal Strategy.
Discovers and executes all test suites across Tiers 1-4, producing a comprehensive
coverage report and returning exit code 0 on complete pass.
"""

import os
import sys
import time
import unittest


def run_all_tests():
    start_time = time.time()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    print("=" * 80)
    print("  OPTIMIZED VWAP SWEEP REVERSAL: E2E TEST RUNNER")
    print("  Independent Opaque-Box Verification Harness (Tiers 1 - 4)")
    print("=" * 80)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"Working Directory: {root_dir}")
    print(f"Python Version: {sys.version.split()[0]}")
    print("-" * 80)

    loader = unittest.TestLoader()
    suite_names = [
        ("Tier 1: Core VWAP, L1 OHLCV, Welford STDV, Sweeps", "test_vwap_features"),
        ("Tier 1: Confluences (HTF Zones, 50% Eq, ADX, SMT)", "test_confluences"),
        ("Tier 1: Drawdown Sizing & Fleet Compounding", "test_drawdown_sizing"),
        ("Tier 2: Boundaries (Zero Vol, 200pt Wicks, Caps, Floor Lock, Consistency)", "test_tier2_boundaries"),
        ("Tier 3: Cross-Feature Pairwise Combinations", "test_tier3_combinations"),
        ("Tier 4: Real-World 85-Day Workload Replay", "test_tier4_scenarios"),
        ("Tier 5: Adversarial Confluences & Microstructure Stress", "test_adversarial_confluences"),
        ("Tier 5: Adversarial Drawdown, Dynamic Sizing & Fleet Math", "test_adversarial_vwap"),
    ]

    total_suites = []
    module_stats = []
    all_passed = True
    total_test_count = 0

    for description, module_name in suite_names:
        suite = loader.loadTestsFromName(f"testing_suite.{module_name}")
        count = suite.countTestCases()
        total_test_count += count
        total_suites.append((description, module_name, suite, count))

    print(f"Discovered {len(suite_names)} test modules with {total_test_count} total test cases.\n")

    overall_suite = unittest.TestSuite()
    for _, _, suite, _ in total_suites:
        overall_suite.addTests(suite)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(overall_suite)

    duration = time.time() - start_time

    print("\n" + "=" * 80)
    print("  TEST EXECUTION SUMMARY TABLE")
    print("=" * 80)
    print(f"{'Module Description':<62} {'Tests':>6} {'Status':>10}")
    print("-" * 80)

    for description, module_name, suite, count in total_suites:
        # Check if any errors or failures belonged to this module
        mod_failed = False
        for failure in result.failures:
            if module_name in str(failure[0]):
                mod_failed = True
                break
        for err in result.errors:
            if module_name in str(err[0]):
                mod_failed = True
                break
        
        status = "FAIL" if mod_failed else "PASS"
        print(f"{description:<62} {count:>6} {status:>10}")

    print("-" * 80)
    print(f"Total Test Cases Executed: {result.testsRun}")
    print(f"Passed:                   {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures:                 {len(result.failures)}")
    print(f"Errors:                   {len(result.errors)}")
    print(f"Execution Time:           {duration:.2f} seconds")
    print(f"Overall Result:           {'ALL TESTS PASSED (SUCCESS)' if result.wasSuccessful() else 'FAILED'}")
    print("=" * 80)

    if result.wasSuccessful():
        print("\n>>> System certification verified: 100% test coverage passed.")
        return 0
    else:
        print(f"\n>>> Verification failed: {len(result.failures)} failures, {len(result.errors)} errors.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
