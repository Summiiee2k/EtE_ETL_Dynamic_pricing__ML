import random
import numpy as np
import pandas as pd
import os
import datetime
import joblib
import faker
import importlib
import requests

fake = faker.Faker()

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
        
        self.model = None
        self.model_features = None 
        
        if os.path.exists("A:\\study\\projects\\EtE_ETL_Dynamic_pricing__ML\\Notebook\\models\\predictor4.pkl"):
            self.model = joblib.load("A:\\study\\projects\\EtE_ETL_Dynamic_pricing__ML\\Notebook\\models\\predictor4.pkl")
            if os.path.exists("A:\\study\\projects\\EtE_ETL_Dynamic_pricing__ML\\Notebook\\models\\model_features.pkl"):
                self.model_features = joblib.load("A:\\study\\projects\\EtE_ETL_Dynamic_pricing__ML\\Notebook\\models\\model_features.pkl")
                print("AI Model & Features Loaded via FAST API ")

        self.csv_path = "data/transactions2.csv"
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

    def simulate_step(self):    
        # 1. Shopper Event
        if random.random() < 0.7: 
            shopper = Shopper()
            product = random.choice(self.products)
            decision, reason = shopper.decide(product)
            self.save_transaction(product, shopper, decision)

            if decision:
                product.inventory -= 1
                product.sold_count += 1
                product.revenue += product.price
                self.log(f"💰 **SALE:** {shopper.name} ({shopper.type}) bought {product.icon} **{product.name}** for €{product.price:.2f}.")
            else:
                if reason == "Stock Empty":
                    self.log(f"⚠️ **LOST SALE:** {shopper.name} wanted {product.name}, but it's out of stock!")
                else:
                    self.log(f"🚶 **WALK:** {shopper.name} ({shopper.type}) left. {product.name} at ${product.price:.2f} was {reason}.")

        # 2. AI Re-pricing
        if random.random() < 0.15:
            p = random.choice(self.products)
            new_price, prob, exp_rev = self.get_optimal_price(p)
            
            if abs(new_price - p.price) > 0.10:
                direction = "📈 Raising" if new_price > p.price else "📉 Dropping"
                self.log(f"🤖 **AI:** {direction} {p.name} to **€{new_price:.2f}**. Chance: {int(prob*100)}%. Exp.Rev: €{exp_rev:.2f}")
                p.update_price(new_price)   