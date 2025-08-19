#!/usr/bin/env python3
"""
Script to insert a fraudulent transaction for testing anomaly detection
Usage: python insert_fraudulent_transaction.py
"""

from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
import random

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['biguard']
users_collection = db['users']
accounts_collection = db['accounts']
transactions_collection = db['transactions']

def insert_fraudulent_transaction():
    """Insert a fraudulent transaction for testing"""
    
    # Find the user by email
    user_email = "slimchouaib2798@gmail.com"
    user = users_collection.find_one({'email': user_email})
    
    if not user:
        print(f"❌ User with email {user_email} not found!")
        print("Available users:")
        for u in users_collection.find({}, {'email': 1, 'first_name': 1, 'last_name': 1}):
            print(f"  - {u.get('email', 'No email')} ({u.get('first_name', '')} {u.get('last_name', '')})")
        return False
    
    user_id = str(user['_id'])
    print(f"✅ Found user: {user.get('first_name', '')} {user.get('last_name', '')} ({user_email})")
    
    # Find user's checking account
    checking_account = accounts_collection.find_one({
        'user_id': user_id,
        'subtype': 'checking'
    })
    
    if not checking_account:
        print("❌ No checking account found for user!")
        return False
    
    print(f"✅ Found checking account: {checking_account.get('name', 'Unknown')}")
    
    # Create a suspicious fraudulent transaction
    fraudulent_transaction = {
        'user_id': user_id,
        'account_id': str(checking_account['_id']),
        'plaid_transaction_id': f'fraud_test_{datetime.now().timestamp()}_suspicious_purchase',
        'amount': 2499.99,  # Large amount to trigger anomaly detection
        'date': datetime.now().strftime('%Y-%m-%d'),
        'name': 'SUSPICIOUS ONLINE PURCHASE - UNKNOWN MERCHANT',
        'merchant_name': 'SUSPICIOUS ONLINE PURCHASE - UNKNOWN MERCHANT',
        'category': 'Shopping',
        'pending': False,
        'fraud_score': 0.95,  # High fraud score
        'is_fraudulent': True,  # Mark as fraudulent
        'is_expense': True,
        'transaction_type': 'spending',
        'is_manual': True,
        'is_sample': True,  # Mark as sample data for demo mode
        'created_at': datetime.utcnow(),
        'anomaly_flags': [
            'unusually_large_amount',
            'suspicious_merchant_name',
            'unusual_timing',
            'high_fraud_score'
        ]
    }
    
    # Insert the fraudulent transaction
    result = transactions_collection.insert_one(fraudulent_transaction)
    
    print(f"✅ Fraudulent transaction inserted successfully!")
    print(f"   Transaction ID: {result.inserted_id}")
    print(f"   Amount: ${fraudulent_transaction['amount']}")
    print(f"   Merchant: {fraudulent_transaction['merchant_name']}")
    print(f"   Fraud Score: {fraudulent_transaction['fraud_score']}")
    print(f"   Date: {fraudulent_transaction['date']}")
    print(f"   Anomaly Flags: {fraudulent_transaction['anomaly_flags']}")
    
    # Also insert a second suspicious transaction (smaller but still suspicious)
    suspicious_transaction = {
        'user_id': user_id,
        'account_id': str(checking_account['_id']),
        'plaid_transaction_id': f'fraud_test_{datetime.now().timestamp()}_late_night_purchase',
        'amount': 899.50,  # Medium-large amount
        'date': datetime.now().strftime('%Y-%m-%d'),
        'name': 'LATE NIGHT ONLINE GAMING - SUSPICIOUS SITE',
        'merchant_name': 'LATE NIGHT ONLINE GAMING - SUSPICIOUS SITE',
        'category': 'Entertainment',
        'pending': False,
        'fraud_score': 0.87,  # High fraud score
        'is_fraudulent': True,  # Mark as fraudulent
        'is_expense': True,
        'transaction_type': 'spending',
        'is_manual': True,
        'is_sample': True,  # Mark as sample data for demo mode
        'created_at': datetime.utcnow(),
        'anomaly_flags': [
            'unusual_timing',
            'suspicious_merchant_name',
            'high_fraud_score',
            'unusual_category_pattern'
        ]
    }
    
    result2 = transactions_collection.insert_one(suspicious_transaction)
    
    print(f"✅ Second suspicious transaction inserted!")
    print(f"   Transaction ID: {result2.inserted_id}")
    print(f"   Amount: ${suspicious_transaction['amount']}")
    print(f"   Merchant: {suspicious_transaction['merchant_name']}")
    print(f"   Fraud Score: {suspicious_transaction['fraud_score']}")
    
    print("\n🎯 Now check your dashboard and chatbot for anomaly detection!")
    print("   - The anomaly detection card should show 'High Risk'")
    print("   - The chatbot should detect these as suspicious when asked about fraud")
    print("   - You can ask the chatbot: 'Are there any suspicious transactions?'")
    
    return True

if __name__ == "__main__":
    print("🚨 Inserting fraudulent transactions for anomaly detection testing...")
    print("=" * 60)
    
    success = insert_fraudulent_transaction()
    
    if success:
        print("\n✅ Success! Fraudulent transactions have been inserted.")
        print("   Check your BiGuard dashboard to see the anomaly detection in action!")
    else:
        print("\n❌ Failed to insert fraudulent transactions.")
        print("   Please check the error messages above.")
