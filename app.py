import streamlit as st
import time
import yaml
import pandas as pd
from src.simulation2 import Market

# --- CONFIG ---
st.set_page_config(page_title="Dynamic Pricing Supermarket", layout="wide")

# Load config
with open("configs/products.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# --- SESSION STATE ---
# We need to keep the Market alive across reruns
if "market" not in st.session_state:
    st.session_state.market = Market(config["products"])

market = st.session_state.market

# --- UI LAYOUT ---
st.title("The Dynamic Pricing Supermarket")
st.markdown("Watching **Supply & Demand** in Real-Time")

# 1. METRICS ROW (The Store Shelf)
shelf_container = st.empty()

# 2. MAIN SIMULATION AREA
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Live Market Trends")
    chart_placeholder = st.empty()

with col2:
    st.subheader("Live Transaction Log")
    log_placeholder = st.empty()

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Control Room")
run_simulation = st.sidebar.toggle("Start Simulation", value=False)
simulation_speed = st.sidebar.slider("Speed (sec/tick)", 0.1, 2.0, 0.5)

# --- THE GAME LOOP ---
def render_shelf():
    # Helper to draw the product cards
    cols = shelf_container.columns(len(market.products))
    for i, product in enumerate(market.products):
        with cols[i]:
            st.metric(
                label=f"{product.icon} {product.name}",
                value=f"${product.price:.2f}",
                delta=f"{product.inventory} left",
                delta_color="normal" if product.inventory > 10 else "inverse"
            )

def render_logs():
    # Render the text logs
    with log_placeholder.container():
        for log in market.logs[:10]: # Show last 10
            st.markdown(log)

# Initial Render
render_shelf()
render_logs()

# LOOP
if run_simulation:
    while True:
        # 1. Run Logic
        market.simulate_step()
        
        # 2. Update UI
        render_shelf()
        render_logs()
        
        # 3. Update Chart (Simple Revenue Tracking)
        # Convert product data to dataframe for charting
        df = pd.DataFrame([vars(p) for p in market.products])
        chart_placeholder.bar_chart(df, x="name", y="sold_count")
        
        # 4. Sleep
        time.sleep(simulation_speed)
        
        # Streamlit requires a rerun to process button clicks to STOP the loop,
        # but inside a while True, we rely on the user unchecking the box 
        # which triggers a full rerun naturally.
        # Note: In local Streamlit, this "while" loop works visually but can be tricky.
        # Ideally, we let the script rerun, but for "Animation", this is the standard hack.