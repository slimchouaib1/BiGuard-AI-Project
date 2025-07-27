

import os
os.environ['PLAID_CLIENT_ID'] = '6853f9614ac5c0002193dd49'
os.environ['PLAID_SECRET'] = 'bb5fd63a66f16fab15feeeb7466075'
os.environ['PLAID_ENV'] = 'sandbox'
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

app.config['SQLALCHEMY_DATABASE_URI'] = get_azure_sqlalchemy_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Plaid environment variables
from plaid import Environment
env_map = {
    'sandbox': Environment.Sandbox,
    'development': getattr(Environment, 'Development', Environment.Sandbox),
    'production': Environment.Production
}
plaid_env = env_map.get(os.environ.get('PLAID_ENV', 'sandbox').lower(), Environment.Sandbox)
PLAID_CLIENT_ID = os.environ.get('PLAID_CLIENT_ID')
PLAID_SECRET = os.environ.get('PLAID_SECRET')

plaid_client = plaid.ApiClient(
    plaid.Configuration(
        host=plaid_env,
        api_key={
            'clientId': PLAID_CLIENT_ID,
            'secret': PLAID_SECRET,
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
    plaid_access_token = db.Column(db.String(255), nullable=False)

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
    
    access_token = create_access_token(identity=str(user.id))
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
        access_token = create_access_token(identity=str(user.id))
        # Sync Plaid transactions for real-time threat detection
        try:
            # For each account, sync transactions from Plaid
            all_transactions = []
            for account in user.accounts:
                request_obj = TransactionsSyncRequest(
                    access_token=account.plaid_access_token,
                    options={'include_personal_finance_category': True}
                )
                response = plaid_api.transactions_sync(request_obj)
                for transaction in response.added:
                    existing_transaction = Transaction.query.filter_by(
                        plaid_transaction_id=transaction.transaction_id
                    ).first()
                    if not existing_transaction:
                        fraud_score = calculate_fraud_score(transaction, user)
                        new_transaction = Transaction(
                            user_id=user.id,
                            account_id=account.id,
                            plaid_transaction_id=transaction.transaction_id,
                            amount=transaction.amount,
                            date=transaction.date,
                            name=transaction.name,
                            merchant_name=transaction.merchant_name,
                            category=transaction.category[0] if transaction.category else None,
                            category_id=transaction.category_id,
                            pending=transaction.pending,
                            fraud_score=fraud_score,
                            is_fraudulent=fraud_score > 0.7
                        )
                        db.session.add(new_transaction)
                        all_transactions.append(new_transaction)
            db.session.commit()
        except Exception as e:
            print(f"[LOGIN] Plaid sync failed: {e}")
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
    user_id = str(get_jwt_identity())
    print(f"[DEBUG] /api/plaid/create-link-token called. JWT identity: {user_id}")
    print(f"[DEBUG] Authorization header: {request.headers.get('Authorization')}")
    try:
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
    except Exception as e:
        print(f"Plaid link token creation error: {e}")
        return jsonify({'error': 'Could not create Plaid link token', 'details': str(e)}), 500

@app.route('/api/plaid/exchange-token', methods=['POST'])
@jwt_required()
def exchange_token():
    user_id = get_jwt_identity()

    data = request.get_json()
    public_token = data.get('public_token')
    remember_account = data.get('remember_account', True)  # Default True
    if not public_token:
        return jsonify({'error': 'Missing public_token'}), 400

    try:
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=public_token
        )
        exchange_response = plaid_api.item_public_token_exchange(exchange_request)
        access_token = exchange_response.access_token

        # Get accounts
        accounts_request = AccountsGetRequest(access_token=access_token)
        accounts_response = plaid_api.accounts_get(accounts_request)

        if remember_account:
            # Save only checking and savings accounts to database
            for account in accounts_response.accounts:
                # Only keep depository accounts with subtype checking or savings
                if str(account.type).lower() == 'depository' and str(account.subtype).lower() in ['checking', 'savings']:
                    existing_account = Account.query.filter_by(plaid_account_id=account.account_id).first()
                    if not existing_account:
                        new_account = Account(
                            user_id=user_id,
                            plaid_account_id=account.account_id,
                            name=account.name,
                            type=str(account.type) if account.type else None,
                            subtype=str(account.subtype) if account.subtype else None,
                            mask=account.mask,
                            institution_name=getattr(account, 'institution_name', None),
                            current_balance=account.balances.current,
                            available_balance=account.balances.available,
                            plaid_access_token=access_token
                        )
                        db.session.add(new_account)
            db.session.commit()
            return jsonify({'message': 'Bank account connected successfully'})
        else:
            # Do not save account, just return success
            return jsonify({'message': 'Bank account linked for this session only'})
    except Exception as e:
        print(f"Plaid token exchange error: {e}")
        return jsonify({'error': 'Could not exchange token', 'details': str(e)}), 500

@app.route('/api/transactions/sync', methods=['POST'])
@jwt_required()
def sync_transactions():
    user_id = get_jwt_identity()
    print(f"[DEBUG] /api/transactions/sync called. JWT identity: {user_id}")
    print(f"[DEBUG] Authorization header: {request.headers.get('Authorization')}")
    user = User.query.get(user_id)
    
    all_transactions = []
    seen_transaction_ids = set()
    # Preload all existing transaction IDs for this user from DB
    existing_ids = set([t.plaid_transaction_id for t in Transaction.query.filter_by(user_id=user_id).all()])
    for account in user.accounts:
        # Get transactions from Plaid
        request_obj = TransactionsSyncRequest(
            access_token=account.plaid_access_token,
            options={
                'include_personal_finance_category': True
            }
        )
        response = plaid_api.transactions_sync(request_obj)
        with db.session.no_autoflush:
            for transaction in response.added:
                txn_id = transaction.transaction_id
                # Add txn_id to seen_transaction_ids immediately
                if txn_id in existing_ids or txn_id in seen_transaction_ids:
                    seen_transaction_ids.add(txn_id)
                    continue
                # Final DB check for bulletproof deduplication
                if Transaction.query.filter_by(plaid_transaction_id=txn_id).first():
                    seen_transaction_ids.add(txn_id)
                    continue
                seen_transaction_ids.add(txn_id)
                # Calculate fraud score
                fraud_score = calculate_fraud_score(transaction, user)
                new_transaction = Transaction(
                    user_id=user_id,
                    account_id=account.id,
                    plaid_transaction_id=txn_id,
                    amount=transaction.amount,
                    date=transaction.date,
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
    per_page = request.args.get('per_page', 50, type=int)
    # Allow up to 200 per page
    if per_page > 200:
        per_page = 200
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
        print(f"[DEBUG] /api/dashboard/stats called. JWT identity: {user_id}")
        print(f"[DEBUG] Authorization header: {request.headers.get('Authorization')}")
        user = User.query.get(user_id)
        print(f"[DEBUG] User object: {user}")
        if user:
            print(f"[DEBUG] User first name: {user.first_name}, last name: {user.last_name}")

        # Get date range (last 30 days)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        # Separate accounts by type
        checking_accounts = [a for a in user.accounts if a.subtype and a.subtype.lower() == 'checking']
        savings_accounts = [a for a in user.accounts if a.subtype and a.subtype.lower() == 'savings']

        # Fetch budgets for this user (per category)
        user_budgets = Budget.query.filter_by(user_id=user_id).all()
        budgets_by_category = {}
        for b in user_budgets:
            budgets_by_category[b.category] = {
                'amount': b.amount,
                'period': b.period
            }

        def get_account_stats(accounts, include_budgets=False):
            account_ids = [a.id for a in accounts]
            transactions = Transaction.query.filter(
                Transaction.user_id == user_id,
                Transaction.account_id.in_(account_ids),
                Transaction.date >= start_date,
                Transaction.date <= end_date
            ).all() if account_ids else []
            total_spent = sum(t.amount for t in transactions if t.amount < 0)
            total_income = sum(t.amount for t in transactions if t.amount > 0)
            # Calculate monthly net income (sum of positive transactions in last 30 days)
            monthly_net_income = sum(t.amount for t in transactions if t.amount > 0)
            category_totals = {}
            for transaction in transactions:
                if transaction.category:
                    if transaction.category not in category_totals:
                        category_totals[transaction.category] = 0
                    category_totals[transaction.category] += abs(transaction.amount)
            fraud_alerts = [t for t in transactions if t.is_fraudulent]
            current_balance = sum(a.current_balance or 0.0 for a in accounts)
            result = {
                'accounts': [{'id': a.id, 'name': a.name, 'current_balance': a.current_balance} for a in accounts],
                'total_spent': abs(total_spent),
                'total_income': total_income,
                'monthly_net_income': monthly_net_income,
                'net_flow': total_income + total_spent,
                'category_breakdown': category_totals,
                'fraud_alerts_count': len(fraud_alerts),
                'fraud_alerts': [{
                    'id': t.id,
                    'amount': t.amount,
                    'name': t.name,
                    'date': t.date.strftime('%Y-%m-%d'),
                    'fraud_score': t.fraud_score
                } for t in fraud_alerts[:5]],
                'current_balance': current_balance,
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
                } for t in transactions]
            }
            if include_budgets:
                # Attach budgets for each category
                result['budgets'] = {cat: budgets_by_category.get(cat) for cat in category_totals.keys()}
            return result

        return jsonify({
            'user': {
                'firstName': user.first_name if user else '',
                'lastName': user.last_name if user else ''
            },
            'checking': get_account_stats(checking_accounts, include_budgets=True),
            'savings': get_account_stats(savings_accounts)
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
    # transaction.date may be a string or a date object
    if isinstance(transaction.date, str):
        transaction_date = datetime.strptime(transaction.date, '%Y-%m-%d').date()
    else:
        transaction_date = transaction.date
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


# Balance over time endpoint
@app.route('/api/accounts/balance-history', methods=['GET'])
@jwt_required()
def get_balance_history():
    """
    Returns running balance over time for each account and total, based on latest Plaid balance and transactions.
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    accounts = user.accounts
    result = []
    total_balance_by_date = {}

    for account in accounts:
        # Get all transactions for this account, sorted by date descending
        txns = Transaction.query.filter_by(account_id=account.id).order_by(Transaction.date.desc()).all()
        # Start from the latest known balance
        running_balance = account.current_balance or 0.0
        history = []
        last_date = None
        for txn in txns:
            # Record balance at this date (after this transaction)
            history.append({
                'date': txn.date.strftime('%Y-%m-%d'),
                'balance': running_balance
            })
            # Subtract/add transaction amount (Plaid: negative = spent, positive = income)
            running_balance -= txn.amount
            last_date = txn.date
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
            'account_id': account.id,
            'account_name': account.name,
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

# Utility: Generate a lot of Plaid sandbox transactions for ML training
from plaid.model.sandbox_item_fire_webhook_request import SandboxItemFireWebhookRequest

@app.route('/api/plaid/sandbox/generate-transactions', methods=['POST'])
@jwt_required()
def generate_sandbox_transactions():
    """
    For all linked Plaid accounts for the current user, fire the sandbox webhook multiple times to generate a large number of transactions, then sync.
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    count = 0
    for account in user.accounts:
        access_token = account.plaid_access_token
        # Fire the webhook multiple times to generate more transactions
        for _ in range(10):  # 10x = 1000+ transactions in sandbox
            try:
                req = SandboxItemFireWebhookRequest(
                    access_token=access_token,
                    webhook_code='DEFAULT_UPDATE'
                )
                plaid_api.sandbox_item_fire_webhook(req)
                count += 1
            except Exception as e:
                print(f"[SANDBOX] Error firing webhook for account {account.id}: {e}")
    # After firing, sync transactions
    try:
        # Reuse the sync_transactions logic
        with app.test_request_context():
            resp = sync_transactions()
        return jsonify({'message': f'Fired {count} webhooks and synced transactions for all accounts.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounts', methods=['GET'])
@jwt_required()
def get_accounts():
    print('[DEBUG] /api/accounts endpoint called')
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        print('[DEBUG] User not found for /api/accounts')
        return jsonify({'error': 'User not found'}), 404
    accounts = user.accounts
    result = []
    for account in accounts:
        result.append({
            'id': account.id,
            'name': account.name,
            'type': account.type,
            'subtype': account.subtype,
            'mask': account.mask,
            'institution_name': account.institution_name,
            'current_balance': account.current_balance,
            'available_balance': account.available_balance,
            'last_updated': account.last_updated.strftime('%Y-%m-%d %H:%M:%S') if account.last_updated else None
        })
    print(f'[DEBUG] Returning {len(result)} accounts for user {user_id}')
    return jsonify(result)

print('[DEBUG] /api/accounts endpoint registered')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Disable auto-reloader to preserve environment variables
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)