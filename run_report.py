"""Validation Testing Report Runner for ByteFlow.

Executes tests/test_validation.py and formats the exact inputs, expected outputs,
actual outputs, and execution runtimes for TC1 through TC6.
"""

import sys
import time
import unittest

# Ensure workspace root is in sys.path
sys.path.insert(0, ".")

from tests.test_validation import TestByteFlowValidationSuite


def main():
    print("=" * 80)
    print(" BYTEFLOW VALIDATION TEST SUITE RUNNER (TC1 - TC6)")
    print("=" * 80)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestByteFlowValidationSuite)
    runner = unittest.TextTestRunner(verbosity=1)
    start_all = time.perf_counter()
    result = runner.run(suite)
    total_time = time.perf_counter() - start_all

    print("\n" + "=" * 80)
    print(" VALIDATION TEST CASE METRICS SUMMARY (TC1 - TC6)")
    print("=" * 80)

    records = getattr(TestByteFlowValidationSuite, "test_records", {})
    for tc_id in sorted(records.keys()):
        data = records[tc_id]
        print(f"[{tc_id}] {data['name']}")
        print(f"  • Execution Runtime : {data['runtime_s'] * 1000.0:.2f} ms ({data['runtime_s']:.4f} s)")
        print(f"  • Test Inputs       : {data['inputs']}")
        print(f"  • Expected Output   : {data['expected']}")
        print(f"  • Actual Output     : {data['actual']}")
        print("-" * 80)

    print(f"Overall Result: {'ALL PASS (100%)' if result.wasSuccessful() else 'FAIL'}")
    print(f"Ran {result.testsRun} tests in {total_time:.3f}s (Errors: {len(result.errors)}, Failures: {len(result.failures)})")
    print("=" * 80)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
