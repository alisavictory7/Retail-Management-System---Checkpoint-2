# tests/test_integrability_tactics.py
"""
Comprehensive tests for Integrability tactics:
- Tailor Interface
- Adapter Pattern
- Use Intermediary
- Publish-Subscribe
"""

import pytest
import json
from unittest.mock import patch, MagicMock

from src.tactics.integrability import (
    IntegrabilityManager, ResellerAPIAdapter, SOAPXMLAdapter,
    MessageBroker, PartnerDataPublisher, ReportingServiceSubscriber,
    InventoryServiceSubscriber
)

class TestTailorInterface:
    """Test Tailor Interface tactic for external API integration"""
    
    def test_reseller_api_adapter_adapt(self):
        """Test ResellerAPIAdapter data adaptation"""
        adapter = ResellerAPIAdapter({
            'base_url': 'https://api.reseller.com',
            'auth_token': 'test_token',
            'timeout': 30
        })
        
        internal_data = {
            'sale_id': 123,
            'user_id': 456,
            'items': [
                {'product_id': 1, 'quantity': 2, 'unit_price': 10.99, 'total_price': 21.98}
            ],
            'total_amount': 21.98
        }
        
        external_data = adapter.adapt(internal_data)
        
        assert external_data['order_id'] == 123
        assert external_data['customer_id'] == 456
        assert external_data['total_amount'] == 21.98
        assert external_data['currency'] == 'USD'
        assert len(external_data['items']) == 1
        assert external_data['items'][0]['product_id'] == 1
    
    def test_reseller_api_adapter_can_handle(self):
        """Test ResellerAPIAdapter can handle detection"""
        adapter = ResellerAPIAdapter({})
        
        valid_data = {'sale_id': 123, 'user_id': 456}
        invalid_data = {'order_id': 123}  # Missing sale_id
        
        assert adapter.can_handle(valid_data) == True
        assert adapter.can_handle(invalid_data) == False
    
    def test_reseller_api_adapter_reverse_adapt(self):
        """Test ResellerAPIAdapter reverse adaptation"""
        adapter = ResellerAPIAdapter({})
        
        external_response = {
            'order_id': 'EXT_123',
            'status': 'confirmed',
            'confirmation_code': 'CONF_456',
            'timestamp': '2023-01-01T12:00:00Z'
        }
        
        internal_data = adapter.reverse_adapt(external_response)
        
        assert internal_data['external_order_id'] == 'EXT_123'
        assert internal_data['status'] == 'confirmed'
        assert internal_data['confirmation_code'] == 'CONF_456'
    
    def test_soap_xml_adapter_adapt(self):
        """Test SOAPXMLAdapter data adaptation"""
        adapter = SOAPXMLAdapter('https://api.soap.com/service?wsdl')
        
        internal_data = {
            'sale_id': 123,
            'user_id': 456,
            'items': [
                {'product_id': 1, 'quantity': 2, 'unit_price': 10.99}
            ],
            'total_amount': 21.98
        }
        
        soap_xml = adapter.adapt(internal_data)
        
        assert '<?xml version="1.0" encoding="UTF-8"?>' in soap_xml
        assert '<soap:Envelope' in soap_xml
        assert '<ProcessOrder' in soap_xml
        assert '<OrderID>123</OrderID>' in soap_xml
        assert '<CustomerID>456</CustomerID>' in soap_xml
        assert '<TotalAmount>21.98</TotalAmount>' in soap_xml
    
    def test_soap_xml_adapter_can_handle(self):
        """Test SOAPXMLAdapter can handle detection"""
        adapter = SOAPXMLAdapter('https://api.soap.com/service?wsdl')
        
        valid_data = {'sale_id': 123, 'user_id': 456}
        invalid_data = {'order_id': 123}  # Missing sale_id
        
        assert adapter.can_handle(valid_data) == True
        assert adapter.can_handle(invalid_data) == False

