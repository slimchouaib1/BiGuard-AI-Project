#!/usr/bin/env python3
"""
Evaluate anomaly detection model with custom dataset
You can provide your own dataset with known fraudulent/legitimate transactions
"""

import os
import sys
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from anomaly_detection import AnomalyDetector

class CustomDatasetEvaluator:
    def __init__(self):
        self.detector = AnomalyDetector()
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['biguard']
        self.users_collection = self.db['users']
        self.transactions_collection = self.db['transactions']
    
    def load_custom_dataset(self, csv_file_path, user_id, data_type='sample'):
        """
        Load custom dataset from CSV file
        Expected CSV columns: name, amount, category, date, is_fraudulent (0/1)
        """
        print(f"📁 Loading custom dataset from: {csv_file_path}")
        
        try:
            # Load CSV file
            df = pd.read_csv(csv_file_path)
            
            # Validate required columns
            required_columns = ['name', 'amount', 'category', 'date', 'is_fraudulent']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                print(f"❌ Missing required columns: {missing_columns}")
                print(f"   Expected columns: {required_columns}")
                return None, None
            
            # Convert to transactions format
            test_transactions = []
            ground_truth = []
            
            for _, row in df.iterrows():
                transaction = {
                    'user_id': str(user_id),
                    'name': str(row['name']),
                    'amount': float(row['amount']),
                    'category': str(row['category']),
                    'date': str(row['date']),
                    'is_expense': float(row['amount']) < 0,  # Negative amounts are expenses
                    'is_sample': data_type == 'sample',
                    'is_fraudulent': bool(row['is_fraudulent']),
                    'is_test_data': True
                }
                
                test_transactions.append(transaction)
                ground_truth.append(int(row['is_fraudulent']))
            
            # Insert into database
            if test_transactions:
                self.transactions_collection.insert_many(test_transactions)
                print(f"✅ Loaded {len(test_transactions)} transactions from custom dataset")
            
            return test_transactions, ground_truth
            
        except Exception as e:
            print(f"❌ Error loading dataset: {e}")
            return None, None
    
    def create_sample_csv_template(self, output_path='sample_dataset_template.csv'):
        """Create a sample CSV template for custom dataset"""
        sample_data = {
            'name': [
                'SUSPICIOUS ONLINE PURCHASE',
                'LATE NIGHT GAMING SITE',
                'UNKNOWN MERCHANT',
                'Salary - Company Inc',
                'Grocery Store',
                'Gas Station',
                'Netflix Subscription'
            ],
            'amount': [
                2500.00,
                900.50,
                1500.00,
                5000.00,
                -85.50,
                -45.00,
                -15.99
            ],
            'category': [
                'Shopping',
                'Entertainment',
                'Shopping',
                'Income',
                'Food & Dining',
                'Transportation',
                'Entertainment'
            ],
            'date': [
                '2025-08-21',
                '2025-08-21',
                '2025-08-21',
                '2025-08-01',
                '2025-08-15',
                '2025-08-10',
                '2025-08-01'
            ],
            'is_fraudulent': [
                1,  # 1 for fraudulent
                1,  # 1 for fraudulent
                1,  # 1 for fraudulent
                0,  # 0 for legitimate
                0,  # 0 for legitimate
                0,  # 0 for legitimate
                0   # 0 for legitimate
            ]
        }
        
        df = pd.DataFrame(sample_data)
        df.to_csv(output_path, index=False)
        print(f"✅ Created sample CSV template: {output_path}")
        print(f"   Format: name, amount, category, date, is_fraudulent")
        print(f"   is_fraudulent: 1 = fraudulent, 0 = legitimate")
        return output_path
    
    def evaluate_with_custom_dataset(self, csv_file_path, user_id, data_type='sample'):
        """Evaluate model with custom dataset"""
        print("🧪 Evaluating with Custom Dataset")
        print("=" * 50)
        
        # Load custom dataset
        test_transactions, ground_truth = self.load_custom_dataset(csv_file_path, user_id, data_type)
        
        if not test_transactions:
            print("❌ Failed to load custom dataset")
            return None
        
        # Run anomaly detection
        print("\n🔍 Running anomaly detection...")
        anomalies = self.detector.detect_anomalies(user_id, limit=200, data_type=data_type)
        
        # Get predictions
        predictions = []
        for tx in test_transactions:
            # Check if transaction was flagged as anomalous
            is_flagged = any(anomaly['transaction_id'] == str(tx['_id']) for anomaly in anomalies)
            predictions.append(1 if is_flagged else 0)
        
        # Calculate metrics
        print("\n📊 Calculating metrics...")
        
        accuracy = accuracy_score(ground_truth, predictions)
        precision = precision_score(ground_truth, predictions, zero_division=0)
        recall = recall_score(ground_truth, predictions, zero_division=0)
        f1 = f1_score(ground_truth, predictions, zero_division=0)
        cm = confusion_matrix(ground_truth, predictions)
        
        # Print results
        print(f"\n📈 Evaluation Results:")
        print(f"   Accuracy:  {accuracy:.4f}")
        print(f"   Precision: {precision:.4f}")
        print(f"   Recall:    {recall:.4f}")
        print(f"   F1-Score:  {f1:.4f}")
        
        print(f"\n📋 Confusion Matrix:")
        print(f"   True Negatives (TN): {cm[0,0]} - Correctly identified legitimate")
        print(f"   False Positives (FP): {cm[0,1]} - Legitimate flagged as fraudulent")
        print(f"   False Negatives (FN): {cm[1,0]} - Fraudulent not detected")
        print(f"   True Positives (TP): {cm[1,1]} - Correctly identified fraudulent")
        
        print(f"\n📄 Classification Report:")
        print(classification_report(ground_truth, predictions, 
                                  target_names=['Legitimate', 'Fraudulent']))
        
        # Performance analysis
        print(f"\n📊 Dataset Analysis:")
        print(f"   Total Transactions: {len(test_transactions)}")
        print(f"   Actual Fraudulent: {sum(ground_truth)}")
        print(f"   Actual Legitimate: {len(ground_truth) - sum(ground_truth)}")
        print(f"   Detected as Fraudulent: {sum(predictions)}")
        print(f"   Detected as Legitimate: {len(predictions) - sum(predictions)}")
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'confusion_matrix': cm.tolist(),
            'dataset_size': len(test_transactions),
            'actual_fraudulent': sum(ground_truth),
            'actual_legitimate': len(ground_truth) - sum(ground_truth)
        }
    
    def clean_custom_test_data(self, user_id, data_type='sample'):
        """Clean up custom test data"""
        print("\n🧹 Cleaning up custom test data...")
        
        # Remove test transactions
        if data_type == 'sample':
            query = {'user_id': str(user_id), 'is_sample': True, 'is_test_data': True}
        else:
            query = {'user_id': str(user_id), 'is_sample': {'$ne': True}, 'is_test_data': True}
        
        result = self.transactions_collection.delete_many(query)
        print(f"✅ Removed {result.deleted_count} test transactions")
        
        # Clear fraudulent transactions from test
        self.detector.clear_fraudulent_transactions(user_id, data_type)
        print(f"✅ Cleared fraudulent transactions from test")

