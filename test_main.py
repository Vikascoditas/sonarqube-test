import pytest
from main import app, db, User, Item

@pytest.fixture(scope='module')
def test_client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
    db.create_all()
    with app.test_client() as client:
        yield client
    db.drop_all()

def test_register(test_client):
    response = test_client.post('/api/register', json={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 201
    assert b"User registered successfully" in response.data

def test_login(test_client):
    test_client.post('/api/register', json={'username': 'testuser', 'password': 'testpass'})
    response = test_client.post('/api/login', json={'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 200
    assert b"Login successful" in response.data

def test_create_item(test_client):
    response = test_client.post('/api/items', json={'name': 'Test Item', 'description': 'Test Description'})
    assert response.status_code == 201
    assert b"Test Item" in response.data

def test_get_item(test_client):
    item = Item(name='Test Item', description='Test Description')
    db.session.add(item)
    db.session.commit()
    response = test_client.get(f'/api/items/{item.id}')
    assert response.status_code == 200
    assert b"Test Item" in response.data

# Add more tests for other routes
