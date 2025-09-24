# tests/test_integration.py
import pytest
import random
from src.main import app
from src.database import get_db, close_db
from src.models import User
from werkzeug.security import check_password_hash

# --- Pytest Fixture ---
# A fixture sets up a consistent and predictable state for tests.
# This fixture provides a 'test client' that we can use to make requests to our app.
@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key' # Use a different key for testing
    with app.test_client() as client:
        with app.app_context():
            # You might want to initialize a clean database before each test
            pass
        yield client

# --- Integration Test ---
def test_user_registration_and_login(client):
    """
    GIVEN a running Flask application connected to a database
    WHEN a new user is registered through the '/register' endpoint
    THEN the user should be created in the database and able to log in
    """
    # --- Part 1: Registration ---
    
    # 1. ARRANGE: Define new user data
    test_username = f"testuser_{random.randint(1000, 9999)}"
    test_password = "password123"
    test_email = f"{test_username}@example.com"

    # 2. ACT: Simulate a POST request to register the new user
    register_response = client.post('/register', data={
        'username': test_username,
        'password': test_password,
        'email': test_email
    }, follow_redirects=True)

    # 3. ASSERT: Check that the registration was successful
    assert register_response.status_code == 200 # Should redirect to login page
    assert b"Login" in register_response.data # Check if login page content is present

    # --- Part 2: Verify Database ---

    # 1. ARRANGE: Get a database session
    with app.app_context():
        db = get_db()
        # 2. ACT: Query the database for the new user
        user_from_db = db.query(User).filter_by(username=test_username).first()

        # 3. ASSERT: Check that the user exists and data is correct
        assert user_from_db is not None
        assert user_from_db.email == test_email
        assert check_password_hash(user_from_db.passwordHash, test_password)

    # --- Part 3: Login ---

    # 1. ARRANGE (already done)

    # 2. ACT: Simulate a POST request to log in with the new user's credentials
    login_response = client.post('/login', data={
        'username': test_username,
        'password': test_password
    }, follow_redirects=True)

    # 3. ASSERT: Check that the login was successful
    assert login_response.status_code == 200
    assert b"Shopping Cart" in login_response.data # Check for main page content
    assert f"Welcome, {test_username}!".encode() in login_response.data

