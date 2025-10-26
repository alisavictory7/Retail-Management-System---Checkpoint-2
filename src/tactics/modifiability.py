# src/tactics/modifiability.py
"""
Modifiability tactics implementation for Checkpoint 2.
Implements: Use Intermediary/Encapsulate, Adapter Pattern, Feature Toggle
"""

from typing import Any, Dict, List, Optional, Tuple, Protocol
from datetime import datetime, timezone
import logging
import json
from abc import ABC, abstractmethod

from .base import BaseTactic, BaseAdapter, BaseFeatureToggle
from ..models import FeatureToggle, AuditLog, SystemMetrics

logger = logging.getLogger(__name__)

# ==============================================
# INTERFACES AND PROTOCOLS
# ==============================================

class DataParser(Protocol):
    """Protocol for data parsers"""
    def parse(self, data: str) -> Dict[str, Any]:
        """Parse data from string format"""
        pass
    
    def can_parse(self, data: str) -> bool:
        """Check if parser can handle the data"""
        pass

class PartnerDataProcessor(Protocol):
    """Protocol for partner data processing"""
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process partner data"""
        pass

# ==============================================
# ADAPTER PATTERN IMPLEMENTATIONS
# ==============================================

class CSVDataAdapter(BaseAdapter):
    """Adapter for CSV partner data format"""
    
    def __init__(self):
        super().__init__("csv_adapter")
    
    def adapt(self, data: str) -> Dict[str, Any]:
        """Convert CSV data to internal format"""
        try:
            lines = data.strip().split('\n')
            if not lines:
                return {}
            
            headers = [h.strip() for h in lines[0].split(',')]
            result = []
            
            for line in lines[1:]:
                if not line.strip():
                    continue
                values = [v.strip() for v in line.split(',')]
                if len(values) == len(headers):
                    row_dict = dict(zip(headers, values))
                    result.append(row_dict)
            
            return {'products': result, 'format': 'csv'}
        except Exception as e:
            self.logger.error(f"CSV parsing error: {e}")
            return {}
    
    def can_handle(self, data: Any) -> bool:
        """Check if this adapter can handle CSV data"""
        if not isinstance(data, str):
            return False
        return ',' in data and '\n' in data

class JSONDataAdapter(BaseAdapter):
    """Adapter for JSON partner data format"""
    
    def __init__(self):
        super().__init__("json_adapter")
    
    def adapt(self, data: str) -> Dict[str, Any]:
        """Convert JSON data to internal format"""
        try:
            parsed_data = json.loads(data)
            if isinstance(parsed_data, list):
                return {'products': parsed_data, 'format': 'json'}
            elif isinstance(parsed_data, dict) and 'products' in parsed_data:
                parsed_data['format'] = 'json'
                return parsed_data
            else:
                return {'products': [parsed_data], 'format': 'json'}
        except Exception as e:
            self.logger.error(f"JSON parsing error: {e}")
            return {}
    
    def can_handle(self, data: Any) -> bool:
        """Check if this adapter can handle JSON data"""
        if not isinstance(data, str):
            return False
        try:
            json.loads(data)
            return True
        except:
            return False

class XMLDataAdapter(BaseAdapter):
    """Adapter for XML partner data format"""
    
    def __init__(self):
        super().__init__("xml_adapter")
    
    def adapt(self, data: str) -> Dict[str, Any]:
        """Convert XML data to internal format"""
        try:
            # Simple XML parsing (in production, use xml.etree.ElementTree)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(data)
            
            products = []
            for product in root.findall('.//product'):
                product_data = {}
                for child in product:
                    product_data[child.tag] = child.text
                products.append(product_data)
            
            return {'products': products, 'format': 'xml'}
        except Exception as e:
            self.logger.error(f"XML parsing error: {e}")
            return {}
    
    def can_handle(self, data: Any) -> bool:
        """Check if this adapter can handle XML data"""
        if not isinstance(data, str):
            return False
        return data.strip().startswith('<') and data.strip().endswith('>')

# ==============================================
# INTERMEDIARY PATTERN
# ==============================================

class PartnerDataIntermediary(BaseTactic):
    """Use Intermediary/Encapsulate tactic for partner data processing"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("partner_data_intermediary", config)
        self.adapters = [
            CSVDataAdapter(),
            JSONDataAdapter(),
            XMLDataAdapter()
        ]
    
    def execute(self, data: str, partner_format: str = None) -> Tuple[bool, Dict[str, Any]]:
        """Process partner data using appropriate adapter"""
        try:
            # Find appropriate adapter
            adapter = self._find_adapter(data, partner_format)
            if not adapter:
                return False, {"error": "No suitable adapter found for data format"}
            
            # Adapt the data
            adapted_data = adapter.adapt(data)
            if not adapted_data:
                return False, {"error": "Failed to adapt data"}
            
            # Log successful adaptation
            self.log_metric("data_adapted", 1, {
                "adapter": adapter.name,
                "format": partner_format or 'unknown',
                "tactic": "intermediary"
            })
            
            return True, adapted_data
            
        except Exception as e:
            self.logger.error(f"Data intermediary error: {e}")
            return False, {"error": f"Data intermediary error: {str(e)}"}
    
    def _find_adapter(self, data: str, partner_format: str = None) -> Optional[BaseAdapter]:
        """Find appropriate adapter for data"""
        if partner_format:
            # Look for specific format
            for adapter in self.adapters:
                if adapter.name == f"{partner_format.lower()}_adapter":
                    return adapter
        
        # Auto-detect format
        for adapter in self.adapters:
            if adapter.can_handle(data):
                return adapter
        
        return None
    
    def add_adapter(self, adapter: BaseAdapter):
        """Add new adapter (for modifiability)"""
        self.adapters.append(adapter)
        self.logger.info(f"Added new adapter: {adapter.name}")
    
    def validate_config(self) -> bool:
        """Validate intermediary configuration"""
        return len(self.adapters) > 0

