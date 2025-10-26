# tests/test_testability_tactics.py
"""
Comprehensive tests for Testability tactics:
- Record/Playback
- Dependency Injection
"""

import pytest
import json
import time
from unittest.mock import patch, MagicMock

from src.tactics.testability import (
    TestabilityManager, TestEnvironment, TestRecorder,
    ServiceContainer, MockPaymentService, MockPartnerAPI, MockDatabase
)

class TestDependencyInjection:
    """Test Dependency Injection framework"""
    
    def test_service_container_registration(self):
        """Test service registration in container"""
        container = ServiceContainer()
        
        # Register service
        container.register(MockPaymentService, MockPaymentService)
        
        # Get service
        service = container.get(MockPaymentService)
        assert isinstance(service, MockPaymentService)
    
    def test_service_container_singleton(self):
        """Test singleton service registration"""
        container = ServiceContainer()
        
        # Register as singleton
        container.register(MockPaymentService, MockPaymentService, singleton=True)
        
        # Get service twice
        service1 = container.get(MockPaymentService)
        service2 = container.get(MockPaymentService)
        
        # Should be the same instance
        assert service1 is service2
    
    def test_service_container_instance_registration(self):
        """Test registering service instance"""
        container = ServiceContainer()
        
        # Create instance
        instance = MockPaymentService(should_fail=True)
        
        # Register instance
        container.register_instance(MockPaymentService, instance)
        
        # Get service
        service = container.get(MockPaymentService)
        assert service is instance
    
    def test_service_container_clear(self):
        """Test clearing container"""
        container = ServiceContainer()
        
        # Register service
        container.register(MockPaymentService, MockPaymentService)
        
        # Clear container
        container.clear()
        
        # Should not find service
        with pytest.raises(ValueError):
            container.get(MockPaymentService)
    
    def test_inject_decorator(self):
        """Test inject decorator"""
        from src.tactics.testability import inject
        
        container = ServiceContainer()
        container.register_instance(MockPaymentService, MockPaymentService())
        
        # Mock the global container
        with patch('src.tactics.testability.container', container):
            service = inject(MockPaymentService)
            assert isinstance(service, MockPaymentService)

class TestMockServices:
    """Test mock services for testing"""
    
    def test_mock_payment_service_success(self):
        """Test successful mock payment service"""
        service = MockPaymentService(should_fail=False)
        
        success, result = service.process_payment(100.0, "card")
        
        assert success == True
        assert "successful" in result
        assert service.call_count == 1
    
    def test_mock_payment_service_failure(self):
        """Test failing mock payment service"""
        service = MockPaymentService(should_fail=True)
        
        success, result = service.process_payment(100.0, "card")
        
        assert success == False
        assert "failure" in result
        assert service.call_count == 1
    
    def test_mock_payment_service_failure_rate(self):
        """Test mock payment service with failure rate"""
        service = MockPaymentService(failure_rate=0.5)  # 50% failure rate
        
        results = []
        for i in range(10):
            success, result = service.process_payment(100.0, "card")
            results.append(success)
        
        # Should have some failures (approximately 50%)
        failure_count = sum(1 for success in results if not success)
        assert failure_count > 0
        assert service.call_count == 10
    
    def test_mock_payment_service_reset(self):
        """Test resetting mock payment service"""
        service = MockPaymentService(should_fail=True, failure_rate=0.5)
        
        # Make some calls
        service.process_payment(100.0, "card")
        service.process_payment(100.0, "card")
        
        # Reset
        service.reset()
        
        assert service.call_count == 0
        assert service.should_fail == False
        assert service.failure_rate == 0.0
    
    def test_mock_partner_api(self):
        """Test mock partner API"""
        response_data = [
            {'id': 1, 'name': 'Product A', 'price': 10.99},
            {'id': 2, 'name': 'Product B', 'price': 25.50}
        ]
        
        service = MockPartnerAPI(response_data)
        
        products = service.fetch_products(1)
        
        assert len(products) == 2
        assert products[0]['name'] == 'Product A'
        assert service.call_count == 1
    
    def test_mock_database(self):
        """Test mock database"""
        db = MockDatabase()
        
        # Create mock object
        class MockObject:
            def __init__(self, id, name):
                self.id = id
                self.name = name
        
        obj1 = MockObject(1, "Test 1")
        obj2 = MockObject(2, "Test 2")
        
        # Add objects
        db.add(obj1)
        db.add(obj2)
        
        # Query objects
        results = db.query(MockObject).all()
        assert len(results) == 2
        
        # Filter query
        filtered = db.query(MockObject).filter_by(name="Test 1").first()
        assert filtered.name == "Test 1"

