import random
import numpy as np
import pandas as pd
import os
import datetime
import joblib
import faker
import importlib
import requests

from collections import deque

fake = faker.Faker()

class DriftDetector:
    """The Observer: Tracks model performance in real-time"""
    def __init__(self, window_size=50, threshold=0.50):
        self.window_size = window_size
        self.threshold = threshold
        self.history = deque(maxlen=window_size) # Auto-removes old items
        self.drift_detected = False

    def add_event(self, predicted_prob, actual_outcome):
        # We consider a "Prediction" to be Positive if prob > 0.5
        predicted_outcome = 1 if predicted_prob > 0.5 else 0
        
        # Was the model correct? (True/False)
        is_correct = (predicted_outcome == actual_outcome)
        self.history.append(is_correct)

    def check_health(self):
        if len(self.history) < 10:
            return 1.0, False # Too early to tell, assume perfect health
        
        # Calculate Accuracy (Sum of True / Total)
        accuracy = sum(self.history) / len(self.history)
        
        # Check Drift
        if accuracy < self.threshold:
            self.drift_detected = True
        else:
            self.drift_detected = False
            
        return accuracy, self.drift_detected


class Product:
    def __init__(self, name, base_price, inventory, icon):
        self.name = name
        self.base_price = base_price
        self.price = base_price
        self.inventory = inventory
        self.icon = icon
        self.sold_count = 0
        self.revenue = 0.0

    def update_price(self, new_price):
        self.price = round(new_price, 2)

class Shopper:
    def __init__(self):
        self.name = fake.first_name()
        self.budget_multiplier = np.random.normal(1.0, 0.25)
        self.type = "Poor" if self.budget_multiplier < 0.9 else "Wealthy" if self.budget_multiplier > 1.1 else "Average"

    def decide(self, product):
        perceived_value = product.base_price * self.budget_multiplier
        
        if product.inventory <= 0:
            return False, "Stock Empty"
        
        if product.price <= perceived_value:
            return True, "Good Deal"
        else:
            diff = product.price - perceived_value
            return False, f"Too Expensive (Value: ${perceived_value:.2f})"

class Market:
    def __init__(self, products_config):
        self.products = [Product(**p) for p in products_config]
        self.logs = []
        self.csv_path = "data/transactions2.csv"
        self.drift_detector = DriftDetector()
        self.current_accuracy = 1.0
        self.last_retrain_time = datetime.datetime.min
        
        if not os.path.exists("data"):
            os.makedirs("data")
    def log(self, message):
        self.logs.insert(0, message) 
        if len(self.logs) > 50:
            self.logs.pop()

    def save_transaction(self, product, shopper, purchased):
        new_row = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "product_name": product.name,
            "price_offered": product.price,
            "inventory_level": product.inventory,
            "budget_multiplier": round(shopper.budget_multiplier, 2),
            "purchased": 1 if purchased else 0
        }
        df = pd.DataFrame([new_row])
        if not os.path.exists(self.csv_path):
            df.to_csv(self.csv_path, index=False)
        else:
            df.to_csv(self.csv_path, mode='a', header=False, index=False)

    def get_optimal_price(self, product):
        """Phase 3 Client: Asks the API for the price"""
        
        # Define the API Payload
        payload = {
            "product_name": product.name,
            "base_price": product.base_price,
            "inventory_level": product.inventory
        }
        try:
            # Send Request
            response = requests.post("http://127.0.0.1:8000/predict", json=payload, timeout=2.0)
            
            if response.status_code == 200:
                data = response.json()
                
                # --- DEBUG PRINT: START ---
                # Checking if the API is actually "Thinking" or just acting like a dumb ass bitch
                if data.get("model_active") is False:
                    print(f" API is in DUMB MODE (Model not loaded). returning base price.")
                else:
                    print(f" API Response for {product.name}: ${data['optimal_price']} (Prob: {data['probability']:.2f})")
                # --- DEBUG PRINT: END ---

                return data["optimal_price"], data["probability"], data["expected_revenue"]
            else:
                print(f" API Error: {response.status_code}")
                return product.base_price, 0, 0
        
        except Exception as e:
            print(f" API Connection Error: {e}")
            return product.base_price, 0, 0
    

    def trigger_healing(self):
        # Cooldown check: Only retrain once every 60 seconds
        now = datetime.datetime.now()
        if (now - self.last_retrain_time).total_seconds() < 60:
            return

        print("DRIFT DETECTED! Requesting Auto-Retrain...")
        try:
            requests.post("http://127.0.0.1:8000/retrain", timeout=1.0)
            self.last_retrain_time = now
            self.log("SYSTEM: Auto-Retraining triggered!")
            # Reset detector so we don't panic immediately again
            self.drift_detector.history.clear() 
        except:
            print("Failed to contact API for retraining.")

    def simulate_step(self):
        # 1. Shopper Event
        if random.random() < 0.7: 
            shopper = Shopper()
            product = random.choice(self.products)
            
            # BEFORE DECISION: Ask API what it *thinks* will happen
            # We call the API just to get the 'probability' for the Drift Detector
            # (In a real app, we would cache this from the pricing step)
            _, predicted_prob, _ = self.get_optimal_price(product)
            
            # REALITY: Shopper decides
            decision, reason = shopper.decide(product)
            self.save_transaction(product, shopper, decision)
            
            # --- NEW: FEED THE OBSERVER ---
            self.drift_detector.add_event(predicted_prob, 1 if decision else 0)
            acc, drift = self.drift_detector.check_health()
            self.current_accuracy = acc # Save for UI

            # LOG DRIFT
            if drift:
                 self.log(f" **DRIFT DETECTED!** Model Accuracy dropped to {int(acc*100)}%")
                 self.trigger_healing()

            if decision:
                product.inventory -= 1
                product.sold_count += 1
                product.revenue += product.price
                self.log(f"💰 **SALE:** {shopper.name} bought {product.name} (${product.price}).")
            else:
                if reason != "Stock Empty":
                    self.log(f"🚶 **WALK:** {shopper.name} left. {product.name} too high.")

        # 2. AI Re-pricing
        if random.random() < 0.15:
            p = random.choice(self.products)
            new_price, prob, exp_rev = self.get_optimal_price(p)
            
            if abs(new_price - p.price) > 0.10:
                direction = "📈 Raising" if new_price > p.price else "📉 Dropping"
                self.log(f"🤖 **AI:** {direction} {p.name} to **€{new_price:.2f}**. Chance: {int(prob*100)}%. Exp.Rev: €{exp_rev:.2f}")
                p.update_price(new_price)   