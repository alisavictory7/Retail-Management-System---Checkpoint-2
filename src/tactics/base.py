# src/tactics/base.py
"""
Base classes and interfaces for all quality tactics and patterns.
This module provides the foundational infrastructure for implementing
the 14+ tactics required for Checkpoint 2.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timezone
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)

class TacticState(Enum):
    """Base state enumeration for tactics"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"

class BaseTactic(ABC):
    """Abstract base class for all quality tactics"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.state = TacticState.ACTIVE
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the tactic with given parameters"""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate the tactic configuration"""
        pass
    
    def is_enabled(self) -> bool:
        """Check if the tactic is enabled"""
        return self.state == TacticState.ACTIVE
    
    def log_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Log a metric for monitoring"""
        self.logger.info(f"Metric: {metric_name}={value}, tags={tags or {}}")

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, not attempting calls
    HALF_OPEN = "half_open"  # Testing if service recovered

class BaseCircuitBreaker(BaseTactic):
    """Base circuit breaker implementation"""
    
    def __init__(self, service_name: str, config: Dict[str, Any] = None):
        super().__init__(f"circuit_breaker_{service_name}", config)
        self.service_name = service_name
        self.failure_threshold = self.config.get('failure_threshold', 5)
        self.timeout_duration = self.config.get('timeout_duration', 60)
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.next_attempt_time = None
    
    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if self.next_attempt_time and datetime.now(timezone.utc) >= self.next_attempt_time:
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        return False
    
    def record_success(self):
        """Record a successful operation"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
        self.logger.info(f"Circuit breaker for {self.service_name} closed after success")
    
    def record_failure(self):
        """Record a failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.next_attempt_time = datetime.now(timezone.utc) + \
                timedelta(seconds=self.timeout_duration)
            self.logger.warning(f"Circuit breaker for {self.service_name} opened after {self.failure_count} failures")
    
    def validate_config(self) -> bool:
        """Validate circuit breaker configuration"""
        return (self.failure_threshold > 0 and 
                self.timeout_duration > 0 and 
                self.service_name is not None)

class BaseQueue(BaseTactic):
    """Base queue implementation for managing work items"""
    
    def __init__(self, queue_name: str, max_size: int = 1000, config: Dict[str, Any] = None):
        super().__init__(f"queue_{queue_name}", config)
        self.queue_name = queue_name
        self.max_size = max_size
        self.items = []
    
    def enqueue(self, item: Any, priority: int = 0) -> bool:
        """Add item to queue with priority"""
        if len(self.items) >= self.max_size:
            self.logger.warning(f"Queue {self.queue_name} is full, dropping item")
            return False
        
        # Simple priority queue implementation
        self.items.append({
            'item': item,
            'priority': priority,
            'timestamp': datetime.now(timezone.utc)
        })
        self.items.sort(key=lambda x: x['priority'], reverse=True)
        return True
    
    def dequeue(self) -> Optional[Any]:
        """Remove and return highest priority item"""
        if not self.items:
            return None
        return self.items.pop(0)['item']
    
    def size(self) -> int:
        """Get current queue size"""
        return len(self.items)
    
    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return len(self.items) == 0
    
    def validate_config(self) -> bool:
        """Validate queue configuration"""
        return self.max_size > 0 and self.queue_name is not None

class BaseFeatureToggle(BaseTactic):
    """Base feature toggle implementation"""
    
    def __init__(self, feature_name: str, config: Dict[str, Any] = None):
        super().__init__(f"toggle_{feature_name}", config)
        self.feature_name = feature_name
        self.is_enabled = False
        self.rollout_percentage = 0
        self.target_users = []
    
    def is_feature_enabled(self, user_id: Optional[int] = None) -> bool:
        """Check if feature is enabled for user"""
        if not self.is_enabled:
            return False
        
        if self.rollout_percentage < 100:
            # Simple hash-based rollout
            if user_id is None:
                return False
            user_hash = hash(str(user_id)) % 100
            return user_hash < self.rollout_percentage
        
        return True
    
    def enable(self, rollout_percentage: int = 100, target_users: List[int] = None):
        """Enable the feature"""
        self.is_enabled = True
        self.rollout_percentage = rollout_percentage
        self.target_users = target_users or []
        self.logger.info(f"Feature {self.feature_name} enabled with {rollout_percentage}% rollout")
    
    def disable(self):
        """Disable the feature"""
        self.is_enabled = False
        self.rollout_percentage = 0
        self.target_users = []
        self.logger.info(f"Feature {self.feature_name} disabled")
    
    def validate_config(self) -> bool:
        """Validate feature toggle configuration"""
        return (0 <= self.rollout_percentage <= 100 and 
                self.feature_name is not None)

class BaseAdapter(ABC):
    """Base adapter pattern implementation"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def adapt(self, data: Any) -> Any:
        """Adapt data from one format to another"""
        pass
    
    @abstractmethod
    def can_handle(self, data: Any) -> bool:
        """Check if this adapter can handle the given data"""
        pass

class BasePublisher:
    """Base publisher for publish-subscribe pattern"""
    
    def __init__(self, topic: str):
        self.topic = topic
        self.subscribers = []
        self.logger = logging.getLogger(f"{__name__}.publisher_{topic}")
    
    def subscribe(self, subscriber):
        """Add a subscriber"""
        if subscriber not in self.subscribers:
            self.subscribers.append(subscriber)
            self.logger.info(f"Subscriber added to topic {self.topic}")
    
    def unsubscribe(self, subscriber):
        """Remove a subscriber"""
        if subscriber in self.subscribers:
            self.subscribers.remove(subscriber)
            self.logger.info(f"Subscriber removed from topic {self.topic}")
    
    def publish(self, message: Any):
        """Publish message to all subscribers"""
        for subscriber in self.subscribers:
            try:
                subscriber.receive(self.topic, message)
            except Exception as e:
                self.logger.error(f"Error notifying subscriber: {e}")

class BaseSubscriber(ABC):
    """Base subscriber for publish-subscribe pattern"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.subscriber_{name}")
    
    @abstractmethod
    def receive(self, topic: str, message: Any):
        """Receive and process a message"""
        pass

class BaseValidator:
    """Base input validator"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.validator_{name}")
    
    def validate(self, data: Any) -> Tuple[bool, str]:
        """Validate data and return (is_valid, error_message)"""
        try:
            return self._validate_impl(data)
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False, str(e)
    
    @abstractmethod
    def _validate_impl(self, data: Any) -> Tuple[bool, str]:
        """Implementation-specific validation logic"""
        pass

class BaseRetry(BaseTactic):
    """Base retry mechanism"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("retry", config)
        self.max_attempts = self.config.get('max_attempts', 3)
        self.delay = self.config.get('delay', 1.0)
        self.backoff_factor = self.config.get('backoff_factor', 2.0)
    
    def execute_with_retry(self, func, *args, **kwargs):
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    wait_time = self.delay * (self.backoff_factor ** attempt)
                    self.logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All {self.max_attempts} attempts failed")
        
        raise last_exception
    
    def validate_config(self) -> bool:
        """Validate retry configuration"""
        return (self.max_attempts > 0 and 
                self.delay > 0 and 
                self.backoff_factor > 0)

# Import time for retry functionality
import time
from datetime import timedelta
