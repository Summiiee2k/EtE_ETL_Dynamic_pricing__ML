import random
import numpy as np
import pandas as pd
import os
import datetime
import joblib
import faker

fake = faker.Faker()

class Product:
    def __init__(self, name, base_price, inventory, icon):
        self.name = name
        self.base_price = base_price
        self.price = base_price
        self.inventory = inventory
        self.icon = icon
        self.sold_count = 0
        self.revenue = 0 # for rack total revenue of the Market, not for each product. This will show me how the prices are effecting the revenue 

    def update_price(self, new_price):
        self.price = round(new_price, 2)

class Shopper:
    def __init__(self):
        self.name = fake.first_name()
        # Personality: Frugal (<1.0) vs Wealthy (>1.0)
        self.budget_multiplier = np.random.normal(1.0, 0.25)
        self.type = "Frugal" if self.budget_multiplier < 0.9 else "Wealthy" if self.budget_multiplier > 1.1 else "Average"

    def decide(self, product):
        # The internal valuation
        perceived_value = product.base_price * self.budget_multiplier
        
        # Decision Logic
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
        
        # Load Model
        self.model = None
        model_path = "A:\\study\\projects\\EtE_ETL_Dynamic_pricing__ML\\Notebook\\models\\predictor2.pkl"
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
            print(f"AI Model Loaded from {model_path}")

        # Data Logging Setup
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
        """AI Logic: Returns (Best Price, Probability, Expected Revenue)"""
        if not self.model:
            return product.base_price, 0, 0
        
        # 1. Generate Candidates
        candidates = np.linspace(product.base_price * 0.7, product.base_price * 1.6, 20)
        
        # 2. Predict
        input_df = pd.DataFrame({
            'price_offered': candidates,
            'inventory_level': [product.inventory] * 20
        })
        buy_probs = self.model.predict_proba(input_df.values)[:, 1]
        
        # 3. Optimize Revenue
        expected_revenues = candidates * buy_probs
        best_index = np.argmax(expected_revenues)
        
        return candidates[best_index], buy_probs[best_index], expected_revenues[best_index]

    def simulate_step(self):
        # --- 1. SHOPPER EVENT ---
        if random.random() < 0.7: 
            shopper = Shopper()
            product = random.choice(self.products)
            decision, reason = shopper.decide(product)
            
            # Save for Training
            self.save_transaction(product, shopper, decision)

            if decision:
                product.inventory -= 1
                product.sold_count += 1
                product.revenue += product.price
                self.log(f" **SALE:** {shopper.name} ({shopper.type}) bought {product.icon} **{product.name}** for ${product.price:.2f}.")
            else:
                # Log why they failed (QOL Improvement)
                if reason == "Stock Empty":
                    self.log(f" **LOST SALE:** {shopper.name} wanted {product.name}, but it's out of stock!")
                else:
                    self.log(f"🚶 **WALK:** {shopper.name} ({shopper.type}) left. {product.name} at ${product.price:.2f} was {reason}.")

        # --- 2. AI RE-PRICING EVENT ---
        # Trigger slightly less often so logs aren't spammy
        if random.random() < 0.15:
            # Pick one random product to adjust (instead of all at once)
            p = random.choice(self.products)
            
            new_price, prob, exp_rev = self.get_optimal_price(p)
            
            # Only change if the price difference is significant (> $0.10)
            if abs(new_price - p.price) > 0.10:
                direction = "📈 Raising" if new_price > p.price else "📉 Dropping"
                
                # THE "WHY" LOG
                self.log(
                    f" **AI:** {direction} {p.name} to **${new_price:.2f}**. "
                    f"Inventory: {p.inventory}. Predicted Buy Chance: {int(prob*100)}%. "
                    f"Exp. Revenue: ${exp_rev:.2f}"
                )
                
                p.update_price(new_price)