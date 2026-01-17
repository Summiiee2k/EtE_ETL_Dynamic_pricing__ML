import pandas as pd
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from contextlib import asynccontextmanager
import os
from src.trainer import run_retraining

# the standard contract for validating the input data
class PricingRequest(BaseModel):
    product_name: str
    base_price: float
    inventory_level: int

class PricingResponse(BaseModel):
    optimal_price: float
    probability: float
    expected_revenue: float
    model_active: bool

# global state, keeping the model in global state as I dont want o reload it 100 times all the time

model_state = {
    "model": None,
    "features": None
}

# --- NEW: BACKGROUND RETRAINER ---
def background_retrain():
    print("Background Task: Retraining initiated...")
    success = run_retraining()
    if success:
        print("Reloading Model in API...")
        load_model() # This refreshes the Global Variable
        print("System Healed! New model is live.")
    else:
        print("Retraining failed (insufficient data?)")

# lifespan, it runs once when we start the server
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Pricing API...")
    load_model()
    yield
    print("Shutting down API...")
    
def load_model():
    model_path = "A:\\study\\projects\\EtE_ETL_Dynamic_pricing__ML\\Notebook\\models\\predictor4.pkl"
    model_features_path = "A:\\study\\projects\\EtE_ETL_Dynamic_pricing__ML\\Notebook\\models\\model_features.pkl"
    
    if os.path.exists(model_path) and os.path.exists(model_features_path):
        model_state["model"] = joblib.load(model_path)
        model_state["features"] = joblib.load(model_features_path)
        print("Model & Features Loaded!")
    else:
        raise HTTPException(status_code=500, detail="Model or features not found")

# Initialze the APP
app = FastAPI(lifespan=lifespan)
@app.post("/retrain")
def trigger_retrain(background_tasks: BackgroundTasks):
    # We don't wait for training to finish. We return "OK" immediately.
    background_tasks.add_task(background_retrain)
    return {"status": "Retraining started in background"}


@app.get("/")
def health_check():
    return {"status": "Working", "model_loaded": model_state["model"] is not None}

@app.post("/predict", response_model=PricingResponse)
def predict_price(request: PricingRequest):
    
    if not model_state.get("model") or not model_state.get("features"):
        
        return {
            "optimal_price": request.base_price,
            "probability": 0.0,
            "expected_revenue": 0.0,
            "model_active": False
        }

    model = model_state["model"]
    features = model_state["features"]
    
    # Generate 20 candidates
    candidates = np.linspace(request.base_price * 0.7, request.base_price * 1.6, 20)
    
    # Create DataFrame
    input_df = pd.DataFrame({
        'price_offered': candidates,
        'inventory_level': [request.inventory_level] * 20
    })
    
    # One-Hot Encoding Logic
    for feature in features:
        if feature not in ['price_offered', 'inventory_level']:
            if feature == f"product_name_{request.product_name}":
                input_df[feature] = 1
            else:
                input_df[feature] = 0
                
    # Reorder to match training
    input_df = input_df[features]
    
    # Predict
    try:
        buy_probs = model.predict_proba(input_df)[:, 1]
        expected_revenues = candidates * buy_probs
        best_index = np.argmax(expected_revenues)
        
        return {
            "optimal_price": float(candidates[best_index]),
            "probability": float(buy_probs[best_index]),
            "expected_revenue": float(expected_revenues[best_index]),
            "model_active": True
        }
    except Exception as e:
        print(f"Prediction Error: {e}")
        raise HTTPException(status_code=500, detail="Model prediction failed")


# --- AUTO-RELOAD ENDPOINT (For Phase 3B) ---
@app.post("/reload")
def trigger_reload():
    load_model()
    return {"status": "Reloaded latest model"}
    
