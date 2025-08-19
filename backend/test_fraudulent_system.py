#!/usr/bin/env python3
"""
Test script to verify the fraudulent transaction system
"""

import os
import sys
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from anomaly_detection import AnomalyDetector

def test_fraudulent_system():
    """Test the fraudulent transaction system"""
    print("🧪 Testing Fraudulent Transaction System")
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
    
    # Get current anomaly summary
    print("\n🔍 Current Anomaly Summary:")
    summary = detector.get_anomaly_summary(user_id, data_type)
    print(f"   Total anomalies: {summary['total_anomalies']}")
    print(f"   High severity: {summary['high_severity']}")
    print(f"   Medium severity: {summary['medium_severity']}")
    print(f"   Low severity: {summary['low_severity']}")
    print(f"   Risk level: {summary['risk_level']}")
    
    # Check fraudulent transactions collections
    print("\n📋 Fraudulent Transactions:")
    if data_type == 'sample':
        fraudulent_txs = list(detector.sample_fraudulent_transactions_collection.find({'user_id': user_id}))
    else:
        fraudulent_txs = list(detector.fraudulent_transactions_collection.find({'user_id': user_id}))
    
    print(f"   Found {len(fraudulent_txs)} fraudulent transactions")
    
    for i, ftx in enumerate(fraudulent_txs[:3]):  # Show first 3
        tx_data = ftx['transaction_data']
        print(f"   {i+1}. {tx_data.get('name', 'Unknown')} - ${tx_data.get('amount', 0):.2f}")
        print(f"      Severity: {ftx['severity']}, Reasons: {', '.join(ftx['reasons'])}")
    
    # Test clearing fraudulent transactions
    print("\n🧹 Testing Clear Function:")
    deleted_count = detector.clear_fraudulent_transactions(user_id, data_type)
    print(f"   Cleared {deleted_count} fraudulent transactions")
    
    # Verify they're cleared
    summary_after = detector.get_anomaly_summary(user_id, data_type)
    print(f"   Anomalies after clearing: {summary_after['total_anomalies']}")
    
    print("\n✅ Test completed successfully!")

if __name__ == "__main__":
    test_fraudulent_system()