def main():
    """Main function for custom dataset evaluation"""
    evaluator = CustomDatasetEvaluator()
    
    # Find test user
    user = evaluator.users_collection.find_one({'email': 'slimchouaib2798@gmail.com'})
    if not user:
        print("❌ Test user not found")
        return
    
    user_id = str(user['_id'])
    print(f"✅ Found test user: {user['email']}")
    
    # Check if user has sample data
    has_sample_data = user.get('has_sample_data', False)
    data_type = 'sample' if has_sample_data else 'real'
    print(f"📊 Data type: {data_type}")
    
    # Check if CSV file is provided
    if len(sys.argv) > 1:
        csv_file_path = sys.argv[1]
        print(f"📁 Using custom dataset: {csv_file_path}")
    else:
        # Create sample template
        csv_file_path = evaluator.create_sample_csv_template()
        print(f"\n📝 No dataset provided. Created sample template: {csv_file_path}")
        print(f"   Please edit this file with your data and run again:")
        print(f"   python evaluate_with_custom_dataset.py {csv_file_path}")
        return
    
    try:
        # Run evaluation
        results = evaluator.evaluate_with_custom_dataset(csv_file_path, user_id, data_type)
        
        if results:
            print(f"\n🎯 Custom dataset evaluation completed!")
            print(f"   Model Performance: {'Good' if results['f1_score'] > 0.7 else 'Needs Improvement'}")
            
            # Recommendations
            print(f"\n💡 Recommendations:")
            if results['precision'] < 0.8:
                print(f"   - High false positives: Consider adjusting thresholds")
            if results['recall'] < 0.8:
                print(f"   - High false negatives: Consider lowering detection thresholds")
            if results['f1_score'] < 0.7:
                print(f"   - Overall performance needs improvement: Retrain model with more data")
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
    
    finally:
        # Clean up test data
        evaluator.clean_custom_test_data(user_id, data_type)

if __name__ == "__main__":
    main()
