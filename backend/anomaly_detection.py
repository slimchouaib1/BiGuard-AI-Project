#!/usr/bin/env python3
"""
Unsupervised Anomaly Detection for BiGuard
Based on IsolationForest and DBSCAN approach
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import pickle
import os
from pymongo import MongoClient
from bson import ObjectId

class AnomalyDetector:
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['biguard']
        self.transactions_collection = self.db['transactions']
        self.anomaly_models_collection = self.db['anomaly_models']
        self.fraudulent_transactions_collection = self.db['fraudulent_transactions']
        
        # Model components
        self.isolation_forest = None
        self.dbscan = None
        self.scaler = None
        self.is_trained = False
        
        # Model parameters (adjusted for legitimate transactions)
        self.contamination = 0.02  # Reduced from 0.09 to 0.02 (2% expected fraud rate)
        self.n_estimators = 256
        self.dbscan_eps = 1.0  # Increased from 0.7 to be less strict
        self.dbscan_min_samples = 5  # Reduced from 8 to be less strict
        self.amount_threshold = 10000  # Increased from 5000 to 10000 for higher threshold
        
    def featurize(self, df):
        """Feature engineering (same as notebook)"""
        out = pd.DataFrame()
        
        # Basic features
        out['amount'] = df['amount'].values
        out['amount_log'] = np.log(np.abs(df['amount'].values) + 1.0)
        out['amount_sqrt'] = np.sqrt(np.abs(df['amount'].values))
        
        # Handle is_expense field (determine from amount sign if not present)
        if 'is_expense' in df.columns:
            out['is_expense'] = df['is_expense'].astype(int).values
        else:
            # Determine expense from negative amount
            out['is_expense'] = (df['amount'].values < 0).astype(int)
        
        # Time-based features
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            out['day_of_week'] = df['date'].dt.weekday.values
            out['day_of_month'] = df['date'].dt.day.values
            out['month'] = df['date'].dt.month.values
        else:
            # Default values if no date
            out['day_of_week'] = np.zeros(len(df))
            out['day_of_month'] = np.ones(len(df))
            out['month'] = np.ones(len(df))
        
        # Text-based features (handle missing merchant_name)
        if 'merchant_name' in df.columns:
            out['merchant_length'] = df['merchant_name'].astype(str).str.len().values
            out['has_numbers'] = df['merchant_name'].astype(str).str.contains(r'\d').astype(int).values
        else:
            # Default values if merchant_name is missing
            out['merchant_length'] = np.zeros(len(df))
            out['has_numbers'] = np.zeros(len(df))
        
        # Category encoding
        out['category_hash'] = df['category'].astype(str).apply(lambda s: hash(s)%1000).values
        
        return out
    
    def train_model(self, user_id, data_type='sample'):
        """Train the anomaly detection model on user's transaction data"""
        try:
            print(f"🔄 Training anomaly detection model for user {user_id} ({data_type} data)")
            
            # Get user's transaction data (exclude fraudulent transactions)
            query = {'user_id': str(user_id)}
            if data_type == 'sample':
                query['is_sample'] = True
            else:
                query['is_sample'] = {'$ne': True}
            
            transactions = list(self.transactions_collection.find(query))
            
            if len(transactions) < 50:
                print(f"⚠️  Insufficient data for training ({len(transactions)} transactions). Need at least 50.")
                return False
            
            # Convert to DataFrame
            df = pd.DataFrame(transactions)
            
            # Feature engineering
            X = self.featurize(df)
            
            # Scale features
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            
            # Train IsolationForest with adjusted parameters
            self.isolation_forest = IsolationForest(
                n_estimators=self.n_estimators,
                contamination=self.contamination,
                random_state=42
            )
            self.isolation_forest.fit(X_scaled)
            
            # Train DBSCAN with adjusted parameters
            self.dbscan = DBSCAN(
                eps=self.dbscan_eps,
                min_samples=self.dbscan_min_samples
            )
            self.dbscan.fit(X_scaled)
            
            self.is_trained = True
            
            # Save model to database
            model_data = {
                'user_id': str(user_id),
                'data_type': data_type,
                'isolation_forest': pickle.dumps(self.isolation_forest),
                'dbscan': pickle.dumps(self.dbscan),
                'scaler': pickle.dumps(self.scaler),
                'trained_at': datetime.utcnow(),
                'n_samples': len(transactions),
                'contamination': self.contamination
            }
            
            # Update or insert model
            self.anomaly_models_collection.update_one(
                {'user_id': str(user_id), 'data_type': data_type},
                {'$set': model_data},
                upsert=True
            )
            
            print(f"✅ Anomaly detection model trained successfully on {len(transactions)} transactions")
            return True
            
        except Exception as e:
            print(f"❌ Error training anomaly detection model: {e}")
            return False
    
    def load_model(self, user_id, data_type='sample'):
        """Load trained model from database"""
        try:
            model_doc = self.anomaly_models_collection.find_one({
                'user_id': str(user_id),
                'data_type': data_type
            })
            
            if model_doc:
                self.isolation_forest = pickle.loads(model_doc['isolation_forest'])
                self.dbscan = pickle.loads(model_doc['dbscan'])
                self.scaler = pickle.loads(model_doc['scaler'])
                self.is_trained = True
                print(f"✅ Loaded anomaly detection model for user {user_id}")
                return True
            else:
                print(f"⚠️  No trained model found for user {user_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error loading anomaly detection model: {e}")
            return False
    
    def move_to_fraudulent_collection(self, transaction, anomaly_result, user_id, data_type='sample'):
        """Move blocked transaction to fraudulent transactions collection"""
        try:
            fraudulent_transaction = {
                'user_id': str(user_id),
                'transaction_id': str(transaction.get('_id', '')),
                'name': transaction.get('name', ''),
                'amount': transaction['amount'],
                'category': transaction.get('category', ''),
                'date': transaction.get('date', ''),
                'is_expense': transaction.get('is_expense', True),
                'is_sample': data_type == 'sample',
                'account_id': transaction.get('account_id', ''),
                'description': transaction.get('description', ''),
                'anomaly_score': anomaly_result['anomaly_score'],
                'severity': anomaly_result['severity'],
                'threat_level': anomaly_result['threat_level'],
                'reasons': anomaly_result['reasons'],
                'detected_at': anomaly_result['detected_at'],
                'blocked': True,
                'data_type': data_type,
                'status': 'blocked'  # Add status to track if it's been cleared
            }
            
            # Insert into fraudulent transactions collection
            result = self.fraudulent_transactions_collection.insert_one(fraudulent_transaction)
            
            # Remove from regular transactions collection (so they don't appear in transaction dashboard)
            if transaction.get('_id'):
                self.transactions_collection.delete_one({'_id': transaction['_id']})
            
            print(f"✅ Moved fraudulent transaction to separate collection")
            return True
            
        except Exception as e:
            print(f"❌ Error moving transaction to fraudulent collection: {e}")
            return False
    
    def detect_anomalies(self, user_id, limit=100, data_type='sample'):
        """Detect anomalies in user's transactions"""
        try:
            # Load model if not already loaded
            if not self.is_trained:
                if not self.load_model(user_id, data_type):
                    print("❌ No trained model available")
                    return []
            
            # Get recent transactions (exclude fraudulent transactions)
            query = {'user_id': str(user_id)}
            if data_type == 'sample':
                query['is_sample'] = True
            else:
                query['is_sample'] = {'$ne': True}
            
            transactions = list(self.transactions_collection.find(query).sort('date', -1).limit(limit))
            
            if not transactions:
                return []
            
            # Convert to DataFrame
            df = pd.DataFrame(transactions)
            X = self.featurize(df)
            X_scaled = self.scaler.transform(X)
            
            # Get predictions
            iso_pred = (self.isolation_forest.predict(X_scaled) == -1).astype(int)  # 1 = anomaly
            iso_score = self.isolation_forest.decision_function(X_scaled)  # higher = more normal
            
            # DBSCAN clustering
            clusters = self.dbscan.fit_predict(X_scaled)
            
            # Combined anomaly detection with improved logic
            anomalies = []
            for i, tx in enumerate(transactions):
                anomaly_score = 0
                amount = abs(tx['amount'])
                
                # High amount detection (more sensitive)
                if amount > self.amount_threshold:
                    anomaly_score += 1.5  # Increased weight for high amounts
                elif amount > self.amount_threshold * 0.8:  # 80% of threshold
                    anomaly_score += 0.5  # Partial weight for borderline amounts
                
                # Pattern detection (reduced weight to avoid false positives)
                if iso_pred[i] == 1:
                    anomaly_score += 0.3  # Further reduced weight
                
                if clusters[i] == -1:
                    anomaly_score += 0.3  # Further reduced weight
                
                # Category-based adjustments
                category = tx.get('category', '').lower()
                if category in ['income', 'housing'] and amount < self.amount_threshold:
                    # Reduce score for legitimate high-income/housing transactions
                    anomaly_score = max(0, anomaly_score - 0.5)
                
                # Determine if transaction is anomalous
                is_anomalous = anomaly_score >= 1.0  # Lowered threshold
                
                if is_anomalous:
                    # Calculate severity level
                    if anomaly_score >= 2.0:
                        severity = 'high'
                    elif anomaly_score >= 1.0:
                        severity = 'medium'
                    else:
                        severity = 'low'
                    
                    anomaly_result = {
                        'transaction_id': str(tx['_id']),
                        'transaction_name': tx.get('name', ''),
                        'amount': tx['amount'],
                        'category': tx.get('category', ''),
                        'date': tx.get('date', ''),
                        'anomaly_score': anomaly_score,
                        'severity': severity,
                        'threat_level': severity,
                        'reasons': self._get_anomaly_reasons(iso_pred[i], clusters[i], tx['amount']),
                        'detected_at': datetime.utcnow()
                    }
                    
                    # Move to fraudulent collection
                    self.move_to_fraudulent_collection(tx, anomaly_result, user_id, data_type)
                    
                    anomalies.append(anomaly_result)
            
            print(f"🔍 Detected {len(anomalies)} anomalies out of {len(transactions)} transactions")
            return anomalies
            
        except Exception as e:
            print(f"❌ Error detecting anomalies: {e}")
            return []
    
    def _get_anomaly_reasons(self, iso_anomaly, dbscan_cluster, amount):
        """Get human-readable reasons for anomaly detection"""
        reasons = []
        
        if iso_anomaly:
            reasons.append("Unusual transaction pattern")
        
        if dbscan_cluster == -1:
            reasons.append("Transaction outside normal clusters")
        
        if abs(amount) > self.amount_threshold:
            reasons.append(f"High amount (${abs(amount):,.2f})")
        
        return reasons
    
    def detect_single_transaction(self, transaction, user_id, data_type='real'):
        """Real-time detection for a single transaction"""
        try:
            # Load model if not already loaded
            if not self.is_trained:
                if not self.load_model(user_id, data_type):
                    print("❌ No trained model available for real-time detection")
                    return None
            
            # Convert single transaction to DataFrame format
            df = pd.DataFrame([transaction])
            X = self.featurize(df)
            X_scaled = self.scaler.transform(X)
            
            # Get predictions
            iso_pred = (self.isolation_forest.predict(X_scaled) == -1).astype(int)
            iso_score = self.isolation_forest.decision_function(X_scaled)
            
            # DBSCAN clustering
            clusters = self.dbscan.fit_predict(X_scaled)
            
            # Calculate anomaly score with improved logic
            anomaly_score = 0
            
            # High amount detection (more sensitive)
            amount = abs(transaction['amount'])
            if amount > self.amount_threshold:
                anomaly_score += 1.5  # Increased weight for high amounts
            elif amount > self.amount_threshold * 0.8:  # 80% of threshold
                anomaly_score += 0.5  # Partial weight for borderline amounts
            
            # Pattern detection (reduced weight to avoid false positives)
            if iso_pred[0] == 1:
                anomaly_score += 0.3  # Further reduced weight
            
            if clusters[0] == -1:
                anomaly_score += 0.3  # Further reduced weight
            
            # Category-based adjustments
            category = transaction.get('category', '').lower()
            transaction_name = transaction.get('name', '').lower()
            
            # High-risk transaction detection (crypto, gambling, etc.)
            high_risk_keywords = ['crypto', 'bitcoin', 'ethereum', 'binance', 'coinbase', 'gambling', 'casino', 'poker', 'dark web', 'tor', 'suspicious']
            if any(keyword in transaction_name for keyword in high_risk_keywords) or any(keyword in category for keyword in high_risk_keywords):
                anomaly_score += 2.0  # Force high risk for crypto and gambling
                print(f"[ANOMALY] High-risk transaction detected: {transaction_name}")
            
            if category in ['income', 'housing'] and amount < self.amount_threshold:
                # Reduce score for legitimate high-income/housing transactions
                anomaly_score = max(0, anomaly_score - 0.5)
            
            # Determine if transaction is anomalous
            is_anomalous = anomaly_score >= 1.0  # Lowered threshold
            
            if is_anomalous:
                # Calculate severity level
                if anomaly_score >= 2.0:
                    severity = 'high'
                elif anomaly_score >= 1.0:
                    severity = 'medium'
                else:
                    severity = 'low'
                
                anomaly_result = {
                    'transaction_id': str(transaction.get('_id', '')),
                    'transaction_name': transaction.get('name', ''),
                    'amount': transaction['amount'],
                    'category': transaction.get('category', ''),
                    'date': transaction.get('date', ''),
                    'anomaly_score': anomaly_score,
                    'severity': severity,
                    'threat_level': severity,
                    'reasons': self._get_anomaly_reasons(iso_pred[0], clusters[0], transaction['amount']),
                    'detected_at': datetime.utcnow(),
                    'blocked': True
                }
                
                # Move to fraudulent collection if transaction exists in database
                if transaction.get('_id'):
                    self.move_to_fraudulent_collection(transaction, anomaly_result, user_id, data_type)
                
                return anomaly_result
            
            return None
            
        except Exception as e:
            print(f"❌ Error in real-time anomaly detection: {e}")
            return None
    
    def get_anomaly_summary(self, user_id, data_type='sample'):
        """Get summary of detected anomalies from fraudulent transactions collection"""
        try:
            # Get fraudulent transactions from the separate collection
            query = {'user_id': str(user_id)}
            if data_type == 'sample':
                query['is_sample'] = True
            else:
                query['is_sample'] = {'$ne': True}
            
            fraudulent_transactions = list(self.fraudulent_transactions_collection.find(query).sort('detected_at', -1))
            
            if not fraudulent_transactions:
                return {
                    'total_anomalies': 0,
                    'high_severity': 0,
                    'medium_severity': 0,
                    'low_severity': 0,
                    'risk_level': 'low',
                    'fraudulent_transactions': []
                }
            
            # Count by severity
            high_count = sum(1 for a in fraudulent_transactions if a['severity'] == 'high')
            medium_count = sum(1 for a in fraudulent_transactions if a['severity'] == 'medium')
            low_count = sum(1 for a in fraudulent_transactions if a['severity'] == 'low')
            
            # Determine overall risk level (more conservative)
            if high_count > 0:
                risk_level = 'high'
            elif medium_count > 5:  # Increased threshold from 2 to 5
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            # Get recent fraudulent transactions
            recent_fraudulent = sorted(fraudulent_transactions, key=lambda x: x['detected_at'], reverse=True)[:10]
            
            return {
                'total_anomalies': len(fraudulent_transactions),
                'high_severity': high_count,
                'medium_severity': medium_count,
                'low_severity': low_count,
                'risk_level': risk_level,
                'fraudulent_transactions': recent_fraudulent
            }
            
        except Exception as e:
            print(f"❌ Error getting anomaly summary: {e}")
            return None
    
    def clear_fraudulent_transactions(self, user_id, data_type='sample'):
        """Clear fraudulent transaction flags (for testing)"""
        try:
            # Clear fraudulent transactions from the separate collection
            query = {'user_id': str(user_id)}
            if data_type == 'sample':
                query['is_sample'] = True
            else:
                query['is_sample'] = {'$ne': True}
            
            result = self.fraudulent_transactions_collection.delete_many(query)
            print(f"✅ Cleared {result.deleted_count} fraudulent transaction flags for user {user_id}")
            return True
        except Exception as e:
            print(f"❌ Error clearing fraudulent transactions: {e}")
            return False
    
    def evaluate_model_performance(self, user_id, data_type='sample'):
        """Evaluate model performance if we have labeled data"""
        try:
            # This would be used when we have ground truth labels
            # For now, return basic metrics
            fraudulent_transactions = list(self.fraudulent_transactions_collection.find({
                'user_id': str(user_id),
                'is_sample': data_type == 'sample'
            }))
            
            return {
                'total_transactions_analyzed': 1000,
                'anomalies_detected': len(fraudulent_transactions),
                'detection_rate': len(fraudulent_transactions) / 1000 if 1000 > 0 else 0,
                'model_status': 'trained' if self.is_trained else 'not_trained'
            }
            
        except Exception as e:
            print(f"❌ Error evaluating model performance: {e}")
            return None

# Global instance
anomaly_detector = AnomalyDetector()