class TestUseIntermediary:
    """Test Use Intermediary tactic for decoupled communication"""
    
    def test_message_broker_publish(self, db_session):
        """Test message broker publishing"""
        broker = MessageBroker(db_session)
        
        message = {
            'partner_id': 1,
            'data': {'product_id': 123, 'price': 10.99},
            'timestamp': '2023-01-01T12:00:00Z'
        }
        
        success, message_text = broker.execute('partner_updates', message, 'data_update')
        
        assert success == True
        assert 'published' in message_text.lower()
        
        # Check database
        from src.models import MessageQueue
        messages = db_session.query(MessageQueue).filter_by(topic='partner_updates').all()
        assert len(messages) == 1
        assert messages[0].message_type == 'data_update'
    
    def test_message_broker_subscribe(self, db_session):
        """Test message broker subscription"""
        broker = MessageBroker(db_session)
        
        # Create mock subscriber
        class MockSubscriber:
            def __init__(self):
                self.name = "test_subscriber"
                self.received_messages = []
            
            def receive(self, topic, message):
                self.received_messages.append((topic, message))
        
        subscriber = MockSubscriber()
        broker.subscribe('test_topic', subscriber)
        
        # Publish message
        broker.execute('test_topic', {'test': 'data'}, 'test_message')
        
        # Check subscriber received message
        assert len(subscriber.received_messages) == 1
        assert subscriber.received_messages[0][0] == 'test_topic'
    
    def test_message_broker_get_pending_messages(self, db_session):
        """Test getting pending messages"""
        broker = MessageBroker(db_session)
        
        # Publish some messages
        broker.execute('topic1', {'data': '1'}, 'type1')
        broker.execute('topic2', {'data': '2'}, 'type2')
        broker.execute('topic1', {'data': '3'}, 'type1')
        
        # Get all pending messages
        all_messages = broker.get_pending_messages()
        assert len(all_messages) == 3
        
        # Get messages for specific topic
        topic1_messages = broker.get_pending_messages('topic1')
        assert len(topic1_messages) == 2
        assert all(msg['topic'] == 'topic1' for msg in topic1_messages)
    
    def test_message_broker_mark_processed(self, db_session):
        """Test marking messages as processed"""
        broker = MessageBroker(db_session)
        
        # Publish message
        broker.execute('test_topic', {'data': 'test'}, 'test_type')
        
        # Get message ID
        messages = broker.get_pending_messages('test_topic')
        message_id = messages[0]['message_id']
        
        # Mark as processed
        broker.mark_processed(message_id, 'subscriber_1')
        
        # Check database
        from src.models import MessageQueue
        message = db_session.query(MessageQueue).filter_by(messageID=message_id).first()
        assert message.status == 'completed'
        assert message.subscriber_id == 'subscriber_1'

class TestPublishSubscribe:
    """Test Publish-Subscribe pattern for asynchronous communication"""
    
    def test_partner_data_publisher(self):
        """Test PartnerDataPublisher"""
        publisher = PartnerDataPublisher()
        
        # Create mock subscriber
        class MockSubscriber:
            def __init__(self):
                self.name = "test_subscriber"
                self.received_messages = []
            
            def receive(self, topic, message):
                self.received_messages.append((topic, message))
        
        subscriber = MockSubscriber()
        publisher.subscribe(subscriber)
        
        # Publish data update
        data = {'product_id': 123, 'price': 10.99}
        publisher.publish_data_update(1, data)
        
        # Check subscriber received message
        assert len(subscriber.received_messages) == 1
        topic, message = subscriber.received_messages[0]
        assert topic == 'partner_data_updates'
        assert message['partner_id'] == 1
        assert message['data'] == data
        assert message['event_type'] == 'data_update'
    
    def test_reporting_service_subscriber(self, db_session):
        """Test ReportingServiceSubscriber"""
        subscriber = ReportingServiceSubscriber(db_session)
        
        message = {
            'partner_id': 1,
            'data': {'product_id': 123, 'price': 10.99},
            'timestamp': '2023-01-01T12:00:00Z',
            'event_type': 'data_update'
        }
        
        # Receive message
        subscriber.receive('partner_data_updates', message)
        
        # Check metrics were logged
        from src.models import SystemMetrics
        metrics = db_session.query(SystemMetrics).filter_by(
            metric_name='partner_data_update'
        ).all()
        assert len(metrics) == 1
        assert metrics[0].service_name == 'reporting_service'
    
    def test_inventory_service_subscriber(self, db_session):
        """Test InventoryServiceSubscriber"""
        subscriber = InventoryServiceSubscriber(db_session)
        
        message = {
            'partner_id': 1,
            'data': {'product_id': 123, 'stock': 100},
            'timestamp': '2023-01-01T12:00:00Z',
            'event_type': 'data_update'
        }
        
        # Receive message
        subscriber.receive('partner_data_updates', message)
        
        # Should process without errors
        assert True  # If we get here, processing succeeded

class TestIntegrabilityManager:
    """Test Integrability Manager integration"""
    
    def test_integrability_manager_initialization(self, db_session):
        """Test integrability manager initialization"""
        manager = IntegrabilityManager(db_session)
        
        assert manager.db == db_session
        assert manager.message_broker is not None
        assert isinstance(manager.message_broker, MessageBroker)
    
    def test_register_and_get_adapter(self, db_session):
        """Test adapter registration and retrieval"""
        manager = IntegrabilityManager(db_session)
        
        # Register adapter
        adapter = ResellerAPIAdapter({'base_url': 'https://api.test.com'})
        manager.register_adapter('test_adapter', adapter)
        
        # Get adapter
        retrieved_adapter = manager.get_adapter('test_adapter')
        assert retrieved_adapter is adapter
        
        # Get non-existent adapter
        non_existent = manager.get_adapter('non_existent')
        assert non_existent is None
    
    def test_adapt_data(self, db_session):
        """Test data adaptation through manager"""
        manager = IntegrabilityManager(db_session)
        
        # Register adapter
        adapter = ResellerAPIAdapter({'base_url': 'https://api.test.com'})
        manager.register_adapter('test_adapter', adapter)
        
        # Adapt data
        data = {'sale_id': 123, 'user_id': 456}
        success, result = manager.adapt_data('test_adapter', data)
        
        assert success == True
        assert result['order_id'] == 123
        assert result['customer_id'] == 456
    
    def test_publish_message(self, db_session):
        """Test message publishing through manager"""
        manager = IntegrabilityManager(db_session)
        
        message = {'test': 'data'}
        success, message_text = manager.publish_message('test_topic', message)
        
        assert success == True
        assert 'published' in message_text.lower()
    
    def test_setup_partner_integration(self, db_session):
        """Test complete partner integration setup"""
        manager = IntegrabilityManager(db_session)
        
        api_config = {
            'base_url': 'https://api.partner.com',
            'auth_token': 'test_token',
            'timeout': 30
        }
        
        success, message = manager.setup_partner_integration(1, api_config)
        
        assert success == True
        assert 'setup complete' in message.lower()
        
        # Check that adapter was registered
        adapter = manager.get_adapter('partner_1_adapter')
        assert adapter is not None
        assert isinstance(adapter, ResellerAPIAdapter)

