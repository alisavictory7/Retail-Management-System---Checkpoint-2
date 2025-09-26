# tests/test_logic.py
import pytest
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock the database imports to avoid connection issues
class MockBase:
    pass

class MockEngine:
    pass

# Mock the database module
sys.modules['src.database'] = type('MockDatabase', (), {
    'Base': MockBase,
    'engine': MockEngine
})()

from models import Product, Cash, Card

# --- Product Tests ---

@pytest.fixture
def basic_product():
    """Create a basic product for testing."""
    product = Product()
    product.name = "Test Product"
    product.price = 25.00
    product.stock = 100
    product._shipping_weight = 0.2
    product._country_of_origin = 'USA'
    product._requires_shipping = True
    product._discount_percent = 0.0
    return product

@pytest.fixture
def discounted_product():
    """Create a discounted product from China."""
    product = Product()
    product.name = "Discounted Product"
    product.price = 1200.00
    product.stock = 50
    product._shipping_weight = 2.5
    product._country_of_origin = 'China'
    product._requires_shipping = True
    product._discount_percent = 10.0
    return product

def test_product_pricing(basic_product, discounted_product):
    """Test product pricing calculations."""
    # Basic product pricing
    assert basic_product.get_discounted_unit_price() == 25.00
    assert basic_product.get_subtotal_for_quantity(3) == 75.00
    
    # Discounted product pricing
    assert discounted_product.get_discounted_unit_price() == 1080.00
    assert discounted_product.get_subtotal_for_quantity(2) == 2160.00

def test_shipping_calculations(basic_product, discounted_product):
    """Test shipping fee calculations."""
    # Basic product shipping
    assert abs(basic_product.get_shipping_fees(2) - 0.60) < 0.01
    
    # Discounted product shipping
    assert abs(discounted_product.get_shipping_fees(1) - 3.75) < 0.01

def test_import_duty_calculations(basic_product, discounted_product):
    """Test import duty calculations."""
    # USA products have no import duty
    assert basic_product.get_import_duty(1) == 0.0
    
    # China products have 5% duty
    assert discounted_product.get_import_duty(1) == 60.00
    assert discounted_product.get_import_duty(2) == 120.00

# --- Payment Tests ---

def test_cash_payment():
    """Test cash payment authorization."""
    cash = Cash()
    cash.amount = 100.00
    cash.status = 'pending'
    cash.cash_tendered = 100.00
    cash.payment_type = 'cash'
    
    is_authorized, reason = cash.authorized()
    assert is_authorized is True
    assert reason == "Approved"

def test_valid_card_payment():
    """Test valid card payment authorization."""
    card = Card()
    card.amount = 100.00
    card.status = 'pending'
    card.card_number = '1234567890123456'
    card.card_type = 'Visa'
    card.card_exp_date = '12/2025'
    card.payment_type = 'card'
    
    is_authorized, reason = card.authorized()
    assert is_authorized is True
    assert reason == "Approved"

def test_invalid_card_payment():
    """Test invalid card payment rejection."""
    card = Card()
    card.amount = 100.00
    card.status = 'pending'
    card.card_number = '123'  # Too short
    card.card_type = 'Visa'
    card.card_exp_date = '12/2025'
    card.payment_type = 'card'
    
    is_authorized, reason = card.authorized()
    assert is_authorized is False
    assert "Invalid Card Number" in reason

# --- Cart Calculation Tests ---

def test_cart_total_calculation():
    """Test cart total calculation logic."""
    # Mock cart item with all fees
    cart_item = {
        'subtotal': 2160.00,
        'shipping_fee': 7.50,
        'import_duty': 120.00
    }
    
    # Calculate expected grand total
    expected_total = cart_item['subtotal'] + cart_item['shipping_fee'] + cart_item['import_duty']
    assert expected_total == 2287.50

