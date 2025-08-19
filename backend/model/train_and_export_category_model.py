# Train and export category classification model

import os
import pickle
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import ColumnTransformer

pipeline_path = os.path.join(os.path.dirname(__file__), 'category_classifier.pkl')
if os.path.exists(pipeline_path):
    with open(pipeline_path, 'rb') as f:
        pipeline = pickle.load(f)
else:
    pipeline = None  # Not trained yet

# Only load CSV and train if running as a script
if __name__ == "__main__":
    # Load data from backend/model/transactions.csv
    df = pd.read_csv('backend/model/transactions.csv')

    X = df[['name', 'amount']]
    y = df['category']

    # Split (not strictly needed for export, but for completeness)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Preprocessing
    name_vectorizer = TfidfVectorizer(ngram_range=(1,2), max_features=5000)
    preprocessor = ColumnTransformer([
        ('name', name_vectorizer, 'name'),
        ('amount', StandardScaler(), ['amount'])
    ])

    # Model
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', rf_model)
    ])

    pipeline.fit(X_train, y_train)

    # Export model
    with open('category_classifier.pkl', 'wb') as f:
        pickle.dump(pipeline, f)

    print('Model trained and saved as category_classifier.pkl')

