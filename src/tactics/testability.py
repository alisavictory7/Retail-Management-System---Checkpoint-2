# src/tactics/testability.py
"""
Testability tactics implementation for Checkpoint 2.
Implements: Record/Playback, Dependency Injection
"""

from typing import Any, Dict, List, Optional, Tuple, Protocol, Type, TypeVar
from datetime import datetime, timezone
import logging
import json
import pickle
import os
from abc import ABC, abstractmethod

from .base import BaseTactic
from ..models import TestRecord, AuditLog, SystemMetrics

logger = logging.getLogger(__name__)

T = TypeVar('T')

# ==============================================
# DEPENDENCY INJECTION FRAMEWORK
# ==============================================

class ServiceContainer:
    """Dependency injection container"""
    
    def __init__(self):
        self.services = {}
        self.singletons = {}
        self.logger = logging.getLogger(__name__)
    
    def register(self, service_type: Type[T], implementation: Type[T], singleton: bool = False):
        """Register a service implementation"""
        self.services[service_type] = implementation
        if singleton:
            self.singletons[service_type] = None
        self.logger.info(f"Registered service: {service_type.__name__}")
    
    def register_instance(self, service_type: Type[T], instance: T):
        """Register a service instance"""
        self.services[service_type] = lambda: instance
        self.singletons[service_type] = instance
        self.logger.info(f"Registered instance: {service_type.__name__}")
    
    def get(self, service_type: Type[T]) -> T:
        """Get service instance"""
        if service_type not in self.services:
            raise ValueError(f"Service {service_type.__name__} not registered")
        
        # Return singleton if available
        if service_type in self.singletons and self.singletons[service_type] is not None:
            return self.singletons[service_type]
        
        # Create new instance
        implementation = self.services[service_type]
        instance = implementation()
        
        # Store as singleton if configured
        if service_type in self.singletons:
            self.singletons[service_type] = instance
        
        return instance
    
    def clear(self):
        """Clear all registrations (for testing)"""
        self.services.clear()
        self.singletons.clear()

# Global container instance
container = ServiceContainer()

def inject(service_type: Type[T]) -> T:
    """Dependency injection decorator"""
    return container.get(service_type)

# ==============================================
# MOCK SERVICES
# ==============================================

class MockPaymentService:
    """Mock payment service for testing"""
    
    def __init__(self, should_fail: bool = False, failure_rate: float = 0.0):
        self.should_fail = should_fail
        self.failure_rate = failure_rate
        self.call_count = 0
        self.logger = logging.getLogger(__name__)
    
    def process_payment(self, amount: float, payment_method: str, **kwargs) -> Tuple[bool, str]:
        """Process payment with configurable failure"""
        self.call_count += 1
        
        if self.should_fail:
            return False, "Mock payment service failure"
        
        if self.failure_rate > 0 and (self.call_count % int(1/self.failure_rate)) == 0:
            return False, f"Mock payment failure (call #{self.call_count})"
        
        return True, f"Mock payment successful for ${amount}"
    
    def reset(self):
        """Reset mock state"""
        self.call_count = 0
        self.should_fail = False
        self.failure_rate = 0.0

class MockPartnerAPI:
    """Mock partner API for testing"""
    
    def __init__(self, response_data: List[Dict[str, Any]] = None):
        self.response_data = response_data or []
        self.call_count = 0
        self.logger = logging.getLogger(__name__)
    
    def fetch_products(self, partner_id: int) -> List[Dict[str, Any]]:
        """Fetch products from partner"""
        self.call_count += 1
        return self.response_data
    
    def set_response_data(self, data: List[Dict[str, Any]]):
        """Set mock response data"""
        self.response_data = data

class MockDatabase:
    """Mock database for testing"""
    
    def __init__(self):
        self.data = {}
        self.transaction_active = False
        self.logger = logging.getLogger(__name__)
    
    def add(self, obj):
        """Add object to mock database"""
        table_name = obj.__class__.__name__
        if table_name not in self.data:
            self.data[table_name] = []
        self.data[table_name].append(obj)
    
    def query(self, model_class):
        """Mock query method"""
        return MockQuery(self.data.get(model_class.__name__, []))
    
    def commit(self):
        """Mock commit"""
        pass
    
    def rollback(self):
        """Mock rollback"""
        pass

class MockQuery:
    """Mock query object"""
    
    def __init__(self, data: List[Any]):
        self.data = data
    
    def filter_by(self, **kwargs):
        """Mock filter_by"""
        filtered = []
        for item in self.data:
            match = True
            for key, value in kwargs.items():
                if not hasattr(item, key) or getattr(item, key) != value:
                    match = False
                    break
            if match:
                filtered.append(item)
        return MockQuery(filtered)
    
    def first(self):
        """Mock first"""
        return self.data[0] if self.data else None
    
    def all(self):
        """Mock all"""
        return self.data
    
    def count(self):
        """Mock count"""
        return len(self.data)

