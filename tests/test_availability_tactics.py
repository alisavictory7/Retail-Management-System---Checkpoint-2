# tests/test_availability_tactics.py
"""
Comprehensive tests for Availability tactics:
- Circuit Breaker Pattern
- Graceful Degradation
- Rollback Tactic
- Retry Tactic
- Removal from Service
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta

from src.tactics.availability import (
    PaymentServiceCircuitBreaker, GracefulDegradationTactic,
    RollbackTactic, PaymentRetryTactic, RemovalFromServiceTactic
)

class TestCircuitBreakerPattern:
    """Test Circuit Breaker Pattern for payment service resilience"""
    
    def test_circuit_breaker_initial_state(self, db_session):
        """Test circuit breaker starts in closed state"""
        breaker = PaymentServiceCircuitBreaker(db_session)
        assert breaker.state.value == "closed"
        assert breaker.failure_count == 0
        assert breaker.can_execute() == True
    
    def test_circuit_breaker_success_flow(self, db_session, mock_payment_service):
        """Test successful payment doesn't trip circuit breaker"""
        breaker = PaymentServiceCircuitBreaker(db_session)
        payment_service = mock_payment_service(should_fail=False)
        
        success, result = breaker.execute(payment_service.process_payment, 100.0, "card")
        
        assert success == True
        assert breaker.state.value == "closed"
        assert breaker.failure_count == 0
    
    def test_circuit_breaker_failure_trips_open(self, db_session, mock_payment_service):
        """Test repeated failures trip circuit breaker to open state"""
        breaker = PaymentServiceCircuitBreaker(db_session, {'failure_threshold': 3})
        payment_service = mock_payment_service(should_fail=True)
        
        # Execute failures up to threshold
        for i in range(3):
            success, result = breaker.execute(payment_service.process_payment, 100.0, "card")
            assert success == False
        
        # Circuit should now be open
        assert breaker.state.value == "open"
        assert breaker.failure_count == 3
        assert breaker.can_execute() == False
    
    def test_circuit_breaker_half_open_recovery(self, db_session, mock_payment_service):
        """Test circuit breaker recovers through half-open state"""
        breaker = PaymentServiceCircuitBreaker(db_session, {'failure_threshold': 2, 'timeout_duration': 1})
        payment_service = mock_payment_service(should_fail=True)
        
        # Trip the circuit
        for i in range(2):
            breaker.execute(payment_service.process_payment, 100.0, "card")
        
        assert breaker.state.value == "open"
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Should be in half-open state
        assert breaker.can_execute() == True
        assert breaker.state.value == "half_open"
        
        # Success should close the circuit
        payment_service.should_fail = False
        success, result = breaker.execute(payment_service.process_payment, 100.0, "card")
        
        assert success == True
        assert breaker.state.value == "closed"

class TestGracefulDegradation:
    """Test Graceful Degradation for order processing during failures"""
    
    def test_graceful_degradation_queues_orders(self, db_session, sample_order_data):
        """Test that orders are queued when payment fails"""
        degradation = GracefulDegradationTactic(db_session)
        
        success, message = degradation.execute(sample_order_data, sample_order_data['user_id'])
        
        assert success == True
        assert "queued" in message.lower()
        
        # Check that order was queued in database
        from src.models import OrderQueue
        queued_orders = db_session.query(OrderQueue).filter_by(
            userID=sample_order_data['user_id']
        ).all()
        assert len(queued_orders) == 1
        assert queued_orders[0].status == 'pending'
    
    def test_graceful_degradation_audit_logging(self, db_session, sample_order_data):
        """Test that graceful degradation logs audit events"""
        degradation = GracefulDegradationTactic(db_session)
        
        degradation.execute(sample_order_data, sample_order_data['user_id'])
        
        # Check audit log
        from src.models import AuditLog
        audit_logs = db_session.query(AuditLog).filter_by(
            event_type="graceful_degradation"
        ).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].action == "order_queued"

class TestRollbackTactic:
    """Test Rollback Tactic for transaction integrity"""
    
    def test_rollback_on_failure(self, db_session):
        """Test that rollback occurs when transaction fails"""
        rollback = RollbackTactic(db_session)
        
        def failing_transaction():
            # Simulate a transaction that fails
            raise Exception("Transaction failed")
        
        success, result = rollback.execute(failing_transaction)
        
        assert success == False
        assert "rolled back" in result.lower()
    
    def test_successful_transaction_no_rollback(self, db_session):
        """Test that successful transactions don't trigger rollback"""
        rollback = RollbackTactic(db_session)
        
        def successful_transaction():
            return "Transaction successful"
        
        success, result = rollback.execute(successful_transaction)
        
        assert success == True
        assert result == "Transaction successful"

