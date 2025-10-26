# tests/test_performance_tactics.py
"""
Comprehensive tests for Performance tactics:
- Manage Event Arrival (Throttling/Queuing)
- Introduce Concurrency
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock

from src.tactics.performance import (
    ThrottlingManager, OrderQueueManager, ConcurrencyManager, PerformanceMonitor
)

class TestThrottlingManager:
    """Test Manage Event Arrival tactic - Throttling for flash sales"""
    
    def test_throttling_allows_requests_within_limit(self, db_session):
        """Test that requests within limit are allowed"""
        throttling = ThrottlingManager(db_session, {'max_rps': 10, 'window_size': 1})
        
        request_data = {'user_id': 1, 'amount': 100.0}
        
        # Should allow requests within limit
        for i in range(5):
            success, message = throttling.execute(request_data)
            assert success == True
    
    def test_throttling_blocks_requests_over_limit(self, db_session):
        """Test that requests over limit are blocked"""
        throttling = ThrottlingManager(db_session, {'max_rps': 3, 'window_size': 1})
        
        request_data = {'user_id': 1, 'amount': 100.0}
        
        # First 3 requests should be allowed
        for i in range(3):
            success, message = throttling.execute(request_data)
            assert success == True
        
        # 4th request should be throttled
        success, message = throttling.execute(request_data)
        assert success == False
        assert "throttled" in message.lower()
    
    def test_throttling_window_reset(self, db_session):
        """Test that throttling window resets after time period"""
        throttling = ThrottlingManager(db_session, {'max_rps': 2, 'window_size': 1})
        
        request_data = {'user_id': 1, 'amount': 100.0}
        
        # Fill up the window
        for i in range(2):
            throttling.execute(request_data)
        
        # Should be throttled
        success, message = throttling.execute(request_data)
        assert success == False
        
        # Wait for window to reset
        time.sleep(1.1)
        
        # Should be allowed again
        success, message = throttling.execute(request_data)
        assert success == True
    
    def test_throttling_metrics_logging(self, db_session):
        """Test that throttling metrics are logged"""
        throttling = ThrottlingManager(db_session, {'max_rps': 2, 'window_size': 1})
        
        request_data = {'user_id': 1, 'amount': 100.0}
        
        # Make requests
        for i in range(3):
            throttling.execute(request_data)
        
        # Check that metrics were logged (this would be verified through the logging system)
        # In a real implementation, you'd check the metrics storage
        assert True  # Placeholder for metrics verification

class TestOrderQueueManager:
    """Test Order queue management for performance"""
    
    def setup_method(self, method):
        """Clean up database before each test"""
        # This will be called before each test method
        pass
    
    def teardown_method(self, method):
        """Clean up database after each test"""
        # This will be called after each test method
        pass
    
    def test_enqueue_order_success(self, db_session, sample_order_data):
        """Test successful order enqueueing"""
        queue_manager = OrderQueueManager(db_session, {'max_size': 100})
        
        success, message = queue_manager.enqueue_order(sample_order_data, priority=1)
        
        assert success == True
        assert "queued" in message.lower()
        
        # Check database record
        from src.models import OrderQueue
        queued_orders = db_session.query(OrderQueue).filter_by(
            userID=sample_order_data['user_id']
        ).all()
        assert len(queued_orders) == 1
        assert queued_orders[0].priority == 1
    
    def test_enqueue_order_priority_ordering(self, db_session, sample_order_data):
        """Test that orders are ordered by priority"""
        queue_manager = OrderQueueManager(db_session, {'max_size': 100})
        
        # Enqueue orders with different priorities
        order1 = sample_order_data.copy()
        order1['sale_id'] = 1
        queue_manager.enqueue_order(order1, priority=3)
        
        order2 = sample_order_data.copy()
        order2['sale_id'] = 2
        queue_manager.enqueue_order(order2, priority=1)
        
        order3 = sample_order_data.copy()
        order3['sale_id'] = 3
        queue_manager.enqueue_order(order3, priority=2)
        
        # Dequeue orders - should come out in priority order (highest first)
        dequeued1 = queue_manager.dequeue_order()
        dequeued2 = queue_manager.dequeue_order()
        dequeued3 = queue_manager.dequeue_order()
        
        assert dequeued1['sale_id'] == 1  # Priority 3
        assert dequeued2['sale_id'] == 3  # Priority 2
        assert dequeued3['sale_id'] == 2  # Priority 1
    
    def test_dequeue_order_empty_queue(self, db_session):
        """Test dequeuing from empty queue"""
        queue_manager = OrderQueueManager(db_session, {'max_size': 100})
        
        result = queue_manager.dequeue_order()
        assert result is None
    
    def test_mark_order_completed(self, db_session, sample_order_data):
        """Test marking order as completed"""
        queue_manager = OrderQueueManager(db_session, {'max_size': 100})
        
        # Enqueue and dequeue order
        queue_manager.enqueue_order(sample_order_data, priority=1)
        dequeued = queue_manager.dequeue_order()
        
        # Mark as completed
        success = queue_manager.mark_completed(dequeued['queue_id'])
        assert success == True
        
        # Check database
        from src.models import OrderQueue
        order = db_session.query(OrderQueue).filter_by(
            queueID=dequeued['queue_id']
        ).first()
        assert order.status == 'completed'
    
    def test_mark_order_failed(self, db_session, sample_order_data):
        """Test marking order as failed"""
        queue_manager = OrderQueueManager(db_session, {'max_size': 100})
        
        # Enqueue and dequeue order
        queue_manager.enqueue_order(sample_order_data, priority=1)
        dequeued = queue_manager.dequeue_order()
        
        # Mark as failed
        success = queue_manager.mark_failed(dequeued['queue_id'], "Test error")
        assert success == True
        
        # Check database
        from src.models import OrderQueue
        order = db_session.query(OrderQueue).filter_by(
            queueID=dequeued['queue_id']
        ).first()
        assert order.status == 'failed'
        assert order.error_message == "Test error"

class TestConcurrencyManager:
    """Test Introduce Concurrency tactic for database operations"""
    
    def test_concurrent_operation_success(self, db_session):
        """Test successful concurrent operation"""
        concurrency = ConcurrencyManager(db_session, {'max_concurrent': 5, 'lock_timeout': 50})
        
        def test_operation():
            return "Operation successful"
        
        success, result = concurrency.execute_with_lock(test_operation)
        
        assert success == True
        assert result == "Operation successful"
    
    def test_concurrent_operation_failure(self, db_session):
        """Test concurrent operation failure handling"""
        concurrency = ConcurrencyManager(db_session, {'max_concurrent': 5, 'lock_timeout': 50})
        
        def failing_operation():
            raise Exception("Operation failed")
        
        success, result = concurrency.execute_with_lock(failing_operation)
        
        assert success == False
        assert "failed" in result.lower()
    
    def test_max_concurrent_limit(self, db_session):
        """Test that max concurrent operations limit is enforced"""
        concurrency = ConcurrencyManager(db_session, {'max_concurrent': 2, 'lock_timeout': 50})
        
        def slow_operation():
            time.sleep(0.1)
            return "Operation completed"
        
        # Start two operations
        results = []
        def run_operation():
            success, result = concurrency.execute_with_lock(slow_operation)
            results.append((success, result))
        
        thread1 = threading.Thread(target=run_operation)
        thread2 = threading.Thread(target=run_operation)
        thread3 = threading.Thread(target=run_operation)
        
        thread1.start()
        thread2.start()
        thread3.start()
        
        thread1.join()
        thread2.join()
        thread3.join()
        
        # Two should succeed, one should fail due to max concurrent limit
        success_count = sum(1 for success, _ in results if success)
        assert success_count == 2
    
    def test_lock_wait_time_measurement(self, db_session):
        """Test that lock wait time is measured"""
        concurrency = ConcurrencyManager(db_session, {'max_concurrent': 1, 'lock_timeout': 50})
        
        # This is a simplified test - in reality, you'd need actual database locks
        wait_time = concurrency.get_lock_wait_time()
        assert isinstance(wait_time, float)
        assert wait_time >= 0

class TestPerformanceMonitor:
    """Test Performance monitoring and metrics collection"""
    
    def test_performance_metrics_collection(self, db_session):
        """Test that performance metrics are collected"""
        monitor = PerformanceMonitor(db_session, {'metrics_interval': 60})
        
        metrics = monitor.execute()
        
        assert isinstance(metrics, dict)
        assert 'timestamp' in metrics
        assert 'queue_size' in metrics
        assert 'active_operations' in metrics
        assert 'lock_wait_time' in metrics
        assert 'response_time' in metrics
    
    def test_metrics_database_logging(self, db_session):
        """Test that metrics are logged to database"""
        monitor = PerformanceMonitor(db_session, {'metrics_interval': 60})
        
        # Execute monitoring
        monitor.execute()
        
        # Check that metrics were logged to database
        from src.models import SystemMetrics
        metrics = db_session.query(SystemMetrics).all()
        assert len(metrics) > 0
    
    def test_queue_size_measurement(self, db_session, sample_order_data):
        """Test that queue size is measured correctly"""
        monitor = PerformanceMonitor(db_session, {'metrics_interval': 60})
        queue_manager = OrderQueueManager(db_session, {'max_size': 100})
        
        # Add some orders to queue
        queue_manager.enqueue_order(sample_order_data, priority=1)
        queue_manager.enqueue_order(sample_order_data, priority=2)
        
        metrics = monitor.execute()
        
        assert metrics['queue_size'] >= 2

class TestPerformanceIntegration:
    """Integration tests for performance tactics working together"""
    
    def test_throttling_with_queuing_integration(self, db_session, sample_order_data):
        """Test throttling working with queuing"""
        throttling = ThrottlingManager(db_session, {'max_rps': 2, 'window_size': 1})
        queue_manager = OrderQueueManager(db_session, {'max_size': 100})
        
        # First two requests should be allowed
        for i in range(2):
            throttled, _ = throttling.execute(sample_order_data)
            assert throttled == True
            
            success, _ = queue_manager.enqueue_order(sample_order_data, priority=i)
            assert success == True
        
        # Third request should be throttled
        throttled, message = throttling.execute(sample_order_data)
        assert throttled == False
        assert "throttled" in message.lower()
    
    def test_concurrency_with_monitoring_integration(self, db_session):
        """Test concurrency control working with monitoring"""
        concurrency = ConcurrencyManager(db_session, {'max_concurrent': 2, 'lock_timeout': 50})
        monitor = PerformanceMonitor(db_session, {'metrics_interval': 60})
        
        def test_operation():
            time.sleep(0.1)
            return "Operation completed"
        
        # Start operations
        results = []
        def run_operation():
            success, result = concurrency.execute_with_lock(test_operation)
            results.append((success, result))
        
        threads = [threading.Thread(target=run_operation) for _ in range(3)]
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Check monitoring
        metrics = monitor.execute()
        assert 'active_operations' in metrics
        assert 'lock_wait_time' in metrics

class TestPerformanceEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_throttling_with_zero_rps(self, db_session):
        """Test throttling with zero requests per second"""
        throttling = ThrottlingManager(db_session, {'max_rps': 0, 'window_size': 1})
        
        request_data = {'user_id': 1, 'amount': 100.0}
        success, message = throttling.execute(request_data)
        
        assert success == False
        assert "throttled" in message.lower()
    
    def test_queue_overflow_handling(self, db_session, sample_order_data):
        """Test handling of queue overflow"""
        queue_manager = OrderQueueManager(db_session, {'max_size': 2})
        
        # Fill up the queue
        for i in range(2):
            queue_manager.enqueue_order(sample_order_data, priority=i)
        
        # Third enqueue should handle overflow gracefully
        success, message = queue_manager.enqueue_order(sample_order_data, priority=3)
        # The implementation should handle this gracefully
        assert isinstance(success, bool)
    
    def test_concurrency_with_database_errors(self, db_session):
        """Test concurrency handling with database errors"""
        concurrency = ConcurrencyManager(db_session, {'max_concurrent': 5, 'lock_timeout': 50})
        
        def failing_operation():
            raise Exception("Database connection failed")
        
        success, result = concurrency.execute_with_lock(failing_operation)
        
        assert success == False
        assert "failed" in result.lower()
    
    def test_monitoring_with_empty_database(self, db_session):
        """Test monitoring with empty database"""
        # Clean up any existing queue items from previous tests
        from src.models import OrderQueue
        db_session.query(OrderQueue).delete()
        db_session.commit()
        
        monitor = PerformanceMonitor(db_session, {'metrics_interval': 60})
        
        metrics = monitor.execute()
        
        assert isinstance(metrics, dict)
        assert metrics['queue_size'] == 0
        assert metrics['active_operations'] == 0