class TestRecordPlayback:
    """Test Record/Playback tactic for test reproducibility"""
    
    def test_test_recorder_initialization(self, db_session):
        """Test test recorder initialization"""
        recorder = TestRecorder(db_session, {})
        
        assert recorder.db == db_session
        assert recorder.current_test is None
        assert recorder.sequence_number == 0
    
    def test_start_recording(self, db_session):
        """Test starting test recording"""
        recorder = TestRecorder(db_session, {})
        
        success, message = recorder.start_recording("test_1")
        
        assert success == True
        assert "Started recording" in message
        assert recorder.current_test == "test_1"
        assert recorder.sequence_number == 0
    
    def test_record_request(self, db_session):
        """Test recording requests"""
        recorder = TestRecorder(db_session, {})
        recorder.start_recording("test_1")
        
        request_data = {
            'endpoint': '/api/test',
            'method': 'POST',
            'data': {'test': 'data'},
            'headers': {'Content-Type': 'application/json'}
        }
        
        success, message = recorder.record_request(
            request_data['endpoint'],
            request_data['method'],
            request_data['data'],
            request_data['headers']
        )
        
        assert success == True
        assert "recorded" in message.lower()
        assert recorder.sequence_number == 1
    
    def test_record_response(self, db_session):
        """Test recording responses"""
        recorder = TestRecorder(db_session, {})
        recorder.start_recording("test_1")
        
        response_data = {
            'status_code': 200,
            'data': {'result': 'success'},
            'headers': {'Content-Type': 'application/json'}
        }
        
        success, message = recorder.record_response(
            response_data['status_code'],
            response_data['data'],
            response_data['headers']
        )
        
        assert success == True
        assert "recorded" in message.lower()
        assert recorder.sequence_number == 1
    
    def test_record_state(self, db_session):
        """Test recording system state"""
        recorder = TestRecorder(db_session, {})
        recorder.start_recording("test_1")
        
        state_data = {
            'database_state': {'users': 10, 'products': 50},
            'memory_usage': 1024,
            'cpu_usage': 50.0
        }
        
        success, message = recorder.record_state("system_state", state_data)
        
        assert success == True
        assert "recorded" in message.lower()
        assert recorder.sequence_number == 1
    
    def test_stop_recording(self, db_session):
        """Test stopping test recording"""
        recorder = TestRecorder(db_session, {})
        recorder.start_recording("test_1")
        
        success, message = recorder.stop_recording()
        
        assert success == True
        assert "Stopped recording" in message
        assert recorder.current_test is None
        assert recorder.sequence_number == 0
    
    def test_playback_test(self, db_session):
        """Test playing back recorded test"""
        recorder = TestRecorder(db_session, {})
        
        # Record some data
        recorder.start_recording("test_1")
        recorder.record_request("/api/test", "POST", {"test": "data"})
        recorder.record_response(200, {"result": "success"})
        recorder.stop_recording()
        
        # Playback test
        success, playback_data = recorder.playback_test("test_1")
        
        assert success == True
        assert len(playback_data) == 2
        assert playback_data[0]['type'] == 'request'
        assert playback_data[1]['type'] == 'response'
    
    def test_get_test_summary(self, db_session):
        """Test getting test summary"""
        recorder = TestRecorder(db_session, {})
        
        # Record some data
        recorder.start_recording("test_1")
        recorder.record_request("/api/test", "POST", {"test": "data"})
        recorder.record_response(200, {"result": "success"})
        recorder.record_state("system_state", {"memory": 1024})
        recorder.stop_recording()
        
        # Get summary
        summary = recorder.get_test_summary("test_1")
        
        assert summary['test_name'] == "test_1"
        assert summary['total_records'] == 3
        assert 'record_types' in summary
        assert summary['record_types']['request'] == 1
        assert summary['record_types']['response'] == 1
        assert summary['record_types']['state'] == 1

