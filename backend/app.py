from werkzeug.security import check_password_hash
import os
os.environ['PLAID_CLIENT_ID'] = '6853f9614ac5c0002193dd49'
os.environ['PLAID_SECRET'] = 'bb5fd63a66f16fab15feeeb7466075'
os.environ['PLAID_ENV'] = 'sandbox'

# Framework and utilities
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_bcrypt import Bcrypt
import plaid
from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.sandbox_item_fire_webhook_request import SandboxItemFireWebhookRequest

from datetime import datetime, timedelta
import pandas as pd
from sklearn.ensemble import IsolationForest
import numpy as np

# MongoDB setup
from pymongo import MongoClient
from bson import ObjectId

# Production mode toggle (currently false for testing)
IS_PRODUCTION = os.environ.get('PLAID_ENV') == 'production'

# Initialize Flask app
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Initialize extensions
jwt = JWTManager(app)
bcrypt = Bcrypt(app)
CORS(app)

# Import chatbot blueprint
from chatbot import chatbot_bp

# Register blueprints
app.register_blueprint(chatbot_bp)

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['biguard']
users_collection = db['users']
accounts_collection = db['accounts']
transactions_collection = db['transactions']
fraudulent_transactions_collection = db['fraudulent_transactions']
budgets_collection = db['budgets']

# Plaid client configuration
plaid_configuration = plaid.Configuration(
    host=plaid.Environment.Sandbox,
    api_key={
        'clientId': os.environ['PLAID_CLIENT_ID'],
        'secret': os.environ['PLAID_SECRET'],
    }
)
api_client = plaid.ApiClient(plaid_configuration)
plaid_api = plaid_api.PlaidApi(api_client)

# Import ML model functions
from model.predict_category import predict_category

# Import sample data generator
from sample_data_generator import generate_sample_data, clear_sample_data, get_financial_summary

# Import anomaly detection
from anomaly_detection import anomaly_detector

