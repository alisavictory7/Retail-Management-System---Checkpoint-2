# tests/test_security_tactics.py
"""
Comprehensive tests for Security tactics:
- Authenticate Actors
- Validate Input
"""

import pytest
import json
from unittest.mock import patch

from src.tactics.security import SecurityManager, AuthenticateActorsTactic, ValidateInputTactic

class TestAuthenticateActors:
    """Test Authenticate Actors tactic for partner API security"""
    
    def test_valid_api_key_authentication(self, db_session, sample_partner):
        """Test authentication with valid API key"""
        auth = AuthenticateActorsTactic(db_session, {})
        
        # Get the actual API key from the sample partner
        from src.models import PartnerAPIKey
        api_key_obj = db_session.query(PartnerAPIKey).filter_by(partnerID=sample_partner.partnerID).first()
        actual_api_key = api_key_obj.api_key
        
        success, message = auth.execute(actual_api_key)
        
        assert success == True
        assert "Authenticated partner" in message
    
    def test_invalid_api_key_rejection(self, db_session):
        """Test that invalid API keys are rejected"""
        auth = AuthenticateActorsTactic(db_session, {})
        
        success, message = auth.execute("invalid_key")
        
        assert success == False
        assert "Invalid API key" in message
    
    def test_expired_api_key_rejection(self, db_session, sample_partner):
        """Test that expired API keys are rejected"""
        # Create expired API key
        from src.models import PartnerAPIKey
        from datetime import datetime, timezone, timedelta
        
        expired_key = PartnerAPIKey(
            partnerID=sample_partner.partnerID,
            api_key="expired_key",
            is_active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        db_session.add(expired_key)
        db_session.commit()
        
        auth = AuthenticateActorsTactic(db_session, {})
        success, message = auth.execute("expired_key")
        
        assert success == False
        assert "expired" in message.lower()
    
    def test_inactive_api_key_rejection(self, db_session, sample_partner):
        """Test that inactive API keys are rejected"""
        # Create inactive API key
        from src.models import PartnerAPIKey
        
        inactive_key = PartnerAPIKey(
            partnerID=sample_partner.partnerID,
            api_key="inactive_key",
            is_active=False
        )
        db_session.add(inactive_key)
        db_session.commit()
        
        auth = AuthenticateActorsTactic(db_session, {})
        success, message = auth.execute("inactive_key")
        
        assert success == False
        assert "Invalid API key" in message
    
    def test_authentication_usage_tracking(self, db_session, sample_partner):
        """Test that API key usage is tracked"""
        auth = AuthenticateActorsTactic(db_session, {})
        
        # Get the actual API key from the sample partner
        from src.models import PartnerAPIKey
        api_key = db_session.query(PartnerAPIKey).filter_by(partnerID=sample_partner.partnerID).first()
        actual_api_key = api_key.api_key
        initial_count = api_key.usage_count
        
        # Authenticate
        auth.execute(actual_api_key)
        
        # Check usage count increased
        db_session.refresh(api_key)
        assert api_key.usage_count == initial_count + 1
    
    def test_authentication_audit_logging(self, db_session):
        """Test that failed authentication attempts are logged"""
        auth = AuthenticateActorsTactic(db_session, {})
        
        # Attempt authentication with invalid key
        auth.execute("invalid_key")
        
        # Check audit log
        from src.models import AuditLog
        audit_logs = db_session.query(AuditLog).filter_by(
            event_type="authentication_failed"
        ).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].success == False

class TestValidateInput:
    """Test Validate Input tactic for SQL injection and XSS prevention"""
    
    def test_valid_input_passes_validation(self, db_session):
        """Test that valid input passes validation"""
        validator = ValidateInputTactic(db_session, {})
        
        valid_data = {
            "name": "Test Product",
            "description": "A valid product description",
            "price": 10.99
        }
        
        success, message = validator.execute(valid_data)
        
        assert success == True
        assert "successful" in message.lower()
    
    def test_sql_injection_detection(self, db_session):
        """Test that SQL injection attempts are detected"""
        validator = ValidateInputTactic(db_session, {})
        
        malicious_data = {
            "name": "Test'; DROP TABLE products; --",
            "description": "SELECT * FROM users WHERE 1=1",
            "price": 10.99
        }
        
        success, message = validator.execute(malicious_data)
        
        assert success == False
        assert "SQL injection" in message
    
    def test_xss_attempt_detection(self, db_session):
        """Test that XSS attempts are detected and sanitized"""
        validator = ValidateInputTactic(db_session, {})
        
        malicious_data = {
            "name": "Test Product",
            "description": "<script>alert('XSS')</script>",
            "price": 10.99
        }
        
        success, message = validator.execute(malicious_data)
        
        assert success == False
        assert "Potential SQL injection detected" in message or "HTML content" in message
    
    def test_suspicious_characters_detection(self, db_session):
        """Test that suspicious characters are detected"""
        validator = ValidateInputTactic(db_session, {})
        
        suspicious_data = {
            "name": "Test Product",
            "description": "Description with < and > characters",
            "price": 10.99
        }
        
        success, message = validator.execute(suspicious_data)
        
        assert success == False
        assert "HTML content detected and sanitized" in message or "Suspicious character" in message
    
    def test_nested_data_validation(self, db_session):
        """Test that nested data structures are validated"""
        validator = ValidateInputTactic(db_session, {})
        
        nested_data = {
            "products": [
                {
                    "name": "Product 1",
                    "description": "Valid description"
                },
                {
                    "name": "Product 2'; DROP TABLE products; --",
                    "description": "Malicious description"
                }
            ]
        }
        
        success, message = validator.execute(nested_data)
        
        assert success == False
        assert "SQL injection" in message
    
    def test_validation_audit_logging(self, db_session):
        """Test that validation failures are logged"""
        validator = ValidateInputTactic(db_session, {})
        
        malicious_data = {"name": "'; DROP TABLE products; --"}
        validator.execute(malicious_data)
        
        # Check audit log
        from src.models import AuditLog
        audit_logs = db_session.query(AuditLog).filter_by(
            event_type="input_validation_failed"
        ).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].success == False

