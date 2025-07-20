#!/usr/bin/env python3
"""
Test script to verify BiGuard backend setup
"""

import sys
import os

def test_imports():
    """Test if all required packages can be imported"""
    print("Testing imports...")
    
    try:
        import flask
        print("✓ Flask imported successfully")
    except ImportError as e:
        print(f"✗ Flask import failed: {e}")
        return False
    
    try:
        import plaid
        print("✓ Plaid imported successfully")
    except ImportError as e:
        print(f"✗ Plaid import failed: {e}")
        return False
    
    try:
        import sklearn
        print("✓ Scikit-learn imported successfully")
    except ImportError as e:
        print(f"✗ Scikit-learn import failed: {e}")
        return False
    
    try:
        import pandas
        print("✓ Pandas imported successfully")
    except ImportError as e:
        print(f"✗ Pandas import failed: {e}")
        return False
    
    try:
        import numpy
        print("✓ NumPy imported successfully")
    except ImportError as e:
        print(f"✗ NumPy import failed: {e}")
        return False
    
    try:
        import pyodbc
        print("✓ PyODBC imported successfully")
    except ImportError as e:
        print(f"✗ PyODBC import failed: {e}")
        print("  Note: PyODBC is optional for local development")
    
    return True

def test_environment():
    """Test environment variables"""
    print("\nTesting environment...")
    
    # Check if .env file exists
    if os.path.exists('.env'):
        print("✓ .env file found")
    else:
        print("⚠ .env file not found - you may need to create one from env.example")
    
    # Check for required environment variables
    required_vars = ['SECRET_KEY', 'JWT_SECRET_KEY']
    optional_vars = ['PLAID_CLIENT_ID', 'PLAID_SECRET', 'DATABASE_URL']
    
    print("\nRequired environment variables:")
    for var in required_vars:
        if os.getenv(var):
            print(f"✓ {var} is set")
        else:
            print(f"✗ {var} is not set")
    
    print("\nOptional environment variables:")
    for var in optional_vars:
        if os.getenv(var):
            print(f"✓ {var} is set")
        else:
            print(f"⚠ {var} is not set (optional)")

def test_flask_app():
    """Test if Flask app can be created"""
    print("\nTesting Flask app creation...")
    
    try:
        from app import app, db
        print("✓ Flask app created successfully")
        
        # Test database creation
        with app.app_context():
            db.create_all()
            print("✓ Database tables created successfully")
        
        return True
    except Exception as e:
        print(f"✗ Flask app creation failed: {e}")
        return False

def main():
    """Run all tests"""
    print("BiGuard Backend Setup Test")
    print("=" * 40)
    
    # Test imports
    imports_ok = test_imports()
    
    # Test environment
    test_environment()
    
    # Test Flask app
    flask_ok = test_flask_app()
    
    print("\n" + "=" * 40)
    print("Test Summary:")
    
    if imports_ok and flask_ok:
        print("✓ All tests passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Create a .env file from env.example")
        print("2. Get Plaid API credentials from https://dashboard.plaid.com/")
        print("3. Run 'python app.py' to start the server")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("1. Make sure all dependencies are installed: pip install -r requirements.txt")
        print("2. Check your Python version (3.8+ required)")
        print("3. Verify your virtual environment is activated")

if __name__ == "__main__":
    main() 