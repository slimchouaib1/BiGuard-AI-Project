import os
import pickle
import pandas as pd

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'category_classifier.pkl')

class CategoryPredictor:
    def __init__(self):
        with open(MODEL_PATH, 'rb') as f:
            self.pipeline = pickle.load(f)

    def predict(self, name, amount):
        data = pd.DataFrame({'name': [name], 'amount': [amount]})
        return self.pipeline.predict(data)[0]

# Singleton instance for backend use
predictor = CategoryPredictor()

def predict_category(name, amount):
    return predictor.predict(name, amount)
