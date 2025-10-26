#!/usr/bin/env python3
"""
Simple test runner for Checkpoint 2 Quality Tactics
Run this script to execute all quality tactics tests.
"""

import sys
import os
import subprocess
import time
from datetime import datetime

def print_banner():
    """Print test banner"""
    print("=" * 80)
    print("CHECKPOINT 2: QUALITY ATTRIBUTES & TACTICS - TEST SUITE")
    print("=" * 80)
    print(f"Test execution started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

def run_pytest_command(test_path, description):
    """Run pytest command and return results"""
    print(f"\n🧪 {description}")
    print("-" * 60)
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"
        ], capture_output=True, text=True, timeout=300)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out after 5 minutes")
        return False, "", "Timeout"
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False, "", str(e)

def main():
    """Main test runner"""
    print_banner()
    
    start_time = time.time()
    
    # Test modules to run
    test_modules = [
        ("tests/test_availability_tactics.py", "Availability Tactics (Circuit Breaker, Graceful Degradation, Rollback, Retry, Removal from Service)"),
        ("tests/test_security_tactics.py", "Security Tactics (Authenticate Actors, Validate Input)"),
        ("tests/test_performance_tactics.py", "Performance Tactics (Throttling, Queuing, Concurrency, Monitoring)"),
        ("tests/test_modifiability_tactics.py", "Modifiability Tactics (Adapter Pattern, Feature Toggle, Intermediary)"),
        ("tests/test_integrability_tactics.py", "Integrability Tactics (Tailor Interface, Adapter, Publish-Subscribe)"),
        ("tests/test_testability_tactics.py", "Testability Tactics (Record/Playback, Dependency Injection)"),
        ("tests/test_usability_tactics.py", "Usability Tactics (Error Handling, Progress Indicator)"),
        ("tests/test_integration.py", "Integration Tests (All Quality Tactics Working Together)"),
        ("tests/test_comprehensive_demo.py", "Comprehensive Quality Scenarios Demonstration")
    ]
    
    results = []
    
    # Run each test module
    for test_path, description in test_modules:
        if os.path.exists(test_path):
            success, stdout, stderr = run_pytest_command(test_path, description)
            results.append({
                'module': test_path,
                'description': description,
                'success': success,
                'stdout': stdout,
                'stderr': stderr
            })
        else:
            print(f"\n⚠️  {description}")
            print(f"   File not found: {test_path}")
            results.append({
                'module': test_path,
                'description': description,
                'success': False,
                'stdout': "",
                'stderr': f"File not found: {test_path}"
            })
    
    # Calculate summary
    end_time = time.time()
    execution_time = end_time - start_time
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['success'])
    failed_tests = total_tests - passed_tests
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST EXECUTION SUMMARY")
    print("=" * 80)
    
    for result in results:
        status = "✅ PASSED" if result['success'] else "❌ FAILED"
        print(f"{status} - {result['description']}")
        if not result['success'] and result['stderr']:
            print(f"    Error: {result['stderr']}")
    
    print("\n" + "-" * 80)
    print(f"Total Test Modules: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
    print(f"Execution Time: {execution_time:.2f} seconds")
    print("=" * 80)
    
    # Print quality tactics summary
    print("\n📋 QUALITY TACTICS IMPLEMENTED:")
    print("-" * 40)
    
    tactics = [
        "✅ Circuit Breaker Pattern (Availability)",
        "✅ Graceful Degradation (Availability)", 
        "✅ Rollback Tactic (Availability)",
        "✅ Retry Tactic (Availability)",
        "✅ Removal from Service (Availability)",
        "✅ Authenticate Actors (Security)",
        "✅ Validate Input (Security)",
        "✅ Throttling Manager (Performance)",
        "✅ Order Queue Manager (Performance)",
        "✅ Concurrency Manager (Performance)",
        "✅ Performance Monitor (Performance)",
        "✅ Adapter Pattern (Modifiability)",
        "✅ Feature Toggle (Modifiability)",
        "✅ Partner Data Intermediary (Modifiability)",
        "✅ Reseller API Adapter (Integrability)",
        "✅ Message Broker (Integrability)",
        "✅ Publish-Subscribe (Integrability)",
        "✅ Dependency Injection (Testability)",
        "✅ Record/Playback (Testability)",
        "✅ User Error Handler (Usability)",
        "✅ Progress Indicator (Usability)"
    ]
    
    for tactic in tactics:
        print(tactic)
    
    print(f"\n🎯 Total Quality Tactics Implemented: {len(tactics)}")
    print("=" * 80)
    
    # Return appropriate exit code
    if failed_tests > 0:
        print(f"\n❌ {failed_tests} test module(s) failed")
        sys.exit(1)
    else:
        print(f"\n✅ All {passed_tests} test module(s) passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
