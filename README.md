# EtE_ETL_Dynamic_pricing_ML 
## What is this project about?
This project is an end-to-end **MLOps demonstration** of a Dynamic Pricing Engine for a supermarket. It simulates a live retail environment where autonomous "Shopper Bots" enter, browse, and make purchasing decisions based on their hidden budget and the displayed prices

--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
## Update 1(12/01/26)
We have hardcoded the logic in the simulation.py file with some products and their prices and inventory. For now we are going to use this hardcoded data to simulate the dynamic pricing. In the later phase we are going to use the ETL pipeline to get the data and introduce an ML model to predict the prices dynamically

## Tech Stack
* **Language:** Python 3.10+
* **Frontend:** Streamlit (Real-time Dashboard)
* **Simulation Logic:** `NumPy` (Probabilistic decision making), `Faker` (Synthetic User Data)
* **Configuration:** YAML (Product catalog management)


In this initial phase, we have built the **"Digital Twin"** environment:
* **Live Store Simulation:** A Streamlit dashboard that visualizes product inventory and pricing in real-time.
* **utonomous Shopper Agents:** Bots with unique names and "budget personalities" (Frugal vs. Wealthy) generated via `Faker`.
* **Supply & Demand Logic:** A baseline rule-based system that adjusts prices when inventory becomes critical (<10 units).
* **Live Event Logging:** A real-time transaction feed showing every shopper's decision process (Buy vs. Walk Away).

--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
## Update 2(14/01/26): ML Implementation
Replaced hardcoded logic with a Random Forest Classifier that predicts purchase probability to optimize revenue.

### Key Features Added
1.  **Data Collection Pipeline:**
    * Simulation now logs every interaction (Shopper vs. Product) into `transactions2.csv`.
    * Captures features: `price`, `inventory_level`, `product_name`, `shopper_budget`.
2.  **Machine Learning Model:**
    * **Type:** Random Forest Classifier (Scikit-Learn).
    * **Input:** Price, Inventory, Product ID (One-Hot Encoded).
    * **Output:** Probability of Sale (0 to 1).
3.  **The "Strategy" Engine:**
    * Instead of predicting a single price, the AI generates 20 candidate prices.
    * Calculates **Expected Revenue** (`Price * Probability of Sale`) for each.
    * Picks the price that maximizes revenue, balancing "Greed" (High Price) vs. "Fear" (Low Probability).
4.  **Updated Real-Time Dashboard:**
    * Live charts tracking Price vs. Inventory trends.
    * Logs showing the AI's internal monologue.

### Challenges & Solutions

#### 1. 0 Inventory Items issue
* **Problem:** The model learned that "High Price = No Sale" perfectly, but it also learned that "Empty Shelf = No Sale." It treated out-of-stock items as "unpopular," skewing the data.
* **Fix:** We filtered out `inventory == 0` rows during training. The model now only judges price sensitivity based on available stock.

#### 2. Product Blindness
* **Problem:** The Demand Curve looked wrong (sales *increased* as prices went up).
* **Root Cause:** The model treated all products equally. It saw expensive Meat selling well and cheap Milk selling poorly, confusing the two into a single "average" product.
* **Fix:** Implemented **One-Hot Encoding** (`pd.get_dummies`) in `regression.ipynb`. The model now explicitly knows the difference between Milk and Meat.

#### 3. Low Recall
* **Problem:** The model had a Recall of `0.18`. It played it too safe, predicting "No Sale" most of the time to maximize accuracy.
* **Fix:** Applied `class_weight="balanced"` to the Random Forest.
* **Result:** Recall jumped to `0.71`. The AI is now aggressive enough to test higher prices without fear.


### Performance Metrics
* **Accuracy:** ~77%
* **Recall (Buy Class):** 71% (Up from 18%)
* **Behavior:** The AI successfully finds the "price ceiling" for each product—raising prices when stock is low (Scarcity Principle) and lowering them to clear excess inventory.

--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------