import random
import numpy as np
import pandas as pd
import os
import datetime
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

    def update_price(self, new_price):
        self.price = round(new_price, 2)

class Shopper:
    def __init__(self):
        self.name = fake.first_name()
        # 1.0 = Average, >1.0 = Rich, <1.0 = Frugal
        self.budget_multiplier = np.random.normal(1.0, 0.2)

    def decide(self, product):
        perceived_value = product.base_price * self.budget_multiplier
        if product.price <= perceived_value and product.inventory > 0:
            return True
        return False

class Market:
    def __init__(self, products_config):
        self.products = [Product(**p) for p in products_config]
        self.logs = []
        
        # Ensure data directory exists
        if not os.path.exists("data"):
            os.makedirs("data")
            
        # Initialize CSV with headers if it doesn't exist
        self.csv_path = "data/transactions.csv"
        if not os.path.exists(self.csv_path):
            df = pd.DataFrame(columns=[
                "timestamp", "product_name", "price_offered", 
                "inventory_level", "budget_multiplier", "purchased"
            ])
            df.to_csv(self.csv_path, index=False)
    
    def log(self, message):
        self.logs.insert(0, message) 
        if len(self.logs) > 50:
            self.logs.pop()

    def save_transaction(self, product, shopper, purchased):
        """Saves the interaction to CSV for ML Training"""
        new_row = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "product_name": product.name,
            "price_offered": product.price,
            "inventory_level": product.inventory,
            "budget_multiplier": round(shopper.budget_multiplier, 2),
            "purchased": 1 if purchased else 0
        }
        # Append to CSV immediately
        df = pd.DataFrame([new_row])
        df.to_csv(self.csv_path, mode='a', header=False, index=False)

    def simulate_step(self):
        # 1. Spawn Shopper
        if random.random() < 0.8: # Increased traffic slightly
            shopper = Shopper()
            product = random.choice(self.products)
            
            # 2. Make Decision
            decision = shopper.decide(product)
            
            # 3. Log the Data (Crucial Step for Phase 2)
            self.save_transaction(product, shopper, decision)

            if decision:
                product.inventory -= 1
                product.sold_count += 1
                self.log(f"✅ {shopper.name} bought **{product.name}** for ${product.price}!")
            else:
                self.log(f"❌ {shopper.name} walked away from **{product.name}** (${product.price}).")
        
        # 4. RANDOM PRICING (Temporary for Data Collection)
        # To train the model, we need to try BAD prices too.
        # If we only use "good" prices, the model won't learn what "too expensive" looks like.
        for p in self.products:
            if random.random() < 0.1: # 10% chance to change price
                # Fluctuate price randomly between 0.8x and 1.5x of base
                fluctuation = random.uniform(0.8, 1.5)
                p.update_price(p.base_price * fluctuation)