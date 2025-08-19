#!/usr/bin/env python3
"""
Test script to verify sample data generation
"""

import os
import sys
from sample_data_generator import generate_sample_data, clear_sample_data, get_financial_summary
from pymongo import MongoClient
from bson import ObjectId

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['biguard']
users_collection = db['users']
accounts_collection = db['accounts']
transactions_collection = db['transactions']
budgets_collection = db['budgets']

def test_sample_data_generation():
    """Test the sample data generation functionality"""
    
    # Create a test user
    test_user = {
        'first_name': 'Test',
        'last_name': 'User',
        'email': 'test@example.com',
        'password': 'hashed_password'
    }
    
    # Insert test user
    result = users_collection.insert_one(test_user)
    user_id = str(result.inserted_id)
    
    print(f"Created test user with ID: {user_id}")
    
    try:
        # Generate sample data
        print("\nGenerating sample data...")
        result = generate_sample_data(user_id, monthly_income=5500)
        
        if result['success']:
            print(f"✅ Sample data generated successfully!")
            print(f"   Monthly income: ${result['monthly_income']:,.2f}")
            print(f"   Accounts created: {result['accounts_created']}")
            print(f"   Transactions created: {result['transactions_created']}")
            print(f"   Budgets created: {result['budgets_created']}")
            
            # Verify data was created
            accounts = list(accounts_collection.find({'user_id': user_id}))
            transactions = list(transactions_collection.find({'user_id': user_id}))
            budgets = list(budgets_collection.find({'user_id': user_id}))
            
            print(f"\n📊 Verification:")
            print(f"   Accounts in DB: {len(accounts)}")
            print(f"   Transactions in DB: {len(transactions)}")
            print(f"   Budgets in DB: {len(budgets)}")
            
            # Show some sample transactions
            if transactions:
                print(f"\n💰 Sample transactions:")
                for i, tx in enumerate(transactions[:5]):
                    sign = "+" if not tx.get('is_expense', True) else "-"
                    print(f"   {i+1}. {tx['name']}: {sign}${tx['amount']:.2f} ({tx['category']})")
            
            # Get financial summary
            summary = get_financial_summary(user_id)
            if summary['success']:
                print(f"\n📈 Financial Summary:")
                print(f"   Monthly income: ${summary['monthly_income']:,.2f}")
                print(f"   Monthly expenses: ${summary['monthly_expenses']:,.2f}")
                print(f"   Net income: ${summary['net_income']:,.2f}")
                print(f"   Total balance: ${summary['total_balance']:,.2f}")
            
        else:
            print(f"❌ Failed to generate sample data: {result['error']}")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up - remove test user and all associated data
        print(f"\n🧹 Cleaning up test data...")
        clear_sample_data(user_id)
        users_collection.delete_one({'_id': ObjectId(user_id)})
        print("✅ Test data cleaned up")

if __name__ == "__main__":
    test_sample_data_generation()
