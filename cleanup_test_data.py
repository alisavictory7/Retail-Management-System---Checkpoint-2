#!/usr/bin/env python3
"""
Clean up test data from the database
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import SessionLocal
from src.models import User, Product, Partner, PartnerAPIKey, FlashSale, Sale, OrderQueue, AuditLog, SystemMetrics, TestRecord, FeatureToggle, CircuitBreakerState, MessageQueue

def cleanup_test_data():
    """Clean up all test data from the database"""
    print("🧹 Cleaning up test data...")
    
    db = SessionLocal()
    
    try:
        # Clean up in reverse dependency order
        db.query(PartnerAPIKey).filter(PartnerAPIKey.api_key.like('test_%')).delete()
        db.query(FlashSale).delete()
        db.query(Sale).delete()
        db.query(OrderQueue).delete()
        db.query(AuditLog).delete()
        db.query(SystemMetrics).delete()
        db.query(TestRecord).delete()
        db.query(FeatureToggle).delete()
        db.query(CircuitBreakerState).delete()
        db.query(MessageQueue).delete()
        db.query(Partner).filter(Partner.name.like('Test%')).delete()
        db.query(User).filter(User.username.like('test_%')).delete()
        db.query(Product).filter(Product.name.like('Test%')).delete()
        
        db.commit()
        print("✅ Test data cleaned up successfully!")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_test_data()
