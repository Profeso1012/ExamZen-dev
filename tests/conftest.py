import pytest
import sys
import os
from examzen import app, db, bcrypt
from examzen.models import User, Organization

# Add project root to sys path so we can import examzen
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def test_client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Use in-memory DB for tests
    app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for easier form testing

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

@pytest.fixture
def new_user():
    return User(
        username='testuser', 
        email='test@test.com', 
        password=bcrypt.generate_password_hash('password').decode('utf-8'),
        age=20,
        status='Student'
    )
