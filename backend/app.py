from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
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
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
import os
import pyodbc
from azure.identity import DefaultAzureCredential
from datetime import datetime, timedelta
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
def get_azure_sqlalchemy_uri():
    # SQL authentication for automated backend connection
    import urllib
    server = 'biguard.database.windows.net'
    database = 'biguard'
    driver = 'ODBC Driver 17 for SQL Server'
    username = os.getenv('AZURE_SQL_USERNAME', 'sqladmin')
    password = os.getenv('AZURE_SQL_PASSWORD', 'Cartable123.')
    return (
        f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver={urllib.parse.quote(driver)}"
    )

# ...existing code...
    # ...existing code...

app.config['SQLALCHEMY_DATABASE_URI'] = get_azure_sqlalchemy_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)
bcrypt = Bcrypt(app)

# Plaid configuration
plaid_client = plaid.ApiClient(
    plaid.Configuration(
        host=plaid.Environment.Sandbox,
        api_key={
            'clientId': os.getenv('PLAID_CLIENT_ID'),
            'secret': os.getenv('PLAID_SECRET'),
        }
    )
)

plaid_api = plaid_api.PlaidApi(plaid_client)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    accounts = db.relationship('Account', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    budgets = db.relationship('Budget', backref='user', lazy=True)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plaid_account_id = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    subtype = db.Column(db.String(50))
    mask = db.Column(db.String(10))
    institution_name = db.Column(db.String(255))
    current_balance = db.Column(db.Float, default=0.0)
    available_balance = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    plaid_transaction_id = db.Column(db.String(255), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    merchant_name = db.Column(db.String(255))
    category = db.Column(db.String(255))
    category_id = db.Column(db.String(255))
    pending = db.Column(db.Boolean, default=False)
    fraud_score = db.Column(db.Float, default=0.0)
    is_fraudulent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    period = db.Column(db.String(20), default='monthly')  # monthly, weekly, yearly
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Authentication routes
@app.route('/')
def home():
    return '<h2>BiGuard Backend is Running</h2><p>API endpoints are available under /api/</p>'
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    password_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    
    user = User(
        email=data['email'],
        password_hash=password_hash,
        first_name=data['first_name'],
        last_name=data['last_name']
    )
    
    db.session.add(user)
    db.session.commit()
    
    access_token = create_access_token(identity=user.id)
    return jsonify({
        'message': 'User registered successfully',
        'access_token': access_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    
    if user and bcrypt.check_password_hash(user.password_hash, data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        })
    
    return jsonify({'error': 'Invalid credentials'}), 401

# Plaid routes
@app.route('/api/plaid/create-link-token', methods=['POST'])
@jwt_required()
def create_link_token():
    user_id = get_jwt_identity()
    
    request_obj = LinkTokenCreateRequest(
        products=[Products("transactions")],
        client_name="BiGuard",
        country_codes=[CountryCode("US")],
        language="en",
        user=LinkTokenCreateRequestUser(
            client_user_id=str(user_id)
        )
    )
    
    response = plaid_api.link_token_create(request_obj)
    return jsonify({'link_token': response.link_token})

@app.route('/api/plaid/exchange-token', methods=['POST'])
@jwt_required()
def exchange_token():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    request_obj = ItemPublicTokenExchangeRequest(
        public_token=data['public_token']
    )
    
    response = plaid_api.item_public_token_exchange(request_obj)
    access_token = response.access_token
    
    # Get accounts
    accounts_request = AccountsGetRequest(access_token=access_token)
    accounts_response = plaid_api.accounts_get(accounts_request)
    
    # Save accounts to database
    for account in accounts_response.accounts:
        existing_account = Account.query.filter_by(plaid_account_id=account.account_id).first()
        if not existing_account:
            new_account = Account(
                user_id=user_id,
                plaid_account_id=account.account_id,
                name=account.name,
                type=account.type,
                subtype=account.subtype,
                mask=account.mask,
                current_balance=account.balances.current,
                available_balance=account.balances.available
            )
            db.session.add(new_account)
    
    db.session.commit()
    
    return jsonify({'message': 'Bank account connected successfully'})

@app.route('/api/transactions/sync', methods=['POST'])
@jwt_required()
def sync_transactions():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    all_transactions = []
    
    for account in user.accounts:
        # Get transactions from Plaid
        request_obj = TransactionsSyncRequest(
            access_token=account.plaid_access_token,
            options={
                'include_personal_finance_category': True
            }
        )
        
        response = plaid_api.transactions_sync(request_obj)
        
        for transaction in response.added:
            # Check if transaction already exists
            existing_transaction = Transaction.query.filter_by(
                plaid_transaction_id=transaction.transaction_id
            ).first()
            
            if not existing_transaction:
                # Calculate fraud score
                fraud_score = calculate_fraud_score(transaction, user)
                
                new_transaction = Transaction(
                    user_id=user_id,
                    account_id=account.id,
                    plaid_transaction_id=transaction.transaction_id,
                    amount=transaction.amount,
                    date=datetime.strptime(transaction.date, '%Y-%m-%d').date(),
                    name=transaction.name,
                    merchant_name=transaction.merchant_name,
                    category=transaction.category[0] if transaction.category else None,
                    category_id=transaction.category_id,
                    pending=transaction.pending,
                    fraud_score=fraud_score,
                    is_fraudulent=fraud_score > 0.7  # Threshold for fraud detection
                )
                
                db.session.add(new_transaction)
                all_transactions.append(new_transaction)
    
    db.session.commit()
    
    return jsonify({
        'message': f'Synced {len(all_transactions)} new transactions',
        'transactions': [{
            'id': t.id,
            'amount': t.amount,
            'name': t.name,
            'date': t.date.strftime('%Y-%m-%d'),
            'category': t.category,
            'fraud_score': t.fraud_score,
            'is_fraudulent': t.is_fraudulent
        } for t in all_transactions]
    })

@app.route('/api/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    user_id = get_jwt_identity()
    
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category = request.args.get('category')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Transaction.query.filter_by(user_id=user_id)
    
    if category:
        query = query.filter_by(category=category)
    
    if start_date:
        query = query.filter(Transaction.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    
    if end_date:
        query = query.filter(Transaction.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    
    transactions = query.order_by(Transaction.date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'transactions': [{
            'id': t.id,
            'amount': t.amount,
            'name': t.name,
            'date': t.date.strftime('%Y-%m-%d'),
            'category': t.category,
            'merchant_name': t.merchant_name,
            'fraud_score': t.fraud_score,
            'is_fraudulent': t.is_fraudulent,
            'pending': t.pending
        } for t in transactions.items],
        'total': transactions.total,
        'pages': transactions.pages,
        'current_page': page
    })

@app.route('/api/dashboard/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    try:
        user_id = get_jwt_identity()
        print(f"Dashboard stats requested for user_id={user_id}")
        user = User.query.get(user_id)
        print(f"User object: {user}")
        if user:
            print(f"User first name: {user.first_name}, last name: {user.last_name}")

        # Get date range (last 30 days)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        # Get transactions for the period
        transactions = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).all()

        # Calculate statistics
        total_spent = sum(t.amount for t in transactions if t.amount < 0)
        total_income = sum(t.amount for t in transactions if t.amount > 0)

        # Category breakdown
        category_totals = {}
        for transaction in transactions:
            if transaction.category:
                if transaction.category not in category_totals:
                    category_totals[transaction.category] = 0
                category_totals[transaction.category] += abs(transaction.amount)

        # Fraud alerts
        fraud_alerts = [t for t in transactions if t.is_fraudulent]

        return jsonify({
            'user': {
                'firstName': user.first_name if user else '',
                'lastName': user.last_name if user else ''
            },
            'total_spent': abs(total_spent),
            'total_income': total_income,
            'net_flow': total_income + total_spent,
            'category_breakdown': category_totals,
            'fraud_alerts_count': len(fraud_alerts),
            'fraud_alerts': [{
                'id': t.id,
                'amount': t.amount,
                'name': t.name,
                'date': t.date.strftime('%Y-%m-%d'),
                'fraud_score': t.fraud_score
            } for t in fraud_alerts[:5]]  # Show only first 5 alerts
        })
    except Exception as e:
        import traceback
        print('Error in /api/dashboard/stats:', e)
        traceback.print_exc()
        return jsonify({'error': str(e)}), 422

# Machine Learning - Fraud Detection
def calculate_fraud_score(transaction, user):
    """
    Calculate fraud score for a transaction using machine learning
    This is a simplified version - in production, you'd use more sophisticated models
    """
    # Get user's transaction history for context
    user_transactions = Transaction.query.filter_by(user_id=user.id).all()
    
    if len(user_transactions) < 10:  # Need minimum transactions for analysis
        return 0.1  # Low risk for new users
    
    # Create features for the transaction
    features = []
    
    # Amount-based features
    amount = abs(transaction.amount)
    avg_amount = np.mean([abs(t.amount) for t in user_transactions])
    amount_ratio = amount / avg_amount if avg_amount > 0 else 1
    
    # Time-based features
    transaction_date = datetime.strptime(transaction.date, '%Y-%m-%d').date()
    recent_transactions = [t for t in user_transactions if (transaction_date - t.date).days <= 7]
    
    # Location-based features (simplified)
    is_new_merchant = not any(t.merchant_name == transaction.merchant_name for t in user_transactions)
    
    # Category-based features
    category_transactions = [t for t in user_transactions if t.category == transaction.category]
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
            t_amount_ratio = abs(t.amount) / avg_amount if avg_amount > 0 else 1
            t_is_new_merchant = not any(ot.merchant_name == t.merchant_name for ot in user_transactions if ot.id != t.id)
            t_category_freq = len([ct for ct in user_transactions if ct.category == t.category]) / len(user_transactions)
            
            training_data.append([
                t_amount_ratio,
                len([rt for rt in user_transactions if (transaction_date - rt.date).days <= 7]),
                t_is_new_merchant,
                t_category_freq,
                abs(t.amount) / 1000
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

# Budget management
@app.route('/api/budgets', methods=['GET'])
@jwt_required()
def get_budgets():
    user_id = get_jwt_identity()
    budgets = Budget.query.filter_by(user_id=user_id).all()
    
    return jsonify([{
        'id': b.id,
        'category': b.category,
        'amount': b.amount,
        'period': b.period
    } for b in budgets])

@app.route('/api/budgets', methods=['POST'])
@jwt_required()
def create_budget():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    budget = Budget(
        user_id=user_id,
        category=data['category'],
        amount=data['amount'],
        period=data.get('period', 'monthly')
    )
    
    db.session.add(budget)
    db.session.commit()
    
    return jsonify({
        'id': budget.id,
        'category': budget.category,
        'amount': budget.amount,
        'period': budget.period
    }), 201

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000) 