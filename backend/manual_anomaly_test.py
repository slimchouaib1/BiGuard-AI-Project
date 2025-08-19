#!/usr/bin/env python3
"""
Manual test script to trigger anomaly detection
"""

import os
import sys
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from anomaly_detection import AnomalyDetector

def manual_anomaly_test():
    """Manually test anomaly detection"""
    print("🔍 Manual Anomaly Detection Test")
    print("=" * 50)
    
    # Initialize anomaly detector
    detector = AnomalyDetector()
    
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')
    db = client['biguard']
    users_collection = db['users']
    transactions_collection = db['transactions']
    
    # Find test user
    user = users_collection.find_one({'email': 'slimchouaib2798@gmail.com'})
    if not user:
        print("❌ Test user not found")
        return
    
    user_id = str(user['_id'])
    print(f"✅ Found test user: {user['email']}")
    
    # Check if user has sample data
    has_sample_data = user.get('has_sample_data', False)
    data_type = 'sample' if has_sample_data else 'real'
    print(f"📊 Data type: {data_type}")
    
    # Get all transactions for this user
    if data_type == 'sample':
        query = {'user_id': str(user_id), 'is_sample': True}
    else:
        query = {'user_id': str(user_id), 'is_sample': {'$ne': True}}
    
    all_transactions = list(transactions_collection.find(query))
    print(f"📋 Found {len(all_transactions)} transactions")
    
    # Show some transaction examples
    print("\n📝 Sample transactions:")
    for i, tx in enumerate(all_transactions[:5]):
        print(f"   {i+1}. {tx.get('name', 'Unknown')} - ${tx.get('amount', 0):.2f} - {tx.get('date', 'Unknown')}")
    
    # Manually trigger anomaly detection
    print(f"\n🚨 Triggering anomaly detection for {data_type} data...")
    anomalies = detector.detect_anomalies(user_id, limit=100, data_type=data_type)
    print(f"✅ Anomaly detection completed: {len(anomalies)} anomalies found")
    
    # Get anomaly summary
    print(f"\n📊 Getting anomaly summary...")
    summary = detector.get_anomaly_summary(user_id, data_type)
    print(f"   Total anomalies: {summary['total_anomalies']}")
    print(f"   High severity: {summary['high_severity']}")
    print(f"   Medium severity: {summary['medium_severity']}")
    print(f"   Low severity: {summary['low_severity']}")
    print(f"   Risk level: {summary['risk_level']}")
    
    # Check fraudulent transactions collections
    print(f"\n📋 Checking fraudulent transactions collections:")
    if data_type == 'sample':
        fraudulent_txs = list(detector.sample_fraudulent_transactions_collection.find({'user_id': user_id}))
    else:
        fraudulent_txs = list(detector.fraudulent_transactions_collection.find({'user_id': user_id}))
    
    print(f"   Found {len(fraudulent_txs)} fraudulent transactions in {data_type} collection")
    
    for i, ftx in enumerate(fraudulent_txs):
        tx_data = ftx['transaction_data']
        print(f"   {i+1}. {tx_data.get('name', 'Unknown')} - ${tx_data.get('amount', 0):.2f}")
        print(f"      Severity: {ftx['severity']}, Reasons: {', '.join(ftx['reasons'])}")
    
    print("\n✅ Manual test completed!")

if __name__ == "__main__":
    manual_anomaly_test()