class TestRetryTactic:
    """Test Retry Tactic for transient failure recovery"""
    
    def test_retry_success_after_failures(self, db_session, mock_payment_service):
        """Test that retry succeeds after initial failures"""
        retry = PaymentRetryTactic(db_session, {'max_attempts': 3, 'delay': 0.1})
        payment_service = mock_payment_service(should_fail=False, failure_rate=0.0)
        
        # Manually set up failure pattern
        call_count = 0
        def controlled_failure():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return {"status": "success"}
        
        success, result = retry.execute(controlled_failure)
        
        assert success == True
        assert call_count >= 2  # Should have retried
    
    def test_retry_fails_after_max_attempts(self, db_session, mock_payment_service):
        """Test that retry fails after max attempts"""
        retry = PaymentRetryTactic(db_session, {'max_attempts':2, 'delay': 0.1})
        payment_service = mock_payment_service(should_fail=True)
        
        success, result = retry.execute(payment_service.process_payment, 100.0, "card")
        
        assert success == False
        assert payment_service.call_count == 2  # Should have tried exactly max_attempts times
    
    def test_retry_exponential_backoff(self, db_session, mock_payment_service):
        """Test that retry uses exponential backoff"""
        retry = PaymentRetryTactic(db_session, {'max_attempts':3, 'delay': 0.1, 'backoff_factor': 2.0})
        payment_service = mock_payment_service(should_fail=True)
        
        start_time = time.time()
        retry.execute(payment_service.process_payment, 100.0, "card")
        end_time = time.time()
        
        # Should have waited: 0.1 + 0.2 = 0.3 seconds
        assert end_time - start_time >= 0.3

class TestRemovalFromService:
    """Test Removal from Service for predictive fault mitigation"""
    
    def test_worker_removal_high_memory(self, db_session):
        """Test that worker is removed when memory usage is high"""
        config = {'memory_threshold': 80}
        removal = RemovalFromServiceTactic(db_session, config)
        
        metrics = {
            'memory_usage': 85.0,
            'cpu_usage': 50.0
        }
        
        should_remove, message = removal.execute("worker_1", metrics)
        
        assert should_remove == True
        assert "memory" in message.lower()
    
    def test_worker_removal_high_cpu(self, db_session):
        """Test that worker is removed when CPU usage is high"""
        config = {'cpu_threshold': 90}
        removal = RemovalFromServiceTactic(db_session, config)
        
        metrics = {
            'memory_usage': 50.0,
            'cpu_usage': 95.0
        }
        
        should_remove, message = removal.execute("worker_2", metrics)
        
        assert should_remove == True
        assert "cpu" in message.lower()
    
    def test_worker_normal_operation(self, db_session):
        """Test that worker continues when metrics are normal"""
        config = {}
        removal = RemovalFromServiceTactic(db_session, config)
        
        metrics = {
            'memory_usage': 50.0,
            'cpu_usage': 60.0
        }
        
        should_remove, message = removal.execute("worker_3", metrics)
        
        assert should_remove == False
        assert "normal" in message.lower()
    
    def test_removal_audit_logging(self, db_session):
        """Test that removal events are logged"""
        config = {'memory_threshold': 80}
        removal = RemovalFromServiceTactic(db_session, config)
        
        metrics = {'memory_usage': 85.0, 'cpu_usage': 50.0}
        removal.execute("worker_4", metrics)
        
        # Check audit log
        from src.models import AuditLog
        audit_logs = db_session.query(AuditLog).filter_by(
            event_type="removal_from_service"
        ).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].action == "worker_removed"

class TestAvailabilityIntegration:
    """Integration tests for availability tactics working together"""
    
    def test_circuit_breaker_with_graceful_degradation(self, db_session, sample_order_data, mock_payment_service):
        """Test circuit breaker working with graceful degradation"""
        breaker = PaymentServiceCircuitBreaker(db_session, {'failure_threshold': 2})
        degradation = GracefulDegradationTactic(db_session)
        payment_service = mock_payment_service(should_fail=True)
        
        # Trip the circuit breaker
        for i in range(2):
            breaker.execute(payment_service.process_payment, 100.0, "card")
        
        # Now circuit is open, so payment should fail
        success, result = breaker.execute(payment_service.process_payment, 100.0, "card")
        assert success == False
        
        # Order should be queued via graceful degradation
        degradation_success, degradation_message = degradation.execute(sample_order_data, sample_order_data['user_id'])
        assert degradation_success == True
    
    def test_retry_with_rollback_integration(self, db_session, mock_payment_service):
        """Test retry working with rollback for transaction integrity"""
        retry = PaymentRetryTactic(db_session, {'max_attempts':2, 'delay': 0.1})
        rollback = RollbackTactic(db_session)
        payment_service = mock_payment_service(should_fail=True)
        
        def payment_transaction():
            success, result = retry.execute(payment_service.process_payment, 100.0, "card")
            if not success:
                raise Exception(f"Payment failed: {result}")
            return result
        
        # Retry should fail after max attempts, triggering rollback
        success, result = rollback.execute(payment_transaction)
        
        assert success == False
        assert "rolled back" in result.lower()
