# tests/test_logic.py
import pytest

# --- Business Logic Function ---
# In a real application, this function might be in a separate 'logic' or 'utils' file.
# For this test, we are defining it here to show a self-contained example.
def calculate_cart_total(cart_items):
    """
    Calculates the total price of all items in a shopping cart.
    :param cart_items: A list of dictionaries, where each dictionary represents an item.
                       Each item must have 'price' and 'quantity' keys.
    :return: The total cost as a float.
    """
    total = 0.0
    for item in cart_items:
        total += float(item['price']) * int(item['quantity'])
    return total

# --- Unit Test ---
def test_calculate_cart_total():
    """
    GIVEN a list of items in a shopping cart
    WHEN the calculate_cart_total function is called
    THEN it should return the correct total amount
    """
    # 1. ARRANGE: Set up the test data
    sample_cart = [
        {'product_id': 1, 'name': 'Laptop', 'price': 1200.00, 'quantity': 1},
        {'product_id': 2, 'name': 'Mouse', 'price': 25.00, 'quantity': 2},
        {'product_id': 3, 'name': 'Keyboard', 'price': 75.00, 'quantity': 1}
    ]
    expected_total = 1200.00 + (25.00 * 2) + 75.00  # Expected total is 1325.00

    # 2. ACT: Call the function being tested
    actual_total = calculate_cart_total(sample_cart)

    # 3. ASSERT: Check if the result is what we expect
    assert actual_total == expected_total
    assert isinstance(actual_total, float)

def test_calculate_cart_total_with_empty_cart():
    """
    GIVEN an empty shopping cart
    WHEN the calculate_cart_total function is called
    THEN it should return 0.0
    """
    # 1. ARRANGE
    empty_cart = []
    expected_total = 0.0

    # 2. ACT
    actual_total = calculate_cart_total(empty_cart)

    # 3. ASSERT
    assert actual_total == expected_total

