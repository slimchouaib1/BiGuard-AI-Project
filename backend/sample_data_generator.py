import os
import random
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['biguard']
users_collection = db['users']
accounts_collection = db['accounts']
transactions_collection = db['transactions']
budgets_collection = db['budgets']

# Sample transaction data with realistic amounts and proper signs
SAMPLE_TRANSACTIONS = {
    'income': [
        {'name': 'Salary - Company Inc', 'amount': 4500.00, 'category': 'Income'},
        {'name': 'Freelance Project Payment', 'amount': 1200.00, 'category': 'Income'},
        {'name': 'Investment Dividend', 'amount': 150.00, 'category': 'Income'},
        {'name': 'Side Gig Payment', 'amount': 800.00, 'category': 'Income'},
        {'name': 'Bonus Payment', 'amount': 1000.00, 'category': 'Income'},
        {'name': 'Rental Income', 'amount': 1800.00, 'category': 'Income'},
        {'name': 'Consulting Fee', 'amount': 750.00, 'category': 'Income'},
        {'name': 'Online Course Revenue', 'amount': 300.00, 'category': 'Income'},
    ],
    'expenses': [
        # Housing
        {'name': 'Rent Payment', 'amount': -1800.00, 'category': 'Housing'},
        {'name': 'Electricity Bill', 'amount': -120.00, 'category': 'Housing'},
        {'name': 'Internet Bill', 'amount': -85.00, 'category': 'Housing'},
        {'name': 'Water Bill', 'amount': -45.00, 'category': 'Housing'},
        {'name': 'Home Insurance', 'amount': -95.00, 'category': 'Housing'},
        
        # Food & Dining
        {'name': 'Grocery Store', 'amount': -85.50, 'category': 'Food & Dining'},
        {'name': 'Starbucks Coffee', 'amount': -4.75, 'category': 'Food & Dining'},
        {'name': 'McDonald\'s', 'amount': -12.30, 'category': 'Food & Dining'},
        {'name': 'Pizza Delivery', 'amount': -28.50, 'category': 'Food & Dining'},
        {'name': 'Restaurant - Italian', 'amount': -65.00, 'category': 'Food & Dining'},
        {'name': 'Coffee Shop', 'amount': -3.50, 'category': 'Food & Dining'},
        {'name': 'Fast Food', 'amount': -15.75, 'category': 'Food & Dining'},
        
        # Transportation
        {'name': 'Gas Station', 'amount': -45.00, 'category': 'Transportation'},
        {'name': 'Uber Ride', 'amount': -18.50, 'category': 'Transportation'},
        {'name': 'Public Transit', 'amount': -2.75, 'category': 'Transportation'},
        {'name': 'Car Insurance', 'amount': -120.00, 'category': 'Transportation'},
        {'name': 'Car Maintenance', 'amount': -85.00, 'category': 'Transportation'},
        {'name': 'Parking Fee', 'amount': -12.00, 'category': 'Transportation'},
        
        # Shopping
        {'name': 'Amazon Purchase', 'amount': -45.99, 'category': 'Shopping'},
        {'name': 'Target', 'amount': -67.25, 'category': 'Shopping'},
        {'name': 'Walmart', 'amount': -89.50, 'category': 'Shopping'},
        {'name': 'Best Buy', 'amount': -299.99, 'category': 'Shopping'},
        {'name': 'Clothing Store', 'amount': -125.00, 'category': 'Shopping'},
        {'name': 'Online Shopping', 'amount': -78.30, 'category': 'Shopping'},
        
        # Entertainment
        {'name': 'Netflix Subscription', 'amount': -15.99, 'category': 'Entertainment'},
        {'name': 'Movie Theater', 'amount': -24.50, 'category': 'Entertainment'},
        {'name': 'Spotify Premium', 'amount': -9.99, 'category': 'Entertainment'},
        {'name': 'Gym Membership', 'amount': -45.00, 'category': 'Entertainment'},
        {'name': 'Concert Tickets', 'amount': -150.00, 'category': 'Entertainment'},
        {'name': 'Video Game Purchase', 'amount': -59.99, 'category': 'Entertainment'},
        
        # Healthcare
        {'name': 'Pharmacy', 'amount': -25.50, 'category': 'Healthcare'},
        {'name': 'Doctor Visit', 'amount': -75.00, 'category': 'Healthcare'},
        {'name': 'Dental Checkup', 'amount': -120.00, 'category': 'Healthcare'},
        {'name': 'Health Insurance', 'amount': -200.00, 'category': 'Healthcare'},
        {'name': 'Medical Supplies', 'amount': -35.00, 'category': 'Healthcare'},
        
        # Travel
        {'name': 'Airline Ticket', 'amount': -450.00, 'category': 'Travel'},
        {'name': 'Hotel Booking', 'amount': -180.00, 'category': 'Travel'},
        {'name': 'Rental Car', 'amount': -85.00, 'category': 'Travel'},
        {'name': 'Travel Insurance', 'amount': -45.00, 'category': 'Travel'},
        {'name': 'Vacation Package', 'amount': -1200.00, 'category': 'Travel'},
        
        # Education
        {'name': 'Online Course', 'amount': -89.99, 'category': 'Education'},
        {'name': 'Bookstore', 'amount': -45.00, 'category': 'Education'},
        {'name': 'Student Loan Payment', 'amount': -350.00, 'category': 'Education'},
        {'name': 'Workshop Fee', 'amount': -125.00, 'category': 'Education'},
        
        # Utilities & Bills
        {'name': 'Phone Bill', 'amount': -65.00, 'category': 'Utilities & Bills'},
        {'name': 'Cable TV', 'amount': -95.00, 'category': 'Utilities & Bills'},
        {'name': 'Credit Card Payment', 'amount': -250.00, 'category': 'Utilities & Bills'},
        {'name': 'Bank Fee', 'amount': -12.00, 'category': 'Utilities & Bills'},
        
        # Miscellaneous
        {'name': 'ATM Withdrawal', 'amount': -100.00, 'category': 'Miscellaneous'},
        {'name': 'Charity Donation', 'amount': -50.00, 'category': 'Miscellaneous'},
        {'name': 'Pet Supplies', 'amount': -35.00, 'category': 'Miscellaneous'},
        {'name': 'Home Improvement', 'amount': -150.00, 'category': 'Miscellaneous'},
    ]
}