class TestTestEnvironment:
    """Test Test Environment for test setup and teardown"""
    
    def test_test_environment_setup(self, db_session):
        """Test test environment setup"""
        test_env = TestEnvironment(db_session)
        
        success, message = test_env.setup_test("test_1")
        
        assert success == True
        assert "setup complete" in message.lower()
    
    def test_test_environment_teardown(self, db_session):
        """Test test environment teardown"""
        test_env = TestEnvironment(db_session)
        test_env.setup_test("test_1")
        
        success, message = test_env.teardown_test()
        
        assert success == True
        assert "teardown complete" in message.lower()
    
    def test_get_mock_service(self, db_session):
        """Test getting mock service from environment"""
        test_env = TestEnvironment(db_session)
        test_env.setup_test("test_1")
        
        # Get mock services
        payment_service = test_env.get_mock_service(MockPaymentService)
        partner_api = test_env.get_mock_service(MockPartnerAPI)
        database = test_env.get_mock_service(MockDatabase)
        
        assert isinstance(payment_service, MockPaymentService)
        assert isinstance(partner_api, MockPartnerAPI)
        assert isinstance(database, MockDatabase)
    
    def test_record_operations(self, db_session):
        """Test recording operations through environment"""
        test_env = TestEnvironment(db_session)
        test_env.setup_test("test_1")
        
        # Record request
        success, message = test_env.record_request("/api/test", "POST", {"test": "data"})
        assert success == True
        
        # Record response
        success, message = test_env.record_response(200, {"result": "success"})
        assert success == True
        
        # Record state
        success, message = test_env.record_state("system_state", {"memory": 1024})
        assert success == True

class TestTestabilityManager:
    """Test Testability Manager integration"""
    
    def test_testability_manager_initialization(self, db_session):
        """Test testability manager initialization"""
        manager = TestabilityManager(db_session)
        
        assert manager.db == db_session
        assert manager.test_environment is not None
        assert manager.recorder is not None
    
    def test_run_test_with_recording(self, db_session):
        """Test running test with recording"""
        manager = TestabilityManager(db_session)
        
        def test_function(test_env):
            # Use mock services
            payment_service = test_env.get_mock_service(MockPaymentService)
            success, result = payment_service.process_payment(100.0, "card")
            
            # Record operations
            test_env.record_request("/api/payment", "POST", {"amount": 100.0})
            test_env.record_response(200 if success else 400, {"result": result})
            
            return {"success": success, "result": result}
        
        success, summary = manager.run_test_with_recording("test_payment", test_function)
        
        assert success == True
        assert summary['test_name'] == "test_payment"
        assert 'test_result' in summary
        assert summary['total_records'] > 0
    
    def test_playback_test(self, db_session):
        """Test playing back recorded test"""
        manager = TestabilityManager(db_session)
        
        # First record a test
        def test_function(test_env):
            test_env.record_request("/api/test", "GET", {})
            test_env.record_response(200, {"result": "success"})
            return {"status": "completed"}
        
        manager.run_test_with_recording("test_playback", test_function)
        
        # Then playback
        success, playback_data = manager.playback_test("test_playback")
        
        assert success == True
        assert len(playback_data) > 0
        assert playback_data[0]['type'] == 'request'
    
    def test_get_available_tests(self, db_session):
        """Test getting available tests"""
        manager = TestabilityManager(db_session)
        
        # Record some tests
        def test_function(test_env):
            test_env.record_request("/api/test", "POST", {"test": "data"})
            test_env.record_response(200, {"result": "success"})
            return {"status": "completed"}
        
        manager.run_test_with_recording("test_1", test_function)
        manager.run_test_with_recording("test_2", test_function)
        
        # Get available tests
        tests = manager.get_available_tests()
        
        assert "test_1" in tests
        assert "test_2" in tests

