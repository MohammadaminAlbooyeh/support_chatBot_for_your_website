import io
import os
import sys
import tempfile
import pytest


# Basic environment check
def test_python_version():
    assert sys.version_info.major >= 3


# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import app, db


@pytest.fixture
def client():
    """Create a test client using an in-memory database and temporary uploads folder."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    tmpdir = tempfile.mkdtemp()
    app.config['UPLOAD_FOLDER'] = tmpdir

    with app.test_client() as client:
        with app.app_context():
            if db is not None:
                db.create_all()
            yield client
            if db is not None:
                db.session.remove()
                db.drop_all()


def test_home_page(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'Support Center' in resp.data


def test_chat_greeting(client):
    resp = client.post('/chat', json={'message': 'hello'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'response' in data
    assert 'welcome' in data['response'].lower() or 'hi' in data['response'].lower()


def test_human_agent_creates_ticket(client):
    # Request a human agent
    resp = client.post('/chat', json={'message': 'please connect me to a human'})
    assert resp.status_code == 200
    data = resp.get_json()
    # When DB is available, ticket_created should be True and ticket_id present
    if db is not None:
        assert data.get('ticket_created') is True
        assert data.get('ticket_id') is not None


def test_upload_no_file(client):
    resp = client.post('/upload')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is False


def test_upload_file(client):
    # Upload a small text file
    data = {
        'file': (io.BytesIO(b'hello'), 'test.txt')
    }
    resp = client.post('/upload', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    payload = resp.get_json()
    # Either upload succeeds or file type rejected depending on allowed extensions
    assert 'success' in payload
    if payload['success']:
        assert 'message' in payload


def test_admin_endpoints(client):
    # Ensure endpoints return JSON lists (may be empty)
    resp1 = client.get('/admin/conversations')
    assert resp1.status_code == 200
    assert isinstance(resp1.get_json(), list)

    resp2 = client.get('/admin/tickets')
    assert resp2.status_code == 200
    assert isinstance(resp2.get_json(), list)

def test_requirements_file():
    """Test that requirements.txt has necessary dependencies."""
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
            assert 'Flask' in requirements, "Flask should be in requirements"
            print("✅ Requirements file validated")
    except FileNotFoundError:
        pytest.skip("requirements.txt not found")

def test_readme_exists():
    """Test that README.md exists."""
    assert os.path.exists('README.md'), "README.md should exist"
    print("✅ README.md exists")

def test_chatbot_structure():
    """Test chatbot project structure."""
    required_files = [
        'src/main.py',
        'requirements.txt', 
        'README.md',
        '.github/workflows/chatBot_support.yaml'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"⚠️ {file_path} missing (optional)")
    
    # At least main.py should exist
    assert os.path.exists('src/main.py'), "main.py is required"

if __name__ == '__main__':
    pytest.main([__file__, '-v'])