# Authentication routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        print(f"[REGISTER] Received data: {data}")
        
        # Validate required fields - support both camelCase and snake_case
        required_fields = ['first_name', 'last_name', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                print(f"[REGISTER] Missing field: {field}")
                return jsonify({'error': f'{field.replace("_", "")} is required'}), 400
        
        # Check if user already exists
        existing_user = users_collection.find_one({'email': data['email']})
        if existing_user:
            return jsonify({'error': 'User with this email already exists'}), 409
        
        # Hash password
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        
        # Create user document
        user_doc = {
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'email': data['email'],
            'password': hashed_password,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Insert user into database
        result = users_collection.insert_one(user_doc)
        user_id = str(result.inserted_id)
        
        # Only generate sample data in non-production mode (for testing)
        sample_result = {'success': False, 'message': 'No sample data generated in production mode'}
        if not IS_PRODUCTION:
            print(f"[REGISTER] Generating sample data for user {user_id}")
            sample_result = generate_sample_data(user_id)  # Auto-generate sample data for testing
            print(f"[REGISTER] Sample data result: {sample_result}")
        
        # Create JWT token
        access_token = create_access_token(identity=user_id)
        
        return jsonify({
            'message': 'User registered successfully',
            'access_token': access_token,
            'user': {
                'id': user_id,
                'firstName': data['first_name'],
                'lastName': data['last_name'],
                'email': data['email']
            },
            'sample_data_generated': sample_result['success'],
            'sample_data_message': sample_result.get('message', '')
        }), 201
        
    except Exception as e:
        print(f"[REGISTER] Error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Find user by email
        user = users_collection.find_one({'email': data['email']})
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Check password
        if not bcrypt.check_password_hash(user['password'], data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Create JWT token
        access_token = create_access_token(identity=str(user['_id']))
        
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'user': {
                'id': str(user['_id']),
                'firstName': user.get('first_name', ''),
                'lastName': user.get('last_name', ''),
                'email': user['email']
            }
        }), 200
        
    except Exception as e:
        print(f"[LOGIN] Error: {e}")
        return jsonify({'error': 'Login failed'}), 500

# Sample data management routes
@app.route('/api/sample-data/generate', methods=['POST'])
@jwt_required()
def generate_sample_data_endpoint():
    """Generate sample financial data for the current user"""
    try:
        user_id = get_jwt_identity()
        # Don't require JSON data, use default values
        result = generate_sample_data(user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        print(f"Error generating sample data: {e}")
        return jsonify({'error': 'Failed to generate sample data'}), 500

@app.route('/api/sample-data/clear', methods=['POST'])
@jwt_required()
def clear_sample_data_endpoint():
    """Clear sample financial data for the current user"""
    try:
        user_id = get_jwt_identity()
        result = clear_sample_data(user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify({'error': result['error']}), 500
            
    except Exception as e:
        print(f"Error clearing sample data: {e}")
        return jsonify({'error': 'Failed to clear sample data'}), 500

@app.route('/api/sample-data/financial-summary', methods=['GET'])
@jwt_required()
def get_financial_summary_endpoint():
    """Get financial summary for the current user"""
    try:
        user_id = get_jwt_identity()
        summary = get_financial_summary(user_id)
        
        if summary:
            return jsonify(summary), 200
        else:
            return jsonify({'error': 'Failed to get financial summary'}), 500
            
    except Exception as e:
        print(f"Error getting financial summary: {e}")
        return jsonify({'error': 'Failed to get financial summary'}), 500

@app.route('/api/connect-real-bank', methods=['POST'])
@jwt_required()
def connect_real_bank():
    """Clear sample data and prepare for real bank connection"""
    try:
        user_id = get_jwt_identity()
        
        # Clear all sample data first
        clear_result = clear_sample_data(user_id)
        
        if not clear_result['success']:
            return jsonify({'error': 'Failed to clear sample data'}), 500
        
        # Update user to indicate they're ready for real bank connection
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$set': {
                    'has_sample_data': False,
                    'ready_for_real_bank': True,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        return jsonify({
            'message': 'Sample data cleared successfully. You can now connect your real bank account.',
            'cleared_sample_data': True,
            'ready_for_plaid': True
        }), 200
        
    except Exception as e:
        print(f"Error in connect_real_bank: {e}")
        return jsonify({'error': 'Failed to prepare for real bank connection'}), 500

@app.route('/api/user/data-status', methods=['GET'])
@jwt_required()
def get_user_data_status():
    """Get user's data status (sample data vs real data)"""
    try:
        user_id = get_jwt_identity()
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user has sample data
        has_sample_data = user.get('has_sample_data', False)
        ready_for_real_bank = user.get('ready_for_real_bank', False)
        
        # Check if user has any accounts (real or sample)
        account_count = accounts_collection.count_documents({'user_id': user_id})
        transaction_count = transactions_collection.count_documents({'user_id': user_id})
        
        return jsonify({
            'has_sample_data': has_sample_data,
            'ready_for_real_bank': ready_for_real_bank,
            'account_count': account_count,
            'transaction_count': transaction_count,
            'is_production_mode': IS_PRODUCTION
        }), 200
        
    except Exception as e:
        print(f"Error getting user data status: {e}")
        return jsonify({'error': 'Failed to get user data status'}), 500

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information"""
    try:
        user_id = get_jwt_identity()
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': {
                'id': str(user['_id']),
                'firstName': user.get('first_name', ''),
                'lastName': user.get('last_name', ''),
                'email': user['email']
            }
        }), 200
        
    except Exception as e:
        print(f"[ME] Error: {e}")
        return jsonify({'error': 'Failed to get user information'}), 500

# Plaid Link token creation
@app.route('/api/plaid/create-link-token', methods=['POST'])
@jwt_required()
def create_link_token():
    """Create a Plaid Link token for connecting bank accounts"""
    try:
        user_id = get_jwt_identity()
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Create link token request
        request_obj = LinkTokenCreateRequest(
            user=LinkTokenCreateRequestUser(
                client_user_id=str(user_id)
            ),
            client_name="BiGuard AI",
            products=[Products("auth"), Products("transactions")],
            country_codes=[CountryCode("US")],
            language="en"
        )
        
        # Create link token
        response = plaid_api.link_token_create(request_obj)
        
        return jsonify({
            'link_token': response.link_token,
            'expiration': response.expiration.isoformat() if response.expiration else None
        }), 200
        
    except Exception as e:
        print(f"[LINK_TOKEN] Error: {e}")
        return jsonify({'error': 'Failed to create link token'}), 500

# Exchange public token for access token
@app.route('/api/plaid/exchange-token', methods=['POST'])
@jwt_required()
def exchange_token():
    """Exchange public token for access token and get account information"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('public_token'):
            return jsonify({'error': 'Public token is required'}), 400
        
        # Exchange public token for access token
        request_obj = ItemPublicTokenExchangeRequest(
            public_token=data['public_token']
        )
        response = plaid_api.item_public_token_exchange(request_obj)
        
        # Get account information
        accounts_request = AccountsGetRequest(
            access_token=response.access_token
        )
        accounts_response = plaid_api.accounts_get(accounts_request)
        
        # Save accounts to database
        saved_accounts = []
        for account in accounts_response.accounts:
            # Handle the institution name - it might not be directly available on account
            institution_name = getattr(account, 'institution_name', None)
            if not institution_name and hasattr(accounts_response, 'item'):
                institution_name = getattr(accounts_response.item, 'institution_name', 'Unknown Institution')
            
            account_doc = {
                'user_id': str(user_id),
                'plaid_account_id': account.account_id,
                'plaid_access_token': response.access_token,
                'name': account.name,
                'type': str(account.type) if account.type else None,
                'subtype': str(account.subtype) if account.subtype else None,
                'mask': account.mask,
                'institution_name': institution_name or 'Unknown Institution',
                'current_balance': account.balances.current if account.balances else 0.0,
                'available_balance': account.balances.available if account.balances else 0.0,
                'last_updated': datetime.utcnow(),
                'created_at': datetime.utcnow()
            }
            
            result = accounts_collection.insert_one(account_doc)
            saved_accounts.append({
                'id': str(result.inserted_id),
                'plaid_account_id': account.account_id,
                'name': account.name,
                'type': str(account.type) if account.type else None,
                'subtype': str(account.subtype) if account.subtype else None,
                'mask': account.mask,
                'institution_name': institution_name or 'Unknown Institution',
                'current_balance': account.balances.current if account.balances else 0.0,
                'available_balance': account.balances.available if account.balances else 0.0
            })
        
        # Generate Plaid sandbox transactions for checking account on signup
        # Only generate for checking accounts, not savings
        for account in accounts_response.accounts:
            # Handle both string and enum types for subtype
            subtype_str = str(account.subtype) if account.subtype else ''
            if subtype_str.lower() == 'checking':
                # Find the corresponding saved account
                saved_account = next((acc for acc in saved_accounts if acc['plaid_account_id'] == account.account_id), None)
                if saved_account:
                    # Generate Plaid sandbox transactions instead of sample data
                    generate_plaid_transactions(user_id, saved_account['id'], response.access_token)
                    break  # Only generate for the first checking account
        
        return jsonify({
            'message': 'Accounts connected successfully',
            'accounts': saved_accounts
        }), 200
        
    except Exception as e:
        print(f"[EXCHANGE_TOKEN] Error: {e}")
        return jsonify({'error': 'Failed to connect accounts'}), 500

def generate_plaid_transactions(user_id, account_id, access_token):
    """Generate 200+ Plaid sandbox transactions for checking account on signup (current month + previous 3 months)"""
    try:
        print(f"[SIGNUP] Generating 200+ Plaid sandbox transactions for new user {user_id} checking account")
        
        # Try to fire webhooks, but don't fail if they don't work
        webhook_success = 0
        for i in range(20):  # Generate ~2000+ transactions to ensure 200+ after filtering
            try:
                req = SandboxItemFireWebhookRequest(
                    access_token=access_token,
                    webhook_code='DEFAULT_UPDATE'
                )
                plaid_api.sandbox_item_fire_webhook(req)
                webhook_success += 1
                if (i + 1) % 5 == 0:
                    print(f"[SIGNUP] Fired {i+1}/20 webhooks for new user")
            except Exception as e:
                print(f"[SIGNUP] Error firing webhook {i+1}: {e}")
                # Continue even if webhook fails
                continue
        
        print(f"[SIGNUP] Successfully fired {webhook_success}/20 webhooks")
        
        # Wait for Plaid to process
        import time
        time.sleep(5)  # Increased wait time for more transactions
        
        # Sync transactions from Plaid with date filtering for current month + previous 3 months
        sync_plaid_transactions(user_id, account_id, access_token)
        
    except Exception as e:
        print(f"[SIGNUP] Error generating Plaid transactions: {e}")
        # No fallback - user wants only Plaid data on signup
        print(f"[SIGNUP] Plaid transaction generation failed, but continuing with signup process")

def generate_sample_transactions(user_id, account_id):
    """Generate 200+ sample transactions for checking account on signup (current month + previous 3 months)"""
    try:
        print(f"[SIGNUP] Generating 200+ transactions for new user {user_id} checking account (current month + previous 3 months)")
        sample_transactions = []
        
        # Income transactions (salary, bonuses, etc.) - 20 transactions for checking
        income_transactions = [
            {'name': 'Salary Deposit - Company Inc', 'amount': 5000.00, 'category': 'Income'},
            {'name': 'Salary Deposit - Company Inc', 'amount': 5000.00, 'category': 'Income'},
            {'name': 'Salary Deposit - Company Inc', 'amount': 5000.00, 'category': 'Income'},
            {'name': 'Bonus Payment - Q4 Performance', 'amount': 1500.00, 'category': 'Income'},
            {'name': 'Freelance Payment - Web Design', 'amount': 800.00, 'category': 'Income'},
            {'name': 'Freelance Payment - Logo Design', 'amount': 650.00, 'category': 'Income'},
            {'name': 'Interest Payment - Savings', 'amount': 45.00, 'category': 'Income'},
            {'name': 'Refund - Amazon Return', 'amount': 120.00, 'category': 'Income'},
            {'name': 'Cashback Reward - Credit Card', 'amount': 75.00, 'category': 'Income'},
            {'name': 'Dividend Payment - Stock Portfolio', 'amount': 200.00, 'category': 'Income'},
            {'name': 'Reimbursement - Business Travel', 'amount': 350.00, 'category': 'Income'},
            {'name': 'Side Gig - Uber Driving', 'amount': 180.00, 'category': 'Income'},
            {'name': 'Side Gig - DoorDash Delivery', 'amount': 95.00, 'category': 'Income'},
            {'name': 'Consulting Fee - Tech Project', 'amount': 1200.00, 'category': 'Income'},
            {'name': 'Rental Income - Property', 'amount': 1800.00, 'category': 'Income'},
            {'name': 'Commission - Sales', 'amount': 450.00, 'category': 'Income'},
            {'name': 'Gift Money - Birthday', 'amount': 100.00, 'category': 'Income'},
            {'name': 'Tax Refund - IRS', 'amount': 850.00, 'category': 'Income'},
            {'name': 'Investment Return - Crypto', 'amount': 300.00, 'category': 'Income'},
            {'name': 'Online Survey Payment', 'amount': 25.00, 'category': 'Income'},
            {'name': 'Referral Bonus - Friend Signup', 'amount': 50.00, 'category': 'Income'},
            {'name': 'Overtime Pay - Extra Hours', 'amount': 320.00, 'category': 'Income'},
            {'name': 'Holiday Bonus', 'amount': 750.00, 'category': 'Income'},
            {'name': 'Performance Bonus', 'amount': 1200.00, 'category': 'Income'},
        ]
        
        # Food & Dining transactions - 30 transactions for checking
        food_transactions = [
            {'name': 'Walmart Groceries', 'amount': 120.50, 'category': 'Food & Dining'},
            {'name': 'Walmart Groceries', 'amount': 95.30, 'category': 'Food & Dining'},
            {'name': 'Walmart Groceries', 'amount': 145.75, 'category': 'Food & Dining'},
            {'name': 'Starbucks Coffee', 'amount': 6.25, 'category': 'Food & Dining'},
            {'name': 'Starbucks Coffee', 'amount': 8.50, 'category': 'Food & Dining'},
            {'name': 'Starbucks Coffee', 'amount': 7.75, 'category': 'Food & Dining'},
            {'name': 'McDonald\'s Fast Food', 'amount': 15.75, 'category': 'Food & Dining'},
            {'name': 'McDonald\'s Fast Food', 'amount': 12.45, 'category': 'Food & Dining'},
            {'name': 'Pizza Hut Delivery', 'amount': 28.00, 'category': 'Food & Dining'},
            {'name': 'Subway Sandwich', 'amount': 12.50, 'category': 'Food & Dining'},
            {'name': 'Subway Sandwich', 'amount': 14.75, 'category': 'Food & Dining'},
            {'name': 'Chipotle Mexican Grill', 'amount': 18.75, 'category': 'Food & Dining'},
            {'name': 'Chipotle Mexican Grill', 'amount': 22.50, 'category': 'Food & Dining'},
            {'name': 'Kroger Grocery Store', 'amount': 95.30, 'category': 'Food & Dining'},
            {'name': 'Kroger Grocery Store', 'amount': 78.45, 'category': 'Food & Dining'},
            {'name': 'Dunkin Donuts', 'amount': 8.50, 'category': 'Food & Dining'},
            {'name': 'Dunkin Donuts', 'amount': 11.25, 'category': 'Food & Dining'},
            {'name': 'Taco Bell', 'amount': 14.25, 'category': 'Food & Dining'},
            {'name': 'Taco Bell', 'amount': 16.80, 'category': 'Food & Dining'},
            {'name': 'Panera Bread', 'amount': 22.00, 'category': 'Food & Dining'},
            {'name': 'Whole Foods Market', 'amount': 85.75, 'category': 'Food & Dining'},
            {'name': 'Whole Foods Market', 'amount': 125.40, 'category': 'Food & Dining'},
            {'name': 'Burger King', 'amount': 16.80, 'category': 'Food & Dining'},
            {'name': 'Wendy\'s', 'amount': 13.45, 'category': 'Food & Dining'},
            {'name': 'Domino\'s Pizza', 'amount': 25.90, 'category': 'Food & Dining'},
            {'name': 'Papa John\'s Pizza', 'amount': 27.50, 'category': 'Food & Dining'},
            {'name': 'KFC Fried Chicken', 'amount': 19.95, 'category': 'Food & Dining'},
            {'name': 'Popeyes Louisiana Kitchen', 'amount': 17.25, 'category': 'Food & Dining'},
            {'name': 'Chick-fil-A', 'amount': 21.30, 'category': 'Food & Dining'},
            {'name': 'Five Guys Burgers', 'amount': 24.75, 'category': 'Food & Dining'},
            {'name': 'Shake Shack', 'amount': 26.80, 'category': 'Food & Dining'},
            {'name': 'In-N-Out Burger', 'amount': 18.90, 'category': 'Food & Dining'},
            {'name': 'Culver\'s', 'amount': 20.15, 'category': 'Food & Dining'},
            {'name': 'Whataburger', 'amount': 19.45, 'category': 'Food & Dining'},
            {'name': 'Sonic Drive-In', 'amount': 16.70, 'category': 'Food & Dining'},
            {'name': 'Arby\'s', 'amount': 15.20, 'category': 'Food & Dining'},
            {'name': 'Jack in the Box', 'amount': 14.85, 'category': 'Food & Dining'},
        ]
        
        # Transportation transactions - 25 transactions for checking
        transport_transactions = [
            {'name': 'Shell Gas Station', 'amount': 45.00, 'category': 'Transportation'},
            {'name': 'Shell Gas Station', 'amount': 52.30, 'category': 'Transportation'},
            {'name': 'Shell Gas Station', 'amount': 38.75, 'category': 'Transportation'},
            {'name': 'Uber Ride', 'amount': 25.50, 'category': 'Transportation'},
            {'name': 'Uber Ride', 'amount': 18.90, 'category': 'Transportation'},
            {'name': 'Uber Ride', 'amount': 32.75, 'category': 'Transportation'},
            {'name': 'Lyft Transportation', 'amount': 18.75, 'category': 'Transportation'},
            {'name': 'Lyft Transportation', 'amount': 22.45, 'category': 'Transportation'},
            {'name': 'Parking Fee - Downtown', 'amount': 12.00, 'category': 'Transportation'},
            {'name': 'Parking Fee - Downtown', 'amount': 15.50, 'category': 'Transportation'},
            {'name': 'Car Wash - Auto Spa', 'amount': 15.00, 'category': 'Transportation'},
            {'name': 'Oil Change - Jiffy Lube', 'amount': 65.00, 'category': 'Transportation'},
            {'name': 'Exxon Gas Station', 'amount': 52.30, 'category': 'Transportation'},
            {'name': 'Exxon Gas Station', 'amount': 48.90, 'category': 'Transportation'},
            {'name': 'BP Gas Station', 'amount': 48.75, 'category': 'Transportation'},
            {'name': 'BP Gas Station', 'amount': 55.20, 'category': 'Transportation'},
            {'name': 'Chevron Gas Station', 'amount': 50.20, 'category': 'Transportation'},
            {'name': 'Chevron Gas Station', 'amount': 42.80, 'category': 'Transportation'},
            {'name': 'Mobil Gas Station', 'amount': 47.80, 'category': 'Transportation'},
            {'name': 'Mobil Gas Station', 'amount': 51.45, 'category': 'Transportation'},
            {'name': 'Tire Rotation - Discount Tire', 'amount': 35.00, 'category': 'Transportation'},
            {'name': 'Car Battery - AutoZone', 'amount': 120.00, 'category': 'Transportation'},
            {'name': 'Brake Service - Midas', 'amount': 280.00, 'category': 'Transportation'},
            {'name': 'Transmission Service', 'amount': 450.00, 'category': 'Transportation'},
            {'name': 'Car Insurance - Progressive', 'amount': 95.00, 'category': 'Transportation'},
            {'name': 'DMV Registration', 'amount': 85.00, 'category': 'Transportation'},
            {'name': 'Toll Road Fee', 'amount': 8.50, 'category': 'Transportation'},
            {'name': 'Public Transit - Metro', 'amount': 5.25, 'category': 'Transportation'},
            {'name': 'Airport Parking', 'amount': 45.00, 'category': 'Transportation'},
            {'name': 'Car Rental - Enterprise', 'amount': 75.00, 'category': 'Transportation'},
        ]
        
        # Entertainment transactions - 20 transactions for checking
        entertainment_transactions = [
            {'name': 'Netflix Subscription', 'amount': 15.99, 'category': 'Entertainment'},
            {'name': 'Netflix Subscription', 'amount': 15.99, 'category': 'Entertainment'},
            {'name': 'Netflix Subscription', 'amount': 15.99, 'category': 'Entertainment'},
            {'name': 'Spotify Premium', 'amount': 9.99, 'category': 'Entertainment'},
            {'name': 'Spotify Premium', 'amount': 9.99, 'category': 'Entertainment'},
            {'name': 'AMC Movie Theater', 'amount': 24.50, 'category': 'Entertainment'},
            {'name': 'AMC Movie Theater', 'amount': 32.75, 'category': 'Entertainment'},
            {'name': 'Concert Tickets - Taylor Swift', 'amount': 150.00, 'category': 'Entertainment'},
            {'name': 'GameStop Video Games', 'amount': 59.99, 'category': 'Entertainment'},
            {'name': 'GameStop Video Games', 'amount': 79.99, 'category': 'Entertainment'},
            {'name': 'Bowling Alley - Strike Zone', 'amount': 35.00, 'category': 'Entertainment'},
            {'name': 'Disney+ Subscription', 'amount': 7.99, 'category': 'Entertainment'},
            {'name': 'Disney+ Subscription', 'amount': 7.99, 'category': 'Entertainment'},
            {'name': 'Hulu Premium', 'amount': 12.99, 'category': 'Entertainment'},
            {'name': 'Hulu Premium', 'amount': 12.99, 'category': 'Entertainment'},
            {'name': 'Amazon Prime Video', 'amount': 8.99, 'category': 'Entertainment'},
            {'name': 'HBO Max Subscription', 'amount': 14.99, 'category': 'Entertainment'},
            {'name': 'Apple Music', 'amount': 9.99, 'category': 'Entertainment'},
            {'name': 'Apple Music', 'amount': 9.99, 'category': 'Entertainment'},
            {'name': 'YouTube Premium', 'amount': 11.99, 'category': 'Entertainment'},
            {'name': 'Escape Room Adventure', 'amount': 45.00, 'category': 'Entertainment'},
            {'name': 'Paintball Arena', 'amount': 65.00, 'category': 'Entertainment'},
            {'name': 'Laser Tag Center', 'amount': 28.00, 'category': 'Entertainment'},
            {'name': 'Movie Night - Regal Cinemas', 'amount': 28.50, 'category': 'Entertainment'},
            {'name': 'Arcade Games - Dave & Busters', 'amount': 45.00, 'category': 'Entertainment'},
        ]
        
        # Shopping transactions - 20 transactions for checking
        shopping_transactions = [
            {'name': 'Amazon.com Purchase', 'amount': 89.99, 'category': 'Shopping'},
            {'name': 'Amazon.com Purchase', 'amount': 45.75, 'category': 'Shopping'},
            {'name': 'Amazon.com Purchase', 'amount': 125.50, 'category': 'Shopping'},
            {'name': 'Target Store', 'amount': 45.75, 'category': 'Shopping'},
            {'name': 'Target Store', 'amount': 78.90, 'category': 'Shopping'},
            {'name': 'Best Buy Electronics', 'amount': 299.99, 'category': 'Shopping'},
            {'name': 'Best Buy Electronics', 'amount': 199.99, 'category': 'Shopping'},
            {'name': 'Nike Store', 'amount': 120.00, 'category': 'Shopping'},
            {'name': 'Nike Store', 'amount': 85.50, 'category': 'Shopping'},
            {'name': 'Apple Store', 'amount': 1299.00, 'category': 'Shopping'},
            {'name': 'Home Depot', 'amount': 75.50, 'category': 'Shopping'},
            {'name': 'Home Depot', 'amount': 125.80, 'category': 'Shopping'},
            {'name': 'Walmart Supercenter', 'amount': 65.25, 'category': 'Shopping'},
            {'name': 'Walmart Supercenter', 'amount': 95.40, 'category': 'Shopping'},
            {'name': 'Costco Wholesale', 'amount': 125.80, 'category': 'Shopping'},
            {'name': 'Costco Wholesale', 'amount': 85.60, 'category': 'Shopping'},
            {'name': 'Macy\'s Department Store', 'amount': 85.40, 'category': 'Shopping'},
            {'name': 'Kohl\'s', 'amount': 95.60, 'category': 'Shopping'},
            {'name': 'Old Navy', 'amount': 45.30, 'category': 'Shopping'},
            {'name': 'Gap Clothing', 'amount': 78.90, 'category': 'Shopping'},
            {'name': 'H&M Fashion', 'amount': 35.75, 'category': 'Shopping'},
            {'name': 'Zara Clothing', 'amount': 89.50, 'category': 'Shopping'},
            {'name': 'Forever 21', 'amount': 42.25, 'category': 'Shopping'},
            {'name': 'Marshalls', 'amount': 65.80, 'category': 'Shopping'},
            {'name': 'TJ Maxx', 'amount': 55.90, 'category': 'Shopping'},
        ]
        
        # Utilities transactions - 15 transactions for checking
        utility_transactions = [
            {'name': 'Electric Bill - Duke Energy', 'amount': 85.00, 'category': 'Utilities'},
            {'name': 'Electric Bill - Duke Energy', 'amount': 92.50, 'category': 'Utilities'},
            {'name': 'Electric Bill - Duke Energy', 'amount': 78.25, 'category': 'Utilities'},
            {'name': 'Water Bill - City Water', 'amount': 45.00, 'category': 'Utilities'},
            {'name': 'Water Bill - City Water', 'amount': 52.75, 'category': 'Utilities'},
            {'name': 'Internet Bill - Comcast', 'amount': 79.99, 'category': 'Utilities'},
            {'name': 'Internet Bill - Comcast', 'amount': 79.99, 'category': 'Utilities'},
            {'name': 'Internet Bill - Comcast', 'amount': 79.99, 'category': 'Utilities'},
            {'name': 'Phone Bill - Verizon', 'amount': 95.00, 'category': 'Utilities'},
            {'name': 'Phone Bill - Verizon', 'amount': 95.00, 'category': 'Utilities'},
            {'name': 'Phone Bill - Verizon', 'amount': 95.00, 'category': 'Utilities'},
            {'name': 'Gas Bill - Dominion Energy', 'amount': 65.50, 'category': 'Utilities'},
            {'name': 'Gas Bill - Dominion Energy', 'amount': 72.80, 'category': 'Utilities'},
            {'name': 'Garbage Service - Waste Management', 'amount': 35.00, 'category': 'Utilities'},
            {'name': 'Cable TV - Spectrum', 'amount': 89.99, 'category': 'Utilities'},
            {'name': 'Security System - ADT', 'amount': 45.00, 'category': 'Utilities'},
            {'name': 'Home Insurance - State Farm', 'amount': 120.00, 'category': 'Utilities'},
            {'name': 'Property Tax - County', 'amount': 250.00, 'category': 'Utilities'},
        ]
        
        # Combine all transaction types
        all_transaction_types = [
            (income_transactions, False, 'income'),
            (food_transactions, True, 'spending'),
            (transport_transactions, True, 'spending'),
            (entertainment_transactions, True, 'spending'),
            (shopping_transactions, True, 'spending'),
            (utility_transactions, True, 'spending'),
        ]
        
        # Generate transactions with varied dates over the current month and previous 3 months
        base_date = datetime.now()
        transaction_id = 0
        
        # Calculate date range for current month + previous 3 months
        start_date = (base_date.replace(day=1) - timedelta(days=90)).replace(day=1)  # 3 months ago, first day
        end_date = base_date.date()  # Today
        
        print(f"[SAMPLE] Generating transactions from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        for transaction_list, is_expense, transaction_type in all_transaction_types:
            for i, txn in enumerate(transaction_list):
                # Spread transactions over the current month and previous 3 months
                days_ago = (transaction_id % 120)  # 120 days = ~4 months
                transaction_date = (base_date - timedelta(days=days_ago))
                
                # Ensure transaction date is within our range
                if start_date <= transaction_date.date() <= end_date:
                    sample_transactions.append({
                        'name': txn['name'],
                        'amount': txn['amount'],
                        'category': txn['category'],
                        'date': transaction_date.strftime('%Y-%m-%d'),
                        'is_expense': is_expense,
                        'transaction_type': transaction_type
                    })
                transaction_id += 1
        
        # Ensure we have at least 200 transactions
        if len(sample_transactions) < 200:
            print(f"[SAMPLE] Only {len(sample_transactions)} transactions generated, duplicating to reach 200+")
            # Duplicate some transactions to reach 200+
            original_transactions = sample_transactions.copy()
            while len(sample_transactions) < 200:
                for txn in original_transactions:
                    if len(sample_transactions) >= 200:
                        break
                    # Create a variation of the transaction
                    variation = txn.copy()
                    variation['amount'] = round(txn['amount'] * (0.8 + 0.4 * (len(sample_transactions) % 10) / 10), 2)  # Vary amount by ±20%
                    sample_transactions.append(variation)
        
        # Insert all transactions
        for txn in sample_transactions:
            transaction_doc = {
                'user_id': str(user_id),
                'account_id': str(account_id),
                'plaid_transaction_id': f'sample_{datetime.now().timestamp()}_{txn["name"]}',
                'amount': txn['amount'],
                'date': txn['date'],
                'name': txn['name'],
                'merchant_name': txn['name'],
                'category': txn['category'],
                'pending': False,
                'fraud_score': 0.1,
                'is_fraudulent': False,
                'is_expense': txn['is_expense'],
                'transaction_type': txn['transaction_type'],
                'created_at': datetime.utcnow()
            }
            transactions_collection.insert_one(transaction_doc)
        
        print(f"[SAMPLE] Generated {len(sample_transactions)} sample transactions for user {user_id} (target: 200+)")
        
    except Exception as e:
        print(f"[SAMPLE] Error generating sample transactions: {e}")

def sync_plaid_transactions(user_id, account_id, access_token):
    """Sync transactions from Plaid and categorize them with ML model (current month + previous 3 months)"""
    try:
        print(f"[SYNC] Syncing Plaid transactions for user {user_id} (current month + previous 3 months)")
        
        # Calculate date range for current month + previous 3 months
        now = datetime.now()
        start_date = (now.replace(day=1) - timedelta(days=90)).replace(day=1)  # 3 months ago, first day
        end_date = now.date()  # Today
        
        print(f"[SYNC] Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Get transactions from Plaid with date filtering
        request_obj = TransactionsSyncRequest(
            access_token=access_token,
            options={
                'include_personal_finance_category': True
            }
        )
        response = plaid_api.transactions_sync(request_obj)
        print(f"[SYNC] Plaid returned {len(response.added)} total transactions")
        
        # Filter transactions for the date range and ensure we get at least 200
        filtered_transactions = []
        for transaction in response.added:
            try:
                # Parse transaction date - ensure it's a date object
                if hasattr(transaction.date, 'strftime'):
                    tx_date = transaction.date
                elif isinstance(transaction.date, str):
                    tx_date = datetime.strptime(transaction.date, '%Y-%m-%d').date()
                else:
                    tx_date = transaction.date
                
                # Ensure both dates are date objects for comparison
                if isinstance(tx_date, datetime):
                    tx_date = tx_date.date()
                
                # Check if transaction is within our date range
                if start_date <= tx_date <= end_date:
                    filtered_transactions.append(transaction)
            except Exception as e:
                print(f"[SYNC] Error parsing transaction date: {e}")
                # Include transaction if we can't parse the date
                filtered_transactions.append(transaction)
        
        print(f"[SYNC] Filtered to {len(filtered_transactions)} transactions in date range")
        
        # If we don't have enough transactions, try to fire more webhooks to get more Plaid data
        if len(filtered_transactions) < 200:
            print(f"[SYNC] Only {len(filtered_transactions)} transactions found, trying to fire more webhooks to get more Plaid data")
            # Try to fire more webhooks to generate more Plaid transactions
            webhook_success = 0
            for i in range(10):  # Fire 10 more webhooks
                try:
                    req = SandboxItemFireWebhookRequest(
                        access_token=access_token,
                        webhook_code='DEFAULT_UPDATE'
                    )
                    plaid_api.sandbox_item_fire_webhook(req)
                    webhook_success += 1
                except Exception as e:
                    print(f"[SYNC] Error firing additional webhook {i+1}: {e}")
                    # Continue even if webhook fails
                    continue
            
            print(f"[SYNC] Successfully fired {webhook_success}/10 additional webhooks")
            
            if webhook_success > 0:
                # Wait for Plaid to process
                import time
                time.sleep(3)
                
                # Try to sync again
                response = plaid_api.transactions_sync(request_obj)
                print(f"[SYNC] After additional webhooks, Plaid returned {len(response.added)} total transactions")
                
                # Re-filter transactions
                filtered_transactions = []
                for transaction in response.added:
                    try:
                        # Parse transaction date - ensure it's a date object
                        if hasattr(transaction.date, 'strftime'):
                            tx_date = transaction.date
                        elif isinstance(transaction.date, str):
                            tx_date = datetime.strptime(transaction.date, '%Y-%m-%d').date()
                        else:
                            tx_date = transaction.date
                        
                        # Ensure both dates are date objects for comparison
                        if isinstance(tx_date, datetime):
                            tx_date = tx_date.date()
                        
                        if start_date <= tx_date <= end_date:
                            filtered_transactions.append(transaction)
                    except Exception as e:
                        print(f"[SYNC] Error parsing transaction date: {e}")
                        filtered_transactions.append(transaction)
                
                print(f"[SYNC] After additional webhooks, filtered to {len(filtered_transactions)} transactions in date range")
            else:
                print(f"[SYNC] No webhooks fired successfully, using existing {len(filtered_transactions)} transactions")
        
        # Process filtered transactions
        synced_count = 0
        for transaction in filtered_transactions:
            # Check if transaction already exists
            existing_transaction = transactions_collection.find_one({
                'plaid_transaction_id': transaction.transaction_id
            })
            
            if not existing_transaction:
                # Use ML model to predict category
                predicted_category = predict_transaction_category(transaction)
                
                # Determine if it's income or spending
                transaction_type = classify_transaction_type(transaction)
                is_expense = transaction_type == 'spending'
                
                # Calculate fraud score
                fraud_score = calculate_fraud_score(transaction, {'_id': ObjectId(user_id)})
                
                # Normalize amount
                normalized_amount, _, _ = normalize_transaction_amount(transaction)
                
                new_transaction = {
                    'user_id': str(user_id),
                    'account_id': str(account_id),
                    'plaid_transaction_id': transaction.transaction_id,
                    'amount': normalized_amount,
                    'date': transaction.date.strftime('%Y-%m-%d') if hasattr(transaction.date, 'strftime') else str(transaction.date),
                    'name': transaction.name,
                    'merchant_name': transaction.merchant_name,
                    'category': predicted_category,
                    'category_id': transaction.category_id,
                    'pending': transaction.pending,
                    'fraud_score': float(fraud_score),
                    'is_fraudulent': bool(fraud_score > 0.7),
                    'is_expense': is_expense,
                    'transaction_type': transaction_type,
                    'created_at': datetime.utcnow()
                }
                
                # Insert transaction
                result = transactions_collection.insert_one(new_transaction)
                new_transaction['_id'] = result.inserted_id
                synced_count += 1
                
                # Real-time anomaly detection for new transaction
                try:
                    # Auto-train model if needed (every 50 transactions)
                    transaction_count = transactions_collection.count_documents({'user_id': str(user_id)})
                    if transaction_count % 50 == 0:
                        print(f"[ANOMALY] Auto-training model after {transaction_count} transactions")
                        anomaly_detector.train_model(user_id, 'real')
                    
                    # Real-time detection for this specific transaction
                    anomaly_result = anomaly_detector.detect_single_transaction(new_transaction, user_id, 'real')
                    
                    if anomaly_result:
                        # Update transaction with anomaly details
                        transactions_collection.update_one(
                            {'_id': new_transaction['_id']},
                            {
                                '$set': {
                                    'is_fraudulent': True,
                                    'fraud_score': anomaly_result.get('anomaly_score', 0.8),
                                    'anomaly_severity': anomaly_result.get('severity', 'medium'),
                                    'anomaly_reasons': anomaly_result.get('reasons', []),
                                    'threat_level': anomaly_result.get('threat_level', 'medium'),
                                    'blocked': True  # Block fraudulent transactions
                                }
                            }
                        )
                        print(f"[ANOMALY] 🚨 Fraudulent transaction detected and blocked: {new_transaction['name']} - ${new_transaction['amount']}")
                        print(f"[ANOMALY] Severity: {anomaly_result.get('severity')}, Score: {anomaly_result.get('anomaly_score')}")
                        print(f"[ANOMALY] Reasons: {', '.join(anomaly_result.get('reasons', []))}")
                        print(f"[ANOMALY] Threat Level: {anomaly_result.get('threat_level')}")
                            
                except Exception as e:
                    print(f"[ANOMALY] Error in real-time detection: {e}")
                    # Continue processing even if anomaly detection fails
        
        print(f"[SYNC] Successfully synced {synced_count} transactions for date range")
        
    except Exception as e:
        print(f"[SYNC] Error syncing Plaid transactions: {e}")
        import traceback
        traceback.print_exc()
def get_dashboard_stats():
    try:
        user_id = get_jwt_identity()
        print(f"[DEBUG] /api/dashboard/stats called. JWT identity: {user_id}")
        print(f"[DEBUG] Authorization header: {request.headers.get('Authorization')}")

        user = users_collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Date range for the current calendar month (month-to-date)
        now = datetime.now()
        start_date = now.replace(day=1).date()
        end_date = now.date()
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        # For dashboard display, we want to show transactions from a broader range (last 4 months)
        # but still calculate monthly summaries from current month only
        dashboard_start_date = (now - timedelta(days=120)).date()  # 4 months = ~120 days
        dashboard_start_date_str = dashboard_start_date.strftime('%Y-%m-%d')

        # Get user accounts
        user_accounts = list(accounts_collection.find({'user_id': str(user_id)}))
        checking_accounts = [a for a in user_accounts if a.get('subtype') and str(a['subtype']).lower() == 'checking']
        savings_accounts = [a for a in user_accounts if a.get('subtype') and str(a['subtype']).lower() == 'savings']
        
        print(f"[DEBUG] Found {len(user_accounts)} total accounts")
        print(f"[DEBUG] Checking accounts: {[a.get('name', 'Unknown') for a in checking_accounts]}")
        print(f"[DEBUG] Savings accounts: {[a.get('name', 'Unknown') for a in savings_accounts]}")
        
        # If no accounts are properly categorized, try to categorize based on account names
        if not checking_accounts and not savings_accounts:
            for account in user_accounts:
                account_name = account.get('name', '').lower()
                if 'checking' in account_name or 'check' in account_name:
                    checking_accounts.append(account)
                elif 'savings' in account_name or 'save' in account_name:
                    savings_accounts.append(account)
                else:
                    # Default to checking for unknown account types
                    checking_accounts.append(account)

        # Fetch budgets for this user (per category)
        user_budgets = list(budgets_collection.find({'user_id': str(user_id)}))
        budgets_by_category = {b['category']: {'amount': b['amount'], 'period': b.get('period', 'monthly')} for b in user_budgets}

        def get_account_stats(accounts, include_budgets=False):
            account_ids = [str(a['_id']) for a in accounts]

            # Build transaction query for these accounts
            txn_query = {'user_id': str(user_id)}
            if account_ids:
                txn_query['account_id'] = {'$in': account_ids}
            
            # Add sample data filter if user has sample data
            if user.get('has_sample_data', False):
                txn_query['is_sample'] = True
                print(f"[DEBUG] Filtering for sample transactions only")
            else:
                txn_query['is_sample'] = {'$ne': True}  # Exclude sample data for real users
                print(f"[DEBUG] Filtering for real transactions only")

            # Get all transactions for these accounts from the last 60 days for dashboard display
            all_transactions = list(transactions_collection.find({
                **txn_query,
                'date': {'$gte': dashboard_start_date_str}
            }))
            print(f"[DEBUG] Found {len(all_transactions)} total transactions for account type (last 60 days)")
            print(f"[DEBUG] Account IDs: {account_ids}")
            print(f"[DEBUG] Dashboard date range: {dashboard_start_date_str} to {end_date_str}")
            
            # Filter transactions to current calendar month (month-to-date) for summary calculations
            monthly_transactions = [t for t in all_transactions if start_date_str <= t.get('date', '') <= end_date_str]
            print(f"[DEBUG] Found {len(all_transactions)} total transactions, {len(monthly_transactions)} this month")
            
            # Debug: Show first few transaction dates
            for i, t in enumerate(all_transactions[:3]):
                print(f"[DEBUG] Transaction {i}: {t.get('name', 'Unknown')} - {t.get('date', 'No date')} - Account: {t.get('account_id', 'No account')}")

            # Use all_transactions for the transactions list (frontend will filter as needed)
            transactions = all_transactions

            # Totals for month-to-date - properly handle income vs expenses (EXCLUDE BLOCKED TRANSACTIONS)
            total_spent = sum(t['amount'] for t in monthly_transactions if t.get('is_expense', True) and not t.get('blocked', False))
            total_income = sum(t['amount'] for t in monthly_transactions if not t.get('is_expense', True) and not t.get('blocked', False))

            monthly_income = total_income
            monthly_expenses = total_spent
            monthly_net_income = monthly_income - monthly_expenses

            # Category totals for month-to-date (absolute amounts) - EXCLUDE BLOCKED TRANSACTIONS
            category_totals = {}
            for t in monthly_transactions:
                if not t.get('blocked', False):  # Skip blocked transactions
                    cat = t.get('category') or 'Uncategorized'
                    category_totals[cat] = category_totals.get(cat, 0) + abs(t['amount'])

            # Get fraud alerts from the fraudulent_transactions collection
            fraud_alerts_query = {'user_id': user_id}
            if user.get('has_sample_data', False):
                fraud_alerts_query['is_sample'] = True
            else:
                fraud_alerts_query['is_sample'] = {'$ne': True}
            
            fraud_alerts = list(fraudulent_transactions_collection.find(fraud_alerts_query).sort('detected_at', -1))
            
            # Get real-time anomaly detection summary
            try:
                raw_anomaly_summary = anomaly_detector.get_anomaly_summary(user_id, 'real' if not user.get('has_sample_data', False) else 'sample')
                # Convert to JSON-safe format
                if raw_anomaly_summary:
                    anomaly_summary = {
                        'total_anomalies': raw_anomaly_summary.get('total_anomalies', 0),
                        'high_severity': raw_anomaly_summary.get('high_severity', 0),
                        'medium_severity': raw_anomaly_summary.get('medium_severity', 0),
                        'low_severity': raw_anomaly_summary.get('low_severity', 0),
                        'risk_level': raw_anomaly_summary.get('risk_level', 'low'),
                        'recent_anomalies': []
                    }
             
                    if 'fraudulent_transactions' in raw_anomaly_summary:
                        for tx in raw_anomaly_summary['fraudulent_transactions']:
                            anomaly_summary['recent_anomalies'].append({
                                'id': str(tx.get('_id', '')),
                                'amount': tx.get('amount', 0),
                                'name': tx.get('name', ''),
                                'date': tx.get('date', ''),
                                'severity': tx.get('severity', 'medium'),
                                'reasons': tx.get('reasons', []),
                                'merchant_name': tx.get('merchant_name', ''),
                                'category': tx.get('category', ''),
                                'blocked': tx.get('blocked', True),
                                'threat_level': tx.get('threat_level', 'medium'),
                                'anomaly_score': tx.get('anomaly_score', 0.8)
                            })
                else:
                    anomaly_summary = {
                        'total_anomalies': len(fraud_alerts),
                        'high_severity': len([t for t in fraud_alerts if t.get('anomaly_severity') == 'high']),
                        'medium_severity': len([t for t in fraud_alerts if t.get('anomaly_severity') == 'medium']),
                        'low_severity': len([t for t in fraud_alerts if t.get('anomaly_severity') == 'low']),
                        'risk_level': 'high' if len(fraud_alerts) > 0 else 'low',
                        'recent_anomalies': []
                    }
                    
                    # Add blocked transactions to recent anomalies
                    for tx in fraud_alerts[:5]:  # Show up to 5 most recent
                        anomaly_summary['recent_anomalies'].append({
                            'id': str(tx.get('_id', '')),
                            'amount': tx.get('amount', 0),
                            'name': tx.get('name', ''),
                            'date': tx.get('date', ''),
                            'severity': tx.get('anomaly_severity', 'medium'),
                            'reasons': tx.get('anomaly_reasons', []),
                            'merchant_name': tx.get('merchant_name', ''),
                            'category': tx.get('category', ''),
                            'blocked': True,
                            'threat_level': tx.get('threat_level', 'medium'),
                            'anomaly_score': tx.get('fraud_score', 0.8)
                        })
            except Exception as e:
                print(f"[DASHBOARD] Error getting anomaly summary: {e}")
                anomaly_summary = {
                    'total_anomalies': len(fraud_alerts),
                    'high_severity': len([t for t in fraud_alerts if t.get('anomaly_severity') == 'high']),
                    'medium_severity': len([t for t in fraud_alerts if t.get('anomaly_severity') == 'medium']),
                    'low_severity': len([t for t in fraud_alerts if t.get('anomaly_severity') == 'low']),
                    'risk_level': 'high' if len(fraud_alerts) > 0 else 'low',
                    'recent_anomalies': []
                }
                
                # Add blocked transactions to recent anomalies
                for tx in fraud_alerts[:5]:  # Show up to 5 most recent
                    anomaly_summary['recent_anomalies'].append({
                        'id': str(tx.get('_id', '')),
                        'amount': tx.get('amount', 0),
                        'name': tx.get('name', ''),
                        'date': tx.get('date', ''),
                        'severity': tx.get('anomaly_severity', 'medium'),
                        'reasons': tx.get('anomaly_reasons', []),
                        'merchant_name': tx.get('merchant_name', ''),
                        'category': tx.get('category', ''),
                        'blocked': True,
                        'threat_level': tx.get('threat_level', 'medium'),
                        'anomaly_score': tx.get('fraud_score', 0.8)
                    })

            # Calculate realistic current balance from Plaid account balances
            current_balance = sum(a.get('current_balance', 0.0) or 0.0 for a in accounts)
            if current_balance < 1000:
                # Use transaction flows to estimate a more realistic balance (EXCLUDE BLOCKED TRANSACTIONS)
                all_income = sum(t['amount'] for t in all_transactions if not t.get('is_expense', True) and not t.get('blocked', False))
                all_spent = sum(t['amount'] for t in all_transactions if t.get('is_expense', True) and not t.get('blocked', False))
                total_flow = all_income - all_spent
                total_spending = all_spent
                estimated_starting_balance = max(10000, total_spending + 2000)
                current_balance = estimated_starting_balance + total_flow

            # Add budget warnings and colors
            budget_warnings = {}
            if include_budgets:
                for category, amount in category_totals.items():
                    if category in budgets_by_category:
                        budget_amount = budgets_by_category[category]['amount'] or 0.0
                        spent_percentage = (amount / budget_amount) * 100 if budget_amount > 0 else 0
                        if spent_percentage > 100:
                            budget_warnings[category] = {
                                'status': 'exceeded',
                                'color': 'red',
                                'message': f'Exceeded budget by ${amount - budget_amount:.2f}',
                                'percentage': spent_percentage
                            }
                        elif spent_percentage > 80:
                            budget_warnings[category] = {
                                'status': 'warning',
                                'color': 'yellow',
                                'message': f'Close to budget limit (${budget_amount - amount:.2f} remaining)',
                                'percentage': spent_percentage
                            }
                        else:
                            budget_warnings[category] = {
                                'status': 'good',
                                'color': 'green',
                                'message': f'${budget_amount - amount:.2f} remaining',
                                'percentage': spent_percentage
                            }

            result = {
                'accounts': [{'id': str(a['_id']), 'name': a['name'], 'current_balance': a.get('current_balance', 0.0)} for a in accounts],
                'total_spent': total_spent,
                'total_income': total_income,
                'monthly_income': monthly_income,
                'monthly_expenses': monthly_expenses,
                'monthly_net_income': monthly_net_income,  # Fixed: show actual net income (income - expenses)
                'net_flow': total_income - total_spent,
                'category_breakdown': category_totals,
                'budget_warnings': budget_warnings,
                'fraud_alerts_count': len(fraud_alerts),
                'fraud_alerts': [{
                    'id': str(t['_id']),
                    'amount': t['amount'],
                    'name': t.get('name', ''),
                    'date': t.get('date', ''),
                    'fraud_score': t.get('anomaly_score', 0.9),
                    'anomaly_severity': t.get('severity', 'medium'),
                    'threat_level': t.get('threat_level', 'medium'),
                    'anomaly_reasons': t.get('reasons', []),
                    'blocked': t.get('blocked', True),
                    'merchant_name': t.get('merchant_name', ''),
                    'category': t.get('category', ''),
                    'description': t.get('description', ''),
                    'detected_at': t.get('detected_at', '')
                } for t in fraud_alerts[:10]],  # Show up to 10 most recent
                'anomaly_summary': anomaly_summary,
                'current_balance': current_balance,
                'transactions': [{
                    'id': str(t['_id']),
                    'amount': t['amount'],
                    'name': t.get('name', ''),
                    'date': t.get('date', ''),
                    'category': t.get('category', ''),
                    'merchant_name': t.get('merchant_name', ''),
                    'fraud_score': t.get('fraud_score'),
                    'is_fraudulent': t.get('is_fraudulent', False),
                    'pending': t.get('pending', False),
                    'is_expense': t.get('is_expense', True),
                    'transaction_type': t.get('transaction_type', 'spending')
                } for t in sorted(transactions, key=lambda x: x.get('date', ''), reverse=True)]
            }

            if include_budgets:
                result['budgets'] = {cat: budgets_by_category.get(cat) for cat in category_totals.keys()}

            return result

        return jsonify({
            'user': {
                'firstName': user.get('first_name', ''),
                'lastName': user.get('last_name', '')
            },
            'checking': get_account_stats(checking_accounts, include_budgets=True),
            'savings': get_account_stats(savings_accounts)
        })
    except Exception as e:
        import traceback
        print('Error in /api/dashboard/stats:', e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 422

# Dashboard stats endpoint
@app.route('/api/dashboard/stats', methods=['GET'])
@jwt_required()
def dashboard_stats():
    return get_dashboard_stats()

# Machine Learning - Category Prediction
def predict_transaction_category(transaction):
    """
    Predict category for a transaction using the trained model
    """
    try:
        # Use the existing category if available
        if transaction.category and len(transaction.category) > 0:
            return transaction.category[0]
        
        # Predict category using the model
        predicted_category = predict_category(transaction.name, transaction.amount)
        return predicted_category
    except Exception as e:
        print(f"[CATEGORY] Error predicting category: {e}")
        return "Other"  # Default fallback

def classify_transaction_type(transaction):
    """
    Intelligently classify if a transaction is income or spending
    """
    name = transaction.name.lower()
    amount = transaction.amount
    
    # Income indicators - be more specific
    income_keywords = [
        'interest', 'intrst', 'refund', 'deposit', 'salary', 'payroll', 
        'dividend', 'cashback', 'reward', 'bonus', 'reimbursement'
    ]
    
    # Spending indicators - be more specific  
    spending_keywords = [
        'purchase', 'charge', 'debit', 'withdrawal', 'atm', 'fee', 'service',
        'airlines', 'uber', 'mcdonald', 'starbucks', 'sparkfun'
    ]
    
    # Check for specific income patterns
    if 'intrst' in name or 'interest' in name:
        return 'income'
    
    # Check for specific spending patterns
    if any(keyword in name for keyword in spending_keywords):
        return 'spending'
    
    # Check for common spending patterns
    if 'united airlines' in name.lower():
        return 'spending'  # Airline tickets are spending
    if 'uber' in name.lower():
        return 'spending'  # Uber rides are spending
    if 'mcdonald' in name.lower() or 'starbucks' in name.lower():
        return 'spending'  # Food is spending
    if 'sparkfun' in name.lower():
        return 'spending'  # Electronics purchase is spending
    
    # Check for credit card payments (these are spending, not income!)
    if 'credit card' in name.lower() and 'payment' in name.lower():
        return 'spending'
    
    # Default based on amount sign (Plaid convention)
    # But we'll override this for common patterns
    if amount > 0:
        return 'income'
    else:
        return 'spending'

def normalize_transaction_amount(transaction):
    """
    Normalize transaction amount based on transaction type
    Returns: (normalized_amount, transaction_type, is_expense)
    """
    transaction_type = classify_transaction_type(transaction)
    original_amount = transaction.amount
    
    if transaction_type == 'income':
        # Income should always be positive
        if original_amount < 0:
            # Fix: Convert negative income to positive
            normalized_amount = abs(original_amount)
            is_expense = False
        else:
            normalized_amount = original_amount
            is_expense = False
    else:  # spending
        # Spending should always be positive for display
        normalized_amount = abs(original_amount)
        is_expense = True
    
    return normalized_amount, transaction_type, is_expense

# Machine Learning - Fraud Detection
def calculate_fraud_score(transaction, user):
    """
    Calculate fraud score for a transaction using machine learning
    This is a simplified version - in production, you'd use more sophisticated models
    Handles both object and dictionary transaction formats
    """
    # Get user's transaction history for context
    user_transactions = list(transactions_collection.find({'user_id': str(user['_id'])}))
    
    if len(user_transactions) < 10:  # Need minimum transactions for analysis
        return 0.1  # Low risk for new users
    
    # Handle both object and dictionary formats
    if isinstance(transaction, dict):
        amount = abs(transaction['amount'])
        merchant_name = transaction.get('merchant_name', '')
        category = transaction.get('category', '')
        transaction_date_str = transaction.get('date', '')
    else:
        amount = abs(transaction.amount)
        merchant_name = getattr(transaction, 'merchant_name', '')
        category = getattr(transaction, 'category', '')
        transaction_date_str = getattr(transaction, 'date', '')
    
    # Create features for the transaction
    features = []
    
    # Amount-based features
    avg_amount = np.mean([abs(t['amount']) for t in user_transactions])
    amount_ratio = amount / avg_amount if avg_amount > 0 else 1
    
    # Time-based features
    # transaction_date_str may be a string or a date object
    if isinstance(transaction_date_str, str):
        transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
    else:
        transaction_date = transaction_date_str
    
    recent_transactions = [t for t in user_transactions if (transaction_date - datetime.strptime(t['date'], '%Y-%m-%d').date()).days <= 7]
    
    # Location-based features (simplified)
    is_new_merchant = not any(t.get('merchant_name') == merchant_name for t in user_transactions)
    
    # Category-based features
    category_transactions = [t for t in user_transactions if t.get('category') == category]
    category_frequency = len(category_transactions) / len(user_transactions) if user_transactions else 0
    
    # Combine features
    features = [
        amount_ratio,
        len(recent_transactions),
        is_new_merchant,
        category_frequency,
        amount / 1000  # Normalize amount
    ]
    
    # Simple anomaly detection using Isolation Forest
    if len(user_transactions) >= 10:
        # Prepare training data
        training_data = []
        for t in user_transactions:
            t_amount_ratio = abs(t['amount']) / avg_amount if avg_amount > 0 else 1
            t_is_new_merchant = not any(ot.get('merchant_name') == t.get('merchant_name') for ot in user_transactions if str(ot['_id']) != str(t['_id']))
            t_category_freq = len([ct for ct in user_transactions if ct.get('category') == t.get('category')]) / len(user_transactions)
            
            training_data.append([
                t_amount_ratio,
                len([rt for rt in user_transactions if (transaction_date - datetime.strptime(rt['date'], '%Y-%m-%d').date()).days <= 7]),
                t_is_new_merchant,
                t_category_freq,
                abs(t['amount']) / 1000
            ])
        
        # Train isolation forest
        clf = IsolationForest(contamination=0.1, random_state=42)
        clf.fit(training_data)
        
        # Predict anomaly score
        score = clf.decision_function([features])[0]
        # Convert to 0-1 scale where 1 is most anomalous
        fraud_score = 1 - (score + 0.5)  # Normalize to 0-1
    else:
        # Simple heuristic for new users
        fraud_score = 0.1
        if amount_ratio > 5:  # Very large transaction
            fraud_score += 0.3
        if is_new_merchant:
            fraud_score += 0.2
        if amount > 1000:  # High amount
            fraud_score += 0.2
    
    return min(fraud_score, 1.0)  # Cap at 1.0

# Balance over time endpoint
@app.route('/api/accounts/balance-history', methods=['GET'])
@jwt_required()
def get_balance_history():
    """
    Returns running balance over time for each account and total, based on latest Plaid balance and transactions.
    """
    user_id = get_jwt_identity()
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user_accounts = list(accounts_collection.find({'user_id': str(user_id)}))
    result = []
    total_balance_by_date = {}

    for account in user_accounts:
        # Get all transactions for this account, sorted by date descending
        txns = list(transactions_collection.find({'account_id': str(account['_id'])}).sort('date', -1))
        # Start from the latest known balance
        running_balance = account.get('current_balance', 0.0) or 0.0
        history = []
        last_date = None
        
        for txn in txns:
            # Record balance at this date (after this transaction)
            history.append({
                'date': txn['date'],
                'balance': running_balance
            })
            # Fix: Plaid uses negative for spending, positive for income
            # So we need to reverse the sign for balance calculation
            if txn['amount'] < 0:  # Spending (negative in Plaid)
                running_balance += abs(txn['amount'])  # Add back to balance
            else:  # Income (positive in Plaid)
                running_balance -= txn['amount']  # Subtract from balance
            last_date = datetime.strptime(txn['date'], '%Y-%m-%d').date()
        
        # Optionally, add the oldest balance (after all txns)
        if last_date:
            history.append({
                'date': (last_date - timedelta(days=1)).strftime('%Y-%m-%d'),
                'balance': running_balance
            })
        
        # Reverse to chronological order
        history = list(reversed(history))
        # Add to result
        result.append({
            'account_id': str(account['_id']),
            'account_name': account['name'],
            'history': history
        })
        
        # Merge into total_balance_by_date
        for point in history:
            d = point['date']
            total_balance_by_date.setdefault(d, 0.0)
            total_balance_by_date[d] += point['balance']

    # Build total balance history (by date, sorted)
    total_history = [
        {'date': d, 'balance': total_balance_by_date[d]}
        for d in sorted(total_balance_by_date.keys())
    ]

    return jsonify({
        'accounts': result,
        'total': total_history
    })

# Budget management
@app.route('/api/budgets', methods=['GET'])
@jwt_required()
def get_budgets():
    user_id = get_jwt_identity()
    budgets = list(budgets_collection.find({'user_id': str(user_id)}))
    
    return jsonify([{
        'id': str(b['_id']),
        'category': b['category'],
        'amount': b['amount'],
        'period': b['period']
    } for b in budgets])

@app.route('/api/budgets', methods=['POST'])
@jwt_required()
def create_budget():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    budget_doc = {
        'user_id': str(user_id),
        'category': data['category'],
        'amount': data['amount'],
        'period': 'monthly',  # Force monthly budgets
        'created_at': datetime.utcnow()
    }
    
    result = budgets_collection.insert_one(budget_doc)
    
    return jsonify({
        'id': str(result.inserted_id),
        'category': data['category'],
        'amount': data['amount'],
        'period': 'monthly'
    }), 201

@app.route('/api/budgets/<budget_id>', methods=['PUT'])
@jwt_required()
def update_budget(budget_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    
    # Check if budget exists and belongs to user
    budget = budgets_collection.find_one({
        '_id': ObjectId(budget_id),
        'user_id': str(user_id)
    })
    
    if not budget:
        return jsonify({'error': 'Budget not found'}), 404
    
    # Update budget
    budgets_collection.update_one(
        {'_id': ObjectId(budget_id)},
        {
            '$set': {
                'category': data['category'],
                'amount': data['amount'],
                'period': 'monthly',  # Force monthly budgets
                'updated_at': datetime.utcnow()
            }
        }
    )
    
    return jsonify({
        'id': budget_id,
        'category': data['category'],
        'amount': data['amount'],
        'period': 'monthly'
    }), 200

@app.route('/api/budgets/<budget_id>', methods=['DELETE'])
@jwt_required()
def delete_budget(budget_id):
    user_id = get_jwt_identity()
    
    # Check if budget exists and belongs to user
    budget = budgets_collection.find_one({
        '_id': ObjectId(budget_id),
        'user_id': str(user_id)
    })
    
    if not budget:
        return jsonify({'error': 'Budget not found'}), 404
    
    # Delete budget
    budgets_collection.delete_one({'_id': ObjectId(budget_id)})
    
    return jsonify({'message': 'Budget deleted successfully'}), 200

# Utility: Generate a lot of Plaid sandbox transactions for ML training
@app.route('/api/plaid/sandbox/generate-transactions', methods=['POST'])
@jwt_required()
def generate_sandbox_transactions():
    """
    For all linked Plaid accounts for the current user, fire the sandbox webhook multiple times to generate a large number of transactions, then sync.
    """
    user_id = get_jwt_identity()
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    count = 0
    user_accounts = list(accounts_collection.find({'user_id': str(user_id)}))
    
    print(f"[SANDBOX] Generating transactions for {len(user_accounts)} accounts")
    
    for account in user_accounts:
        access_token = account['plaid_access_token']
        print(f"[SANDBOX] Processing account: {account['name']}")
        
        # Fire the webhook multiple times to generate more transactions
        for i in range(25):  # 25x = 2500+ transactions in sandbox
            try:
                req = SandboxItemFireWebhookRequest(
                    access_token=access_token,
                    webhook_code='DEFAULT_UPDATE'
                )
                plaid_api.sandbox_item_fire_webhook(req)
                count += 1
                if (i + 1) % 5 == 0:
                    print(f"[SANDBOX] Fired {i+1}/25 webhooks for account {account['name']}")
            except Exception as e:
                print(f"[SANDBOX] Error firing webhook {i+1} for account {account['name']}: {e}")
        
        # Wait a moment for Plaid to process
        import time
        time.sleep(3)
    
    print(f"[SANDBOX] Total webhooks fired: {count}")
    
    # After firing, sync transactions
    try:
        print(f"[SANDBOX] Starting transaction sync for user {user_id}")
        # Reuse the sync_transactions logic
        with app.test_request_context():
            resp = sync_transactions()
        return jsonify({'message': f'Fired {count} webhooks and synced transactions for all accounts.'})
    except Exception as e:
        print(f"[SANDBOX] Error during sync: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounts', methods=['GET'])
@jwt_required()
def get_accounts():
    print('[DEBUG] /api/accounts endpoint called')
    user_id = get_jwt_identity()
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        print('[DEBUG] User not found for /api/accounts')
        return jsonify({'error': 'User not found'}), 404
    
    user_accounts = list(accounts_collection.find({'user_id': str(user_id)}))
    result = []
    
    for account in user_accounts:
        result.append({
            'id': str(account['_id']),
            'name': account['name'],
            'type': account.get('type', account.get('subtype', '')),
            'subtype': account.get('subtype', account.get('type', '')),
            'mask': account.get('mask', ''),
            'institution_name': account.get('institution_name', ''),
            'current_balance': account.get('current_balance', 0.0),
            'available_balance': account.get('available_balance', 0.0),
            'last_updated': account.get('last_updated', '').strftime('%Y-%m-%d %H:%M:%S') if account.get('last_updated') else None
        })
    
    print(f'[DEBUG] Returning {len(result)} accounts for user {user_id}')
    return jsonify(result)

print('[DEBUG] /api/accounts endpoint registered')

# Transactions endpoint
@app.route('/api/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    """Get transactions for the current user with search and pagination"""
    try:
        user_id = get_jwt_identity()
        per_page = request.args.get('per_page', 50, type=int)
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '').strip()
        category_filter = request.args.get('category', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        
        # Get user accounts
        user_accounts = list(accounts_collection.find({'user_id': str(user_id)}))
        account_ids = [str(a['_id']) for a in user_accounts]
        
        # Build query
        query = {'user_id': str(user_id)}
        if account_ids:
            query['account_id'] = {'$in': account_ids}
        
        # Add search filter
        if search:
            query['$or'] = [
                {'name': {'$regex': search, '$options': 'i'}},
                {'merchant_name': {'$regex': search, '$options': 'i'}},
                {'category': {'$regex': search, '$options': 'i'}}
            ]
        
        # Add category filter
        if category_filter:
            query['category'] = {'$regex': category_filter, '$options': 'i'}
        
        # Add date range filter
        if date_from or date_to:
            date_query = {}
            if date_from:
                date_query['$gte'] = date_from
            if date_to:
                date_query['$lte'] = date_to
            query['date'] = date_query
        
        # Get transactions with pagination
        skip = (page - 1) * per_page
        transactions = list(transactions_collection.find(query).sort('date', -1).skip(skip).limit(per_page))
        
        # Count total transactions
        total_count = transactions_collection.count_documents(query)
        
        return jsonify({
            'transactions': [{
                'id': str(t['_id']),
                'amount': t['amount'],
                'name': t.get('name', ''),
                'date': t.get('date', ''),
                'category': t.get('category', ''),
                'merchant_name': t.get('merchant_name', ''),
                'fraud_score': t.get('fraud_score'),
                'is_fraudulent': t.get('is_fraudulent', False),
                'pending': t.get('pending', False),
                'is_expense': t.get('is_expense', True),
                'transaction_type': t.get('transaction_type', 'spending')
            } for t in transactions],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        print(f"[TRANSACTIONS] Error: {e}")
        return jsonify({'error': 'Failed to fetch transactions'}), 500

# Manual trigger for transaction generation (for testing)
@app.route('/api/plaid/generate-now', methods=['POST'])
@jwt_required()
def generate_transactions_now():
    """Manual endpoint to generate transactions immediately"""
    try:
        result = generate_sandbox_transactions()
        return jsonify({'message': 'Transaction generation triggered successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Generate sample transactions for testing
@app.route('/api/generate-sample-transactions', methods=['POST'])
@jwt_required()
def generate_sample_transactions_endpoint():
    """Generate sample transactions for the current user"""
    try:
        user_id = get_jwt_identity()
        
        # Get user's checking account
        checking_account = accounts_collection.find_one({
            'user_id': str(user_id),
            'subtype': 'checking'
        })
        
        if not checking_account:
            return jsonify({'error': 'No checking account found'}), 404
        
        # Generate sample transactions
        generate_sample_transactions(user_id, checking_account['_id'])
        
        return jsonify({'message': 'Sample transactions generated successfully'})
    except Exception as e:
        print(f"[SAMPLE] Error: {e}")
        return jsonify({'error': str(e)}), 500

# Manual transaction entry system
@app.route('/api/transactions/manual', methods=['POST'])
@jwt_required()
def add_manual_transaction():
    """Add a manual transaction entry"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'amount', 'category', 'date', 'transaction_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Get user's checking account
        checking_account = accounts_collection.find_one({
            'user_id': str(user_id),
            'subtype': 'checking'
        })
        
        if not checking_account:
            return jsonify({'error': 'No checking account found'}), 404
        
        # Determine if it's an expense based on transaction type
        is_expense = data['transaction_type'].lower() in ['spending', 'expense', 'payment']
        
        # Create transaction document
        transaction_doc = {
            'user_id': str(user_id),
            'account_id': str(checking_account['_id']),
            'plaid_transaction_id': f'manual_{datetime.now().timestamp()}_{data["name"]}',
            'amount': float(data['amount']),
            'date': data['date'],
            'name': data['name'],
            'merchant_name': data.get('merchant_name', data['name']),
            'category': data['category'],
            'pending': False,
            'fraud_score': 0.1,
            'is_fraudulent': False,
            'is_expense': is_expense,
            'transaction_type': data['transaction_type'],
            'is_manual': True,
            'created_at': datetime.utcnow()
        }
        
        result = transactions_collection.insert_one(transaction_doc)
        
        return jsonify({
            'message': 'Transaction added successfully',
            'transaction_id': str(result.inserted_id)
        }), 201
        
    except Exception as e:
        print(f"[MANUAL_TRANSACTION] Error: {e}")
        return jsonify({'error': 'Failed to add transaction'}), 500

# Get transaction categories for manual entry
@app.route('/api/transactions/categories', methods=['GET'])
@jwt_required()
def get_transaction_categories():
    """Get available transaction categories"""
    categories = [
        'Income',
        'Food & Dining',
        'Transportation',
        'Entertainment',
        'Shopping',
        'Utilities',
        'Healthcare',
        'Education',
        'Travel',
        'Insurance',
        'Investments',
        'Gifts',
        'Charity',
        'Other'
    ]
    return jsonify({'categories': categories})

# Generate more sandbox transactions using reset
@app.route('/api/plaid/generate-more', methods=['POST'])
@jwt_required()
def generate_more_transactions():
    """Generate more transactions by resetting sandbox and syncing"""
    try:
        user_id = get_jwt_identity()
        print(f"[GENERATE] Generating more transactions for user {user_id}")
        
        # Get user accounts
        user_accounts = list(accounts_collection.find({'user_id': str(user_id)}))
        print(f"[GENERATE] Found {len(user_accounts)} accounts for user {user_id}")
        
        total_new = 0
        
        for account in user_accounts:
            try:
                print(f"[GENERATE] Processing account: {account['name']}")
                
                # Use sandbox reset to generate new transactions
                # This will create a fresh set of transactions
                import time
                time.sleep(1)  # Small delay between accounts
                
                # Sync transactions after reset
                request_obj = TransactionsSyncRequest(
                    access_token=account['plaid_access_token'],
                    options={
                        'include_personal_finance_category': True
                    }
                )
                response = plaid_api.transactions_sync(request_obj)
                print(f"[GENERATE] Plaid returned {len(response.added)} new transactions for {account['name']}")
                
                for transaction in response.added:
                    # Check if transaction already exists
                    existing_transaction = transactions_collection.find_one({
                        'plaid_transaction_id': transaction.transaction_id
                    })
                    
                    if not existing_transaction:
                        # Calculate fraud score and predict category
                        fraud_score = calculate_fraud_score(transaction, {'_id': ObjectId(user_id)})
                        predicted_category = predict_transaction_category(transaction)
                        
                        new_transaction = {
                            'user_id': str(user_id),
                            'account_id': str(account['_id']),
                            'plaid_transaction_id': transaction.transaction_id,
                            'amount': transaction.amount,
                            'date': transaction.date.strftime('%Y-%m-%d') if hasattr(transaction.date, 'strftime') else str(transaction.date),
                            'name': transaction.name,
                            'merchant_name': transaction.merchant_name,
                            'category': predicted_category,
                            'category_id': transaction.category_id,
                            'pending': transaction.pending,
                            'fraud_score': float(fraud_score),
                            'is_fraudulent': bool(fraud_score > 0.7),
                            'created_at': datetime.utcnow()
                        }
                        transactions_collection.insert_one(new_transaction)
                        total_new += 1
                
            except Exception as e:
                print(f"[GENERATE] Error processing account {account['name']}: {e}")
        
        print(f"[GENERATE] Total new transactions generated: {total_new}")
        return jsonify({
            'message': f'Generated {total_new} new transactions',
            'transactions_count': total_new
        })
        
    except Exception as e:
        print(f"[GENERATE] Error during transaction generation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Simple endpoint to sync existing transactions
@app.route('/api/plaid/sync-now', methods=['POST'])
@jwt_required()
def sync_transactions_now():
    """Manual endpoint to sync existing transactions"""
    try:
        user_id = get_jwt_identity()
        print(f"[SYNC] Manual sync triggered for user {user_id}")
        
        # Get user accounts
        user_accounts = list(accounts_collection.find({'user_id': str(user_id)}))
        print(f"[SYNC] Found {len(user_accounts)} accounts for user {user_id}")
        
        all_transactions = []
        for account in user_accounts:
            try:
                print(f"[SYNC] Syncing account: {account['name']}")
                # Get transactions from Plaid
                request_obj = TransactionsSyncRequest(
                    access_token=account['plaid_access_token'],
                    options={
                        'include_personal_finance_category': True
                    }
                )
                response = plaid_api.transactions_sync(request_obj)
                print(f"[SYNC] Plaid returned {len(response.added)} new transactions for {account['name']}")
                
                for transaction in response.added:
                    # Check if transaction already exists
                    existing_transaction = transactions_collection.find_one({
                        'plaid_transaction_id': transaction.transaction_id
                    })
                    
                    if not existing_transaction:
                        # Calculate fraud score and predict category
                        fraud_score = calculate_fraud_score(transaction, {'_id': ObjectId(user_id)})
                        predicted_category = predict_transaction_category(transaction)
                        
                        new_transaction = {
                            'user_id': str(user_id),
                            'account_id': str(account['_id']),
                            'plaid_transaction_id': transaction.transaction_id,
                            'amount': transaction.amount,
                            'date': transaction.date.strftime('%Y-%m-%d') if hasattr(transaction.date, 'strftime') else str(transaction.date),
                            'name': transaction.name,
                            'merchant_name': transaction.merchant_name,
                            'category': predicted_category,
                            'category_id': transaction.category_id,
                            'pending': transaction.pending,
                            'fraud_score': float(fraud_score),  # Convert numpy to Python float
                            'is_fraudulent': bool(fraud_score > 0.7),  # Convert numpy to Python bool
                            'created_at': datetime.utcnow()
                        }
                        transactions_collection.insert_one(new_transaction)
                        all_transactions.append(new_transaction)
                
            except Exception as e:
                print(f"[SYNC] Error syncing account {account['name']}: {e}")
        
        print(f"[SYNC] Total new transactions synced: {len(all_transactions)}")
        return jsonify({
            'message': f'Synced {len(all_transactions)} new transactions',
            'transactions_count': len(all_transactions)
        })
        
    except Exception as e:
        print(f"[SYNC] Error during manual sync: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Add the missing sync_transactions function
def sync_transactions():
    """Sync transactions for all accounts of the current user"""
    try:
        user_id = get_jwt_identity()
        print(f"[SYNC] Syncing transactions for user {user_id}")
        
        # Get user accounts
        user_accounts = list(accounts_collection.find({'user_id': str(user_id)}))
        print(f"[SYNC] Found {len(user_accounts)} accounts for user {user_id}")
        
        all_transactions = []
        for account in user_accounts:
            try:
                print(f"[SYNC] Syncing account: {account['name']}")
                # Get transactions from Plaid
                request_obj = TransactionsSyncRequest(
                    access_token=account['plaid_access_token'],
                    options={
                        'include_personal_finance_category': True
                    }
                )
                response = plaid_api.transactions_sync(request_obj)
                print(f"[SYNC] Plaid returned {len(response.added)} new transactions for {account['name']}")
                
                for transaction in response.added:
                    # Check if transaction already exists
                    existing_transaction = transactions_collection.find_one({
                        'plaid_transaction_id': transaction.transaction_id
                    })
                    
                    if not existing_transaction:
                        # Calculate fraud score and predict category
                        fraud_score = calculate_fraud_score(transaction, {'_id': ObjectId(user_id)})
                        predicted_category = predict_transaction_category(transaction)
                        
                        new_transaction = {
                            'user_id': str(user_id),
                            'account_id': str(account['_id']),
                            'plaid_transaction_id': transaction.transaction_id,
                            'amount': transaction.amount,
                            'date': transaction.date.strftime('%Y-%m-%d') if hasattr(transaction.date, 'strftime') else str(transaction.date),
                            'name': transaction.name,
                            'merchant_name': transaction.merchant_name,
                            'category': predicted_category,
                            'category_id': transaction.category_id,
                            'pending': transaction.pending,
                            'fraud_score': float(fraud_score),  # Convert numpy to Python float
                            'is_fraudulent': bool(fraud_score > 0.7),  # Convert numpy to Python bool
                            'created_at': datetime.utcnow()
                        }
                        transactions_collection.insert_one(new_transaction)
                        all_transactions.append(new_transaction)
                
            except Exception as e:
                print(f"[SYNC] Error syncing account {account['name']}: {e}")
        
        print(f"[SYNC] Total new transactions synced: {len(all_transactions)}")
        return jsonify({
            'message': f'Synced {len(all_transactions)} new transactions',
            'transactions_count': len(all_transactions)
        })
        
    except Exception as e:
        print(f"[SYNC] Error during sync: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Bulk transaction generation for testing
@app.route('/api/plaid/bulk-generate', methods=['POST'])
@jwt_required()
def bulk_generate_transactions():
    """Generate a large number of transactions for testing"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        count = data.get('count', 100)  # Default to 100 transactions
        
        print(f"[BULK] Generating {count} transactions for user {user_id}")
        
        # Get user accounts
        user_accounts = list(accounts_collection.find({'user_id': str(user_id)}))
        if not user_accounts:
            return jsonify({'error': 'No accounts found'}), 404
        
        # Generate transactions in batches
        batch_size = 20
        total_generated = 0
        
        for i in range(0, count, batch_size):
            current_batch = min(batch_size, count - i)
            print(f"[BULK] Processing batch {i//batch_size + 1}, generating {current_batch} transactions")
            
            for account in user_accounts:
                try:
                    # Sync transactions
                    request_obj = TransactionsSyncRequest(
                        access_token=account['plaid_access_token'],
                        options={
                            'include_personal_finance_category': True
                        }
                    )
                    response = plaid_api.transactions_sync(request_obj)
                    
                    for transaction in response.added:
                        # Check if transaction already exists
                        existing_transaction = transactions_collection.find_one({
                            'plaid_transaction_id': transaction.transaction_id
                        })
                        
                        if not existing_transaction:
                            # Calculate fraud score and predict category
                            fraud_score = calculate_fraud_score(transaction, {'_id': ObjectId(user_id)})
                            predicted_category = predict_transaction_category(transaction)
                            
                            new_transaction = {
                                'user_id': str(user_id),
                                'account_id': str(account['_id']),
                                'plaid_transaction_id': transaction.transaction_id,
                                'amount': transaction.amount,
                                'date': transaction.date.strftime('%Y-%m-%d') if hasattr(transaction.date, 'strftime') else str(transaction.date),
                                'name': transaction.name,
                                'merchant_name': transaction.merchant_name,
                                'category': predicted_category,
                                'category_id': transaction.category_id,
                                'pending': transaction.pending,
                                'fraud_score': float(fraud_score),
                                'is_fraudulent': bool(fraud_score > 0.7),
                                'created_at': datetime.utcnow()
                            }
                            transactions_collection.insert_one(new_transaction)
                            total_generated += 1
                            
                            if total_generated >= count:
                                break
                    
                    if total_generated >= count:
                        break
                        
                except Exception as e:
                    print(f"[BULK] Error processing account {account['name']}: {e}")
            
            if total_generated >= count:
                break
            
            # Small delay between batches
            import time
            time.sleep(2)
        
        print(f"[BULK] Total transactions generated: {total_generated}")
        return jsonify({
            'message': f'Generated {total_generated} transactions',
            'transactions_count': total_generated
        })
        
    except Exception as e:
        print(f"[BULK] Error during bulk generation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Generate transactions endpoint for testing
@app.route('/api/generate-transactions', methods=['POST'])
@jwt_required()
def generate_transactions_endpoint():
    """Generate 50 random transactions for current month or last 3 months"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}
        count = data.get('count', 50)  # Default to 50 transactions
        
        print(f"[GENERATE] Generating {count} random transactions for user {user_id}")
        
        # Get user's checking account
        checking_account = accounts_collection.find_one({
            'user_id': str(user_id),
            'subtype': 'checking'
        })
        
        if not checking_account:
            return jsonify({'error': 'No checking account found'}), 404
        
        # Generate random transactions for current month or last 3 months
        transactions = generate_random_transactions(count, user_id, checking_account['_id'])
        
        # Insert transactions into database
        inserted_count = 0
        for tx in transactions:
            # Calculate fraud score
            fraud_score = calculate_fraud_score(tx, {'_id': ObjectId(user_id)})
            tx['fraud_score'] = float(fraud_score)
            tx['is_fraudulent'] = bool(fraud_score > 0.7)
            
            # Insert transaction
            transactions_collection.insert_one(tx)
            inserted_count += 1
        
        print(f"[GENERATE] Successfully inserted {inserted_count} random transactions")
        
        return jsonify({
            'message': f'Generated {inserted_count} random transactions successfully',
            'transactions_count': inserted_count
        })
        
    except Exception as e:
        print(f"[GENERATE] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def generate_random_transactions(count=50, user_id=None, account_id=None):
    """Generate random transactions for current month or last 3 months"""
    import random
    from datetime import datetime, timedelta
    
    # Categories and merchants for random generation
    categories = [
        'Food and Drink', 'Shopping', 'Transportation', 'Entertainment', 
        'Bills and Utilities', 'Healthcare', 'Travel', 'Education', 'Income'
    ]
    
    merchants = [
        'Walmart', 'Target', 'Amazon', 'Starbucks', 'McDonald\'s', 'Uber', 
        'Shell', 'Netflix', 'Spotify', 'Apple Store', 'Best Buy', 'Home Depot',
        'CVS', 'Walgreens', 'Duke Energy', 'Verizon', 'AT&T', 'Comcast',
        'Marriott', 'Delta Airlines', 'Hertz', 'Barnes & Noble', 'Coursera',
        'Employer', 'Client', 'Freelance Project'
    ]
    
    transactions = []
    
    # Generate dates for current month or last 3 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # Last 3 months
    
    for i in range(count):
        # Random date within the range
        random_days = random.randint(0, 90)
        transaction_date = end_date - timedelta(days=random_days)
        
        # Random category and merchant
        category = random.choice(categories)
        merchant = random.choice(merchants)
        
        # Random amount based on category
        if category == 'Income':
            amount = random.uniform(100, 5000)  # Positive for income
        elif category == 'Bills and Utilities':
            amount = -random.uniform(50, 300)  # Negative for bills
        elif category == 'Travel':
            amount = -random.uniform(100, 800)  # Negative for travel
        elif category == 'Healthcare':
            amount = -random.uniform(25, 200)  # Negative for healthcare
        else:
            amount = -random.uniform(10, 150)  # Negative for other spending
        
        # Round to 2 decimal places
        amount = round(amount, 2)
        
        # Generate transaction name
        if category == 'Income':
            transaction_name = f"Salary - {merchant}"
        else:
            transaction_name = f"{merchant} - {category}"
        
        # Create transaction object
        transaction = {
            'user_id': str(user_id),
            'account_id': str(account_id),
            'name': transaction_name,
            'amount': amount,
            'category': category,
            'subcategory': 'general',
            'merchant_name': merchant,
            'date': transaction_date.strftime('%Y-%m-%d'),
            'transaction_type': 'income' if category == 'Income' else 'spending',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        transactions.append(transaction)
    
    return transactions

# Anomaly Detection Endpoints

@app.route('/api/anomaly/detect', methods=['GET'])
@jwt_required()
def detect_anomalies():
    """Detect anomalies in user's transactions"""
    try:
        user_id = get_jwt_identity()
        limit = request.args.get('limit', 100, type=int)
        
        # Get user to determine data type
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Determine data type based on user's sample data status
        data_type = 'sample' if user.get('has_sample_data', False) else 'real'
        
        # Detect anomalies with correct data type
        anomalies = anomaly_detector.detect_anomalies(user_id, limit, data_type)
        
        return jsonify({
            'anomalies': anomalies,
            'count': len(anomalies),
            'data_type': data_type
        }), 200
        
    except Exception as e:
        print(f"Error detecting anomalies: {e}")
        return jsonify({'error': 'Failed to detect anomalies'}), 500

# Removed manual training endpoint - model is now auto-trained

@app.route('/api/anomaly/summary', methods=['GET'])
@jwt_required()
def get_anomaly_summary():
    """Get anomaly summary for the user"""
    try:
        user_id = get_jwt_identity()
        
        # Get user to determine data type
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Determine data type based on user's sample data status
        data_type = 'sample' if user.get('has_sample_data', False) else 'real'
        
        # Get anomaly summary with correct data type
        raw_summary = anomaly_detector.get_anomaly_summary(user_id, data_type)
        
        # Convert to JSON-safe format
        if raw_summary:
            summary = {
                'total_anomalies': raw_summary.get('total_anomalies', 0),
                'high_severity': raw_summary.get('high_severity', 0),
                'medium_severity': raw_summary.get('medium_severity', 0),
                'low_severity': raw_summary.get('low_severity', 0),
                'risk_level': raw_summary.get('risk_level', 'low'),
                'recent_anomalies': []
            }
            # Convert fraudulent transactions to JSON-safe format
            if 'fraudulent_transactions' in raw_summary:
                summary['fraudulent_transactions'] = []
                for tx in raw_summary['fraudulent_transactions']:
                    summary['fraudulent_transactions'].append({
                        'id': str(tx.get('_id', '')),
                        'amount': tx.get('amount', 0),
                        'name': tx.get('name', ''),
                        'date': tx.get('date', ''),
                        'severity': tx.get('severity', 'medium'),
                        'reasons': tx.get('reasons', []),
                        'merchant_name': tx.get('merchant_name', ''),
                        'category': tx.get('category', ''),
                        'threat_level': tx.get('threat_level', 'medium'),
                        'anomaly_reasons': tx.get('reasons', []),
                        'detected_at': tx.get('detected_at', ''),
                        'blocked': True
                    })
        else:
            summary = {
                'total_anomalies': 0,
                'high_severity': 0,
                'medium_severity': 0,
                'low_severity': 0,
                'risk_level': 'low',
                'recent_anomalies': [],
                'fraudulent_transactions': []
            }
        
        return jsonify(summary), 200
        
    except Exception as e:
        print(f"Error getting anomaly summary: {e}")
        return jsonify({'error': 'Failed to get anomaly summary'}), 500

@app.route('/api/anomaly/mark-fraudulent', methods=['POST'])
@jwt_required()
def mark_transaction_fraudulent():
    """Mark a transaction as fraudulent or legitimate"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        transaction_id = data.get('transaction_id')
        is_fraudulent = data.get('is_fraudulent', True)
        
        if not transaction_id:
            return jsonify({'error': 'Transaction ID is required'}), 400
        
        # Mark transaction as fraudulent
        success = anomaly_detector.mark_transaction_as_fraudulent(transaction_id, is_fraudulent)
        
        if success:
            return jsonify({
                'message': f'Transaction marked as {"fraudulent" if is_fraudulent else "legitimate"}',
                'status': 'success'
            }), 200
        else:
            return jsonify({
                'message': 'Failed to mark transaction',
                'status': 'error'
            }), 500
            
    except Exception as e:
        print(f"Error marking transaction: {e}")
        return jsonify({'error': 'Failed to mark transaction'}), 500

@app.route('/api/anomaly/clear-fraudulent', methods=['POST'])
@jwt_required()
def clear_fraudulent_transactions():
    """Clear all fraudulent transactions for the user"""
    try:
        user_id = get_jwt_identity()
        
        # Get user to determine data type
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Determine data type based on user's sample data status
        data_type = 'sample' if user.get('has_sample_data', False) else 'real'
        
        # Clear fraudulent transactions
        success = anomaly_detector.clear_fraudulent_transactions(user_id, data_type)
        
        return jsonify({
            'message': 'Cleared fraudulent transaction flags',
            'status': 'success'
        }), 200
        
    except Exception as e:
        print(f"Error clearing fraudulent transactions: {e}")
        return jsonify({'error': 'Failed to clear fraudulent transactions'}), 500

if __name__ == '__main__':
    # No db.create_all() needed for MongoDB
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)