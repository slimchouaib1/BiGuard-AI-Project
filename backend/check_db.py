from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta

client = MongoClient('mongodb://localhost:27017/')
db = client['biguard']

# Get the most recent user
users = list(db.users.find().sort('_id', -1).limit(1))
if users:
    user = users[0]
    user_id = str(user['_id'])
    print(f"Latest user ID: {user_id}")
    print(f"Has sample data: {user.get('has_sample_data', False)}")
    
    # Check accounts
    accounts = list(db.accounts.find({'user_id': user_id}))
    print(f"Accounts: {len(accounts)}")
    for acc in accounts:
        print(f"  - {acc.get('name', 'Unknown')} (ID: {acc['_id']})")
    
    # Check transactions
    transactions = list(db.transactions.find({'user_id': user_id}))
    print(f"Transactions: {len(transactions)}")
    
    # Check transaction dates
    dates = [tx.get('date') for tx in transactions]
    unique_dates = sorted(set(dates))
    print(f"Transaction date range: {min(unique_dates)} to {max(unique_dates)}")
    
    # Check current date and 60 days ago
    now = datetime.now()
    sixty_days_ago = (now - timedelta(days=60)).strftime('%Y-%m-%d')
    print(f"Current date: {now.strftime('%Y-%m-%d')}")
    print(f"60 days ago: {sixty_days_ago}")
    
    # Count transactions in last 60 days
    recent_transactions = [tx for tx in transactions if tx.get('date', '') >= sixty_days_ago]
    print(f"Transactions in last 60 days: {len(recent_transactions)}")
    
    for tx in transactions[:5]:
        print(f"  - {tx.get('name', 'Unknown')} (Date: {tx.get('date', 'No date')}, Account: {tx.get('account_id', 'No account')})")
    
    # Check budgets
    budgets = list(db.budgets.find({'user_id': user_id}))
    print(f"Budgets: {len(budgets)}")
else:
    print("No users found")
