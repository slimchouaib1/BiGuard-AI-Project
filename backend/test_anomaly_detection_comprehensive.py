#!/usr/bin/env python3
"""
Comprehensive test script for anomaly detection
Creates both legitimate and fraudulent transactions for testing
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
from bson import ObjectId
import random

def create_comprehensive_test_data():
    """Create comprehensive test data with both legitimate and fraudulent transactions"""
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client['biguard']
        users_collection = db['users']
        accounts_collection = db['accounts']
        transactions_collection = db['transactions']
        fraudulent_transactions_collection = db['fraudulent_transactions']
        
        # Find the user
        email = "slimchouaib73333333333333332@gmail.com"
        user = users_collection.find_one({'email': email})
        if not user:
            print(f"❌ User with email {email} not found")
            return False
        
        user_id = str(user['_id'])
        print(f"✅ Found user: {email}")
        print(f"   User ID: {user_id}")
        
        # Find user's account
        account = accounts_collection.find_one({'user_id': user_id})
        if not account:
            print(f"❌ No account found for user")
            return False
        
        account_id = str(account['_id'])
        print(f"✅ Found account: {account['name']}")
        
        # Enable sample data mode for the user
        users_collection.update_one(
            {'_id': user['_id']},
            {'$set': {'has_sample_data': True}}
        )
        print(f"✅ Enabled sample data mode for user")
        
        # Note: Not clearing existing sample transactions - adding new ones only
        print(f"📝 Adding new sample transactions (keeping existing ones)")
        
        # Comprehensive test transactions
        test_transactions = [
            # LEGITIMATE TRANSACTIONS
            {
                'name': 'Monthly Salary - Tech Corp',
                'amount': 6500.00,
                'category': 'Income',
                'merchant_name': 'Tech Corporation',
                'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'is_expense': False,
                'is_fraudulent': False,
                'is_sample': True
            },
            {
                'name': 'Freelance Project Payment',
                'amount': 1200.00,
                'category': 'Income',
                'merchant_name': 'Freelance Client',
                'date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
                'is_expense': False,
                'is_fraudulent': False,
                'is_sample': True
            },
            {
                'name': 'Rent Payment',
                'amount': 1800.00,
                'category': 'Housing',
                'merchant_name': 'Downtown Apartments',
                'date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
                'is_expense': True,
                'is_fraudulent': False,
                'is_sample': True
            },
            {
                'name': 'Grocery Shopping',
                'amount': 150.75,
                'category': 'Food & Dining',
                'merchant_name': 'Walmart Supercenter',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'is_expense': True,
                'is_fraudulent': False,
                'is_sample': True
            },
            {
                'name': 'Coffee Shop',
                'amount': 12.50,
                'category': 'Food & Dining',
                'merchant_name': 'Starbucks',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'is_expense': True,
                'is_fraudulent': False,
                'is_sample': True
            },
            {
                'name': 'Amazon Purchase',
                'amount': 95.00,
                'category': 'Shopping',
                'merchant_name': 'Amazon.com',
                'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'is_expense': True,
                'is_fraudulent': False,
                'is_sample': True
            },
            {
                'name': 'Netflix Subscription',
                'amount': 15.99,
                'category': 'Entertainment',
                'merchant_name': 'Netflix',
                'date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
                'is_expense': True,
                'is_fraudulent': False,
                'is_sample': True
            },
            
            # FRAUDULENT TRANSACTIONS
            {
                'name': 'Cryptocurrency Purchase - Bitcoin Exchange',
                'amount': 8500.00,
                'category': 'Investment',
                'merchant_name': 'CryptoExchange.com',
                'date': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
                'is_expense': True,
                'is_fraudulent': True,
                'is_sample': True,
                'severity': 'high',
                'reasons': ['High-risk cryptocurrency transaction', 'Unusual spending pattern'],
                'blocked': True
            },
            {
                'name': 'Suspicious International Transfer',
                'amount': 15000.00,
                'category': 'Transfer',
                'merchant_name': 'Unknown International Bank',
                'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'is_expense': True,
                'is_fraudulent': True,
                'is_sample': True,
                'severity': 'high',
                'reasons': ['Large international transfer', 'Suspicious destination'],
                'blocked': True
            },
            {
                'name': 'Dark Web Marketplace Purchase',
                'amount': 750.00,
                'category': 'Other',
                'merchant_name': 'Anonymous Vendor',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'is_expense': True,
                'is_fraudulent': True,
                'is_sample': True,
                'severity': 'high',
                'reasons': ['Dark web activity detected', 'High-risk merchant'],
                'blocked': True
            },
            {
                'name': 'Gambling Site - Large Bet',
                'amount': 5000.00,
                'category': 'Entertainment',
                'merchant_name': 'OnlineCasino.net',
                'date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
                'is_expense': True,
                'is_fraudulent': True,
                'is_sample': True,
                'severity': 'medium',
                'reasons': ['Gambling activity', 'Large amount'],
                'blocked': True
            },
            {
                'name': 'Unknown Merchant - Suspicious Purchase',
                'amount': 2500.00,
                'category': 'Shopping',
                'merchant_name': 'Unknown Vendor LLC',
                'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'is_expense': True,
                'is_fraudulent': True,
                'is_sample': True,
                'severity': 'medium',
                'reasons': ['Unknown merchant', 'Unusual transaction pattern'],
                'blocked': True
            }
        ]
        
        print(f"🧪 Creating {len(test_transactions)} comprehensive test transactions...")
        
        for i, tx in enumerate(test_transactions):
            print(f"📦 Creating transaction {i+1}: {tx['name']}")
            
            # Create transaction document
            transaction_doc = {
                'user_id': user_id,
                'account_id': account_id,
                'plaid_transaction_id': f'comprehensive_test_{datetime.now().timestamp()}_{i}',
                'amount': tx['amount'],
                'date': tx['date'],
                'name': tx['name'],
                'merchant_name': tx['merchant_name'],
                'category': tx['category'],
                'pending': False,
                'fraud_score': 0.9 if tx['is_fraudulent'] else 0.1,
                'is_fraudulent': tx['is_fraudulent'],
                'is_expense': tx['is_expense'],
                'transaction_type': 'income' if not tx['is_expense'] else 'spending',
                'is_sample': tx['is_sample'],
                'blocked': tx.get('blocked', False),
                'created_at': datetime.utcnow()
            }
            
            # Add anomaly details for fraudulent transactions
            if tx['is_fraudulent']:
                transaction_doc.update({
                    'anomaly_severity': tx['severity'],
                    'anomaly_reasons': tx['reasons'],
                    'threat_level': tx['severity']
                })
            
            # Insert transaction based on type
            if tx['is_fraudulent']:
                # Insert into fraudulent transactions collection for dashboard display
                fraudulent_doc = {
                    'user_id': user_id,
                    'transaction_id': f'comprehensive_test_{datetime.now().timestamp()}_{i}',
                    'name': tx['name'],
                    'amount': tx['amount'],
                    'category': tx['category'],
                    'date': tx['date'],
                    'is_expense': tx['is_expense'],
                    'is_sample': tx['is_sample'],
                    'account_id': account_id,
                    'description': tx['name'],
                    'anomaly_score': 0.9,
                    'severity': tx['severity'],
                    'threat_level': tx['severity'],
                    'reasons': tx['reasons'],
                    'detected_at': datetime.utcnow(),
                    'blocked': True,
                    'data_type': 'sample',
                    'status': 'blocked',
                    'merchant_name': tx['merchant_name']
                }
                result = fraudulent_transactions_collection.insert_one(fraudulent_doc)
                print(f"   🚨 FRAUDULENT: {tx['name']} - ${tx['amount']:,.2f}")
                print(f"      Severity: {tx['severity']}, Blocked: Yes, Added to fraud collection")
            else:
                # Insert legitimate transaction into main collection
                result = transactions_collection.insert_one(transaction_doc)
                print(f"   ✅ LEGITIMATE: {tx['name']} - ${tx['amount']:,.2f}")
        
        # Count results
        legitimate_count = len([t for t in test_transactions if not t['is_fraudulent']])
        fraudulent_count = len([t for t in test_transactions if t['is_fraudulent']])
        
        print(f"\n✅ Successfully created comprehensive test data:")
        print(f"   📊 Total transactions: {len(test_transactions)}")
        print(f"   ✅ Legitimate transactions: {legitimate_count}")
        print(f"   🚨 Fraudulent transactions: {fraudulent_count}")
        print(f"   🎭 User is now in demo mode with realistic test data")
        print(f"   📱 Test the webapp to see anomaly detection in action!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating comprehensive test data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    create_comprehensive_test_data()