# ==============================================
# RECORD/PLAYBACK TACTIC
# ==============================================

class TestRecorder(BaseTactic):
    """Record/Playback tactic for test reproducibility"""
    
    def __init__(self, db_session, config: Dict[str, Any] = None):
        super().__init__("test_recorder", config)
        self.db = db_session
        self.recording_dir = config.get('recording_dir', 'test_recordings')
        self.current_test = None
        self.sequence_number = 0
        
        # Create recording directory if it doesn't exist
        os.makedirs(self.recording_dir, exist_ok=True)
    
    def start_recording(self, test_name: str) -> Tuple[bool, str]:
        """Start recording a test"""
        try:
            self.current_test = test_name
            self.sequence_number = 0
            
            # Clear any existing records for this test
            self.db.query(TestRecord).filter_by(test_name=test_name).delete()
            self.db.commit()
            
            self.logger.info(f"Started recording test: {test_name}")
            return True, f"Started recording test: {test_name}"
            
        except Exception as e:
            self.logger.error(f"Failed to start recording: {e}")
            return False, f"Failed to start recording: {str(e)}"
    
    def record_request(self, endpoint: str, method: str, data: Dict[str, Any], 
                      headers: Dict[str, str] = None) -> Tuple[bool, str]:
        """Record a request"""
        try:
            if not self.current_test:
                return False, "No active test recording"
            
            record_data = {
                'endpoint': endpoint,
                'method': method,
                'data': data,
                'headers': headers or {},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self._save_record('request', record_data)
            return True, "Request recorded"
            
        except Exception as e:
            self.logger.error(f"Failed to record request: {e}")
            return False, f"Failed to record request: {str(e)}"
    
    def record_response(self, status_code: int, data: Dict[str, Any], 
                       headers: Dict[str, str] = None) -> Tuple[bool, str]:
        """Record a response"""
        try:
            if not self.current_test:
                return False, "No active test recording"
            
            record_data = {
                'status_code': status_code,
                'data': data,
                'headers': headers or {},
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self._save_record('response', record_data)
            return True, "Response recorded"
            
        except Exception as e:
            self.logger.error(f"Failed to record response: {e}")
            return False, f"Failed to record response: {str(e)}"
    
    def record_state(self, state_name: str, state_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Record system state"""
        try:
            if not self.current_test:
                return False, "No active test recording"
            
            record_data = {
                'state_name': state_name,
                'state_data': state_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self._save_record('state', record_data)
            return True, "State recorded"
            
        except Exception as e:
            self.logger.error(f"Failed to record state: {e}")
            return False, f"Failed to record state: {str(e)}"
    
    def _save_record(self, record_type: str, data: Dict[str, Any]):
        """Save record to database"""
        self.sequence_number += 1
        
        record = TestRecord(
            test_name=self.current_test,
            record_type=record_type,
            sequence_number=self.sequence_number,
            timestamp=datetime.now(timezone.utc),
            data=json.dumps(data),
            record_metadata=json.dumps({
                'recording_time': datetime.now(timezone.utc).isoformat()
            })
        )
        
        self.db.add(record)
        self.db.commit()
    
    def stop_recording(self) -> Tuple[bool, str]:
        """Stop recording"""
        try:
            if not self.current_test:
                return False, "No active test recording"
            
            test_name = self.current_test
            self.current_test = None
            self.sequence_number = 0
            
            self.logger.info(f"Stopped recording test: {test_name}")
            return True, f"Stopped recording test: {test_name}"
            
        except Exception as e:
            self.logger.error(f"Failed to stop recording: {e}")
            return False, f"Failed to stop recording: {str(e)}"
    
    def playback_test(self, test_name: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """Playback a recorded test"""
        try:
            # Get all records for the test
            records = self.db.query(TestRecord).filter_by(
                test_name=test_name
            ).order_by(TestRecord.sequence_number).all()
            
            if not records:
                return False, []
            
            playback_data = []
            for record in records:
                data = json.loads(record.data)
                playback_data.append({
                    'type': record.record_type,
                    'sequence': record.sequence_number,
                    'data': data,
                    'timestamp': record.timestamp.isoformat()
                })
            
            self.logger.info(f"Playback test: {test_name} ({len(playback_data)} records)")
            return True, playback_data
            
        except Exception as e:
            self.logger.error(f"Failed to playback test: {e}")
            return False, []
    
    def get_test_summary(self, test_name: str) -> Dict[str, Any]:
        """Get test recording summary"""
        try:
            records = self.db.query(TestRecord).filter_by(test_name=test_name).all()
            
            summary = {
                'test_name': test_name,
                'total_records': len(records),
                'record_types': {},
                'duration': None
            }
            
            if records:
                # Count record types
                for record in records:
                    record_type = record.record_type
                    summary['record_types'][record_type] = summary['record_types'].get(record_type, 0) + 1
                
                # Calculate duration
                timestamps = [record.timestamp for record in records]
                if timestamps:
                    summary['duration'] = (max(timestamps) - min(timestamps)).total_seconds()
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get test summary: {e}")
            return {}
    
    def execute(self, test_name: str) -> Tuple[bool, str]:
        """Execute test recording operation"""
        return self.start_recording(test_name)
    
    def validate_config(self) -> bool:
        """Validate test recorder configuration"""
        return self.db is not None

# ==============================================
# TESTING INFRASTRUCTURE
# ==============================================

class TestEnvironment:
    """Test environment setup and teardown"""
    
    def __init__(self, db_session, config: Dict[str, Any] = None):
        self.db = db_session
        self.config = config or {}
        self.container = ServiceContainer()
        self.recorder = TestRecorder(db_session, self.config.get('recorder', {}))
        self.logger = logging.getLogger(__name__)
    
    def setup_test(self, test_name: str) -> Tuple[bool, str]:
        """Setup test environment"""
        try:
            # Clear container
            self.container.clear()
            
            # Register mock services
            self.container.register_instance(MockPaymentService, MockPaymentService())
            self.container.register_instance(MockPartnerAPI, MockPartnerAPI())
            self.container.register_instance(MockDatabase, MockDatabase())
            
            # Start recording
            success, message = self.recorder.start_recording(test_name)
            if not success:
                return False, f"Failed to start recording: {message}"
            
            self.logger.info(f"Test environment setup complete: {test_name}")
            return True, f"Test environment setup complete: {test_name}"
            
        except Exception as e:
            self.logger.error(f"Failed to setup test environment: {e}")
            return False, f"Failed to setup test environment: {str(e)}"
    
    def teardown_test(self) -> Tuple[bool, str]:
        """Teardown test environment"""
        try:
            # Stop recording
            success, message = self.recorder.stop_recording()
            if not success:
                return False, f"Failed to stop recording: {message}"
            
            # Clear container
            self.container.clear()
            
            self.logger.info("Test environment teardown complete")
            return True, "Test environment teardown complete"
            
        except Exception as e:
            self.logger.error(f"Failed to teardown test environment: {e}")
            return False, f"Failed to teardown test environment: {str(e)}"
    
    def get_mock_service(self, service_type: Type[T]) -> T:
        """Get mock service instance"""
        return self.container.get(service_type)
    
    def record_request(self, endpoint: str, method: str, data: Dict[str, Any], 
                      headers: Dict[str, str] = None):
        """Record a test request"""
        return self.recorder.record_request(endpoint, method, data, headers)
    
    def record_response(self, status_code: int, data: Dict[str, Any], 
                       headers: Dict[str, str] = None):
        """Record a test response"""
        return self.recorder.record_response(status_code, data, headers)
    
    def record_state(self, state_name: str, state_data: Dict[str, Any]):
        """Record system state"""
        return self.recorder.record_state(state_name, state_data)

# ==============================================
# TESTABILITY MANAGER
# ==============================================

class TestabilityManager:
    """Central manager for all testability tactics"""
    
    def __init__(self, db_session, config: Dict[str, Any] = None):
        self.db = db_session
        self.config = config or {}
        self.test_environment = TestEnvironment(db_session, self.config.get('test_environment', {}))
        self.recorder = TestRecorder(db_session, self.config.get('recorder', {}))
        self.logger = logging.getLogger(__name__)
    
    def run_test_with_recording(self, test_name: str, test_func) -> Tuple[bool, Dict[str, Any]]:
        """Run test with recording and playback capability"""
        try:
            # Setup test environment
            success, message = self.test_environment.setup_test(test_name)
            if not success:
                return False, {"error": message}
            
            # Run the test
            test_result = test_func(self.test_environment)
            
            # Teardown test environment
            self.test_environment.teardown_test()
            
            # Get test summary
            summary = self.recorder.get_test_summary(test_name)
            summary['test_result'] = test_result
            
            return True, summary
            
        except Exception as e:
            self.logger.error(f"Test execution failed: {e}")
            return False, {"error": str(e)}
    
    def playback_test(self, test_name: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """Playback a recorded test"""
        return self.recorder.playback_test(test_name)
    
    def get_available_tests(self) -> List[str]:
        """Get list of available recorded tests"""
        try:
            tests = self.db.query(TestRecord.test_name).distinct().all()
            return [test[0] for test in tests]
        except Exception as e:
            self.logger.error(f"Failed to get available tests: {e}")
            return []
