#!/usr/bin/env python3
"""
Setup script for BiGuard Backend
"""

import os
import subprocess
import sys

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def create_env_file():
    """Create .env file from template"""
    if os.path.exists('.env'):
        print("✓ .env file already exists")
        return True
    
    if os.path.exists('env.example'):
        try:
            with open('env.example', 'r') as f:
                content = f.read()
            
            with open('.env', 'w') as f:
                f.write(content)
            
            print("✓ Created .env file from template")
            print("⚠ Please edit .env file with your actual values")
            return True
        except Exception as e:
            print(f"✗ Failed to create .env file: {e}")
            return False
    else:
        print("✗ env.example file not found")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} is not compatible")
        print("  Python 3.8+ is required")
        return False

def main():
    """Main setup function"""
    print("BiGuard Backend Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        return
    
    # Create virtual environment if it doesn't exist
    if not os.path.exists('venv'):
        print("\nCreating virtual environment...")
        if run_command('python -m venv venv', 'Creating virtual environment'):
            print("✓ Virtual environment created")
            print("⚠ Please activate it:")
            print("  On Windows: venv\\Scripts\\activate")
            print("  On macOS/Linux: source venv/bin/activate")
        else:
            print("✗ Failed to create virtual environment")
            return
    else:
        print("✓ Virtual environment already exists")
    
    # Create .env file
    create_env_file()
    
    # Install dependencies
    print("\nInstalling dependencies...")
    if run_command('pip install -r requirements.txt', 'Installing Python dependencies'):
        print("✓ Dependencies installed successfully")
    else:
        print("✗ Failed to install dependencies")
        print("  Please make sure your virtual environment is activated")
        return
    
    # Run test setup
    print("\nRunning setup tests...")
    if run_command('python test_setup.py', 'Running setup tests'):
        print("✓ Setup tests completed")
    else:
        print("⚠ Setup tests failed - check the output above")
    
    print("\n" + "=" * 40)
    print("Setup Complete!")
    print("\nNext steps:")
    print("1. Edit .env file with your configuration")
    print("2. Get Plaid API credentials from https://dashboard.plaid.com/")
    print("3. Run 'python app.py' to start the server")
    print("4. The API will be available at http://localhost:5000")
    
    print("\nFor more information, see README.md")

if __name__ == "__main__":
    main() 