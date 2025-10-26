# src/tactics/security.py
"""
Security tactics implementation for Checkpoint 2.
Implements: Authenticate Actors, Validate Input
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import logging
import hashlib
import bleach
import re
from sqlalchemy.orm import Session

from .base import BaseTactic, BaseValidator
from ..models import PartnerAPIKey, AuditLog, SystemMetrics

logger = logging.getLogger(__name__)

class AuthenticateActorsTactic(BaseTactic):
    """Authenticate Actors tactic for partner API security"""
    
    def __init__(self, db_session: Session, config: Dict[str, Any] = None):
        super().__init__("authenticate_actors", config)
        self.db = db_session
    
    def execute(self, api_key: str, partner_id: Optional[int] = None) -> Tuple[bool, str]:
        """Authenticate partner using API key"""
        try:
            # Find API key in database
            api_key_record = self.db.query(PartnerAPIKey).filter_by(
                api_key=api_key,
                is_active=True
            ).first()
            
            if not api_key_record:
                self._log_failed_auth(api_key, "Invalid API key")
                return False, "Invalid API key"
            
            # Check if key is expired
            if api_key_record.expires_at:
                now = datetime.now(timezone.utc)
                expires_at = api_key_record.expires_at
                # Handle both timezone-aware and timezone-naive datetimes
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at < now:
                    self._log_failed_auth(api_key, "API key expired")
                    return False, "API key expired"
            
            # Update usage statistics
            api_key_record.last_used = datetime.now(timezone.utc)
            api_key_record.usage_count += 1
            self.db.commit()
            
            self.log_metric("auth_success", 1, {
                "partner_id": str(api_key_record.partnerID),
                "tactic": "authenticate_actors"
            })
            
            return True, f"Authenticated partner {api_key_record.partnerID}"
            
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            self._log_failed_auth(api_key, f"Authentication error: {str(e)}")
            return False, f"Authentication error: {str(e)}"
    
    def _log_failed_auth(self, api_key: str, reason: str):
        """Log failed authentication attempt"""
        try:
            audit = AuditLog(
                event_type="authentication_failed",
                entity_type="PartnerAPIKey",
                action="authenticate",
                new_values=f'{{"api_key": "{api_key[:8]}...", "reason": "{reason}"}}',
                success=False,
                error_message=reason
            )
            self.db.add(audit)
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Failed to log audit: {e}")
    
    def validate_config(self) -> bool:
        """Validate authentication configuration"""
        return self.db is not None

class InputValidator(BaseValidator):
    """Input validation for SQL injection prevention"""
    
    def __init__(self, name: str = "input_validator"):
        super().__init__(name)
        self.sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+'.*'\s*=\s*'.*')",
            r"(--|#|\/\*|\*\/)",
            r"(\b(UNION|UNION ALL)\b)",
            r"(\b(SCRIPT|JAVASCRIPT|VBSCRIPT)\b)",
            r"(\b(ONLOAD|ONERROR|ONCLICK)\b)",
        ]
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.sql_patterns]
    
    def _validate_impl(self, data: Any) -> Tuple[bool, str]:
        """Validate input for SQL injection and XSS"""
        if isinstance(data, str):
            # Check for SQL injection patterns
            for pattern in self.compiled_patterns:
                if pattern.search(data):
                    return False, f"Potential SQL injection detected: {pattern.pattern}"
            
            # Sanitize HTML content
            sanitized = bleach.clean(data, tags=[], strip=True)
            if sanitized != data:
                return False, "HTML content detected and sanitized"
            
            # Check for suspicious characters
            suspicious_chars = ['<', '>', '"', "'", ';', '--', '/*', '*/']
            for char in suspicious_chars:
                if char in data:
                    return False, f"Suspicious character detected: {char}"
        
        elif isinstance(data, dict):
            # Recursively validate dictionary values
            for key, value in data.items():
                is_valid, error = self._validate_impl(value)
                if not is_valid:
                    return False, f"Invalid value for key '{key}': {error}"
        
        elif isinstance(data, list):
            # Validate list items
            for i, item in enumerate(data):
                is_valid, error = self._validate_impl(item)
                if not is_valid:
                    return False, f"Invalid item at index {i}: {error}"
        
        return True, "Input is valid"
    
    def sanitize_input(self, data: str) -> str:
        """Sanitize input data"""
        # Remove HTML tags
        sanitized = bleach.clean(data, tags=[], strip=True)
        
        # Escape special characters
        sanitized = sanitized.replace("'", "''")
        sanitized = sanitized.replace('"', '""')
        sanitized = sanitized.replace(';', '')
        sanitized = sanitized.replace('--', '')
        
        return sanitized

class ValidateInputTactic(BaseTactic):
    """Validate Input tactic for partner feed security"""
    
    def __init__(self, db_session: Session, config: Dict[str, Any] = None):
        super().__init__("validate_input", config)
        self.db = db_session
        self.validator = InputValidator()
    
    def execute(self, input_data: Any, data_type: str = "partner_feed") -> Tuple[bool, str]:
        """Validate input data for security threats"""
        try:
            is_valid, error_message = self.validator.validate(input_data)
            
            if is_valid:
                self.log_metric("input_validation_success", 1, {
                    "data_type": data_type,
                    "tactic": "validate_input"
                })
                return True, "Input validation successful"
            else:
                self._log_validation_failure(input_data, error_message, data_type)
                return False, f"Input validation failed: {error_message}"
                
        except Exception as e:
            self.logger.error(f"Input validation error: {e}")
            self._log_validation_failure(input_data, str(e), data_type)
            return False, f"Input validation error: {str(e)}"
    
    def _log_validation_failure(self, input_data: Any, error_message: str, data_type: str):
        """Log validation failure"""
        try:
            # Truncate input data for logging
            data_str = str(input_data)[:100] + "..." if len(str(input_data)) > 100 else str(input_data)
            
            audit = AuditLog(
                event_type="input_validation_failed",
                entity_type="PartnerFeed",
                action="validate",
                new_values=f'{{"data_type": "{data_type}", "error": "{error_message}"}}',
                success=False,
                error_message=f"Validation failed for {data_type}: {error_message}"
            )
            self.db.add(audit)
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Failed to log validation failure: {e}")
    
    def validate_config(self) -> bool:
        """Validate input validation configuration"""
        return self.db is not None and self.validator is not None

class SecurityManager:
    """Central security manager for all security tactics"""
    
    def __init__(self, db_session: Session, config: Dict[str, Any] = None):
        self.db = db_session
        self.config = config or {}
        self.auth_tactic = AuthenticateActorsTactic(db_session, self.config.get('auth', {}))
        self.input_tactic = ValidateInputTactic(db_session, self.config.get('input', {}))
        self.logger = logging.getLogger(__name__)
    
    def authenticate_partner(self, api_key: str) -> Tuple[bool, str]:
        """Authenticate partner with API key"""
        return self.auth_tactic.execute(api_key)
    
    def validate_partner_data(self, data: Any) -> Tuple[bool, str]:
        """Validate partner data for security threats"""
        return self.input_tactic.execute(data, "partner_feed")
    
    def is_secure_operation(self, api_key: str, data: Any) -> Tuple[bool, str]:
        """Check if operation is secure (both auth and validation)"""
        # First authenticate
        auth_success, auth_message = self.authenticate_partner(api_key)
        if not auth_success:
            return False, f"Authentication failed: {auth_message}"
        
        # Then validate input
        validation_success, validation_message = self.validate_partner_data(data)
        if not validation_success:
            return False, f"Input validation failed: {validation_message}"
        
        return True, "Operation is secure"
