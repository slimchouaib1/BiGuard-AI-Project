import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from datetime import datetime, timedelta
import joblib
import os
from pymongo import MongoClient
from bson import ObjectId

class AnomalyDetector:
    def __init__(self):
        self.isolation_forest = IsolationForest(
            contamination=0.1,  # Expect 10% of transactions to be anomalies
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.dbscan = DBSCAN(eps=0.5, min_samples=5)
        self.model_path = os.path.join(os.path.dirname(__file__), 'anomaly_detector.pkl')
        self.load_model()
        
        # MongoDB connection
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['biguard']
        self.transactions_collection = self.db['transactions']
        self.users_collection = self.db['users']
        # New collections for fraudulent transactions
        self.fraudulent_transactions_collection = self.db['fraudulent_transactions']
        self.sample_fraudulent_transactions_collection = self.db['sample_fraudulent_transactions']
    
    def load_model(self):
        """Load trained model if it exists"""
        if os.path.exists(self.model_path):
            try:
                model_data = joblib.load(self.model_path)
                self.isolation_forest = model_data['isolation_forest']
                self.scaler = model_data['scaler']
                self.dbscan = model_data['dbscan']
                print("Anomaly detection model loaded successfully")
            except Exception as e:
                print(f"Error loading anomaly detection model: {e}")
    
    def save_model(self):
        """Save trained model"""
        try:
            model_data = {
                'isolation_forest': self.isolation_forest,
                'scaler': self.scaler,
                'dbscan': self.dbscan
            }
            joblib.dump(model_data, self.model_path)
            print("Anomaly detection model saved successfully")
        except Exception as e:
            print(f"Error saving anomaly detection model: {e}")
    
    def extract_features(self, transactions):
        """Extract features from transactions for anomaly detection"""
        if not transactions:
            return pd.DataFrame()
        
        features = []
        for tx in transactions:
            # Basic transaction features
            amount = abs(float(tx.get('amount', 0)))
            is_expense = 1 if tx.get('is_expense', True) else 0
            
            # Time-based features
            tx_date = datetime.strptime(tx.get('date', '2025-01-01'), '%Y-%m-%d')
            day_of_week = tx_date.weekday()
            day_of_month = tx_date.day
            month = tx_date.month
            
            # Category encoding (simple hash-based encoding)
            category = tx.get('category', 'Unknown')
            category_hash = hash(category) % 1000  # Simple hash for category
            
            # Merchant features
            merchant_name = tx.get('merchant_name', '') or tx.get('name', '')
            merchant_length = len(merchant_name)
            has_numbers = 1 if any(c.isdigit() for c in merchant_name) else 0
            
            # Amount-based features
            amount_log = np.log(amount + 1)  # Log transform for skewed amounts
            amount_sqrt = np.sqrt(amount)  # Square root transform
            
            features.append([
                amount, amount_log, amount_sqrt, is_expense,
                day_of_week, day_of_month, month,
                category_hash, merchant_length, has_numbers
            ])
        
        return pd.DataFrame(features, columns=[
            'amount', 'amount_log', 'amount_sqrt', 'is_expense',
            'day_of_week', 'day_of_month', 'month',
            'category_hash', 'merchant_length', 'has_numbers'
        ])
    
    def train_model(self, user_id=None, data_type='real'):
        """Train the anomaly detection model on user's transaction data"""
        try:
            # Get transactions for training
            if user_id:
                # Train on specific user's data with data type filter
                if data_type == 'sample':
                    query = {'user_id': str(user_id), 'is_sample': True}
                else:
                    query = {'user_id': str(user_id), 'is_sample': {'$ne': True}}
            else:
                # Train on all available data
                query = {}
            
            transactions = list(self.transactions_collection.find(query))
            
            if len(transactions) < 10:
                print("Not enough transactions for training (need at least 10)")
                return False
            
            # Extract features
            features_df = self.extract_features(transactions)
            
            if features_df.empty:
                print("No features extracted from transactions")
                return False
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features_df)
            
            # Train Isolation Forest
            self.isolation_forest.fit(features_scaled)
            
            # Train DBSCAN for clustering
            self.dbscan.fit(features_scaled)
            
            # Save the trained model
            self.save_model()
            
            print(f"Anomaly detection model trained on {len(transactions)} transactions")
            return True
            
        except Exception as e:
            print(f"Error training anomaly detection model: {e}")
            return False
    
    def detect_anomalies(self, user_id, limit=50, data_type='real'):
        """Detect anomalies in user's recent transactions"""
        try:
            # Build query based on data type
            if data_type == 'sample':
                # Only look at sample transactions
                query = {'user_id': str(user_id), 'is_sample': True}
            else:
                # Look at real transactions (exclude sample)
                query = {'user_id': str(user_id), 'is_sample': {'$ne': True}}
            
            # Get user's recent transactions
            transactions = list(self.transactions_collection.find(query).sort('date', -1).limit(limit))
            
            if not transactions:
                return []
            
            # Check if model needs training (if we have enough data)
            if len(transactions) >= 10:
                try:
                    # Try to use the model, if it fails, train it
                    features_df = self.extract_features(transactions[:10])  # Use first 10 for testing
                    if not features_df.empty:
                        features_scaled = self.scaler.transform(features_df)
                except:
                    # Model not trained, train it now
                    print(f"Training anomaly detection model for user {user_id}")
                    self.train_model(user_id, data_type)
            
            # Extract features
            features_df = self.extract_features(transactions)
            
            if features_df.empty:
                return []
            
            # Scale features
            features_scaled = self.scaler.transform(features_df)
            
            # Detect anomalies using Isolation Forest
            anomaly_scores = self.isolation_forest.decision_function(features_scaled)
            anomaly_predictions = self.isolation_forest.predict(features_scaled)
            
            # Detect clusters using DBSCAN
            clusters = self.dbscan.fit_predict(features_scaled)
            
            # Combine results and identify anomalies
            anomalies = []
            for i, (tx, score, prediction, cluster) in enumerate(zip(transactions, anomaly_scores, anomaly_predictions, clusters)):
                is_anomaly = False
                anomaly_reason = []
                
                # Isolation Forest anomaly (prediction = -1 means anomaly)
                if prediction == -1:
                    is_anomaly = True
                    anomaly_reason.append("Unusual transaction pattern")
                
                # DBSCAN outlier (cluster = -1 means outlier)
                if cluster == -1:
                    is_anomaly = True
                    anomaly_reason.append("Transaction outside normal clusters")
                
                # Additional rule-based checks
                amount = abs(float(tx.get('amount', 0)))
                
                # Check for unusually large amounts
                if amount > 1000:  # Threshold for large transactions
                    is_anomaly = True
                    anomaly_reason.append("Unusually large amount")
                
                # Check for unusual timing (transactions outside normal hours)
                tx_date = datetime.strptime(tx.get('date', '2025-01-01'), '%Y-%m-%d')
                if tx_date.hour < 6 or tx_date.hour > 23:
                    is_anomaly = True
                    anomaly_reason.append("Unusual transaction time")
                
                # Check for rapid successive transactions
                if i > 0:
                    prev_tx = transactions[i-1]
                    prev_date = datetime.strptime(prev_tx.get('date', '2025-01-01'), '%Y-%m-%d')
                    time_diff = abs((tx_date - prev_date).total_seconds())
                    if time_diff < 300:  # Less than 5 minutes apart
                        is_anomaly = True
                        anomaly_reason.append("Rapid successive transactions")
                
                if is_anomaly:
                    # Save fraudulent transaction to appropriate collection
                    fraudulent_tx = {
                        'original_transaction_id': str(tx.get('_id')),
                        'user_id': str(user_id),
                        'transaction_data': tx,
                        'anomaly_score': float(score),
                        'reasons': anomaly_reason,
                        'severity': 'high' if len(anomaly_reason) > 2 else 'medium' if len(anomaly_reason) > 1 else 'low',
                        'detected_at': datetime.utcnow(),
                        'is_sample': data_type == 'sample',
                        'status': 'blocked'  # Transaction is blocked
                    }
                    
                    # Save to appropriate collection
                    if data_type == 'sample':
                        self.sample_fraudulent_transactions_collection.insert_one(fraudulent_tx)
                    else:
                        self.fraudulent_transactions_collection.insert_one(fraudulent_tx)
                    
                    anomalies.append({
                        'transaction_id': str(tx.get('_id')),
                        'transaction': tx,
                        'anomaly_score': float(score),
                        'reasons': anomaly_reason,
                        'severity': 'high' if len(anomaly_reason) > 2 else 'medium' if len(anomaly_reason) > 1 else 'low'
                    })
            
            # Sort by anomaly score (most anomalous first)
            anomalies.sort(key=lambda x: x['anomaly_score'])
            
            return anomalies
            
        except Exception as e:
            print(f"Error detecting anomalies: {e}")
            return []
    
    def get_anomaly_summary(self, user_id, data_type='real'):
        """Get a summary of detected anomalies for a user"""
        try:
            # Get fraudulent transactions from appropriate collection
            if data_type == 'sample':
                fraudulent_collection = self.sample_fraudulent_transactions_collection
            else:
                fraudulent_collection = self.fraudulent_transactions_collection
            
            # Get all fraudulent transactions for this user from the fraudulent collections
            fraudulent_transactions = list(fraudulent_collection.find({
                'user_id': str(user_id)
            }).sort('detected_at', -1))
            
            # Also get transactions that are already marked as fraudulent in the main transactions collection
            if data_type == 'sample':
                query = {'user_id': str(user_id), 'is_sample': True, 'is_fraudulent': True}
            else:
                query = {'user_id': str(user_id), 'is_sample': {'$ne': True}, 'is_fraudulent': True}
            
            already_fraudulent_transactions = list(self.transactions_collection.find(query))
            
            # Convert already fraudulent transactions to the same format
            for tx in already_fraudulent_transactions:
                # Check if this transaction is already in the fraudulent collection
                existing = fraudulent_collection.find_one({
                    'original_transaction_id': str(tx['_id'])
                })
                
                if not existing:
                    # Add it to the fraudulent collection
                    fraudulent_tx = {
                        'original_transaction_id': str(tx.get('_id')),
                        'user_id': str(user_id),
                        'transaction_data': tx,
                        'anomaly_score': tx.get('fraud_score', 0.8),  # Use fraud_score if available
                        'reasons': tx.get('anomaly_flags', ['Pre-marked as fraudulent']),
                        'severity': 'high' if tx.get('fraud_score', 0) > 0.8 else 'medium' if tx.get('fraud_score', 0) > 0.6 else 'low',
                        'detected_at': tx.get('created_at', datetime.utcnow()),
                        'is_sample': data_type == 'sample',
                        'status': 'blocked'
                    }
                    fraudulent_collection.insert_one(fraudulent_tx)
                    fraudulent_transactions.append(fraudulent_tx)
            
            if not fraudulent_transactions:
                return {
                    'total_anomalies': 0,
                    'high_severity': 0,
                    'medium_severity': 0,
                    'low_severity': 0,
                    'recent_anomalies': [],
                    'fraudulent_transactions': [],
                    'risk_level': 'low'
                }
            
            # Count by severity
            high_severity = len([ft for ft in fraudulent_transactions if ft['severity'] == 'high'])
            medium_severity = len([ft for ft in fraudulent_transactions if ft['severity'] == 'medium'])
            low_severity = len([ft for ft in fraudulent_transactions if ft['severity'] == 'low'])
            
            # Determine overall risk level
            if high_severity > 0:
                risk_level = 'high'
            elif medium_severity > 2:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            # Format fraudulent transactions for display
            formatted_fraudulent = []
            for ft in fraudulent_transactions:
                tx_data = ft['transaction_data']
                formatted_fraudulent.append({
                    'id': str(ft['_id']),
                    'transaction_id': ft['original_transaction_id'],
                    'name': tx_data.get('name', 'Unknown'),
                    'amount': tx_data.get('amount', 0),
                    'date': tx_data.get('date', 'Unknown'),
                    'category': tx_data.get('category', 'Unknown'),
                    'merchant_name': tx_data.get('merchant_name', ''),
                    'reasons': ft['reasons'],
                    'severity': ft['severity'],
                    'anomaly_score': ft['anomaly_score'],
                    'detected_at': ft['detected_at'],
                    'status': ft['status']
                })
            
            return {
                'total_anomalies': len(fraudulent_transactions),
                'high_severity': high_severity,
                'medium_severity': medium_severity,
                'low_severity': low_severity,
                'recent_anomalies': formatted_fraudulent[:5],  # Top 5 most recent
                'fraudulent_transactions': formatted_fraudulent,
                'risk_level': risk_level
            }
            
        except Exception as e:
            print(f"Error getting anomaly summary: {e}")
            return {
                'total_anomalies': 0,
                'high_severity': 0,
                'medium_severity': 0,
                'low_severity': 0,
                'recent_anomalies': [],
                'fraudulent_transactions': [],
                'risk_level': 'low'
            }
    
    def clear_fraudulent_transactions(self, user_id, data_type='real'):
        """Clear all fraudulent transactions for a user"""
        try:
            # Clear from fraudulent collections
            if data_type == 'sample':
                result = self.sample_fraudulent_transactions_collection.delete_many({
                    'user_id': str(user_id)
                })
                # Also clear from main transactions collection
                main_result = self.transactions_collection.update_many(
                    {'user_id': str(user_id), 'is_sample': True, 'is_fraudulent': True},
                    {'$unset': {'is_fraudulent': '', 'anomaly_flags': '', 'fraud_score': ''}}
                )
            else:
                result = self.fraudulent_transactions_collection.delete_many({
                    'user_id': str(user_id)
                })
                # Also clear from main transactions collection
                main_result = self.transactions_collection.update_many(
                    {'user_id': str(user_id), 'is_sample': {'$ne': True}, 'is_fraudulent': True},
                    {'$unset': {'is_fraudulent': '', 'anomaly_flags': '', 'fraud_score': ''}}
                )
            
            return result.deleted_count
            
        except Exception as e:
            print(f"Error clearing fraudulent transactions: {e}")
            return 0
    
    def mark_transaction_as_fraudulent(self, transaction_id, is_fraudulent=True):
        """Mark a transaction as fraudulent or legitimate"""
        try:
            result = self.transactions_collection.update_one(
                {'_id': ObjectId(transaction_id)},
                {'$set': {'is_fraudulent': is_fraudulent}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error marking transaction as fraudulent: {e}")
            return False

# Global instance
anomaly_detector = AnomalyDetector()
