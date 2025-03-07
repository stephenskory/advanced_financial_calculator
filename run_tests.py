#!/usr/bin/env python3
"""Test runner for Advanced Financial Calculator
"""

import os
import sys
import unittest

if __name__ == "__main__":
    # Add the test directory to the path
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"))

    # Discover and run all tests
    test_suite = unittest.defaultTestLoader.discover("tests")
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)

    # Return appropriate exit code
    sys.exit(not result.wasSuccessful())
