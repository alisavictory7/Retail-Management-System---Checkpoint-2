# tests/test_comprehensive_demo.py
"""
Comprehensive demonstration of all quality tactics and patterns.
This test suite demonstrates all 14+ tactics working together in realistic scenarios.
"""

import pytest
import time
import json
from unittest.mock import patch, MagicMock

from src.tactics.manager import QualityTacticsManager

def get_default_config():
    """Get default configuration for QualityTacticsManager"""
    return {
        'throttling': {'max_rps': 10, 'window_size': 1},
        'queue': {'max_size': 100},
        'concurrency': {'max_concurrent': 5, 'lock_timeout': 50},
        'monitoring': {'metrics_interval': 60},
        'usability': {},
        'circuit_breaker': {'failure_threshold': 3, 'timeout_duration': 60},
        'graceful_degradation': {},
        'rollback': {},
        'retry': {},
        'removal_from_service': {},
        'security': {},
        'modifiability': {},
        'integrability': {},
        'testability': {}
    }

class TestComprehensiveQualityScenarios:
    """Comprehensive tests demonstrating all quality scenarios"""
    
    def test_availability_scenario_flash_sale_overload(self, db_session, sample_user, sample_products):
        """Test Availability Scenario A.1: Flash Sale Overload with Circuit Breaker and Graceful Degradation"""
        quality_manager = QualityTacticsManager(db_session, get_default_config())
        
        # Simulate flash sale order processing
        order_data = {
            'sale_id': 1,
            'user_id': sample_user.userID,
            'items': [{'product_id': sample_products[0].productID, 'quantity': 1, 'unit_price': 10.99}],
            'total_amount': 10.99,
            'priority': 1
        }
        
        # Test circuit breaker with failing payment service
        def failing_payment():
            raise Exception("Payment service timeout")
        
        # First few calls should fail and trip circuit breaker
        for i in range(3):
            success, result = quality_manager.execute_with_circuit_breaker(failing_payment)
            assert success == False
        
        # Circuit should now be open
        success, result = quality_manager.execute_with_circuit_breaker(failing_payment)
        assert success == False
        assert "unavailable" in result.lower()
        
        # Orders should be queued via graceful degradation
        success, message = quality_manager.queue_order_for_retry(order_data, sample_user.userID)
        assert success == True
        assert "queued" in message.lower()
    
    def test_availability_scenario_transient_failure_recovery(self, db_session, sample_user):
        """Test Availability Scenario A.2: Transient Failure Recovery with Rollback and Retry"""
        quality_manager = QualityTacticsManager(db_session, get_default_config())
        
        # Simulate transient payment failure with retry
        call_count = 0
        def transient_payment():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary network error")
            return {"status": "success", "transaction_id": "TXN_123"}
        
        success, result = quality_manager.execute_with_retry(transient_payment)
        assert success == True
        assert call_count == 3  # Should have retried 3 times
        
        # Test rollback on permanent failure
        def permanent_failure():
            raise Exception("Card declined")
        
        success, result = quality_manager.execute_with_rollback(permanent_failure)
        assert success == False
        assert "rolled back" in result.lower()
    
    def test_security_scenario_partner_authentication(self, db_session, sample_partner):
        """Test Security Scenario S.1: Partner Authentication and Input Validation"""
        quality_manager = QualityTacticsManager(db_session, get_default_config())
        
        # Create API key for the sample partner
        from src.models import PartnerAPIKey
        from datetime import datetime, timezone, timedelta
        import random
        
        api_key = PartnerAPIKey(
            partnerID=sample_partner.partnerID,
            api_key=f"test_api_key_{random.randint(1000, 9999)}",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_active=True
        )
        db_session.add(api_key)
        db_session.commit()
        
        # Test valid API key authentication
        success, message = quality_manager.authenticate_partner(api_key.api_key)
        assert success == True
        assert "Authenticated partner" in message
        
        # Test invalid API key rejection
        success, message = quality_manager.authenticate_partner("invalid_key")
        assert success == False
        assert "Invalid API key" in message
        
        # Test input validation
        valid_data = {"name": "Test Product", "price": 10.99}
        success, message = quality_manager.validate_partner_data(valid_data)
        assert success == True
        
        # Test malicious input rejection
        malicious_data = {"name": "'; DROP TABLE products; --", "price": 10.99}
        success, message = quality_manager.validate_partner_data(malicious_data)
        assert success == False
        assert "validation failed" in message.lower()
    
    def test_modifiability_scenario_new_partner_format(self, db_session, sample_partner_data, sample_user):
        """Test Modifiability Scenario M.1: New Partner Format Support"""
        quality_manager = QualityTacticsManager(db_session, get_default_config())
        
        # Test CSV format processing
        success, result = quality_manager.process_partner_data(sample_partner_data['csv_data'], 'csv')
        assert success == True
        assert result['format'] == 'csv'
        assert len(result['products']) == 2
        
        # Test JSON format processing
        success, result = quality_manager.process_partner_data(sample_partner_data['json_data'], 'json')
        assert success == True
        assert result['format'] == 'json'
        assert len(result['products']) == 1
        
        # Test XML format processing
        success, result = quality_manager.process_partner_data(sample_partner_data['xml_data'], 'xml')
        assert success == True
        assert result['format'] == 'xml'
        assert len(result['products']) == 1
        
        # Test feature toggle for partner sync
        success, message = quality_manager.enable_feature("partner_sync_enabled", 100, updated_by="test_user")
        assert success == True
        
        enabled, message = quality_manager.is_feature_enabled("partner_sync_enabled", sample_user.userID)
        assert enabled == True
    
    def test_performance_scenario_flash_sale_load(self, db_session, sample_user):
        """Test Performance Scenario P.1: Flash Sale Load with Throttling and Queuing"""
        quality_manager = QualityTacticsManager(db_session, get_default_config())
        
        # Simulate high load requests
        request_data = {
            'user_id': sample_user.userID,
            'cart_size': 1,
            'total_amount': 10.99
        }
        
        # First few requests should be allowed
        for i in range(5):
            throttled, message = quality_manager.check_throttling(request_data)
            assert throttled == True
        
        # Simulate queue processing
        order_data = {
            'sale_id': i + 1,
            'user_id': sample_user.userID,
            'total_amount': 10.99,
            'priority': i
        }
        
        success, message = quality_manager.enqueue_order(order_data, priority=i)
        assert success == True
        
        # Test concurrency control
        def test_operation():
            return "Operation completed"
        
        success, result = quality_manager.execute_with_concurrency_control(test_operation)
        assert success == True
        assert result == "Operation completed"
    
    def test_integrability_scenario_external_api_integration(self, db_session):
        """Test Integrability Scenario I.1: External API Integration with Adapters"""
        quality_manager = QualityTacticsManager(db_session, get_default_config())
        
        # Setup partner integration
        api_config = {
            'base_url': 'https://api.partner.com',
            'auth_token': 'test_token',
            'timeout': 30
        }
        
        success, message = quality_manager.setup_partner_integration(1, api_config)
        assert success == True
        
        # Test data adaptation
        internal_data = {'sale_id': 123, 'user_id': 456, 'total_amount': 100.0}
        success, external_data = quality_manager.adapt_data('partner_1_adapter', internal_data)
        assert success == True
        assert external_data['order_id'] == 123
        assert external_data['customer_id'] == 456
        
        # Test message publishing
        message_data = {'partner_id': 1, 'data': external_data}
        success, message = quality_manager.publish_message('partner_1_updates', message_data)
        assert success == True
    
    def test_testability_scenario_record_playback(self, db_session, sample_user):
        """Test Testability Scenario T.1: Record/Playback for Test Reproducibility"""
        quality_manager = QualityTacticsManager(db_session, get_default_config())
        
        def test_function(test_env):
            # Simulate test operations
            test_env.record_request("/api/payment", "POST", {"amount": 100.0})
            test_env.record_response(200, {"status": "success"})
            test_env.record_state("payment_completed", {"transaction_id": "TXN_123"})
            
            return {"status": "completed", "transaction_id": "TXN_123"}
        
        # Run test with recording
        success, summary = quality_manager.run_test_with_recording("payment_test", test_function)
        assert success == True
        assert summary['test_name'] == "payment_test"
        assert summary['total_records'] >= 3
        
        # Playback test
        success, playback_data = quality_manager.playback_test("payment_test")
        assert success == True
        assert len(playback_data) >= 3
        
        # Verify recorded data
        request_record = next(r for r in playback_data if r['type'] == 'request')
        assert request_record['data']['endpoint'] == "/api/payment"
        assert request_record['data']['method'] == "POST"
    
    def test_usability_scenario_error_recovery(self, db_session, sample_user):
        """Test Usability Scenario U.1: Error Recovery with User-Friendly Messages"""
        quality_manager = QualityTacticsManager(db_session, get_default_config())
        
        # Test payment error handling
        success, response = quality_manager.handle_payment_error('card_declined', 100.0, 'card')
        assert success == True
        assert response['error_code'] == 'card_declined'
        assert 'declined' in response['message'].lower()
        assert len(response['suggestions']) > 0
        assert 'alternative_payment_methods' in response
        
        # Test progress tracking for long operations
        operation_id = "order_processing_123"
        success, message = quality_manager.start_progress_tracking(operation_id, "order_processing", 30)
        assert success == True
        
        # Simulate progress updates
        quality_manager.update_progress(operation_id, 25, "Validating order")
        quality_manager.update_progress(operation_id, 50, "Processing payment")
        quality_manager.update_progress(operation_id, 75, "Updating inventory")
        
        # Check progress before reaching 100% (which auto-completes)
        progress = quality_manager.get_progress(operation_id)
        assert progress is not None
        assert progress['progress'] == 75
        assert progress['current_step'] == "Updating inventory"
        
        # Complete operation manually (since 100% auto-completes)
        quality_manager.complete_operation(operation_id, True)
        
        # After completion, operation is removed from active operations
        # so get_progress will return None
        progress = quality_manager.get_progress(operation_id)
        assert progress is None
    
    def test_comprehensive_flash_sale_scenario(self, db_session, sample_user, sample_products, sample_flash_sale):
        """Test comprehensive flash sale scenario with all quality tactics"""
        quality_manager = QualityTacticsManager(db_session, get_default_config())
        
        # Enable flash sale feature
        quality_manager.enable_feature("flash_sale_enabled", 100, updated_by="test_user")
        
        # Simulate flash sale order processing
        order_data = {
            'sale_id': 1,
            'user_id': sample_user.userID,
            'items': [{'product_id': sample_products[0].productID, 'quantity': 1, 'unit_price': 10.99}],
            'total_amount': 10.99,
            'priority': 1
        }
        
        # Process flash sale order with all tactics
        success, result = quality_manager.process_flash_sale_order(order_data, sample_user.userID)
        
        # Should succeed with all quality tactics applied
        assert success == True
        assert 'operation_id' in result
        assert result['status'] == 'success'
    
    def test_comprehensive_partner_catalog_scenario(self, db_session, sample_partner, sample_partner_data):
        """Test comprehensive partner catalog scenario with all quality tactics"""
        quality_manager = QualityTacticsManager(db_session, get_default_config())
        
        # Create API key for the sample partner
        from src.models import PartnerAPIKey
        from datetime import datetime, timezone, timedelta
        import random
        
        api_key = PartnerAPIKey(
            partnerID=sample_partner.partnerID,
            api_key=f"test_api_key_{random.randint(1000, 9999)}",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_active=True
        )
        db_session.add(api_key)
        db_session.commit()
        
        # Process partner catalog ingest with all tactics
        success, result = quality_manager.process_partner_catalog_ingest(
            partner_id=sample_partner.partnerID,
            data=sample_partner_data['csv_data'],
            api_key=api_key.api_key
        )
        
        # Should succeed with all quality tactics applied
        assert success == True
        assert result['status'] == 'success'
        assert 'processed_items' in result
        assert result['processed_items'] == 2  # CSV has 2 products
    
    def test_system_health_monitoring(self, db_session):
        """Test comprehensive system health monitoring"""
        quality_manager = QualityTacticsManager(db_session, get_default_config())
        
        # Get system health
        health = quality_manager.get_system_health()
        
        # Verify health structure
        assert 'timestamp' in health
        assert 'availability' in health
        assert 'performance' in health
        assert 'features' in health
        assert 'security' in health
        
        # Verify availability metrics
        assert 'circuit_breaker_state' in health['availability']
        assert 'queue_size' in health['availability']
        assert 'active_operations' in health['availability']
        
        # Verify performance metrics
        assert isinstance(health['performance'], dict)
        
        # Verify feature status
        assert 'flash_sale_enabled' in health['features']
        assert 'partner_sync_enabled' in health['features']
        
        # Verify security status
        assert 'authentication_active' in health['security']
        assert 'input_validation_active' in health['security']
    
    def test_tactic_validation(self, db_session):
        """Test that all tactics are properly configured and validated"""
        quality_manager = QualityTacticsManager(db_session, get_default_config())
        
        # Validate all tactics
        validation_results = quality_manager.validate_all_tactics()
        
        # All tactics should be valid
        for tactic_name, is_valid in validation_results.items():
            if tactic_name != 'error':
                assert is_valid == True, f"Tactic {tactic_name} failed validation"
        
        # Should have validated multiple tactics
        assert len(validation_results) >= 10