class TestTestabilityIntegration:
    """Integration tests for testability tactics working together"""
    
    def test_complete_testing_workflow(self, db_session):
        """Test complete testing workflow"""
        manager = TestabilityManager(db_session)
        
        def comprehensive_test(test_env):
            # Get mock services
            payment_service = test_env.get_mock_service(MockPaymentService)
            partner_api = test_env.get_mock_service(MockPartnerAPI)
            database = test_env.get_mock_service(MockDatabase)
            
            # Record initial state
            test_env.record_state("initial_state", {"memory": 1024, "cpu": 50})
            
            # Test payment processing
            test_env.record_request("/api/payment", "POST", {"amount": 100.0, "method": "card"})
            success, result = payment_service.process_payment(100.0, "card")
            test_env.record_response(200 if success else 400, {"result": result})
            
            # Test partner API
            test_env.record_request("/api/partner/products", "GET", {"partner_id": 1})
            products = partner_api.fetch_products(1)
            test_env.record_response(200, {"products": products})
            
            # Record final state
            test_env.record_state("final_state", {"memory": 2048, "cpu": 75})
            
            return {
                "payment_success": success,
                "products_count": len(products),
                "status": "completed"
            }
        
        # Run test with recording
        success, summary = manager.run_test_with_recording("comprehensive_test", comprehensive_test)
        
        assert success == True
        assert summary['test_result']['status'] == "completed"
        assert summary['total_records'] >= 5  # Multiple records should be made
    
    def test_dependency_injection_with_recording(self, db_session):
        """Test dependency injection working with recording"""
        manager = TestabilityManager(db_session)
        
        def di_test(test_env):
            # Get services through DI
            payment_service = test_env.get_mock_service(MockPaymentService)
            
            # Configure service behavior
            payment_service.should_fail = True
            
            # Record and execute
            test_env.record_request("/api/payment", "POST", {"amount": 100.0})
            success, result = payment_service.process_payment(100.0, "card")
            test_env.record_response(400, {"error": result})
            
            return {"payment_failed": not success}
        
        success, summary = manager.run_test_with_recording("di_test", di_test)
        
        assert success == True
        assert summary['test_result']['payment_failed'] == True

class TestTestabilityEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_recorder_without_active_test(self, db_session):
        """Test recorder operations without active test"""
        recorder = TestRecorder(db_session, {})
        
        # Try to record without starting
        success, message = recorder.record_request("/api/test", "GET", {})
        assert success == False
        assert "No active test" in message
    
    def test_playback_nonexistent_test(self, db_session):
        """Test playing back non-existent test"""
        recorder = TestRecorder(db_session, {})
        
        success, data = recorder.playback_test("nonexistent_test")
        assert success == False
        assert len(data) == 0
    
    def test_test_environment_with_database_error(self, db_session):
        """Test test environment with database errors"""
        # Mock database session to raise exception
        with patch.object(db_session, 'query', side_effect=Exception("Database error")):
            test_env = TestEnvironment(db_session)
            success, message = test_env.setup_test("test_1")
            assert success == False
            assert "error" in message.lower()
    
    def test_mock_service_error_handling(self):
        """Test mock service error handling"""
        service = MockPaymentService(should_fail=True)
        
        # Should not raise exception, should return failure result
        success, result = service.process_payment(100.0, "card")
        assert success == False
        assert "failure" in result
