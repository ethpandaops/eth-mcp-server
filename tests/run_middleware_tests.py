#!/usr/bin/env python3
"""
Script to run middleware tests with proper environment setup.

This script ensures all middleware tests run with the correct Python path
and displays detailed results.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_middleware_tests():
    """Run all middleware tests with detailed output."""
    print("=" * 80)
    print("Running Middleware Tests")
    print("=" * 80)
    
    # Set environment variables
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    # Test categories
    test_categories = [
        ("Error Handler Tests", "TestErrorHandler"),
        ("Request Validator Tests", "TestRequestValidator"),
        ("Response Formatter Tests", "TestResponseFormatter"),
        ("Middleware Integration Tests", "TestMiddlewareIntegration"),
        ("Edge Cases Tests", "TestEdgeCases"),
    ]
    
    # Run tests by category
    all_passed = True
    
    for category_name, test_class in test_categories:
        print(f"\n{'-' * 60}")
        print(f"{category_name}")
        print(f"{'-' * 60}")
        
        cmd = [
            sys.executable,
            "-m", "pytest",
            "tests/test_middleware.py",
            f"-k", test_class,
            "-v",
            "--tb=short",
            "--no-header"
        ]
        
        result = subprocess.run(cmd, env=env, cwd=project_root)
        
        if result.returncode != 0:
            all_passed = False
            print(f"\n❌ {category_name} FAILED")
        else:
            print(f"\n✅ {category_name} PASSED")
    
    # Run all tests together for coverage
    print(f"\n{'=' * 80}")
    print("Running All Middleware Tests with Coverage")
    print(f"{'=' * 80}")
    
    cmd = [
        sys.executable,
        "-m", "pytest",
        "tests/test_middleware.py",
        "-v",
        "--tb=short",
        "--cov=src.middleware",
        "--cov-report=term-missing"
    ]
    
    subprocess.run(cmd, env=env, cwd=project_root)
    
    return all_passed


def run_specific_test(test_name: str):
    """Run a specific test by name."""
    print(f"\nRunning specific test: {test_name}")
    print("-" * 60)
    
    cmd = [
        sys.executable,
        "-m", "pytest",
        "tests/test_middleware.py",
        f"-k", test_name,
        "-v",
        "-s"  # Show print statements
    ]
    
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    subprocess.run(cmd, env=env, cwd=project_root)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        run_specific_test(test_name)
    else:
        # Run all tests
        success = run_middleware_tests()
        
        print("\n" + "=" * 80)
        if success:
            print("✅ All middleware tests passed!")
        else:
            print("❌ Some middleware tests failed!")
            sys.exit(1)
        print("=" * 80)


if __name__ == "__main__":
    main()