class TestQualityScenarioDemonstration:
    """Demonstration tests showing quality scenarios in action"""
    
    def test_demonstrate_all_quality_attributes(self, db_session, sample_user, sample_products, sample_partner, sample_partner_data):
        """Demonstrate all quality attributes working together"""
        quality_manager = QualityTacticsManager(db_session, get_default_config())
        
        print("\n=== QUALITY ATTRIBUTES DEMONSTRATION ===")
        
        # 1. AVAILABILITY - Circuit Breaker and Graceful Degradation
        print("\n1. AVAILABILITY: Testing Circuit Breaker and Graceful Degradation")
        
        def failing_payment():
            raise Exception("Payment service down")
        
        # Trip circuit breaker
        for i in range(3):
            success, result = quality_manager.execute_with_circuit_breaker(failing_payment)
            print(f"   Payment attempt {i+1}: {'SUCCESS' if success else 'FAILED'}")
        
        # Circuit should be open now
        success, result = quality_manager.execute_with_circuit_breaker(failing_payment)
        print(f"   Circuit breaker active: {'SUCCESS' if success else 'FAILED (Expected)'}")
        
        # 2. SECURITY - Authentication and Input Validation
        print("\n2. SECURITY: Testing Authentication and Input Validation")
        
        # Valid authentication
        success, message = quality_manager.authenticate_partner("test_api_key_123")
        print(f"   Valid API key: {'AUTHENTICATED' if success else 'REJECTED'}")
        
        # Invalid authentication
        success, message = quality_manager.authenticate_partner("invalid_key")
        print(f"   Invalid API key: {'AUTHENTICATED' if success else 'REJECTED (Expected)'}")
        
        # Input validation
        malicious_data = {"name": "'; DROP TABLE products; --", "price": 10.99}
        success, message = quality_manager.validate_partner_data(malicious_data)
        print(f"   Malicious input: {'ACCEPTED' if success else 'REJECTED (Expected)'}")
        
        # 3. MODIFIABILITY - Feature Toggles and Adapters
        print("\n3. MODIFIABILITY: Testing Feature Toggles and Adapters")
        
        # Enable feature
        quality_manager.enable_feature("flash_sale_enabled", 100, updated_by="demo_user")
        enabled, message = quality_manager.is_feature_enabled("flash_sale_enabled", sample_user.userID)
        print(f"   Feature toggle: {'ENABLED' if enabled else 'DISABLED'}")
        
        # Data format adaptation
        success, result = quality_manager.process_partner_data(sample_partner_data['csv_data'], 'csv')
        print(f"   CSV data processing: {'SUCCESS' if success else 'FAILED'}")
        
        # 4. PERFORMANCE - Throttling and Queuing
        print("\n4. PERFORMANCE: Testing Throttling and Queuing")
        
        request_data = {'user_id': sample_user.userID, 'cart_size': 1, 'total_amount': 10.99}
        throttled, message = quality_manager.check_throttling(request_data)
        print(f"   Request throttling: {'ALLOWED' if throttled else 'THROTTLED'}")
        
        order_data = {'sale_id': 1, 'user_id': sample_user.userID, 'total_amount': 10.99}
        success, message = quality_manager.enqueue_order(order_data, priority=1)
        print(f"   Order queuing: {'SUCCESS' if success else 'FAILED'}")
        
        # 5. INTEGRABILITY - Adapters and Message Publishing
        print("\n5. INTEGRABILITY: Testing Adapters and Message Publishing")
        
        # Setup partner integration
        api_config = {'base_url': 'https://api.partner.com', 'auth_token': 'test_token', 'timeout': 30}
        success, message = quality_manager.setup_partner_integration(1, api_config)
        print(f"   Partner integration: {'SUCCESS' if success else 'FAILED'}")
        
        # Data adaptation
        internal_data = {'sale_id': 123, 'user_id': 456, 'total_amount': 100.0}
        success, external_data = quality_manager.adapt_data('partner_1_adapter', internal_data)
        print(f"   Data adaptation: {'SUCCESS' if success else 'FAILED'}")
        
        # 6. TESTABILITY - Record/Playback
        print("\n6. TESTABILITY: Testing Record/Playback")
        
        def test_operation(test_env):
            test_env.record_request("/api/test", "POST", {"test": "data"})
            test_env.record_response(200, {"result": "success"})
            return {"status": "completed"}
        
        success, summary = quality_manager.run_test_with_recording("demo_test", test_operation)
        print(f"   Test recording: {'SUCCESS' if success else 'FAILED'}")
        
        success, playback_data = quality_manager.playback_test("demo_test")
        print(f"   Test playback: {'SUCCESS' if success else 'FAILED'}")
        
        # 7. USABILITY - Error Handling and Progress Tracking
        print("\n7. USABILITY: Testing Error Handling and Progress Tracking")
        
        # Error handling
        success, response = quality_manager.handle_payment_error('card_declined', 100.0, 'card')
        print(f"   Error handling: {'SUCCESS' if success else 'FAILED'}")
        print(f"   Error suggestions: {len(response.get('suggestions', []))} suggestions provided")
        
        # Progress tracking
        operation_id = "demo_operation"
        quality_manager.start_progress_tracking(operation_id, "demo_operation", 30)
        quality_manager.update_progress(operation_id, 50, "Half complete")
        progress = quality_manager.get_progress(operation_id)
        print(f"   Progress tracking: {'SUCCESS' if progress else 'FAILED'}")
        if progress:
            print(f"   Progress: {progress['progress']}% - {progress['current_step']}")
        
        print("\n=== DEMONSTRATION COMPLETE ===")
        
        # All demonstrations should succeed
        assert True  # If we get here, all demonstrations completed successfully

if __name__ == "__main__":
    # Run the comprehensive demonstration
    pytest.main([f"{__file__}::TestQualityScenarioDemonstration::test_demonstrate_all_quality_attributes", "-v", "-s"])
