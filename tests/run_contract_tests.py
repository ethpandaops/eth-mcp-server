#!/usr/bin/env python3
"""
Simple script to run contract tests and display summary.
"""
import subprocess
import sys

def run_tests():
    """Run the contract tests using pytest."""
    print("Running contract tests...")
    print("-" * 60)
    
    try:
        # Run pytest with verbose output
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_contract.py", "-v", "--tb=short"],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
            
        return result.returncode
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)