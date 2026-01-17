import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import os

def run_retraining():
    print("♻️  TRAINING STARTED: Loading data...")
    
    # 1. Load Data
    if not os.path.exists("data/transactions2.csv"):
        print("No data found.")
        return False
        
    df = pd.read_csv("data/transactions2.csv")

    # 2. Cleaning
    df = df.dropna()
    df = df[df['purchased'].isin([0, 1])]
    df = df[df['inventory_level'] > 0] 

    if len(df) < 50:
        print("Not enough data to retrain yet.")
        return False

    # 3. Feature Engineering (One-Hot)
    df_encoded = pd.get_dummies(df, columns=['product_name'], drop_first=False)
    
    # Save feature names so we don't break the API
    feature_cols = ['price_offered', 'inventory_level'] + [c for c in df_encoded.columns if 'product_name_' in c]
    joblib.dump(feature_cols, "models/model_features.pkl")

    X = df_encoded[feature_cols]
    y = df_encoded['purchased'].astype(int)

    # 4. Train
    model = RandomForestClassifier(
        n_estimators=100, 
        max_depth=10, 
        class_weight="balanced",
        random_state=42
    )
    model.fit(X, y)
    
    # 5. Evaluate
    acc = accuracy_score(y, model.predict(X))
    print(f"New Model Trained! Accuracy: {acc:.2f}")

    # 6. Save
    if not os.path.exists("models"):
        os.makedirs("models")
    joblib.dump(model, "models/pricing_model.pkl")
    
    return True