class TestIntegrabilityIntegration:
    """Integration tests for integrability tactics working together"""
    
    def test_complete_integration_flow(self, db_session):
        """Test complete integration flow with all tactics"""
        manager = IntegrabilityManager(db_session)
        
        # Setup partner integration
        api_config = {
            'base_url': 'https://api.partner.com',
            'auth_token': 'test_token',
            'timeout': 30
        }
        manager.setup_partner_integration(1, api_config)
        
        # Adapt data
        internal_data = {'sale_id': 123, 'user_id': 456, 'total_amount': 100.0}
        success, external_data = manager.adapt_data('partner_1_adapter', internal_data)
        assert success == True
        
        # Publish message
        message = {'partner_id': 1, 'data': external_data}
        success, message_text = manager.publish_message('partner_1_updates', message)
        assert success == True
    
    def test_multiple_partner_integration(self, db_session):
        """Test integration with multiple partners"""
        manager = IntegrabilityManager(db_session)
        
        # Setup multiple partners
        for i in range(3):
            api_config = {
                'base_url': f'https://api.partner{i}.com',
                'auth_token': f'token_{i}',
                'timeout': 30
            }
            manager.setup_partner_integration(i, api_config)
        
        # Check that all adapters were registered
        for i in range(3):
            adapter = manager.get_adapter(f'partner_{i}_adapter')
            assert adapter is not None
    
    def test_publish_subscribe_integration(self, db_session):
        """Test publish-subscribe integration"""
        manager = IntegrabilityManager(db_session)
        
        # Create mock subscribers
        class MockSubscriber:
            def __init__(self, name):
                self.name = name
                self.messages = []
            
            def receive(self, topic, message):
                self.messages.append((topic, message))
        
        subscriber1 = MockSubscriber('sub1')
        subscriber2 = MockSubscriber('sub2')
        
        # Subscribe to topic
        manager.subscribe_to_topic('test_topic', subscriber1)
        manager.subscribe_to_topic('test_topic', subscriber2)
        
        # Publish message
        manager.publish_message('test_topic', {'test': 'data'})
        
        # Check both subscribers received message
        assert len(subscriber1.messages) == 1
        assert len(subscriber2.messages) == 1

class TestIntegrabilityEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_adapter_with_invalid_data(self):
        """Test adapter with invalid data"""
        adapter = ResellerAPIAdapter({})
        
        # Invalid data (missing required fields)
        invalid_data = {'invalid': 'data'}
        result = adapter.adapt(invalid_data)
        
        # Should handle gracefully
        assert isinstance(result, dict)
    
    def test_message_broker_with_database_error(self, db_session):
        """Test message broker with database errors"""
        broker = MessageBroker(db_session)
        
        # Mock database session to raise exception
        with patch.object(db_session, 'add', side_effect=Exception("Database error")):
            success, message = broker.execute('test_topic', {'test': 'data'})
            assert success == False
            assert "error" in message.lower()
    
    def test_publisher_with_no_subscribers(self):
        """Test publisher with no subscribers"""
        publisher = PartnerDataPublisher()
        
        # Should not raise exception
        publisher.publish_data_update(1, {'test': 'data'})
        assert True  # If we get here, no exception was raised
    
    def test_subscriber_with_invalid_message(self, db_session):
        """Test subscriber with invalid message"""
        subscriber = ReportingServiceSubscriber(db_session)
        
        # Invalid message format
        invalid_message = "not a dictionary"
        
        # Should handle gracefully
        subscriber.receive('test_topic', invalid_message)
        assert True  # If we get here, no exception was raised
    
    def test_integrability_manager_with_missing_adapter(self, db_session):
        """Test integrability manager with missing adapter"""
        manager = IntegrabilityManager(db_session)
        
        # Try to adapt data with non-existent adapter
        success, result = manager.adapt_data('non_existent', {'test': 'data'})
        assert success == False
        assert "not found" in result
