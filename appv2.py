import streamlit as st
import time
import yaml
import pandas as pd
import altair as alt
import importlib
import src.simulation2
import os

# --- FORCE RELOAD OF CODE ---
# This ensures we get the latest Simulation & DriftDetector classes
importlib.reload(src.simulation2) 
from src.simulation2 import Market

# --- CONFIG ---
st.set_page_config(page_title="Dynamic Price Engine", layout="wide")

# Load config
with open("configs/products.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# --- SESSION STATE ---
if "market" not in st.session_state:
    st.session_state.market = Market(config["products"])


# If the market object is old (missing the new Observer), we rebuild it.
if not hasattr(st.session_state.market, 'drift_detector'):
    st.toast("System Update: Initializing Observer Module...", icon=None)
    del st.session_state.market
    st.session_state.market = Market(config["products"])
    st.rerun()

market = st.session_state.market

# --- UI HEADER ---
st.title("Dynamic Pricing Engine")
st.markdown("Real-time Market simulation with Dynamic Pricing depending upon Demand and Supply")

# --- METRICS ROW ---
# We now have 4 metrics: Revenue, Sold, Inventory, Model Health
m1, m2, m3, m4 = st.columns(4)
metric_rev = m1.empty()
metric_sold = m2.empty()
metric_inv = m3.empty()
metric_health = m4.empty()

st.divider()

# --- MAIN DASHBOARD (Split Layout) ---
col_shelf, col_logs = st.columns([2, 1])

with col_shelf:
    st.subheader("Store Inventory")
    shelf_container = st.empty()

with col_logs:
    st.subheader("System Logs")
    log_container = st.empty()

st.divider()    

# --- ANALYTICS SECTION (Full Width) ---
st.subheader("Real-Time Analytics")
chart_container = st.empty()

# --- SIDEBAR ---
st.sidebar.header("Controls")
run_simulation = st.sidebar.toggle("Start Simulation", value=False)
sim_speed = st.sidebar.slider("Simulation Speed (s)", 0.1, 2.0, 0.5)

if st.sidebar.button("Reset System"):
    # Clear session state and CSV
    st.session_state.market = Market(config["products"])
    if os.path.exists("data/transactions.csv"):
        os.remove("data/transactions.csv")
    st.rerun()

# --- HELPER FUNCTIONS ---
def render_metrics():
    total_rev = sum(p.revenue for p in market.products)
    total_sold = sum(p.sold_count for p in market.products)
    avg_inv = sum(p.inventory for p in market.products) / len(market.products)
    
    # Financial Metrics
    metric_rev.metric("Total Revenue", f"€ {total_rev:,.2f}")
    metric_sold.metric("Units Sold", f"{total_sold}")
    metric_inv.metric("Avg Inventory", f"{int(avg_inv)}")

    # --- NEW: OBSERVER METRIC ---
    # Calculates the rolling accuracy of the last 50 decisions
    health = market.current_accuracy * 100
    
    # Logic: Green ("normal") if > 60%, Red ("inverse") if < 60%
    state = "normal" if health > 60 else "inverse"
    label = "Stable" if health > 60 else "DRIFT DETECTED"
    
    metric_health.metric(
        "Model Health (Accuracy)", 
        f"{int(health)}%", 
        delta=label, 
        delta_color=state
    )

def render_shelf():
    with shelf_container.container():
        cols = st.columns(3)
        for i, p in enumerate(market.products):
            col_idx = i % 3
            with cols[col_idx]:
                # Text-based inventory status
                inv_status = "Low Stock" if p.inventory < 20 else "In Stock"
                inv_color = "inverse" if p.inventory < 20 else "normal"
                
                st.metric(
                    label=f"{p.name}",
                    value=f"€ {p.price:.2f}",
                    delta=f"{p.inventory} units ({inv_status})",
                    delta_color=inv_color
                )
                st.caption(f"Revenue: € {p.revenue:.2f}")
                st.progress(min(p.inventory / 100, 1.0))

def render_logs():
    with log_container.container():
        # Custom CSS for the log box (Dark mode friendly)
        st.markdown("""
            <style>
            .log-box {
                height: 300px;
                overflow-y: scroll;
                background-color: #0e1117;
                border: 1px solid #262730;
                padding: 10px;
                border-radius: 5px;
                font-family: monospace;
                font-size: 12px;
            }
            </style>
        """, unsafe_allow_html=True)
        
        log_html = "<div class='log-box'>"
        for log in market.logs[:30]:
            color = "#b0b0b0" # Default Grey
            
            # Simple keyword matching for colors
            if "SALE:" in log: color = "#00cc00"     
            if "WALK:" in log: color = "#ff1100"     
            if "AI:" in log: color = "#fffb00"       
            if "DRIFT" in log: color = "#0011ff"     
            
            log_html += f"<span style='color:{color}'>{log}</span><br>"
        log_html += "</div>"
        
        st.markdown(log_html, unsafe_allow_html=True)

def render_charts():
    # Check if file exists
    if not os.path.exists(market.csv_path):
        chart_container.info("Waiting for simulation data... (File not created yet)")
        return

    try:
        df = pd.read_csv(market.csv_path)
        
        # Check if data is empty
        if len(df) < 5: 
            chart_container.info(f"Gathering data... ({len(df)}/5 rows)")
            return
        
        # FIX: Ensure timestamp is actually a date
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Filter for last 300 points
        recent_df = df.tail(300)
        
        # Base Chart
        base = alt.Chart(recent_df).encode(
            x=alt.X('timestamp:T', axis=None)
        )
        
        # Price Line (Green)
        line_price = base.mark_line(color='#00cc00', strokeWidth=2).encode(
            y=alt.Y('price_offered', title='Price (EUR)', scale=alt.Scale(zero=False)),
            tooltip=['product_name', 'price_offered', 'inventory_level']
        )
        
        # Inventory Area (Orange)
        area_inv = base.mark_area(color='#ff9900', opacity=0.3).encode(
            y=alt.Y('inventory_level', title='Inventory'),
        )
        
        # Combine
        c = (area_inv + line_price).facet(
            column=alt.Column('product_name', title=None),
            columns=2
        ).resolve_scale(y='independent')
        
        chart_container.altair_chart(c, use_container_width=True)
            
    except Exception as e:
        chart_container.error(f"Chart Render Error: {str(e)}")


# --- INITIAL RENDER (Run once on load) ---
render_metrics()
render_shelf()
render_logs()
render_charts() 

# --- SIMULATION LOOP ---
if run_simulation:
    market.simulate_step()
    
    render_metrics()
    render_shelf()
    render_logs()
    
    # Update charts every 5 ticks to avoid UI lag
    if len(market.logs) % 5 == 0:
        render_charts()
        
    time.sleep(sim_speed)
    st.rerun()