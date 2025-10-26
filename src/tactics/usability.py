# src/tactics/usability.py
"""
Usability tactics implementation for Checkpoint 2.
Implements: Minimize Impact of User Errors, Maintain System Model (Progress Indicator)
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import logging
import json
import time
import threading
from enum import Enum

from .base import BaseTactic
from ..models import AuditLog, SystemMetrics

logger = logging.getLogger(__name__)

# ==============================================
# ERROR TYPES AND SEVERITY
# ==============================================

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorType(Enum):
    """Error types"""
    VALIDATION = "validation"
    PAYMENT = "payment"
    SYSTEM = "system"
    NETWORK = "network"
    USER_INPUT = "user_input"

# ==============================================
# MINIMIZE IMPACT OF USER ERRORS TACTIC
# ==============================================

class UserErrorHandler(BaseTactic):
    """Minimize Impact of User Errors tactic"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("user_error_handler", config)
        self.error_messages = {
            'payment_declined': {
                'message': 'Your payment was declined. Please try a different payment method.',
                'suggestions': [
                    'Check your card details',
                    'Try a different card',
                    'Contact your bank',
                    'Use cash payment'
                ],
                'severity': ErrorSeverity.MEDIUM,
                'recovery_time': 90  # seconds
            },
            'insufficient_stock': {
                'message': 'Sorry, we don\'t have enough items in stock.',
                'suggestions': [
                    'Reduce quantity',
                    'Check back later',
                    'Try similar products',
                    'Get notified when available'
                ],
                'severity': ErrorSeverity.LOW,
                'recovery_time': 30
            },
            'invalid_input': {
                'message': 'Please check your input and try again.',
                'suggestions': [
                    'Verify all required fields',
                    'Check format requirements',
                    'Try again',
                    'Contact support if needed'
                ],
                'severity': ErrorSeverity.LOW,
                'recovery_time': 15
            },
            'system_error': {
                'message': 'We\'re experiencing technical difficulties. Please try again.',
                'suggestions': [
                    'Refresh the page',
                    'Try again in a few minutes',
                    'Contact support',
                    'Use alternative methods'
                ],
                'severity': ErrorSeverity.HIGH,
                'recovery_time': 120
            }
        }
    
    def execute(self, error_type: str, context: Dict[str, Any] = None) -> Tuple[bool, Dict[str, Any]]:
        """Handle user error and provide recovery guidance"""
        try:
            if context is None:
                context = None
            else:
                context = context or {}
            error_info = self.error_messages.get(error_type, self._get_default_error())
            
            # Create user-friendly error response
            error_response = {
                'error_type': error_type,
                'message': error_info['message'],
                'suggestions': error_info['suggestions'],
                'severity': error_info['severity'].value,
                'recovery_time': error_info['recovery_time'],
                'context': context,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error_id': self._generate_error_id()
            }
            
            # Log error for analysis
            self._log_error(error_type, error_info, context)
            
            # Track error metrics
            self.log_metric("user_error_handled", 1, {
                "error_type": error_type,
                "severity": error_info['severity'].value,
                "tactic": "minimize_user_errors"
            })
            
            return True, error_response
            
        except Exception as e:
            self.logger.error(f"Error handling failed: {e}")
            return False, {
                'error_type': 'system_error',
                'message': 'An unexpected error occurred.',
                'suggestions': ['Please try again', 'Contact support'],
                'severity': 'critical',
                'recovery_time': 300
            }
    
    def _get_default_error(self) -> Dict[str, Any]:
        """Get default error configuration"""
        return {
            'message': 'An error occurred. Please try again.',
            'suggestions': ['Try again', 'Contact support'],
            'severity': ErrorSeverity.MEDIUM,
            'recovery_time': 60
        }
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID"""
        import random
        return f"ERR_{int(time.time() * 1000000)}_{random.randint(1000, 9999)}"
    
    def _log_error(self, error_type: str, error_info: Dict[str, Any], context: Dict[str, Any]):
        """Log error for analysis"""
        try:
            # This would typically log to a database or monitoring system
            self.logger.info(f"User error handled: {error_type}, severity: {error_info['severity'].value}")
        except Exception as e:
            self.logger.error(f"Failed to log error: {e}")
    
    def validate_config(self) -> bool:
        """Validate error handler configuration"""
        return len(self.error_messages) > 0

class PaymentErrorHandler(UserErrorHandler):
    """Specialized handler for payment errors"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.name = "payment_error_handler"
        self.payment_error_messages = {
            'card_declined': {
                'message': 'Your card was declined by the bank.',
                'suggestions': [
                    'Check your card details',
                    'Ensure sufficient funds',
                    'Contact your bank',
                    'Try a different card'
                ],
                'severity': ErrorSeverity.MEDIUM,
                'recovery_time': 60
            },
            'expired_card': {
                'message': 'Your card has expired.',
                'suggestions': [
                    'Use a different card',
                    'Update card information',
                    'Contact your bank'
                ],
                'severity': ErrorSeverity.LOW,
                'recovery_time': 30
            },
            'invalid_cvv': {
                'message': 'Invalid CVV code.',
                'suggestions': [
                    'Check the 3-digit code on your card',
                    'Try again',
                    'Contact your bank if needed'
                ],
                'severity': ErrorSeverity.LOW,
                'recovery_time': 15
            },
            'insufficient_funds': {
                'message': 'Insufficient funds in your account.',
                'suggestions': [
                    'Add funds to your account',
                    'Use a different payment method',
                    'Try a smaller amount'
                ],
                'severity': ErrorSeverity.MEDIUM,
                'recovery_time': 90
            }
        }
    
    def handle_payment_error(self, error_code: str, amount: float, payment_method: str) -> Tuple[bool, Dict[str, Any]]:
        """Handle specific payment errors"""
        try:
            error_info = self.payment_error_messages.get(error_code, self._get_default_error())
            
            # Add payment-specific context
            context = {
                'amount': amount,
                'payment_method': payment_method,
                'error_code': error_code
            }
            
            # Create enhanced error response
            error_response = {
                'error_type': 'payment_error',
                'error_code': error_code,
                'message': error_info['message'],
                'suggestions': error_info['suggestions'],
                'severity': error_info['severity'].value,
                'recovery_time': error_info['recovery_time'],
                'context': context,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error_id': self._generate_error_id(),
                'alternative_payment_methods': self._get_alternative_payment_methods(payment_method)
            }
            
            # Log payment error
            self._log_payment_error(error_code, amount, payment_method)
            
            return True, error_response
            
        except Exception as e:
            self.logger.error(f"Payment error handling failed: {e}")
            return False, self._get_fallback_error_response()
    
    def _get_alternative_payment_methods(self, current_method: str) -> List[str]:
        """Get alternative payment methods"""
        all_methods = ['card', 'cash', 'paypal', 'apple_pay', 'google_pay']
        return [method for method in all_methods if method != current_method]
    
    def _log_payment_error(self, error_code: str, amount: float, payment_method: str):
        """Log payment error specifically"""
        self.logger.info(f"Payment error: {error_code}, amount: ${amount}, method: {payment_method}")
    
    def _get_fallback_error_response(self) -> Dict[str, Any]:
        """Get fallback error response"""
        return {
            'error_type': 'payment_error',
            'message': 'Payment processing failed. Please try again.',
            'suggestions': ['Try again', 'Use a different payment method', 'Contact support'],
            'severity': 'high',
            'recovery_time': 120
        }

