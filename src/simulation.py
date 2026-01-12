#Update 1(12/01/2025): this script is for simulating the dynamic pricing, for now its hardcoded as in the later phase we are going to use the ETL pipeline to get the data and introduce an ML model to predict the prices dynamically

import random
import yaml
import faker
import numpy as np

fake = faker.Faker()


class Product:
    def __init__(self, name, base_price, inventory, icon):
        self.name = name
        self.base_price = base_price
        self.price = base_price
        self.inventory = inventory
        self.icon = icon
        self.sold_count =0

    def update_price(self, new_price):
        self.price = round(new_price, 2)

class Shopper:
    def __init__(self):
        self.name = fake.first_name()
        self.budget_multiplyer = np.random.normal(1.0, 0.2) #1.0 = Average spender, 1.5 = Rich, 0.8 = Frugal. 

    def decide(self, product):
        #this logic for shopper deciding to buy or not is based on the price of the product and the budget of the shopper
        percieved_value = product.base_price * self.budget_multiplyer

        #update 1 logic is simple, if price< percieveed value then GGWP we buy!
        if product.price <= percieved_value and product.inventory > 0:
            return True
        else:
            return False

class Market:
    def __init__(self, products_config):
        self.products = [Product(**p) for p in products_config]
        self.logs = [] # The live feed buffer
    
    def log(self, message):
        # Keep only last 50 logs to prevent la
        self.logs.insert(0, message) 
        if len(self.logs) > 50:
            self.logs.pop()

    def simulate_step(self):
        """Runs one 'tick' of the simulation (e.g., 1 hour or 1 minute)"""
        
        # 1. Randomly spawn a shopper
        if random.random() < 0.7: # 70% chance a shopper enters
            shopper = Shopper()
            self.log(f"👤 **{shopper.name}** entered the store.")
            
            # 2. Shopper looks at a random product
            product = random.choice(self.products)
            
            # 3. Shopper thinks...
            decision = shopper.decide(product)
            
            if decision:
                product.inventory -= 1
                product.sold_count += 1
                self.log(f" {shopper.name} bought **{product.name}** for ${product.price}!")
                self.log(f" {product.name} Stock: {product.inventory} left.")
            else:
                self.log(f" {shopper.name} looked at **{product.name}** (${product.price}) and walked away.")
        
        # 4. (Update 1 Pricing Logic) - Simple Supply/Demand Rule
        # If inventory is low (< 10), raise price by 10%
        for p in self.products:
            if p.inventory < 10 and p.inventory > 0:
                old_price = p.price
                p.update_price(p.price * 1.01) # Small 1% increase
                if p.price != old_price:
                   # Only log if price actually changed significantly
                   pass