import pytest
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import app, db

@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

@pytest.fixture
def app_context():
    """Create an application context for testing."""
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

def test_home_page(client):
    """Test that the home page loads successfully."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Support Center' in response.data

def test_chat_endpoint(client):
    """Test the chat endpoint with various messages."""
    # Test greeting
    response = client.post('/chat', 
                          json={'message': 'hello'}, 
                          content_type='application/json')
    assert response.status_code == 200
    data = response.get_json()
    assert 'response' in data
    assert 'Welcome' in data['response'] or 'Hi there' in data['response']

def test_chat_help(client):
    """Test help request."""
    response = client.post('/chat', 
                          json={'message': 'help'}, 
                          content_type='application/json')
    assert response.status_code == 200
    data = response.get_json()
    assert 'Billing' in data['response']
    assert 'Technical' in data['response']

def test_chat_human_agent(client):
    """Test human agent request creates support ticket."""
    response = client.post('/chat', 
                          json={'message': 'I need to speak to a human'}, 
                          content_type='application/json')
    assert response.status_code == 200
    data = response.get_json()
    assert 'connecting you with a live agent' in data['response']
    assert data.get('ticket_created') == True

def test_file_upload_no_file(client):
    """Test file upload without file."""
    response = client.post('/upload')
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] == False
    assert 'No file selected' in data['error']

def test_admin_conversations(client):
    """Test admin conversations endpoint."""
    # First create a conversation
    client.post('/chat', 
                json={'message': 'test message'}, 
                content_type='application/json')
    
    response = client.get('/admin/conversations')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

def test_admin_tickets(client):
    """Test admin tickets endpoint."""
    response = client.get('/admin/tickets')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

def test_response_categories(client):
    """Test various response categories."""
    test_cases = [
        ('billing help', 'billing'),
        ('technical issue', 'technical'),
        ('account problem', 'account'),
        ('payment issue', 'payment'),
        ('login trouble', 'login')
    ]
    
    for message, expected_keyword in test_cases:
        response = client.post('/chat', 
                              json={'message': message}, 
                              content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        # Check that response contains relevant content (case insensitive)
        assert any(keyword in data['response'].lower() for keyword in [expected_keyword, 'help', 'assist'])

if __name__ == '__main__':
    pytest.main([__file__, '-v'])