def generate_sample_data(user_id, monthly_income=None):
    """Generate realistic sample financial data for a user"""
    try:
        # If no monthly income provided, generate a realistic one
        if not monthly_income:
            monthly_income = random.choice([3500, 4500, 5500, 6500, 7500, 8500])
        
        # Calculate realistic starting balance (2-4 months of income)
        starting_balance = monthly_income * random.uniform(2.0, 4.0)
        
        # Create sample accounts
        accounts = [
            {
                'user_id': str(user_id),
                'name': 'Main Checking Account',
                'subtype': 'checking',
                'current_balance': starting_balance * 0.7,
                'account_number': '****1234',
                'is_sample': True
            },
            {
                'user_id': str(user_id),
                'name': 'Savings Account',
                'subtype': 'savings',
                'current_balance': starting_balance * 0.3,
                'account_number': '****5678',
                'is_sample': True
            }
        ]
        
        # Insert accounts and get their IDs
        account_ids = []
        for account in accounts:
            result = accounts_collection.insert_one(account)
            account_ids.append(result.inserted_id)
        
        # Generate transactions for the last 4 months
        transactions = []
        current_date = datetime.now()
        
        # Define consistent salary amount
        base_salary = monthly_income * 0.7  # 70% of monthly income as base salary
        
        for month_offset in range(4):
            month_date = current_date - timedelta(days=30 * month_offset)
            
            # Add consistent salary transaction (always on the 1st of the month)
            salary_date = month_date.replace(day=1)
            transactions.append({
                'user_id': str(user_id),
                'name': 'Salary - Company Inc',
                'amount': base_salary,
                'category': 'Income',
                'date': salary_date.strftime('%Y-%m-%d'),
                'is_expense': False,
                'is_sample': True,
                'account_id': str(account_ids[0])  # Always to checking account
            })
            
            # Add 2-4 additional income transactions per month (bonuses, freelance, etc.)
            # But exclude 'Salary' transactions to avoid duplicates
            additional_income_count = random.randint(2, 4)
            for i in range(additional_income_count):
                # Filter out salary transactions to avoid duplicates
                non_salary_income = [inc for inc in SAMPLE_TRANSACTIONS['income'] if not inc['name'].startswith('Salary')]
                income = random.choice(non_salary_income)
                transaction_date = month_date - timedelta(days=random.randint(1, 28))
                
                # Adjust income amount based on type
                if income['name'].startswith('Bonus'):
                    amount = base_salary * random.uniform(0.15, 0.25)  # 15-25% of salary
                elif income['name'].startswith('Freelance'):
                    amount = base_salary * random.uniform(0.1, 0.2)  # 10-20% of salary
                elif income['name'].startswith('Investment'):
                    amount = random.uniform(50, 300)  # Fixed range for investments
                else:
                    amount = income['amount'] * random.uniform(0.8, 1.2)
                
                transactions.append({
                    'user_id': str(user_id),
                    'name': income['name'],
                    'amount': amount,
                    'category': income['category'],
                    'date': transaction_date.strftime('%Y-%m-%d'),
                    'is_expense': False,
                    'is_sample': True,
                    'account_id': str(account_ids[0] if random.random() > 0.3 else account_ids[1])
                })
            
            # Add 35-45 expense transactions per month (at least 40 total per month)
            expense_count = random.randint(35, 45)
            for i in range(expense_count):
                expense = random.choice(SAMPLE_TRANSACTIONS['expenses'])
                transaction_date = month_date - timedelta(days=random.randint(1, 28))
                
                # Vary the amount slightly
                amount = expense['amount'] * random.uniform(0.8, 1.2)
                
                transactions.append({
                    'user_id': str(user_id),
                    'name': expense['name'],
                    'amount': abs(amount),  # Store as positive, but mark as expense
                    'category': expense['category'],
                    'date': transaction_date.strftime('%Y-%m-%d'),
                    'is_expense': True,
                    'is_sample': True,
                    'account_id': str(account_ids[0] if random.random() > 0.3 else account_ids[1])
                })
        
        # Insert transactions
        if transactions:
            transactions_collection.insert_many(transactions)
        
        # Trigger anomaly detection on the new sample data
        try:
            from anomaly_detection import anomaly_detector
            # Run anomaly detection on the sample data
            anomalies = anomaly_detector.detect_anomalies(user_id, limit=100, data_type='sample')
            print(f"Anomaly detection completed: {len(anomalies)} anomalies found in sample data")
        except Exception as e:
            print(f"Error running anomaly detection on sample data: {e}")
        
        # Don't create budgets automatically for new accounts
        # Users can create their own budgets when needed
        budgets = []
        
        # Update user with sample data flag
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$set': {
                    'has_sample_data': True,
                    'monthly_income': monthly_income,
                    'sample_data_created_at': datetime.now(),
                    'ready_for_real_bank': False  # Reset this flag when generating sample data
                }
            }
        )
        
        return {
            'success': True,
            'message': f'Generated sample data with ${monthly_income:,.2f} monthly income',
            'accounts_created': len(accounts),
            'transactions_created': len(transactions),
            'budgets_created': len(budgets),
            'monthly_income': monthly_income,
            'starting_balance': starting_balance
        }
        
    except Exception as e:
        print(f"Error generating sample data: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def clear_sample_data(user_id):
    """Clear all sample data for a user"""
    try:
        # Remove sample accounts
        accounts_collection.delete_many({
            'user_id': str(user_id),
            'is_sample': True
        })
        
        # Remove sample transactions
        transactions_collection.delete_many({
            'user_id': str(user_id),
            'is_sample': True
        })
        
        # Remove sample budgets
        budgets_collection.delete_many({
            'user_id': str(user_id),
            'is_sample': True
        })
        
        # Remove sample fraudulent transactions
        try:
            from anomaly_detection import anomaly_detector
            anomaly_detector.clear_fraudulent_transactions(user_id, data_type='sample')
        except Exception as e:
            print(f"Error clearing sample fraudulent transactions: {e}")
        
        # Update user
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$unset': {
                    'has_sample_data': '',
                    'monthly_income': '',
                    'sample_data_created_at': '',
                    'ready_for_real_bank': ''
                }
            }
        )
        
        return {
            'success': True,
            'message': 'Sample data cleared successfully'
        }
        
    except Exception as e:
        print(f"Error clearing sample data: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def get_financial_summary(user_id):
    """Get financial summary for a user"""
    try:
        # Get all transactions for the current month
        now = datetime.now()
        start_date = now.replace(day=1).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
        transactions = list(transactions_collection.find({
            'user_id': str(user_id),
            'date': {'$gte': start_date, '$lte': end_date}
        }))
        
        # Calculate totals
        total_income = sum(t['amount'] for t in transactions if not t.get('is_expense', True))
        total_expenses = sum(t['amount'] for t in transactions if t.get('is_expense', True))
        net_income = total_income - total_expenses
        
        # Get account balances
        accounts = list(accounts_collection.find({'user_id': str(user_id)}))
        total_balance = sum(a.get('current_balance', 0) for a in accounts)
        
        # Get category breakdown
        category_totals = {}
        for t in transactions:
            cat = t.get('category', 'Uncategorized')
            amount = t['amount']
            if t.get('is_expense', True):
                category_totals[cat] = category_totals.get(cat, 0) + amount
            else:
                category_totals[cat] = category_totals.get(cat, 0) + amount
        
        return {
            'success': True,
            'monthly_income': total_income,
            'monthly_expenses': total_expenses,
            'net_income': net_income,
            'total_balance': total_balance,
            'category_breakdown': category_totals,
            'transaction_count': len(transactions)
        }
        
    except Exception as e:
        print(f"Error getting financial summary: {e}")
        return {
            'success': False,
            'error': str(e)
        }
