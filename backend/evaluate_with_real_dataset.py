#!/usr/bin/env python3
"""
Evaluate anomaly detection model with real dataset
Uses the provided train/test CSV files for comprehensive evaluation
"""

import os
import sys
import pandas as pd
import numpy as np
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

class RealDatasetEvaluator:
    def __init__(self):
        self.detector = AnomalyDetector()
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['biguard']
        self.users_collection = self.db['users']
        self.transactions_collection = self.db['transactions']
    
    def load_dataset(self, csv_file_path, user_id, data_type='sample', is_test_data=True):
        """
        Load dataset from CSV file with the exact schema provided
        """
        print(f"📁 Loading dataset from: {csv_file_path}")
        
        try:
            # Load CSV file
            df = pd.read_csv(csv_file_path)
            print(f"   Loaded {len(df)} transactions")
            print(f"   Fraudulent transactions: {df['is_fraudulent'].sum()}")
            print(f"   Legitimate transactions: {len(df) - df['is_fraudulent'].sum()}")
            
            # Convert to transactions format
            test_transactions = []
            ground_truth = []
            
            for _, row in df.iterrows():
                # Handle NaN values
                transaction = {
                    'user_id': str(user_id),
                    'account_id': str(row['account_id']) if pd.notna(row['account_id']) else '',
                    'name': str(row['name']) if pd.notna(row['name']) else '',
                    'merchant_name': str(row['merchant_name']) if pd.notna(row['merchant_name']) else '',
                    'amount': float(row['amount']) if pd.notna(row['amount']) else 0.0,
                    'category': str(row['category']) if pd.notna(row['category']) else '',
                    'date': str(row['date']) if pd.notna(row['date']) else '',
                    'pending': bool(row['pending']) if pd.notna(row['pending']) else False,
                    'is_expense': bool(row['is_expense']) if pd.notna(row['is_expense']) else False,
                    'is_sample': data_type == 'sample',
                    'is_fraudulent': bool(row['is_fraudulent']) if pd.notna(row['is_fraudulent']) else False,
                    'is_test_data': is_test_data,
                    'note': str(row.get('note', '')) if pd.notna(row.get('note', '')) else ''
                }
                
                test_transactions.append(transaction)
                # Handle empty is_fraudulent values
                if pd.notna(row['is_fraudulent']) and row['is_fraudulent'] != '':
                    ground_truth.append(int(row['is_fraudulent']))
                else:
                    ground_truth.append(0)  # Default to legitimate if empty
            
            # Insert into database
            if test_transactions:
                self.transactions_collection.insert_many(test_transactions)
                print(f"✅ Inserted {len(test_transactions)} transactions into database")
            
            return test_transactions, ground_truth
            
        except Exception as e:
            print(f"❌ Error loading dataset: {e}")
            return None, None
    
    def train_model_on_dataset(self, train_csv_path, user_id, data_type='sample'):
        """Train the anomaly detection model on the training dataset"""
        print(f"\n🔄 Training model on training dataset...")
        
        # Load training data
        train_transactions, _ = self.load_dataset(train_csv_path, user_id, data_type, is_test_data=False)
        
        if not train_transactions:
            print("❌ Failed to load training dataset")
            return False
        
        # Train the model
        try:
            success = self.detector.train_model(user_id, data_type)
            if success:
                print("✅ Model trained successfully on training dataset")
            else:
                print("❌ Failed to train model")
            return success
        except Exception as e:
            print(f"❌ Error training model: {e}")
            return False
    
    def evaluate_model(self, test_csv_path, user_id, data_type='sample'):
        """Evaluate the anomaly detection model on test dataset"""
        print(f"\n🧪 Evaluating Anomaly Detection Model")
        print("=" * 60)
        
        # Load test dataset
        test_transactions, ground_truth = self.load_dataset(test_csv_path, user_id, data_type, is_test_data=True)
        
        if not test_transactions:
            print("❌ Failed to load test dataset")
            return None
        
        # Run anomaly detection
        print(f"\n🔍 Running anomaly detection on test data...")
        anomalies = self.detector.detect_anomalies(user_id, limit=200, data_type=data_type)
        
        # Get predictions
        predictions = []
        anomaly_scores = []
        
        for tx in test_transactions:
            # Check if transaction was flagged as anomalous
            matching_anomaly = next((anomaly for anomaly in anomalies 
                                   if anomaly['transaction_id'] == str(tx['_id'])), None)
            
            if matching_anomaly:
                predictions.append(1)  # Flagged as fraudulent
                anomaly_scores.append(matching_anomaly['anomaly_score'])
            else:
                predictions.append(0)  # Not flagged
                anomaly_scores.append(0.0)  # Default score for non-anomalies
        
        # Calculate metrics
        print(f"\n📊 Calculating evaluation metrics...")
        
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
        
        # Balanced Accuracy
        balanced_accuracy = (recall + specificity) / 2
        
        print(f"\n🔍 Additional Metrics:")
        print(f"   Specificity (TNR): {specificity:.4f}")
        print(f"   False Positive Rate: {fpr:.4f}")
        print(f"   False Negative Rate: {fnr:.4f}")
        print(f"   Balanced Accuracy: {balanced_accuracy:.4f}")
        
        # Performance analysis
        print(f"\n📊 Performance Analysis:")
        print(f"   Total Test Transactions: {len(test_transactions)}")
        print(f"   Actual Fraudulent: {sum(ground_truth)}")
        print(f"   Actual Legitimate: {len(ground_truth) - sum(ground_truth)}")
        print(f"   Detected as Fraudulent: {sum(predictions)}")
        print(f"   Detected as Legitimate: {len(predictions) - sum(predictions)}")
        
        # Analyze fraudulent transactions
        print(f"\n🔍 Fraudulent Transaction Analysis:")
        fraudulent_txs = [tx for tx, gt in zip(test_transactions, ground_truth) if gt == 1]
        detected_fraudulent = [tx for tx, pred in zip(test_transactions, predictions) if pred == 1]
        
        print(f"   Total fraudulent in test: {len(fraudulent_txs)}")
        print(f"   Correctly detected: {len([tx for tx in fraudulent_txs if tx in detected_fraudulent])}")
        print(f"   Missed: {len(fraudulent_txs) - len([tx for tx in fraudulent_txs if tx in detected_fraudulent])}")
        
        # Show examples of missed fraudulent transactions
        missed_fraudulent = [tx for tx in fraudulent_txs if tx not in detected_fraudulent]
        if missed_fraudulent:
            print(f"\n❌ Missed Fraudulent Transactions:")
            for i, tx in enumerate(missed_fraudulent[:5]):  # Show first 5
                print(f"   {i+1}. {tx['name']} - ${tx['amount']:.2f} - {tx['category']}")
        
        # Show examples of false positives
        false_positives = [tx for tx, gt, pred in zip(test_transactions, ground_truth, predictions) 
                          if gt == 0 and pred == 1]
        if false_positives:
            print(f"\n⚠️  False Positive Transactions:")
            for i, tx in enumerate(false_positives[:5]):  # Show first 5
                print(f"   {i+1}. {tx['name']} - ${tx['amount']:.2f} - {tx['category']}")
        
        # Save results
        results = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'specificity': specificity,
            'false_positive_rate': fpr,
            'false_negative_rate': fnr,
            'balanced_accuracy': balanced_accuracy,
            'confusion_matrix': cm.tolist(),
            'test_transactions_count': len(test_transactions),
            'actual_fraudulent': sum(ground_truth),
            'actual_legitimate': len(ground_truth) - sum(ground_truth),
            'detected_fraudulent': sum(predictions),
            'detected_legitimate': len(predictions) - sum(predictions),
            'missed_fraudulent': len(missed_fraudulent),
            'false_positives': len(false_positives),
            'evaluation_date': datetime.now().isoformat()
        }
        
        # Save to database
        self.db['anomaly_evaluation_results'].insert_one(results)
        print(f"\n💾 Results saved to database")
        
        return results
    
    def clean_test_data(self, user_id, data_type='sample'):
        """Clean up test data after evaluation"""
        print(f"\n🧹 Cleaning up test data...")
        
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
    evaluator = RealDatasetEvaluator()
    
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
    
    # Check if CSV files are provided
    if len(sys.argv) < 3:
        print("❌ Please provide both train and test CSV files:")
        print("   python evaluate_with_real_dataset.py transactions_train.csv transactions_test.csv")
        return
    
    train_csv_path = sys.argv[1]
    test_csv_path = sys.argv[2]
    
    print(f"📁 Training dataset: {train_csv_path}")
    print(f"📁 Test dataset: {test_csv_path}")
    
    try:
        # First, train the model on training data
        train_success = evaluator.train_model_on_dataset(train_csv_path, user_id, data_type)
        
        if not train_success:
            print("❌ Failed to train model, cannot proceed with evaluation")
            return
        
        # Then evaluate on test data
        results = evaluator.evaluate_model(test_csv_path, user_id, data_type)
        
        if results:
            print(f"\n🎯 Evaluation completed successfully!")
            
            # Performance assessment
            if results['f1_score'] > 0.8:
                performance = "Excellent"
            elif results['f1_score'] > 0.7:
                performance = "Good"
            elif results['f1_score'] > 0.6:
                performance = "Fair"
            else:
                performance = "Poor"
            
            print(f"   Model Performance: {performance} (F1: {results['f1_score']:.4f})")
            
            # Recommendations
            print(f"\n💡 Recommendations:")
            if results['precision'] < 0.8:
                print(f"   - High false positives: Consider adjusting thresholds")
            if results['recall'] < 0.8:
                print(f"   - High false negatives: Consider lowering detection thresholds")
            if results['f1_score'] < 0.7:
                print(f"   - Overall performance needs improvement: Retrain model with more data")
            
            # Specific insights
            if results['missed_fraudulent'] > 0:
                print(f"   - {results['missed_fraudulent']} fraudulent transactions were missed")
            if results['false_positives'] > 0:
                print(f"   - {results['false_positives']} legitimate transactions were flagged as fraudulent")
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up test data
        evaluator.clean_test_data(user_id, data_type)

if __name__ == "__main__":
    main()