# ==============================================
# FEATURE TOGGLE IMPLEMENTATION
# ==============================================

class DatabaseFeatureToggle(BaseFeatureToggle):
    """Database-backed feature toggle implementation"""
    
    def __init__(self, db_session, feature_name: str, config: Dict[str, Any] = None):
        super().__init__(feature_name, config)
        self.db = db_session
    
    def execute(self, user_id: Optional[int] = None) -> Tuple[bool, str]:
        """Check if feature is enabled"""
        try:
            # Get feature toggle from database
            toggle = self.db.query(FeatureToggle).filter_by(
                feature_name=self.feature_name
            ).first()
            
            if not toggle:
                return False, f"Feature toggle '{self.feature_name}' not found"
            
            # Check if feature is enabled
            if not toggle.is_enabled:
                return False, f"Feature '{self.feature_name}' is disabled"
            
            # Check rollout percentage
            if toggle.rollout_percentage < 100:
                if user_id is None:
                    return False, "User ID required for partial rollout"
                
                # Simple hash-based rollout using a more deterministic approach
                import hashlib
                user_hash = int(hashlib.md5(f"{self.feature_name}_{user_id}".encode()).hexdigest()[:8], 16) % 100
                if user_hash >= toggle.rollout_percentage:
                    return False, f"User not in rollout group for '{self.feature_name}'"
            
            # Check target users
            if toggle.target_users:
                try:
                    target_users = json.loads(toggle.target_users)
                    if user_id not in target_users:
                        return False, f"User not in target list for '{self.feature_name}'"
                except:
                    pass  # Ignore JSON parsing errors
            
            self.log_metric("feature_enabled", 1, {
                "feature": self.feature_name,
                "user_id": str(user_id) if user_id else "none",
                "tactic": "feature_toggle"
            })
            
            return True, f"Feature '{self.feature_name}' is enabled"
            
        except Exception as e:
            self.logger.error(f"Feature toggle error: {e}")
            return False, f"Feature toggle error: {str(e)}"
    
    def enable(self, rollout_percentage: int = 100, target_users: List[int] = None, 
               updated_by: str = None) -> Tuple[bool, str]:
        """Enable the feature"""
        try:
            toggle = self.db.query(FeatureToggle).filter_by(
                feature_name=self.feature_name
            ).first()
            
            if not toggle:
                # Create new toggle
                toggle = FeatureToggle(
                    feature_name=self.feature_name,
                    is_enabled=True,
                    rollout_percentage=rollout_percentage,
                    target_users=json.dumps(target_users) if target_users else None,
                    updated_by=updated_by
                )
                self.db.add(toggle)
            else:
                # Update existing toggle
                toggle.is_enabled = True
                toggle.rollout_percentage = rollout_percentage
                toggle.target_users = json.dumps(target_users) if target_users else None
                toggle.updated_by = updated_by
                toggle.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            
            # Log audit
            self._log_audit("feature_enabled", {
                "rollout_percentage": rollout_percentage,
                "target_users": target_users
            })
            
            return True, f"Feature '{self.feature_name}' enabled"
            
        except Exception as e:
            self.logger.error(f"Failed to enable feature: {e}")
            self.db.rollback()
            return False, f"Failed to enable feature: {str(e)}"
    
    def disable(self, updated_by: str = None) -> Tuple[bool, str]:
        """Disable the feature"""
        try:
            toggle = self.db.query(FeatureToggle).filter_by(
                feature_name=self.feature_name
            ).first()
            
            if not toggle:
                return False, f"Feature toggle '{self.feature_name}' not found"
            
            toggle.is_enabled = False
            toggle.rollout_percentage = 0
            toggle.target_users = None
            toggle.updated_by = updated_by
            toggle.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            
            # Log audit
            self._log_audit("feature_disabled", {})
            
            return True, f"Feature '{self.feature_name}' disabled"
            
        except Exception as e:
            self.logger.error(f"Failed to disable feature: {e}")
            self.db.rollback()
            return False, f"Failed to disable feature: {str(e)}"
    
    def _log_audit(self, action: str, changes: Dict[str, Any]):
        """Log feature toggle changes"""
        try:
            audit = AuditLog(
                event_type="feature_toggle",
                entity_type="FeatureToggle",
                entity_id=None,
                action=action,
                new_values=json.dumps(changes),
                success=True
            )
            self.db.add(audit)
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Failed to log audit: {e}")
    
    def validate_config(self) -> bool:
        """Validate feature toggle configuration"""
        return self.db is not None

