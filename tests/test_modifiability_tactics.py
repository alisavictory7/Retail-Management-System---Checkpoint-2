# tests/test_modifiability_tactics.py
"""
Comprehensive tests for Modifiability tactics:
- Use Intermediary/Encapsulate
- Adapter Pattern
- Feature Toggle
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from src.tactics.modifiability import (
    ModifiabilityManager, PartnerDataIntermediary, DatabaseFeatureToggle,
    CSVDataAdapter, JSONDataAdapter, XMLDataAdapter
)

class TestAdapterPattern:
    """Test Adapter Pattern for different data formats"""
    
    def test_csv_adapter_parsing(self):
        """Test CSV data adapter parsing"""
        adapter = CSVDataAdapter()
        
        csv_data = "name,price,stock\nProduct A,10.99,100\nProduct B,25.50,50"
        
        result = adapter.adapt(csv_data)
        
        assert result['format'] == 'csv'
        assert len(result['products']) == 2
        assert result['products'][0]['name'] == 'Product A'
        assert result['products'][0]['price'] == '10.99'
        assert result['products'][1]['name'] == 'Product B'
        assert result['products'][1]['price'] == '25.50'
    
    def test_csv_adapter_can_handle(self):
        """Test CSV adapter can handle detection"""
        adapter = CSVDataAdapter()
        
        csv_data = "name,price,stock\nProduct A,10.99,100"
        non_csv_data = '{"name": "Product A"}'
        
        assert adapter.can_handle(csv_data) == True
        assert adapter.can_handle(non_csv_data) == False
    
    def test_json_adapter_parsing(self):
        """Test JSON data adapter parsing"""
        adapter = JSONDataAdapter()
        
        json_data = '{"products": [{"name": "Product A", "price": 10.99, "stock": 100}]}'
        
        result = adapter.adapt(json_data)
        
        assert result['format'] == 'json'
        assert len(result['products']) == 1
        assert result['products'][0]['name'] == 'Product A'
        assert result['products'][0]['price'] == 10.99
    
    def test_json_adapter_can_handle(self):
        """Test JSON adapter can handle detection"""
        adapter = JSONDataAdapter()
        
        json_data = '{"name": "Product A"}'
        non_json_data = "name,price,stock\nProduct A,10.99,100"
        
        assert adapter.can_handle(json_data) == True
        assert adapter.can_handle(non_json_data) == False
    
    def test_xml_adapter_parsing(self):
        """Test XML data adapter parsing"""
        adapter = XMLDataAdapter()
        
        xml_data = '''<products>
            <product>
                <name>Product A</name>
                <price>10.99</price>
                <stock>100</stock>
            </product>
        </products>'''
        
        result = adapter.adapt(xml_data)
        
        assert result['format'] == 'xml'
        assert len(result['products']) == 1
        assert result['products'][0]['name'] == 'Product A'
        assert result['products'][0]['price'] == '10.99'
    
    def test_xml_adapter_can_handle(self):
        """Test XML adapter can handle detection"""
        adapter = XMLDataAdapter()
        
        xml_data = '<product><name>Product A</name></product>'
        non_xml_data = '{"name": "Product A"}'
        
        assert adapter.can_handle(xml_data) == True
        assert adapter.can_handle(non_xml_data) == False

class TestPartnerDataIntermediary:
    """Test Use Intermediary/Encapsulate tactic for partner data processing"""
    
    def test_intermediary_auto_detection(self):
        """Test that intermediary auto-detects data format"""
        intermediary = PartnerDataIntermediary()
        
        # Test CSV
        csv_data = "name,price,stock\nProduct A,10.99,100"
        success, result = intermediary.execute(csv_data)
        assert success == True
        assert result['format'] == 'csv'
        
        # Test JSON
        json_data = '{"products": [{"name": "Product A", "price": 10.99}]}'
        success, result = intermediary.execute(json_data)
        assert success == True
        assert result['format'] == 'json'
        
        # Test XML
        xml_data = '<products><product><name>Product A</name></product></products>'
        success, result = intermediary.execute(xml_data)
        assert success == True
        assert result['format'] == 'xml'
    
    def test_intermediary_specific_format(self):
        """Test that intermediary can handle specific format requests"""
        intermediary = PartnerDataIntermediary()
        
        csv_data = "name,price,stock\nProduct A,10.99,100"
        success, result = intermediary.execute(csv_data, partner_format="csv")
        assert success == True
        assert result['format'] == 'csv'
    
    def test_intermediary_unknown_format(self):
        """Test that intermediary handles unknown formats gracefully"""
        intermediary = PartnerDataIntermediary()
        
        unknown_data = "This is not a recognized format"
        success, result = intermediary.execute(unknown_data)
        assert success == False
        assert "No suitable adapter" in result['error']
    
    def test_intermediary_add_adapter(self):
        """Test that new adapters can be added dynamically"""
        intermediary = PartnerDataIntermediary()
        
        # Create custom adapter
        class CustomAdapter:
            def __init__(self):
                self.name = "custom_adapter"
            
            def adapt(self, data):
                return {'format': 'custom', 'data': data}
            
            def can_handle(self, data):
                return 'custom' in data
        
        custom_adapter = CustomAdapter()
        intermediary.add_adapter(custom_adapter)
        
        # Test custom adapter
        custom_data = "This is custom data format"
        success, result = intermediary.execute(custom_data)
        assert success == True
        assert result['format'] == 'custom'

class TestFeatureToggle:
    """Test Feature Toggle mechanism for runtime feature control"""
    
    def test_feature_toggle_creation(self, db_session):
        """Test creating a new feature toggle"""
        toggle = DatabaseFeatureToggle(db_session, "test_feature")
        
        # Initially disabled
        enabled, message = toggle.execute()
        assert enabled == False
        assert "not found" in message
    
    def test_feature_toggle_enable(self, db_session):
        """Test enabling a feature toggle"""
        toggle = DatabaseFeatureToggle(db_session, "test_feature")
        
        success, message = toggle.enable(rollout_percentage=100, updated_by="test_user")
        assert success == True
        assert "enabled" in message
        
        # Check database
        from src.models import FeatureToggle
        db_toggle = db_session.query(FeatureToggle).filter_by(
            feature_name="test_feature"
        ).first()
        assert db_toggle is not None
        assert db_toggle.is_enabled == True
        assert db_toggle.rollout_percentage == 100
    
    def test_feature_toggle_disable(self, db_session):
        """Test disabling a feature toggle"""
        toggle = DatabaseFeatureToggle(db_session, "test_feature")
        
        # Enable first
        toggle.enable(rollout_percentage=100, updated_by="test_user")
        
        # Then disable
        success, message = toggle.disable(updated_by="test_user")
        assert success == True
        assert "disabled" in message
        
        # Check database
        from src.models import FeatureToggle
        db_toggle = db_session.query(FeatureToggle).filter_by(
            feature_name="test_feature"
        ).first()
        assert db_toggle.is_enabled == False
        assert db_toggle.rollout_percentage == 0
    
    def test_feature_toggle_rollout_percentage(self, db_session):
        """Test feature toggle with partial rollout"""
        toggle = DatabaseFeatureToggle(db_session, "test_feature")
        
        # Enable with 50% rollout
        toggle.enable(rollout_percentage=50, updated_by="test_user")
        
        # Test with different user IDs
        enabled1, _ = toggle.execute(user_id=1)
        enabled2, _ = toggle.execute(user_id=2)
        enabled3, _ = toggle.execute(user_id=3)
        enabled4, _ = toggle.execute(user_id=4)
        
        # Should have roughly 50% enabled (due to hash-based selection)
        enabled_count = sum([enabled1, enabled2, enabled3, enabled4])
        assert enabled_count >= 1  # At least some should be enabled
        assert enabled_count <= 3  # Not all should be enabled
    
    def test_feature_toggle_target_users(self, db_session):
        """Test feature toggle with specific target users"""
        toggle = DatabaseFeatureToggle(db_session, "test_feature")
        
        # Enable for specific users only
        toggle.enable(rollout_percentage=100, target_users=[1, 3], updated_by="test_user")
        
        # Test with different user IDs
        enabled1, _ = toggle.execute(user_id=1)
        enabled2, _ = toggle.execute(user_id=2)
        enabled3, _ = toggle.execute(user_id=3)
        enabled4, _ = toggle.execute(user_id=4)
        
        assert enabled1 == True
        assert enabled2 == False
        assert enabled3 == True
        assert enabled4 == False
    
    def test_feature_toggle_audit_logging(self, db_session):
        """Test that feature toggle changes are audited"""
        toggle = DatabaseFeatureToggle(db_session, "test_feature")
        
        # Enable feature
        toggle.enable(rollout_percentage=100, updated_by="test_user")
        
        # Check audit log
        from src.models import AuditLog
        audit_logs = db_session.query(AuditLog).filter_by(
            event_type="feature_toggle"
        ).all()
        assert len(audit_logs) == 1
        assert audit_logs[0].action == "feature_enabled"

class TestModifiabilityManager:
    """Test Modifiability Manager integration"""
    
    def test_modifiability_manager_initialization(self, db_session):
        """Test modifiability manager initialization"""
        manager = ModifiabilityManager(db_session)
        
        assert manager.db == db_session
        assert manager.data_intermediary is not None
        assert isinstance(manager.data_intermediary, PartnerDataIntermediary)
    
    def test_process_partner_data(self, db_session, sample_partner_data):
        """Test processing partner data through manager"""
        manager = ModifiabilityManager(db_session)
        
        # Test CSV processing
        success, result = manager.process_partner_data(sample_partner_data['csv_data'])
        assert success == True
        assert result['format'] == 'csv'
        
        # Test JSON processing
        success, result = manager.process_partner_data(sample_partner_data['json_data'])
        assert success == True
        assert result['format'] == 'json'
    
    def test_feature_toggle_management(self, db_session):
        """Test feature toggle management through manager"""
        manager = ModifiabilityManager(db_session)
        
        # Enable feature
        success, message = manager.enable_feature("test_feature", 100, updated_by="test_user")
        assert success == True
        
        # Check if enabled
        enabled, message = manager.is_feature_enabled("test_feature", user_id=1)
        assert enabled == True
        
        # Disable feature
        success, message = manager.disable_feature("test_feature", updated_by="test_user")
        assert success == True
        
        # Check if disabled
        enabled, message = manager.is_feature_enabled("test_feature", user_id=1)
        assert enabled == False
    
    def test_get_feature_toggle_caching(self, db_session):
        """Test that feature toggles are cached in manager"""
        manager = ModifiabilityManager(db_session)
        
        # Get feature toggle twice
        toggle1 = manager.get_feature_toggle("test_feature")
        toggle2 = manager.get_feature_toggle("test_feature")
        
        # Should be the same instance (cached)
        assert toggle1 is toggle2

class TestModifiabilityIntegration:
    """Integration tests for modifiability tactics working together"""
    
    def test_complete_partner_integration_flow(self, db_session, sample_partner_data):
        """Test complete partner integration flow with all tactics"""
        manager = ModifiabilityManager(db_session)
        
        # Enable partner sync feature
        manager.enable_feature("partner_sync_enabled", 100, updated_by="test_user")
        
        # Process different data formats
        formats = ['csv', 'json', 'xml']
        for format_type in formats:
            data = sample_partner_data[f'{format_type}_data']
            success, result = manager.process_partner_data(data, format_type)
            assert success == True
            assert result['format'] == format_type
    
    def test_feature_toggle_with_data_processing(self, db_session, sample_partner_data):
        """Test feature toggle affecting data processing"""
        manager = ModifiabilityManager(db_session)
        
        # Initially disabled
        enabled, _ = manager.is_feature_enabled("partner_sync_enabled", user_id=1)
        assert enabled == False
        
        # Enable feature
        manager.enable_feature("partner_sync_enabled", 100, updated_by="test_user")
        
        # Now should be enabled
        enabled, _ = manager.is_feature_enabled("partner_sync_enabled", user_id=1)
        assert enabled == True
        
        # Data processing should work
        success, result = manager.process_partner_data(sample_partner_data['csv_data'])
        assert success == True

class TestModifiabilityEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_adapter_with_malformed_data(self):
        """Test adapters with malformed data"""
        csv_adapter = CSVDataAdapter()
        
        # Malformed CSV
        malformed_csv = "name,price\nProduct A,10.99\nIncomplete row"
        result = csv_adapter.adapt(malformed_csv)
        
        # Should handle gracefully
        assert isinstance(result, dict)
        assert 'format' in result
    
    def test_feature_toggle_with_invalid_percentage(self, db_session):
        """Test feature toggle with invalid rollout percentage"""
        toggle = DatabaseFeatureToggle(db_session, "test_feature")
        
        # Invalid percentage should be handled gracefully
        success, message = toggle.enable(rollout_percentage=150, updated_by="test_user")
        # Implementation should clamp to valid range
        assert isinstance(success, bool)
    
    def test_intermediary_with_empty_data(self):
        """Test intermediary with empty data"""
        intermediary = PartnerDataIntermediary()
        
        success, result = intermediary.execute("")
        assert success == False
        assert "No suitable adapter" in result['error']
    
    def test_feature_toggle_database_error(self, db_session):
        """Test feature toggle with database errors"""
        # Mock database session to raise exception
        with patch.object(db_session, 'query', side_effect=Exception("Database error")):
            toggle = DatabaseFeatureToggle(db_session, "test_feature")
            enabled, message = toggle.execute()
            
            assert enabled == False
            assert "error" in message.lower()
