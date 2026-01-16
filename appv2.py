import streamlit as st
import time
import yaml
import pandas as pd
import altair as alt
from src.simulation2 import Market
import os

# --- CONFIG ---
st.set_page_config(page_title="Dynamic Price SuperMarket", layout="wide")

# Load config
with open("configs/products.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# --- SESSION STATE ---
if "market" not in st.session_state:
    st.session_state.market = Market(config["products"])

market = st.session_state.market

# --- UI HEADER ---
st.title("Dynamic Pricing Engine")
st.markdown("Real-time Market simulation with Dynamic Pricing depending upon Demand and Supply")

# --- METRICS ROW ---
m1, m2, m3, m4 = st.columns(4)
metric_rev = m1.empty()
metric_sold = m2.empty()
metric_traffic = m3.empty()
metric_model = m4.empty()

st.divider()

# --- MAIN DASHBOARD (Split Layout) ---
col_shelf, col_logs = st.columns([2, 1])

with col_shelf:
    st.subheader("Store Stats")
    shelf_container = st.empty()

with col_logs:
    st.subheader("Decision Logs")
    log_container = st.empty()

st.divider()    

# --- ANALYTICS SECTION (Full Width) ---
st.subheader("Real-Time Market Analytics")
chart_container = st.empty()

# --- SIDEBAR ---
run_simulation = st.sidebar.toggle("Start Simulation", value=False)
sim_speed = st.sidebar.slider("Simulation Speed", 0.1, 2.0, 0.5)

if st.sidebar.button("Reset Simulation"):
    # Clear session state and CSV
    st.session_state.market = Market(config["products"])
    if os.path.exists("data/transactions2.csv"):
        os.remove("data/transactions2.csv")
    st.rerun()

# --- HELPER FUNCTIONS ---
def render_metrics():
    total_rev = sum(p.revenue for p in market.products)
    total_sold = sum(p.sold_count for p in market.products)
    
    metric_rev.metric("Total Revenue", f"€{total_rev:,.2f}", delta="Live")
    metric_sold.metric("Units Sold", f"{total_sold}", delta="Count")
    metric_traffic.metric("Market Status", "Open" if run_simulation else "Paused")

def render_shelf():
    with shelf_container.container():
        
        cols = st.columns(3)
        for i, p in enumerate(market.products):
            col_idx = i % 3
            with cols[col_idx]:
                inv_color = "off" if p.inventory > 20 else "inverse"
                st.metric(
                    label=f"{p.icon} {p.name}",
                    value=f"€{p.price:.2f}",
                    delta=f"{p.inventory} left",
                    delta_color=inv_color
                )
                st.caption(f"Rev: €{p.revenue:.2f}")
                st.progress(min(p.inventory / 100, 1.0))

def render_logs():
    with log_container.container():
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
        for log in market.logs[:20]:
            color = "#ffffff"
            if "💰" in log: color = "#008000"
            if "🚶" in log: color = "#CD1C18"
            if "🤖" in log: color = "#FFEF00"
            
            log_html += f"<span style='color:{color}'>{log}</span><br>"
        log_html += "</div>"
        
        st.markdown(log_html, unsafe_allow_html=True)

def render_charts():
    # Check if file exists
    if not os.path.exists(market.csv_path):
        chart_container.info("Waiting for simulation data... (File not created yet)")
        return
        df = pd.read_csv(market.csv_path)
        
        # Check if data is empty
        if len(df) < 5: 
            chart_container.info(f"Gathering data... ({len(df)}/5 rows)")
            return
        
        # FIX: Ensure timestamp is actually a date (Altair is strict about this)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Filter for last 300 points
        recent_df = df.tail(300)
        
        # Base Chart
        base = alt.Chart(recent_df).encode(
            x=alt.X('timestamp:T', axis=None)
        )
        
        # Price Line (Green)
        line_price = base.mark_line(color='#00cc00', strokeWidth=2).encode(
            y=alt.Y('price_offered', title='Price (€)', scale=alt.Scale(zero=False)),
            tooltip=['product_name', 'price_offered', 'inventory_level']
        )
        
        # Inventory Area (Orange)
        area_inv = base.mark_area(color='#ff9900', opacity=0.3).encode(
            y=alt.Y('inventory_level', title='Inventory'),
        )
        
        # Combine
        c = (area_inv + line_price).facet(
            column=alt.Column('product_name', title=None)
        ).resolve_scale(y='independent')
        
        chart_container.altair_chart(c, use_container_width=True)
            
    



# --- INITIAL RENDER (Run once on load) ---
render_metrics()
render_shelf()
render_logs()
render_charts() 
# --- SIMULATION LOOP ---
if run_simulation:
    while True:
        market.simulate_step()
        
        render_metrics()
        render_shelf()
        render_logs()
        # Update charts every 5 ticks to avoid lag
        if len(market.logs) % 5 == 0:
            render_charts()
            
        time.sleep(sim_speed)
        st.rerun()