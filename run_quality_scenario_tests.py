#!/usr/bin/env python3
"""
Quality Scenario Test Runner

This script runs all quality scenario tests and provides detailed reporting
on whether each response measure is fulfilled or not.

Usage:
    python run_quality_scenario_tests.py
"""

import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def print_header():
    """Print the test runner header."""
    print("\n" + "="*80)
    print("🎯 QUALITY SCENARIO VALIDATION TEST SUITE")
    print("="*80)
    print(f"Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*80)
    print("This test suite validates all quality scenarios from Project Deliverable 2")
    print("Documentation.md with specific verification of response measures.")
    print("="*80)


def run_quality_scenario_tests():
    """Run all quality scenario tests with detailed reporting."""
    print_header()
    
    # Test files to run
    test_files = [
        "tests/test_quality_scenario_validation.py",
        "tests/test_quality_scenarios.py"
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_file in test_files:
        if not Path(test_file).exists():
            print(f"⚠️  Test file {test_file} not found, skipping...")
            continue
            
        print(f"\n🧪 Running {test_file}...")
        print("-" * 60)
        
        try:
            # Run pytest with detailed output
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                test_file, 
                "-v", 
                "--tb=short",
                "--capture=no",  # Show print statements
                "--durations=10"  # Show slowest 10 tests
            ], capture_output=True, text=True, timeout=300)  # 5 minute timeout
            
            # Parse results
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if '::' in line and ('PASSED' in line or 'FAILED' in line):
                    total_tests += 1
                    if 'PASSED' in line:
                        passed_tests += 1
                    elif 'FAILED' in line:
                        failed_tests += 1
            
            # Print output
            print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            
            if result.returncode == 0:
                print(f"✅ {test_file} completed successfully")
            else:
                print(f"❌ {test_file} had failures (exit code: {result.returncode})")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_file} timed out after 5 minutes")
            failed_tests += 1
            total_tests += 1
        except Exception as e:
            print(f"💥 Error running {test_file}: {e}")
            failed_tests += 1
            total_tests += 1
    
    return total_tests, passed_tests, failed_tests


def print_summary(total_tests, passed_tests, failed_tests):
    """Print the test summary."""
    print("\n" + "="*80)
    print("📊 QUALITY SCENARIO VALIDATION SUMMARY")
    print("="*80)
    print(f"Completed at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*80)
    
    if total_tests > 0:
        success_rate = (passed_tests / total_tests) * 100
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate == 100.0:
            print(f"\n🎉 ALL QUALITY SCENARIOS SUCCESSFULLY VALIDATED!")
            print("   The retail management system meets all documented quality requirements.")
            print("   All response measures have been verified and fulfilled.")
        elif success_rate >= 90.0:
            print(f"\n✅ EXCELLENT QUALITY VALIDATION!")
            print(f"   {success_rate:.1f}% of scenarios validated - system meets most quality requirements.")
        elif success_rate >= 80.0:
            print(f"\n⚠️  GOOD QUALITY VALIDATION")
            print(f"   {success_rate:.1f}% of scenarios validated - some improvements needed.")
        else:
            print(f"\n❌ QUALITY VALIDATION NEEDS IMPROVEMENT")
            print(f"   {success_rate:.1f}% of scenarios validated - significant improvements required.")
    else:
        print("⚠️  No tests were executed.")
    
    print("="*80)
    
    return success_rate if total_tests > 0 else 0


def main():
    """Main function."""
    start_time = time.time()
    
    try:
        # Run quality scenario tests
        total_tests, passed_tests, failed_tests = run_quality_scenario_tests()
        
        # Print summary
        success_rate = print_summary(total_tests, passed_tests, failed_tests)
        
        # Calculate total time
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\n⏱️  Total execution time: {total_time:.2f} seconds")
        
        # Return appropriate exit code
        if success_rate == 100.0:
            print("\n🎯 Quality scenario validation completed successfully!")
            return 0
        else:
            print(f"\n⚠️  Quality scenario validation completed with {failed_tests} failures.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Test execution interrupted by user.")
        return 130
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
