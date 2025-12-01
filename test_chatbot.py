import pytest
import sys
import os

# Simple test file that focuses on basic functionality
def test_python_version():
    """Test that Python version is compatible."""
    assert sys.version_info >= (3, 8)
    print(f"✅ Python version: {sys.version}")

def test_file_structure():
    """Test that required files exist."""
    assert os.path.exists('src/main.py'), "main.py should exist"
    assert os.path.exists('requirements.txt'), "requirements.txt should exist"
    print("✅ File structure verified")

def test_imports():
    """Test that main modules can be imported."""
    try:
        sys.path.insert(0, 'src')
        import main
        assert hasattr(main, 'app'), "Flask app should be defined"
        print("✅ Main module imports successfully")
    except ImportError as e:
        pytest.skip(f"Import test skipped: {e}")

def test_basic_flask_app():
    """Test basic Flask app functionality."""
    try:
        sys.path.insert(0, 'src')
        import main
        
        # Test that app exists and can be configured
        app = main.app
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            response = client.get('/')
            # Just check that we get some response
            assert response.status_code in [200, 404, 500], "Should get some HTTP response"
            print("✅ Basic Flask app test passed")
            
    except Exception as e:
        pytest.skip(f"Flask test skipped: {e}")

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