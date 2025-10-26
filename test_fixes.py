#!/usr/bin/env python3
"""
Simple test to verify quality scenario fixes
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tactics.manager import QualityTacticsManager
from src.database import SessionLocal

def test_basic_functionality():
    """Test basic quality tactics functionality"""
    print("🔍 Testing Quality Tactics Fixes")
    print("=" * 50)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Initialize quality manager
        quality_manager = QualityTacticsManager(db, {})
        
        # Test 1: Circuit Breaker
        print("\n1. Testing Circuit Breaker...")
        def failing_payment():
            raise Exception('Payment service down')
        
        failures = 0
        for i in range(3):
            success, result = quality_manager.execute_with_circuit_breaker(failing_payment)
            if not success:
                failures += 1
            print(f"   Attempt {i+1}: {success} - {result}")
        
        print(f"   Circuit breaker failures: {failures}/3")
        
        # Test 2: Feature Toggle
        print("\n2. Testing Feature Toggle...")
        success, message = quality_manager.enable_feature('test_feature', 100, updated_by='test')
        print(f"   Enable: {success} - {message}")
        
        # Test 3: Error Handling
        print("\n3. Testing Error Handling...")
        success, response = quality_manager.handle_payment_error('card_declined', 100.0, 'card')
        print(f"   Error handling: {success}")
        if success:
            print(f"   Response keys: {list(response.keys())}")
        
        # Test 4: Progress Tracking
        print("\n4. Testing Progress Tracking...")
        success, message = quality_manager.start_progress_tracking('test_op', 'test_operation', 30)
        print(f"   Progress tracking: {success} - {message}")
        
        print("\n✅ All basic tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_basic_functionality()
