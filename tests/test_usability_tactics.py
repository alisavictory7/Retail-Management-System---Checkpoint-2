# tests/test_usability_tactics.py
"""
Comprehensive tests for Usability tactics:
- Minimize Impact of User Errors
- Maintain System Model (Progress Indicator)
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock

from src.tactics.usability import (
    UsabilityManager, UserErrorHandler, PaymentErrorHandler,
    ProgressIndicator, ErrorSeverity, ErrorType
)

class TestUserErrorHandler:
    """Test Minimize Impact of User Errors tactic"""
    
    def test_user_error_handler_initialization(self):
        """Test user error handler initialization"""
        handler = UserErrorHandler()
        
        assert handler.name == "user_error_handler"
        assert handler.state.value == "active"
        assert len(handler.error_messages) > 0
    
    def test_handle_payment_declined_error(self):
        """Test handling payment declined error"""
        handler = UserErrorHandler()
        
        success, response = handler.execute('payment_declined', {'amount': 100.0})
        
        assert success == True
        assert response['error_type'] == 'payment_declined'
        assert 'declined' in response['message'].lower()
        assert len(response['suggestions']) > 0
        assert response['severity'] == 'medium'
        assert response['recovery_time'] == 90
    
    def test_handle_insufficient_stock_error(self):
        """Test handling insufficient stock error"""
        handler = UserErrorHandler()
        
        success, response = handler.execute('insufficient_stock', {'product_id': 123})
        
        assert success == True
        assert response['error_type'] == 'insufficient_stock'
        assert 'stock' in response['message'].lower()
        assert len(response['suggestions']) > 0
        assert response['severity'] == 'low'
        assert response['recovery_time'] == 30
    
    def test_handle_invalid_input_error(self):
        """Test handling invalid input error"""
        handler = UserErrorHandler()
        
        success, response = handler.execute('invalid_input', {'field': 'email'})
        
        assert success == True
        assert response['error_type'] == 'invalid_input'
        assert 'input' in response['message'].lower()
        assert len(response['suggestions']) > 0
        assert response['severity'] == 'low'
        assert response['recovery_time'] == 15
    
    def test_handle_system_error(self):
        """Test handling system error"""
        handler = UserErrorHandler()
        
        success, response = handler.execute('system_error', {'component': 'database'})
        
        assert success == True
        assert response['error_type'] == 'system_error'
        assert 'difficulties' in response['message'].lower()
        assert len(response['suggestions']) > 0
        assert response['severity'] == 'high'
        assert response['recovery_time'] == 120
    
    def test_handle_unknown_error(self):
        """Test handling unknown error type"""
        handler = UserErrorHandler()
        
        success, response = handler.execute('unknown_error', {})
        
        assert success == True
        assert response['error_type'] == 'unknown_error'
        assert 'error occurred' in response['message'].lower()
        assert response['severity'] == 'medium'
    
    def test_error_response_structure(self):
        """Test error response structure"""
        handler = UserErrorHandler()
        
        success, response = handler.execute('payment_declined', {'amount': 100.0})
        
        # Check required fields
        required_fields = ['error_type', 'message', 'suggestions', 'severity', 'recovery_time', 'context', 'timestamp', 'error_id']
        for field in required_fields:
            assert field in response
        
        # Check data types
        assert isinstance(response['suggestions'], list)
        assert isinstance(response['recovery_time'], int)
        assert isinstance(response['severity'], str)
        assert isinstance(response['error_id'], str)
    
    def test_error_id_generation(self):
        """Test that error IDs are unique"""
        handler = UserErrorHandler()
        
        success1, response1 = handler.execute('payment_declined', {})
        success2, response2 = handler.execute('payment_declined', {})
        
        assert response1['error_id'] != response2['error_id']
        assert response1['error_id'].startswith('ERR_')

class TestPaymentErrorHandler:
    """Test specialized payment error handler"""
    
    def test_payment_error_handler_initialization(self):
        """Test payment error handler initialization"""
        handler = PaymentErrorHandler()
        
        assert handler.name == "payment_error_handler"
        assert len(handler.payment_error_messages) > 0
    
    def test_handle_card_declined(self):
        """Test handling card declined error"""
        handler = PaymentErrorHandler()
        
        success, response = handler.handle_payment_error('card_declined', 100.0, 'card')
        
        assert success == True
        assert response['error_code'] == 'card_declined'
        assert 'declined' in response['message'].lower()
        assert len(response['suggestions']) > 0
        assert response['severity'] == 'medium'
        assert response['context']['amount'] == 100.0
        assert response['context']['payment_method'] == 'card'
    
    def test_handle_expired_card(self):
        """Test handling expired card error"""
        handler = PaymentErrorHandler()
        
        success, response = handler.handle_payment_error('expired_card', 50.0, 'card')
        
        assert success == True
        assert response['error_code'] == 'expired_card'
        assert 'expired' in response['message'].lower()
        assert response['severity'] == 'low'
        assert response['recovery_time'] == 30
    
    def test_handle_invalid_cvv(self):
        """Test handling invalid CVV error"""
        handler = PaymentErrorHandler()
        
        success, response = handler.handle_payment_error('invalid_cvv', 75.0, 'card')
        
        assert success == True
        assert response['error_code'] == 'invalid_cvv'
        assert 'CVV' in response['message']
        assert response['severity'] == 'low'
        assert response['recovery_time'] == 15
    
    def test_handle_insufficient_funds(self):
        """Test handling insufficient funds error"""
        handler = PaymentErrorHandler()
        
        success, response = handler.handle_payment_error('insufficient_funds', 200.0, 'card')
        
        assert success == True
        assert response['error_code'] == 'insufficient_funds'
        assert 'funds' in response['message'].lower()
        assert response['severity'] == 'medium'
        assert response['recovery_time'] == 90
    
    def test_alternative_payment_methods(self):
        """Test alternative payment methods suggestion"""
        handler = PaymentErrorHandler()
        
        success, response = handler.handle_payment_error('card_declined', 100.0, 'card')
        
        assert success == True
        assert 'alternative_payment_methods' in response
        assert isinstance(response['alternative_payment_methods'], list)
        assert 'card' not in response['alternative_payment_methods']  # Current method excluded
        assert 'cash' in response['alternative_payment_methods']
    
    def test_fallback_error_response(self):
        """Test fallback error response"""
        handler = PaymentErrorHandler()
        
        # Mock the handler to raise exception
        with patch.object(handler, '_log_payment_error', side_effect=Exception("Test error")):
            success, response = handler.handle_payment_error('card_declined', 100.0, 'card')
            
            assert success == False
            assert 'failed' in response['message'].lower()

class TestProgressIndicator:
    """Test Maintain System Model tactic - Progress Indicator"""
    
    def test_progress_indicator_initialization(self):
        """Test progress indicator initialization"""
        indicator = ProgressIndicator({})
        
        assert indicator.name == "progress_indicator"
        assert len(indicator.active_operations) == 0
        assert indicator.update_interval == 1
        assert indicator.max_operation_time == 300
    
    def test_start_progress_tracking(self):
        """Test starting progress tracking"""
        indicator = ProgressIndicator({})
        
        success, message = indicator.execute("op_1", "payment_processing", 30)
        
        assert success == True
        assert "started" in message.lower()
        assert "op_1" in indicator.active_operations
        assert indicator.active_operations["op_1"]['status'] == 'started'
        assert indicator.active_operations["op_1"]['operation_type'] == 'payment_processing'
    
    def test_update_progress(self):
        """Test updating progress"""
        indicator = ProgressIndicator({})
        indicator.execute("op_1", "payment_processing", 30)
        
        success, message = indicator.update_progress("op_1", 50, "Processing payment")
        
        assert success == True
        assert "updated" in message.lower()
        assert indicator.active_operations["op_1"]['progress'] == 50
        assert indicator.active_operations["op_1"]['current_step'] == "Processing payment"
    
    def test_get_progress(self):
        """Test getting progress information"""
        indicator = ProgressIndicator({})
        indicator.execute("op_1", "payment_processing", 30)
        indicator.update_progress("op_1", 75, "Almost done")
        
        progress = indicator.get_progress("op_1")
        
        assert progress is not None
        assert progress['operation_id'] == "op_1"
        assert progress['operation_type'] == "payment_processing"
        assert progress['progress'] == 75
        assert progress['current_step'] == "Almost done"
        assert progress['status'] == "started"
        assert 'elapsed_time' in progress
        assert 'estimated_remaining' in progress
    
    def test_complete_operation_success(self):
        """Test completing operation successfully"""
        indicator = ProgressIndicator({})
        indicator.execute("op_1", "payment_processing", 30)
        
        success, message = indicator.complete_operation("op_1", True)
        
        assert success == True
        assert "completed" in message.lower()
        assert "op_1" not in indicator.active_operations  # Should be removed
    
    def test_complete_operation_failure(self):
        """Test completing operation with failure"""
        indicator = ProgressIndicator({})
        indicator.execute("op_1", "payment_processing", 30)
        
        success, message = indicator.complete_operation("op_1", False, "Payment failed")
        
        assert success == True
        assert "completed" in message.lower()
        assert "op_1" not in indicator.active_operations  # Should be removed
    
    def test_operation_timeout(self):
        """Test operation timeout handling"""
        indicator = ProgressIndicator({'max_operation_time': 1})  # 1 second timeout
        indicator.execute("op_1", "payment_processing", 30)
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Operation should be completed due to timeout
        assert "op_1" not in indicator.active_operations
    
    def test_duplicate_operation_id(self):
        """Test handling duplicate operation IDs"""
        indicator = ProgressIndicator({})
        indicator.execute("op_1", "payment_processing", 30)
        
        # Try to start same operation again
        success, message = indicator.execute("op_1", "payment_processing", 30)
        
        assert success == False
        assert "already in progress" in message.lower()
    
    def test_nonexistent_operation_update(self):
        """Test updating progress for non-existent operation"""
        indicator = ProgressIndicator({})
        
        success, message = indicator.update_progress("nonexistent", 50)
        
        assert success == False
        assert "not found" in message.lower()
    
    def test_nonexistent_operation_completion(self):
        """Test completing non-existent operation"""
        indicator = ProgressIndicator({})
        
        success, message = indicator.complete_operation("nonexistent", True)
        
        assert success == False
        assert "not found" in message.lower()
    
    def test_progress_validation(self):
        """Test progress value validation"""
        indicator = ProgressIndicator({})
        success, message = indicator.execute("op_1", "payment_processing", 30)
        assert success == True
        
        # Small delay to ensure operation is stored
        import time
        time.sleep(0.1)
        
        # Test progress clamping - use 99 to avoid triggering deletion
        success, message = indicator.update_progress("op_1", 99)
        assert success == True
        assert indicator.active_operations["op_1"]['progress'] == 99
        
        # Test progress > 100 gets clamped to 100
        success, message = indicator.update_progress("op_1", 150)
        assert success == True
        # The operation should be deleted when progress >= 100
        assert "op_1" not in indicator.active_operations
    
    def test_operation_types_and_durations(self):
        """Test different operation types and their estimated durations"""
        indicator = ProgressIndicator({})
        
        operation_types = [
            'payment_processing',
            'order_processing', 
            'inventory_update',
            'partner_sync',
            'report_generation',
            'data_validation'
        ]
        
        for op_type in operation_types:
            success, message = indicator.execute(f"op_{op_type}", op_type)
            assert success == True
            assert indicator.active_operations[f"op_{op_type}"]['estimated_duration'] > 0

class TestUsabilityManager:
    """Test Usability Manager integration"""
    
    def test_usability_manager_initialization(self):
        """Test usability manager initialization"""
        manager = UsabilityManager({})
        
        assert manager.error_handler is not None
        assert manager.payment_error_handler is not None
        assert manager.progress_indicator is not None
    
    def test_handle_user_error(self):
        """Test handling user errors through manager"""
        manager = UsabilityManager({})
        
        success, response = manager.handle_user_error('payment_declined', {'amount': 100.0})
        
        assert success == True
        assert response['error_type'] == 'payment_declined'
        assert 'declined' in response['message'].lower()
    
    def test_handle_payment_error(self):
        """Test handling payment errors through manager"""
        manager = UsabilityManager({})
        
        success, response = manager.handle_payment_error('card_declined', 100.0, 'card')
        
        assert success == True
        assert response['error_code'] == 'card_declined'
        assert 'declined' in response['message'].lower()
    
    def test_progress_tracking_workflow(self):
        """Test complete progress tracking workflow"""
        manager = UsabilityManager({})
        
        # Start progress tracking
        success, message = manager.start_progress_tracking("op_1", "payment_processing", 30)
        assert success == True
        
        # Update progress
        success, message = manager.update_progress("op_1", 25, "Validating payment")
        assert success == True
        
        success, message = manager.update_progress("op_1", 75, "Processing payment")
        assert success == True
        
        # Get progress
        progress = manager.get_progress("op_1")
        assert progress is not None
        assert progress['progress'] == 75
        assert progress['current_step'] == "Processing payment"
        
        # Complete operation
        success, message = manager.complete_operation("op_1", True)
        assert success == True

class TestUsabilityIntegration:
    """Integration tests for usability tactics working together"""
    
    def test_error_handling_with_progress_tracking(self):
        """Test error handling integrated with progress tracking"""
        manager = UsabilityManager({})
        
        # Start operation
        manager.start_progress_tracking("payment_op", "payment_processing", 30)
        manager.update_progress("payment_op", 50, "Processing payment")
        
        # Simulate error
        success, error_response = manager.handle_payment_error('card_declined', 100.0, 'card')
        assert success == True
        
        # Complete operation with error
        manager.complete_operation("payment_op", False, error_response['message'])
        
        # Check that operation is no longer active
        progress = manager.get_progress("payment_op")
        assert progress is None
    
    def test_complete_user_journey(self):
        """Test complete user journey with error recovery"""
        manager = UsabilityManager({})
        
        # Start order processing
        manager.start_progress_tracking("order_1", "order_processing", 60)
        manager.update_progress("order_1", 20, "Validating order")
        
        # Simulate payment error
        success, error_response = manager.handle_payment_error('insufficient_funds', 200.0, 'card')
        assert success == True
        
        # Update progress with error
        manager.update_progress("order_1", 40, f"Payment error: {error_response['message']}")
        
        # User tries alternative payment method
        success, error_response = manager.handle_payment_error('card_declined', 200.0, 'card')
        assert success == True
        
        # User tries cash payment (should succeed)
        manager.update_progress("order_1", 80, "Processing cash payment")
        manager.update_progress("order_1", 100, "Order completed successfully")
        
        # Complete operation
        manager.complete_operation("order_1", True)
        
        # Verify operation is completed
        progress = manager.get_progress("order_1")
        assert progress is None

class TestUsabilityEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_error_handler_with_invalid_error_type(self):
        """Test error handler with invalid error type"""
        handler = UserErrorHandler()
        
        success, response = handler.execute('invalid_error_type', {})
        
        assert success == True
        assert response['error_type'] == 'invalid_error_type'
        assert 'error occurred' in response['message'].lower()
    
    def test_progress_indicator_with_negative_progress(self):
        """Test progress indicator with negative progress"""
        indicator = ProgressIndicator({})
        success, message = indicator.execute("op_1", "test_operation", 30)
        assert success == True
        
        success, message = indicator.update_progress("op_1", -10)
        assert success == True
        # Check that negative progress is handled (should be clamped to 0)
        assert indicator.active_operations["op_1"]['progress'] == 0  # Should be clamped to 0
    
    def test_progress_indicator_concurrent_operations(self):
        """Test progress indicator with concurrent operations"""
        indicator = ProgressIndicator({})
        
        # Start multiple operations
        for i in range(5):
            indicator.execute(f"op_{i}", "test_operation", 30)
            indicator.update_progress(f"op_{i}", i * 20)
        
        # Check all operations are tracked
        assert len(indicator.active_operations) == 5
        
        # Complete some operations
        indicator.complete_operation("op_0", True)
        indicator.complete_operation("op_1", True)
        
        # Check remaining operations
        assert len(indicator.active_operations) == 3
        assert "op_0" not in indicator.active_operations
        assert "op_1" not in indicator.active_operations
    
    def test_error_handler_with_none_context(self):
        """Test error handler with None context"""
        handler = UserErrorHandler()
        
        success, response = handler.execute('payment_declined', None)
        
        assert success == True
        assert response['context'] is None
    
    def test_progress_indicator_with_very_long_operation(self):
        """Test progress indicator with very long operation"""
        indicator = ProgressIndicator({'max_operation_time': 2})  # 2 second timeout
        indicator.execute("long_op", "long_operation", 300)  # 5 minute estimated duration
        
        # Update progress
        indicator.update_progress("long_op", 10, "Just started")
        
        # Wait for timeout
        time.sleep(2.1)
        
        # Operation should be completed due to timeout
        assert "long_op" not in indicator.active_operations