# ==============================================
# MAINTAIN SYSTEM MODEL TACTIC (PROGRESS INDICATOR)
# ==============================================

class ProgressIndicator(BaseTactic):
    """Maintain System Model tactic - Progress Indicator for long operations"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("progress_indicator", config)
        self.active_operations = {}
        self.update_interval = config.get('update_interval', 1)  # seconds
        self.max_operation_time = config.get('max_operation_time', 300)  # seconds
        self.logger = logging.getLogger(__name__)
    
    def execute(self, operation_id: str, operation_type: str, 
                estimated_duration: int = None) -> Tuple[bool, str]:
        """Start progress tracking for an operation"""
        try:
            if operation_id in self.active_operations:
                return False, f"Operation {operation_id} already in progress"
            
            # Create operation tracking
            operation = {
                'operation_id': operation_id,
                'operation_type': operation_type,
                'status': 'started',
                'progress': 0,
                'start_time': datetime.now(timezone.utc),
                'estimated_duration': estimated_duration or self._estimate_duration(operation_type),
                'current_step': 'Initializing',
                'total_steps': self._get_total_steps(operation_type),
                'completed_steps': 0,
                'last_update': datetime.now(timezone.utc)
            }
            
            self.active_operations[operation_id] = operation
            
            # Start progress monitoring thread
            monitor_thread = threading.Thread(
                target=self._monitor_progress,
                args=(operation_id,),
                daemon=True
            )
            monitor_thread.start()
            
            self.log_metric("operation_started", 1, {
                "operation_type": operation_type,
                "tactic": "progress_indicator"
            })
            
            return True, f"Progress tracking started for {operation_id}"
            
        except Exception as e:
            self.logger.error(f"Failed to start progress tracking: {e}")
            return False, f"Failed to start progress tracking: {str(e)}"
    
    def update_progress(self, operation_id: str, progress: int, 
                       current_step: str = None) -> Tuple[bool, str]:
        """Update operation progress"""
        try:
            if operation_id not in self.active_operations:
                return False, f"Operation {operation_id} not found"
            
            operation = self.active_operations[operation_id]
            operation['progress'] = max(0, min(progress, 100))
            operation['completed_steps'] = int((progress / 100) * operation['total_steps'])
            operation['last_update'] = datetime.now(timezone.utc)
            
            if current_step:
                operation['current_step'] = current_step
            
            # Check if operation is complete
            if progress >= 100:
                operation['status'] = 'completed'
                operation['end_time'] = datetime.now(timezone.utc)
                del self.active_operations[operation_id]
            
            return True, "Progress updated"
            
        except Exception as e:
            self.logger.error(f"Failed to update progress: {e}")
            return False, f"Failed to update progress: {str(e)}"
    
    def get_progress(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for operation"""
        try:
            if operation_id not in self.active_operations:
                return None
            
            operation = self.active_operations[operation_id]
            
            # Calculate estimated time remaining
            elapsed = (datetime.now(timezone.utc) - operation['start_time']).total_seconds()
            estimated_remaining = self._calculate_remaining_time(operation, elapsed)
            
            return {
                'operation_id': operation_id,
                'operation_type': operation['operation_type'],
                'status': operation['status'],
                'progress': operation['progress'],
                'current_step': operation['current_step'],
                'completed_steps': operation['completed_steps'],
                'total_steps': operation['total_steps'],
                'elapsed_time': elapsed,
                'estimated_remaining': estimated_remaining,
                'last_update': operation['last_update'].isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get progress: {e}")
            return None
    
    def complete_operation(self, operation_id: str, success: bool = True, 
                          error_message: str = None) -> Tuple[bool, str]:
        """Complete an operation"""
        try:
            if operation_id not in self.active_operations:
                return False, f"Operation {operation_id} not found"
            
            operation = self.active_operations[operation_id]
            operation['status'] = 'completed' if success else 'failed'
            operation['end_time'] = datetime.now(timezone.utc)
            operation['success'] = success
            operation['error_message'] = error_message
            operation['progress'] = 100
            
            # Log completion
            self.log_metric("operation_completed", 1, {
                "operation_type": operation['operation_type'],
                "success": success,
                "tactic": "progress_indicator"
            })
            
            # Remove from active operations
            del self.active_operations[operation_id]
            
            return True, f"Operation {operation_id} completed"
            
        except Exception as e:
            self.logger.error(f"Failed to complete operation: {e}")
            return False, f"Failed to complete operation: {str(e)}"
    
    def _estimate_duration(self, operation_type: str) -> int:
        """Estimate operation duration based on type"""
        duration_estimates = {
            'payment_processing': 10,
            'order_processing': 15,
            'inventory_update': 5,
            'partner_sync': 30,
            'report_generation': 20,
            'data_validation': 8
        }
        return duration_estimates.get(operation_type, 15)
    
    def _get_total_steps(self, operation_type: str) -> int:
        """Get total steps for operation type"""
        step_counts = {
            'payment_processing': 4,
            'order_processing': 6,
            'inventory_update': 3,
            'partner_sync': 8,
            'report_generation': 5,
            'data_validation': 3
        }
        return step_counts.get(operation_type, 4)
    
    def _calculate_remaining_time(self, operation: Dict[str, Any], elapsed: float) -> float:
        """Calculate estimated remaining time"""
        if operation['progress'] <= 0:
            return operation['estimated_duration']
        
        # Simple linear estimation
        total_estimated = operation['estimated_duration']
        progress_ratio = operation['progress'] / 100
        
        if progress_ratio > 0:
            estimated_total = elapsed / progress_ratio
            return max(0, estimated_total - elapsed)
        
        return total_estimated
    
    def _monitor_progress(self, operation_id: str):
        """Monitor operation progress and timeout"""
        try:
            while operation_id in self.active_operations:
                operation = self.active_operations[operation_id]
                elapsed = (datetime.now(timezone.utc) - operation['start_time']).total_seconds()
                
                # Check for timeout
                if elapsed > self.max_operation_time:
                    self.complete_operation(operation_id, False, "Operation timed out")
                    break
                
                time.sleep(self.update_interval)
                
        except Exception as e:
            self.logger.error(f"Progress monitoring error: {e}")
    
    def validate_config(self) -> bool:
        """Validate progress indicator configuration"""
        return (self.update_interval > 0 and 
                self.max_operation_time > 0)

# ==============================================
# USABILITY MANAGER
# ==============================================

class UsabilityManager:
    """Central manager for all usability tactics"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.error_handler = UserErrorHandler(config)
        self.payment_error_handler = PaymentErrorHandler(config)
        self.progress_indicator = ProgressIndicator(config)
        self.logger = logging.getLogger(__name__)
    
    def handle_user_error(self, error_type: str, context: Dict[str, Any] = None) -> Tuple[bool, Dict[str, Any]]:
        """Handle user error with recovery guidance"""
        return self.error_handler.execute(error_type, context)
    
    def handle_payment_error(self, error_code: str, amount: float, payment_method: str) -> Tuple[bool, Dict[str, Any]]:
        """Handle payment-specific errors"""
        return self.payment_error_handler.handle_payment_error(error_code, amount, payment_method)
    
    def start_progress_tracking(self, operation_id: str, operation_type: str, 
                               estimated_duration: int = None) -> Tuple[bool, str]:
        """Start progress tracking for an operation"""
        return self.progress_indicator.execute(operation_id, operation_type, estimated_duration)
    
    def update_progress(self, operation_id: str, progress: int, current_step: str = None) -> Tuple[bool, str]:
        """Update operation progress"""
        return self.progress_indicator.update_progress(operation_id, progress, current_step)
    
    def get_progress(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for operation"""
        return self.progress_indicator.get_progress(operation_id)
    
    def complete_operation(self, operation_id: str, success: bool = True, error_message: str = None) -> Tuple[bool, str]:
        """Complete an operation"""
        return self.progress_indicator.complete_operation(operation_id, success, error_message)
