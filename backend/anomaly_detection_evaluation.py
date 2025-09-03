#!/usr/bin/env python3
"""
Comprehensive evaluation script for anomaly detection system
Tests accuracy, precision, recall, F1-score, and other metrics
"""

import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson import ObjectId
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score
)
import matplotlib.pyplot as plt
import seaborn as sns

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from anomaly_detection import AnomalyDetector

class AnomalyDetectionEvaluator:
    def __init__(self):
        self.detector = AnomalyDetector()
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['biguard']
        self.users_collection = self.db['users']
        self.transactions_collection = self.db['transactions']
        
    def create_test_dataset(self, user_id, data_type='sample'):
        """Create a test dataset with known fraudulent and legitimate transactions"""
        print("🔧 Creating test dataset...")
        
        # Get existing transactions
        if data_type == 'sample':
            query = {'user_id': str(user_id), 'is_sample': True}
        else:
            query = {'user_id': str(user_id), 'is_sample': {'$ne': True}}
        
        existing_transactions = list(self.transactions_collection.find(query))
        
        # Create ground truth labels
        ground_truth = []
        test_transactions = []
        
        # Mark some transactions as known fraudulent (for testing)
        fraudulent_patterns = [
            {'name': 'SUSPICIOUS ONLINE PURCHASE', 'amount': 2500, 'is_fraudulent': True},
            {'name': 'LATE NIGHT GAMING', 'amount': 900, 'is_fraudulent': True},
            {'name': 'UNKNOWN MERCHANT', 'amount': 1500, 'is_fraudulent': True},
            {'name': 'INTERNATIONAL TRANSFER', 'amount': 3000, 'is_fraudulent': True},
            {'name': 'CRYPTO EXCHANGE', 'amount': 2000, 'is_fraudulent': True},
        ]
        
        # Mark some transactions as known legitimate
        legitimate_patterns = [
            {'name': 'Salary - Company Inc', 'amount': 5000, 'is_fraudulent': False},
            {'name': 'Grocery Store', 'amount': 85, 'is_fraudulent': False},
            {'name': 'Gas Station', 'amount': 45, 'is_fraudulent': False},
            {'name': 'Netflix Subscription', 'amount': 16, 'is_fraudulent': False},
            {'name': 'Restaurant - Italian', 'amount': 65, 'is_fraudulent': False},
        ]
        
        # Create test transactions
        test_data = []
        
        # Add known fraudulent transactions
        for pattern in fraudulent_patterns:
            for i in range(5):  # Create 5 instances of each fraudulent pattern
                test_tx = {
                    'user_id': str(user_id),
                    'name': f"{pattern['name']} - Test {i+1}",
                    'amount': pattern['amount'] + np.random.randint(-100, 100),
                    'category': 'Shopping' if 'PURCHASE' in pattern['name'] else 'Entertainment',
                    'date': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                    'is_expense': True,
                    'is_sample': data_type == 'sample',
                    'is_fraudulent': pattern['is_fraudulent'],
                    'is_test_data': True  # Mark as test data
                }
                test_data.append(test_tx)
                ground_truth.append(1)  # 1 for fraudulent
                test_transactions.append(test_tx)
        
        # Add known legitimate transactions
        for pattern in legitimate_patterns:
            for i in range(10):  # Create 10 instances of each legitimate pattern
                test_tx = {
                    'user_id': str(user_id),
                    'name': f"{pattern['name']} - Test {i+1}",
                    'amount': pattern['amount'] + np.random.randint(-20, 20),
                    'category': 'Income' if 'Salary' in pattern['name'] else 'Food & Dining',
                    'date': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                    'is_expense': 'Salary' not in pattern['name'],
                    'is_sample': data_type == 'sample',
                    'is_fraudulent': pattern['is_fraudulent'],
                    'is_test_data': True  # Mark as test data
                }
                test_data.append(test_tx)
                ground_truth.append(0)  # 0 for legitimate
                test_transactions.append(test_tx)
        
        # Insert test transactions
        if test_data:
            self.transactions_collection.insert_many(test_data)
            print(f"✅ Created {len(test_data)} test transactions")
        
        return test_transactions, ground_truth
    
    def evaluate_model(self, user_id, data_type='sample'):
        """Evaluate the anomaly detection model"""
        print("🧪 Evaluating Anomaly Detection Model")
        print("=" * 60)
        
        # Create test dataset
        test_transactions, ground_truth = self.create_test_dataset(user_id, data_type)
        
        if not test_transactions:
            print("❌ No test transactions created")
            return
        
        # Run anomaly detection
        print("\n🔍 Running anomaly detection on test data...")
        anomalies = self.detector.detect_anomalies(user_id, limit=200, data_type=data_type)
        
        # Get predictions
        predictions = []
        for tx in test_transactions:
            # Check if transaction was flagged as anomalous
            is_flagged = any(anomaly['transaction_id'] == str(tx['_id']) for anomaly in anomalies)
            predictions.append(1 if is_flagged else 0)
        
        # Calculate metrics
        print("\n📊 Calculating evaluation metrics...")
        
        # Basic metrics
        accuracy = accuracy_score(ground_truth, predictions)
        precision = precision_score(ground_truth, predictions, zero_division=0)
        recall = recall_score(ground_truth, predictions, zero_division=0)
        f1 = f1_score(ground_truth, predictions, zero_division=0)
        
        # Confusion matrix
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
        
        # Detailed classification report
        print(f"\n📄 Detailed Classification Report:")
        print(classification_report(ground_truth, predictions, 
                                  target_names=['Legitimate', 'Fraudulent']))
        
        # Calculate additional metrics
        tn, fp, fn, tp = cm.ravel()
        
        # Specificity (True Negative Rate)
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        
        # False Positive Rate
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        
        # False Negative Rate
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
        
        print(f"\n🔍 Additional Metrics:")
        print(f"   Specificity (TNR): {specificity:.4f}")
        print(f"   False Positive Rate: {fpr:.4f}")
        print(f"   False Negative Rate: {fnr:.4f}")
        
        # Performance analysis
        print(f"\n📊 Performance Analysis:")
        print(f"   Total Test Transactions: {len(test_transactions)}")
        print(f"   Actual Fraudulent: {sum(ground_truth)}")
        print(f"   Actual Legitimate: {len(ground_truth) - sum(ground_truth)}")
        print(f"   Detected as Fraudulent: {sum(predictions)}")
        print(f"   Detected as Legitimate: {len(predictions) - sum(predictions)}")
        
        # Save results
        results = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'specificity': specificity,
            'false_positive_rate': fpr,
            'false_negative_rate': fnr,
            'confusion_matrix': cm.tolist(),
            'test_transactions_count': len(test_transactions),
            'actual_fraudulent': sum(ground_truth),
            'actual_legitimate': len(ground_truth) - sum(ground_truth),
            'detected_fraudulent': sum(predictions),
            'detected_legitimate': len(predictions) - sum(predictions),
            'evaluation_date': datetime.now().isoformat()
        }
        
        # Save to database
        self.db['anomaly_evaluation_results'].insert_one(results)
        print(f"\n💾 Results saved to database")
        
        return results
    
    def clean_test_data(self, user_id, data_type='sample'):
        """Clean up test data after evaluation"""
        print("\n🧹 Cleaning up test data...")
        
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
    """Main evaluation function"""
    evaluator = AnomalyDetectionEvaluator()
    
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
    
    try:
        # Run evaluation
        results = evaluator.evaluate_model(user_id, data_type)
        
        if results:
            print(f"\n🎯 Evaluation completed successfully!")
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
        evaluator.clean_test_data(user_id, data_type)

if __name__ == "__main__":
    main()