# ==============================================
# MODIFIABILITY MANAGER
# ==============================================

class ModifiabilityManager:
    """Central manager for all modifiability tactics"""
    
    def __init__(self, db_session, config: Dict[str, Any] = None):
        self.db = db_session
        self.config = config or {}
        self.data_intermediary = PartnerDataIntermediary()
        self.feature_toggles = {}
        self.logger = logging.getLogger(__name__)
    
    def get_feature_toggle(self, feature_name: str) -> DatabaseFeatureToggle:
        """Get or create feature toggle"""
        if feature_name not in self.feature_toggles:
            self.feature_toggles[feature_name] = DatabaseFeatureToggle(
                self.db, feature_name
            )
        return self.feature_toggles[feature_name]
    
    def process_partner_data(self, data: str, partner_format: str = None) -> Tuple[bool, Dict[str, Any]]:
        """Process partner data using intermediary pattern"""
        return self.data_intermediary.execute(data, partner_format)
    
    def is_feature_enabled(self, feature_name: str, user_id: int = None) -> Tuple[bool, str]:
        """Check if feature is enabled"""
        toggle = self.get_feature_toggle(feature_name)
        return toggle.execute(user_id)
    
    def enable_feature(self, feature_name: str, rollout_percentage: int = 100, 
                      target_users: List[int] = None, updated_by: str = None) -> Tuple[bool, str]:
        """Enable a feature"""
        toggle = self.get_feature_toggle(feature_name)
        return toggle.enable(rollout_percentage, target_users, updated_by)
    
    def disable_feature(self, feature_name: str, updated_by: str = None) -> Tuple[bool, str]:
        """Disable a feature"""
        toggle = self.get_feature_toggle(feature_name)
        return toggle.disable(updated_by)
