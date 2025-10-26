# src/services/partner_catalog_service.py
import json
import requests
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from src.models import Partner, PartnerProduct, Product
import logging

logger = logging.getLogger(__name__)

class PartnerCatalogService:
    """Service class for managing Partner/VAR catalog synchronization"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_partner(self, name: str, api_endpoint: str, api_key: str, 
                      sync_frequency: int = 3600) -> Tuple[bool, str, Optional[Partner]]:
        """Create a new partner"""
        try:
            partner = Partner(
                name=name,
                api_endpoint=api_endpoint,
                api_key=api_key,
                sync_frequency=sync_frequency,
                last_sync=None,
                status='active'
            )
            
            self.db.add(partner)
            self.db.commit()
            self.db.refresh(partner)
            
            logger.info(f"Created partner {partner.partnerID}: {name}")
            return True, "Partner created successfully", partner
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating partner: {e}")
            return False, f"Error creating partner: {str(e)}", None
    
    def get_partner_by_id(self, partner_id: int) -> Optional[Partner]:
        """Get partner by ID"""
        return self.db.query(Partner).filter_by(partnerID=partner_id).first()
    
    def get_active_partners(self) -> List[Partner]:
        """Get all active partners"""
        return self.db.query(Partner).filter(Partner._status == 'active').all()
    
    def sync_partner_catalog(self, partner_id: int) -> Tuple[bool, str, int]:
        """Synchronize catalog from a partner"""
        try:
            partner = self.get_partner_by_id(partner_id)
            if not partner:
                return False, "Partner not found", 0
            
            if not partner.api_endpoint:
                return False, "Partner API endpoint not configured", 0
            
            # Fetch data from partner API
            products_data = self._fetch_partner_products(partner)
            if not products_data:
                return False, "Failed to fetch products from partner", 0
            
            # Process and sync products
            synced_count = self._process_partner_products(partner, products_data)
            
            # Update partner sync timestamp
            partner.last_sync = datetime.now(timezone.utc)
            self.db.commit()
            
            logger.info(f"Synced {synced_count} products from partner {partner.name}")
            return True, f"Successfully synced {synced_count} products", synced_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error syncing partner catalog: {e}")
            return False, f"Error syncing catalog: {str(e)}", 0
    
    def _fetch_partner_products(self, partner: Partner) -> Optional[List[Dict[str, Any]]]:
        """Fetch products from partner API"""
        try:
            headers = {
                'Authorization': f'Bearer {partner.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                partner.api_endpoint,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API request failed with status {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error fetching from partner API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching partner data: {e}")
            return None
    
    def _process_partner_products(self, partner: Partner, products_data: List[Dict[str, Any]]) -> int:
        """Process and sync partner products"""
        synced_count = 0
        
        for product_data in products_data:
            try:
                # Extract product information
                external_id = product_data.get('id', '')
                name = product_data.get('name', '')
                price = product_data.get('price', 0)
                description = product_data.get('description', '')
                stock = product_data.get('stock', 0)
                
                if not external_id or not name:
                    continue
                
                # Check if partner product already exists
                partner_product = self.db.query(PartnerProduct).filter(
                    PartnerProduct.partnerID == partner.partnerID,
                    PartnerProduct.external_product_id == str(external_id)
                ).first()
                
                if partner_product:
                    # Update existing product
                    self._update_existing_product(partner_product, product_data)
                else:
                    # Create new product mapping
                    self._create_new_product_mapping(partner, external_id, product_data)
                
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Error processing product {product_data.get('id', 'unknown')}: {e}")
                continue
        
        return synced_count
    
    def _update_existing_product(self, partner_product: PartnerProduct, product_data: Dict[str, Any]):
        """Update existing partner product"""
        partner_product.sync_data = json.dumps(product_data)
        partner_product.sync_status = 'synced'
        partner_product.last_synced = datetime.now(timezone.utc)
        
        # Update the actual product if mapped
        if partner_product.product:
            product = partner_product.product
            product.name = product_data.get('name', product.name)
            product.price = product_data.get('price', product.price)
            product.description = product_data.get('description', product.description)
            product.stock = product_data.get('stock', product.stock)
    
    def _create_new_product_mapping(self, partner: Partner, external_id: str, product_data: Dict[str, Any]):
        """Create new product mapping"""
        # Create new product
        product = Product(
            name=product_data.get('name', ''),
            description=product_data.get('description', ''),
            price=product_data.get('price', 0),
            stock=product_data.get('stock', 0),
            shipping_weight=product_data.get('shipping_weight', 0),
            discount_percent=0,
            country_of_origin=product_data.get('country_of_origin', 'Unknown'),
            requires_shipping=product_data.get('requires_shipping', True)
        )
        
        self.db.add(product)
        self.db.flush()  # Get the product ID
        
        # Create partner product mapping
        partner_product = PartnerProduct(
            partnerID=partner.partnerID,
            external_product_id=str(external_id),
            productID=product.productID,
            sync_status='synced',
            last_synced=datetime.now(timezone.utc),
            sync_data=json.dumps(product_data)
        )
        
        self.db.add(partner_product)
    
    def get_partner_products(self, partner_id: int) -> List[PartnerProduct]:
        """Get all products for a partner"""
        return self.db.query(PartnerProduct).filter(
            PartnerProduct.partnerID == partner_id
        ).all()
    
    def sync_all_partners(self) -> Dict[str, Any]:
        """Sync all active partners"""
        results = {
            'total_partners': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'total_products_synced': 0,
            'errors': []
        }
        
        partners = self.get_active_partners()
        results['total_partners'] = len(partners)
        
        for partner in partners:
            try:
                success, message, count = self.sync_partner_catalog(partner.partnerID)
                if success:
                    results['successful_syncs'] += 1
                    results['total_products_synced'] += count
                else:
                    results['failed_syncs'] += 1
                    results['errors'].append(f"{partner.name}: {message}")
            except Exception as e:
                results['failed_syncs'] += 1
                results['errors'].append(f"{partner.name}: {str(e)}")
        
        return results
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get synchronization status for all partners"""
        partners = self.get_active_partners()
        status = []
        
        for partner in partners:
            partner_status = {
                'partner_id': partner.partnerID,
                'name': partner.name,
                'last_sync': partner.last_sync,
                'sync_frequency': partner.sync_frequency,
                'status': partner.status,
                'product_count': len(self.get_partner_products(partner.partnerID))
            }
            status.append(partner_status)
        
        return {'partners': status}