class TestSecurityIntegration:
    """Integration tests for security tactics working together"""
    
    def test_secure_operation_flow(self, db_session, sample_partner):
        """Test complete secure operation flow"""
        security_manager = SecurityManager(db_session, {})
        
        valid_data = {
            "name": "Test Product",
            "description": "Valid product description",
            "price": 10.99
        }
        
        # Get the actual API key from the sample partner
        from src.models import PartnerAPIKey
        api_key = db_session.query(PartnerAPIKey).filter_by(partnerID=sample_partner.partnerID).first()
        actual_api_key = api_key.api_key
        
        success, message = security_manager.is_secure_operation(actual_api_key, valid_data)
        
        assert success == True
        assert "secure" in message.lower()
    
    def test_insecure_operation_rejection(self, db_session):
        """Test that insecure operations are rejected"""
        security_manager = SecurityManager(db_session)
        
        malicious_data = {
            "name": "'; DROP TABLE products; --",
            "description": "<script>alert('XSS')</script>",
            "price": 10.99
        }
        
        success, message = security_manager.is_secure_operation("invalid_key", malicious_data)
        
        assert success == False
        assert "Authentication failed" in message
    
    def test_authentication_before_validation(self, db_session, sample_partner):
        """Test that authentication happens before validation"""
        security_manager = SecurityManager(db_session)
        
        malicious_data = {"name": "'; DROP TABLE products; --"}
        
        # Should fail at authentication step, not validation
        success, message = security_manager.is_secure_operation("invalid_key", malicious_data)
        
        assert success == False
        assert "Authentication failed" in message
    
    def test_partner_data_validation_flow(self, db_session, sample_partner, sample_partner_data):       
        """Test complete partner data validation flow"""
        security_manager = SecurityManager(db_session, {})
        
        # Test CSV data (parse first)
        import json
        csv_lines = sample_partner_data['csv_data'].split('\n')
        csv_data = [line.split(',') for line in csv_lines[1:]]  # Skip header
        success, message = security_manager.validate_partner_data(csv_data)
        assert success == True
        
        # Test JSON data (parse first)
        json_data = json.loads(sample_partner_data['json_data'])
        success, message = security_manager.validate_partner_data(json_data)
        assert success == True
        
        # Test malicious data
        malicious_csv = "name,price,stock\n'; DROP TABLE products; --,10.99,100"
        success, message = security_manager.validate_partner_data(malicious_csv)
        assert success == False

class TestSecurityEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_input_validation(self, db_session):
        """Test validation of empty input"""
        validator = ValidateInputTactic(db_session, {})
        
        success, message = validator.execute("")
        assert success == True
        
        success, message = validator.execute({})
        assert success == True
    
    def test_none_input_validation(self, db_session):
        """Test validation of None input"""
        validator = ValidateInputTactic(db_session, {})
        
        success, message = validator.execute(None)
        assert success == True
    
    def test_large_input_validation(self, db_session):
        """Test validation of large input data"""
        validator = ValidateInputTactic(db_session, {})
        
        large_data = {
            "name": "A" * 10000,  # Very long name
            "description": "B" * 50000,  # Very long description
            "price": 10.99
        }
        
        success, message = validator.execute(large_data)
        assert success == True
    
    def test_unicode_input_validation(self, db_session):
        """Test validation of Unicode input"""
        validator = ValidateInputTactic(db_session, {})
        
        unicode_data = {
            "name": "产品名称",
            "description": "产品描述 with émojis 🚀",
            "price": 10.99
        }
        
        success, message = validator.execute(unicode_data)
        assert success == True
    
    def test_database_connection_error_handling(self, db_session):
        """Test error handling when database connection fails"""
        # Mock database session to raise exception
        with patch.object(db_session, 'query', side_effect=Exception("Database error")):
            auth = AuthenticateActorsTactic(db_session, {})
            success, message = auth.execute("test_key")
            
            assert success == False
            assert "error" in message.lower()
