# src/tactics/integrability.py
"""
Integrability tactics implementation for Checkpoint 2.
Implements: Tailor Interface, Adapter Pattern, Use Intermediary, Publish-Subscribe
"""

from typing import Any, Dict, List, Optional, Tuple, Protocol
from datetime import datetime, timezone
import logging
import json
from abc import ABC, abstractmethod

from .base import BaseTactic, BaseAdapter, BasePublisher, BaseSubscriber
from .modifiability import CSVDataAdapter, JSONDataAdapter, XMLDataAdapter
from ..models import MessageQueue, AuditLog, SystemMetrics

logger = logging.getLogger(__name__)

# ==============================================
# INTERFACES AND PROTOCOLS
# ==============================================

class ExternalAPI(Protocol):
    """Protocol for external APIs"""
    def call(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call external API endpoint"""
        pass
    
    def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Authenticate with external API"""
        pass

class InternalService(Protocol):
    """Protocol for internal services"""
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data internally"""
        pass

# ==============================================
# TAILOR INTERFACE TACTIC
# ==============================================

class ResellerAPIAdapter(BaseAdapter):
    """Adapter for external reseller APIs (Tailor Interface tactic)"""
    
    def __init__(self, api_config: Dict[str, Any]):
        super().__init__("reseller_api_adapter")
        self.api_config = api_config
        self.base_url = api_config.get('base_url')
        self.auth_token = api_config.get('auth_token')
        self.timeout = api_config.get('timeout', 30)
    
    def adapt(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt internal data to external API format"""
        try:
            # Transform internal order format to external API format
            external_data = {
                'order_id': data.get('sale_id'),
                'customer_id': data.get('user_id'),
                'items': self._adapt_items(data.get('items', [])),
                'total_amount': float(data.get('total_amount', 0)),
                'currency': 'USD',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self.logger.info(f"Adapted data for external API: {external_data}")
            return external_data
            
        except Exception as e:
            self.logger.error(f"Data adaptation error: {e}")
            return {}
    
    def _adapt_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Adapt order items to external format"""
        adapted_items = []
        for item in items:
            adapted_item = {
                'product_id': item.get('product_id'),
                'quantity': item.get('quantity'),
                'unit_price': float(item.get('unit_price', 0)),
                'total_price': float(item.get('total_price', 0))
            }
            adapted_items.append(adapted_item)
        return adapted_items
    
    def can_handle(self, data: Any) -> bool:
        """Check if adapter can handle the data"""
        return isinstance(data, dict) and 'sale_id' in data
    
    def reverse_adapt(self, external_data: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt external API response to internal format"""
        try:
            internal_data = {
                'external_order_id': external_data.get('order_id'),
                'status': external_data.get('status'),
                'confirmation_code': external_data.get('confirmation_code'),
                'processed_at': external_data.get('timestamp')
            }
            return internal_data
        except Exception as e:
            self.logger.error(f"Reverse adaptation error: {e}")
            return {}

class SOAPXMLAdapter(BaseAdapter):
    """Adapter for SOAP/XML external APIs"""
    
    def __init__(self, wsdl_url: str):
        super().__init__("soap_xml_adapter")
        self.wsdl_url = wsdl_url
    
    def adapt(self, data: Dict[str, Any]) -> str:
        """Convert data to SOAP XML format"""
        try:
            # Simple SOAP envelope (in production, use zeep or similar)
            soap_envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <ProcessOrder xmlns="http://example.com/orderservice">
            <OrderID>{data.get('sale_id')}</OrderID>
            <CustomerID>{data.get('user_id')}</CustomerID>
            <TotalAmount>{data.get('total_amount')}</TotalAmount>
            <Items>
                {self._build_items_xml(data.get('items', []))}
            </Items>
        </ProcessOrder>
    </soap:Body>
</soap:Envelope>"""
            return soap_envelope
        except Exception as e:
            self.logger.error(f"SOAP XML adaptation error: {e}")
            return ""
    
    def _build_items_xml(self, items: List[Dict[str, Any]]) -> str:
        """Build XML for order items"""
        items_xml = ""
        for item in items:
            items_xml += f"""
                <Item>
                    <ProductID>{item.get('product_id')}</ProductID>
                    <Quantity>{item.get('quantity')}</Quantity>
                    <UnitPrice>{item.get('unit_price')}</UnitPrice>
                </Item>"""
        return items_xml
    
    def can_handle(self, data: Any) -> bool:
        """Check if adapter can handle SOAP data"""
        return isinstance(data, dict) and 'sale_id' in data

# ==============================================
# USE INTERMEDIARY TACTIC
# ==============================================

class MessageBroker(BaseTactic):
    """Message broker for Use Intermediary tactic"""
    
    def __init__(self, db_session, config: Dict[str, Any] = None):
        super().__init__("message_broker", config)
        self.db = db_session
        self.publishers = {}
        self.subscribers = {}
    
    def execute(self, topic: str, message: Dict[str, Any], message_type: str = "data_update") -> Tuple[bool, str]:
        """Publish message to topic"""
        try:
            # Store message in database
            message_record = MessageQueue(
                topic=topic,
                message_type=message_type,
                payload=json.dumps(message),
                status='pending',
                scheduled_for=datetime.now(timezone.utc)
            )
            
            self.db.add(message_record)
            self.db.commit()
            
            # Notify subscribers
            if topic in self.publishers:
                self.publishers[topic].publish(message)
            
            self.log_metric("message_published", 1, {
                "topic": topic,
                "message_type": message_type,
                "tactic": "use_intermediary"
            })
            
            return True, f"Message published to topic '{topic}'"
            
        except Exception as e:
            self.logger.error(f"Message publishing error: {e}")
            self.db.rollback()
            return False, f"Message publishing error: {str(e)}"
    
    def subscribe(self, topic: str, subscriber: BaseSubscriber):
        """Subscribe to topic"""
        if topic not in self.publishers:
            self.publishers[topic] = BasePublisher(topic)
        
        self.publishers[topic].subscribe(subscriber)
        self.subscribers[topic] = self.subscribers.get(topic, [])
        self.subscribers[topic].append(subscriber)
        
        self.logger.info(f"Subscriber '{subscriber.name}' subscribed to topic '{topic}'")
    
    def get_pending_messages(self, topic: str = None) -> List[Dict[str, Any]]:
        """Get pending messages from database"""
        try:
            query = self.db.query(MessageQueue).filter_by(status='pending')
            if topic:
                query = query.filter_by(topic=topic)
            
            messages = query.all()
            return [{
                'message_id': msg.messageID,
                'topic': msg.topic,
                'message_type': msg.message_type,
                'payload': json.loads(msg.payload),
                'created_at': msg.created_at
            } for msg in messages]
        except Exception as e:
            self.logger.error(f"Failed to get pending messages: {e}")
            return []
    
    def mark_processed(self, message_id: int, subscriber_id: str):
        """Mark message as processed"""
        try:
            message = self.db.query(MessageQueue).filter_by(messageID=message_id).first()
            if message:
                message.status = 'completed'
                message.subscriber_id = subscriber_id
                self.db.commit()
        except Exception as e:
            self.logger.error(f"Failed to mark message processed: {e}")
    
    def validate_config(self) -> bool:
        """Validate message broker configuration"""
        return self.db is not None

# ==============================================
# PUBLISH-SUBSCRIBE PATTERN
# ==============================================

class PartnerDataPublisher(BasePublisher):
    """Publisher for partner data updates"""
    
    def __init__(self):
        super().__init__("partner_data_updates")
    
    def publish_data_update(self, partner_id: int, data: Dict[str, Any]):
        """Publish partner data update"""
        message = {
            'partner_id': partner_id,
            'data': data,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'event_type': 'data_update'
        }
        self.publish(message)

class ReportingServiceSubscriber(BaseSubscriber):
    """Subscriber for reporting service"""
    
    def __init__(self, db_session):
        super().__init__("reporting_service")
        self.db = db_session
    
    def receive(self, topic: str, message: Any):
        """Receive and process partner data updates"""
        try:
            if topic == "partner_data_updates":
                self._process_partner_data_update(message)
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    def _process_partner_data_update(self, message: Dict[str, Any]):
        """Process partner data update for reporting"""
        try:
            # Log the update for reporting
            self.logger.info(f"Processing partner data update: {message}")
            
            # Update reporting metrics
            self._update_reporting_metrics(message)
            
        except Exception as e:
            self.logger.error(f"Error processing partner data update: {e}")
    
    def _update_reporting_metrics(self, message: Dict[str, Any]):
        """Update reporting metrics"""
        try:
            metric = SystemMetrics(
                metric_name="partner_data_update",
                metric_value=1,
                metric_unit="count",
                service_name="reporting_service",
                tags=json.dumps({
                    "partner_id": message.get('partner_id'),
                    "event_type": message.get('event_type')
                })
            )
            self.db.add(metric)
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Failed to update reporting metrics: {e}")

class InventoryServiceSubscriber(BaseSubscriber):
    """Subscriber for inventory service"""
    
    def __init__(self, db_session):
        super().__init__("inventory_service")
        self.db = db_session
    
    def receive(self, topic: str, message: Any):
        """Receive and process inventory updates"""
        try:
            if topic == "partner_data_updates":
                self._process_inventory_update(message)
        except Exception as e:
            self.logger.error(f"Error processing inventory update: {e}")
    
    def _process_inventory_update(self, message: Dict[str, Any]):
        """Process inventory update"""
        try:
            # Update inventory based on partner data
            self.logger.info(f"Processing inventory update: {message}")
            
        except Exception as e:
            self.logger.error(f"Error processing inventory update: {e}")

# ==============================================
# INTEGRABILITY MANAGER
# ==============================================

class IntegrabilityManager:
    """Central manager for all integrability tactics"""
    
    def __init__(self, db_session, config: Dict[str, Any] = None):
        self.db = db_session
        self.config = config or {}
        self.message_broker = MessageBroker(db_session)
        self.adapters = {}
        self.subscribers = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize default adapters
        self._initialize_adapters()
    
    def _initialize_adapters(self):
        """Initialize default adapters"""
        # Register JSON adapter
        json_adapter = JSONDataAdapter()
        self.register_adapter("json_adapter", json_adapter)
        
        # Register CSV adapter
        csv_adapter = CSVDataAdapter()
        self.register_adapter("csv_adapter", csv_adapter)
        
        # Register XML adapter
        xml_adapter = XMLDataAdapter()
        self.register_adapter("xml_adapter", xml_adapter)
        
        # Register reseller API adapter
        reseller_config = {'base_url': 'https://api.example.com', 'auth_token': 'default', 'timeout': 30}
        reseller_adapter = ResellerAPIAdapter(reseller_config)
        self.register_adapter("reseller_adapter", reseller_adapter)
    
    def register_adapter(self, name: str, adapter: BaseAdapter):
        """Register a new adapter"""
        self.adapters[name] = adapter
        self.logger.info(f"Registered adapter: {name}")
    
    def get_adapter(self, name: str) -> Optional[BaseAdapter]:
        """Get adapter by name"""
        return self.adapters.get(name)
    
    def adapt_data(self, adapter_name: str, data: Any) -> Tuple[bool, Any]:
        """Adapt data using specified adapter"""
        adapter = self.get_adapter(adapter_name)
        if not adapter:
            return False, f"Adapter '{adapter_name}' not found"
        
        if not adapter.can_handle(data):
            return False, f"Adapter '{adapter_name}' cannot handle this data"
        
        adapted_data = adapter.adapt(data)
        return True, adapted_data
    
    def publish_message(self, topic: str, message: Dict[str, Any], message_type: str = "data_update") -> Tuple[bool, str]:
        """Publish message to topic"""
        return self.message_broker.execute(topic, message, message_type)
    
    def subscribe_to_topic(self, topic: str, subscriber: BaseSubscriber):
        """Subscribe to topic"""
        self.message_broker.subscribe(topic, subscriber)
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(subscriber)
    
    def setup_partner_integration(self, partner_id: int, api_config: Dict[str, Any]) -> Tuple[bool, str]:
        """Setup integration for a new partner"""
        try:
            # Register adapter for partner
            adapter_name = f"partner_{partner_id}_adapter"
            adapter = ResellerAPIAdapter(api_config)
            self.register_adapter(adapter_name, adapter)
            
            # Setup message publishing
            publisher = PartnerDataPublisher()
            self.message_broker.publishers[f"partner_{partner_id}_updates"] = publisher
            
            # Subscribe reporting service
            if "reporting_service" not in self.subscribers:
                reporting_subscriber = ReportingServiceSubscriber(self.db)
                self.subscribe_to_topic(f"partner_{partner_id}_updates", reporting_subscriber)
            
            # Subscribe inventory service
            if "inventory_service" not in self.subscribers:
                inventory_subscriber = InventoryServiceSubscriber(self.db)
                self.subscribe_to_topic(f"partner_{partner_id}_updates", inventory_subscriber)
            
            self.logger.info(f"Partner {partner_id} integration setup complete")
            return True, f"Partner {partner_id} integration setup complete"
            
        except Exception as e:
            self.logger.error(f"Failed to setup partner integration: {e}")
            return False, f"Failed to setup partner integration: {str(e)}"
