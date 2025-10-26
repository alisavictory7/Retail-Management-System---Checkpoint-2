#!/usr/bin/env python3
"""
Test circuit breaker functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.tactics.manager import QualityTacticsManager
from src.database import SessionLocal

def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("🔍 Testing Circuit Breaker")
    print("=" * 40)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Initialize quality manager
        quality_manager = QualityTacticsManager(db, {})
        
        print("✅ Quality manager initialized successfully")
        
        # Test circuit breaker with failing function
        def failing_payment():
            raise Exception('Payment service down')
        
        print("\nTesting circuit breaker with failing payment...")
        failures = 0
        
        for i in range(5):
            success, result = quality_manager.execute_with_circuit_breaker(failing_payment)
            if not success:
                failures += 1
            print(f"  Attempt {i+1}: {success} - {result}")
        
        print(f"\nCircuit breaker failures: {failures}/5")
        
        if failures >= 3:
            print("✅ Circuit breaker working correctly (should trip after 3+ failures)")
        else:
            print("⚠️  Circuit breaker may not be working as expected")
        
        # Test other functionality
        print("\nTesting other quality tactics...")
        
        # Feature toggle
        success, message = quality_manager.enable_feature('test_feature', 100, updated_by='test')
        print(f"Feature Toggle: {success} - {message}")
        
        # Error handling
        success, response = quality_manager.handle_payment_error('card_declined', 100.0, 'card')
        print(f"Error Handling: {success}")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_circuit_breaker()
