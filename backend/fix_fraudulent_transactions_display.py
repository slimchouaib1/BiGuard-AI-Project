#!/usr/bin/env python3
"""
Fix script to move fraudulent transactions to the correct collection
so they appear in the dashboard fraud detection zone
"""

from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

def fix_fraudulent_transactions_display():
    """Move fraudulent transactions to the correct collection for dashboard display"""
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client['biguard']
        transactions_collection = db['transactions']
        fraudulent_transactions_collection = db['fraudulent_transactions']
        
        # Find all fraudulent transactions in the main collection
        fraudulent_transactions = list(transactions_collection.find({
            'is_fraudulent': True,
            'blocked': True
        }))
        
        print(f"🔍 Found {len(fraudulent_transactions)} fraudulent transactions in main collection")
        
        if not fraudulent_transactions:
            print("❌ No fraudulent transactions found to move")
            return False
        
        moved_count = 0
        for tx in fraudulent_transactions:
            print(f"📦 Processing: {tx.get('name', 'Unknown')} - ${tx.get('amount', 0):,.2f}")
            
            # Create fraudulent transaction document
            fraudulent_doc = {
                'user_id': tx.get('user_id', ''),
                'transaction_id': str(tx.get('_id', '')),
                'name': tx.get('name', ''),
                'amount': tx.get('amount', 0),
                'category': tx.get('category', ''),
                'date': tx.get('date', ''),
                'is_expense': tx.get('is_expense', True),
                'is_sample': tx.get('is_sample', False),
                'account_id': tx.get('account_id', ''),
                'description': tx.get('description', ''),
                'anomaly_score': tx.get('fraud_score', 0.9),
                'severity': tx.get('anomaly_severity', 'high'),
                'threat_level': tx.get('threat_level', 'high'),
                'reasons': tx.get('anomaly_reasons', ['High-risk transaction detected']),
                'detected_at': tx.get('created_at', datetime.utcnow()),
                'blocked': True,
                'data_type': 'sample' if tx.get('is_sample', False) else 'real',
                'status': 'blocked',
                'merchant_name': tx.get('merchant_name', '')
            }
            
            # Insert into fraudulent transactions collection
            result = fraudulent_transactions_collection.insert_one(fraudulent_doc)
            
            if result.inserted_id:
                print(f"   ✅ Moved to fraudulent collection")
                moved_count += 1
            else:
                print(f"   ❌ Failed to move")
        
        print(f"\n✅ Successfully moved {moved_count} fraudulent transactions")
        print(f"📊 Dashboard should now show {moved_count} fraudulent transactions detected & blocked")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing fraudulent transactions display: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_fraudulent_transactions_display()
