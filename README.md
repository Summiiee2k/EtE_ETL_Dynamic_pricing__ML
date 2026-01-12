# EtE_ETL_Dynamic_pricing_ML 
## What is this project about?
This project is an end-to-end **MLOps demonstration** of a Dynamic Pricing Engine for a supermarket. It simulates a live retail environment where autonomous "Shopper Bots" enter, browse, and make purchasing decisions based on their hidden budget and the displayed prices

--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
## Update 1(12/01/2026)
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