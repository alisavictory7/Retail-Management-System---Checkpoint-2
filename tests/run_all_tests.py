#!/usr/bin/env python3
"""
Comprehensive Test Runner for Checkpoint 2 Quality Tactics
Demonstrates all 14+ quality tactics and patterns working together.
"""

import sys
import os
import pytest
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def print_banner():
    """Print test banner"""
    print("=" * 80)
    print("CHECKPOINT 2: QUALITY ATTRIBUTES & TACTICS - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"Test execution started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

def print_test_summary(results):
    """Print test execution summary"""
    print("\n" + "=" * 80)
    print("TEST EXECUTION SUMMARY")
    print("=" * 80)
    
    total_tests = results.get('total', 0)
    passed_tests = results.get('passed', 0)
    failed_tests = results.get('failed', 0)
    skipped_tests = results.get('skipped', 0)
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Skipped: {skipped_tests}")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "N/A")
    
    if failed_tests > 0:
        print(f"\n❌ {failed_tests} test(s) failed")
    else:
        print(f"\n✅ All {passed_tests} test(s) passed!")
    
    print("=" * 80)

def run_quality_attribute_tests():
    """Run tests for each quality attribute"""
    test_modules = [
        'tests.test_availability_tactics',
        'tests.test_security_tactics', 
        'tests.test_performance_tactics',
        'tests.test_modifiability_tactics',
        'tests.test_integrability_tactics',
        'tests.test_testability_tactics',
        'tests.test_usability_tactics'
    ]
    
    results = {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'skipped': 0
    }
    
    for module in test_modules:
        print(f"\n🧪 Running {module}...")
        try:
            # Run pytest for this module using file path instead of module name
            module_path = module.replace('tests.', 'tests/').replace('.', '/') + '.py'
            result = pytest.main([module_path, "-v", "--tb=short"])
            
            # Parse result (0 = success, 1 = failure, 2 = error, 3 = no tests, 4 = interrupted, 5 = usage error)
            if result == 0:
                print(f"✅ {module} - All tests passed")
                results['passed'] += 1
            else:
                print(f"❌ {module} - Some tests failed")
                results['failed'] += 1
            
            results['total'] += 1
            
        except Exception as e:
            print(f"❌ {module} - Error: {e}")
            results['failed'] += 1
            results['total'] += 1
    
    return results

def run_comprehensive_demo():
    """Run comprehensive demonstration"""
    print("\n🎯 Running Comprehensive Quality Scenarios Demonstration...")
    
    try:
        result = pytest.main([
            'tests/test_comprehensive_demo.py::TestQualityScenarioDemonstration::test_demonstrate_all_quality_attributes',
            "-v", "-s"
        ])
        
        if result == 0:
            print("✅ Comprehensive demonstration completed successfully")
            return True
        else:
            print("❌ Comprehensive demonstration failed")
            return False
            
    except Exception as e:
        print(f"❌ Comprehensive demonstration error: {e}")
        return False

def run_specific_tactic_tests():
    """Run specific tests for each tactic"""
    tactic_tests = [
        # Availability Tactics
        ("Circuit Breaker Pattern", "tests.test_availability_tactics::TestCircuitBreakerPattern"),
        ("Graceful Degradation", "tests.test_availability_tactics::TestGracefulDegradation"),
        ("Rollback Tactic", "tests.test_availability_tactics::TestRollbackTactic"),
        ("Retry Tactic", "tests.test_availability_tactics::TestRetryTactic"),
        ("Removal from Service", "tests.test_availability_tactics::TestRemovalFromService"),
        
        # Security Tactics
        ("Authenticate Actors", "tests.test_security_tactics::TestAuthenticateActors"),
        ("Validate Input", "tests.test_security_tactics::TestValidateInput"),
        
        # Performance Tactics
        ("Throttling Manager", "tests.test_performance_tactics::TestThrottlingManager"),
        ("Order Queue Manager", "tests.test_performance_tactics::TestOrderQueueManager"),
        ("Concurrency Manager", "tests.test_performance_tactics::TestConcurrencyManager"),
        ("Performance Monitor", "tests.test_performance_tactics::TestPerformanceMonitor"),
        
        # Modifiability Tactics
        ("Adapter Pattern", "tests.test_modifiability_tactics::TestAdapterPattern"),
        ("Feature Toggle", "tests.test_modifiability_tactics::TestFeatureToggle"),
        ("Partner Data Intermediary", "tests.test_modifiability_tactics::TestPartnerDataIntermediary"),
        
        # Integrability Tactics
        ("Reseller API Adapter", "tests.test_integrability_tactics::TestTailorInterface"),
        ("Message Broker", "tests.test_integrability_tactics::TestUseIntermediary"),
        ("Publish-Subscribe", "tests.test_integrability_tactics::TestPublishSubscribe"),
        
        # Testability Tactics
        ("Dependency Injection", "tests.test_testability_tactics::TestDependencyInjection"),
        ("Record/Playback", "tests.test_testability_tactics::TestRecordPlayback"),
        
        # Usability Tactics
        ("User Error Handler", "tests.test_usability_tactics::TestUserErrorHandler"),
        ("Progress Indicator", "tests.test_usability_tactics::TestProgressIndicator"),
    ]
    
    print("\n🔍 Running Individual Tactic Tests...")
    print("-" * 60)
    
    passed = 0
    failed = 0
    
    for tactic_name, test_path in tactic_tests:
        print(f"\nTesting {tactic_name}...")
        try:
            # Convert module::class format to file::class format
            if '::' in test_path:
                file_part, class_part = test_path.split('::', 1)
                file_path = file_part.replace('tests.', 'tests/').replace('.', '/') + '.py'
                test_path = f"{file_path}::{class_part}"
            else:
                test_path = test_path.replace('tests.', 'tests/').replace('.', '/') + '.py'
            
            result = pytest.main([test_path, "-v", "--tb=short", "-q"])
            if result == 0:
                print(f"✅ {tactic_name}")
                passed += 1
            else:
                print(f"❌ {tactic_name}")
                failed += 1
        except Exception as e:
            print(f"❌ {tactic_name} - Error: {e}")
            failed += 1
    
    print(f"\n📊 Individual Tactic Results: {passed} passed, {failed} failed")
    return passed, failed

def main():
    """Main test runner"""
    print_banner()
    
    start_time = time.time()
    
    # Run comprehensive quality attribute tests
    print("\n🚀 PHASE 1: Quality Attribute Tests")
    print("-" * 40)
    results = run_quality_attribute_tests()
    
    # Run individual tactic tests
    print("\n🚀 PHASE 2: Individual Tactic Tests")
    print("-" * 40)
    passed, failed = run_specific_tactic_tests()
    
    # Run comprehensive demonstration
    print("\n🚀 PHASE 3: Comprehensive Demonstration")
    print("-" * 40)
    demo_success = run_comprehensive_demo()
    
    # Calculate final results
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Print final summary
    print_test_summary({
        'total': results['total'] + passed + failed + 1,  # +1 for demo
        'passed': results['passed'] + passed + (1 if demo_success else 0),
        'failed': results['failed'] + failed + (0 if demo_success else 1),
        'skipped': results['skipped']
    })
    
    print(f"\n⏱️  Total execution time: {execution_time:.2f} seconds")
    
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
    if results['failed'] > 0 or failed > 0 or not demo_success:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
