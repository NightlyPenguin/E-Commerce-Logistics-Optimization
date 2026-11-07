import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# -------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & STYLING
# -------------------------------------------------------------------------
st.set_page_config(
    page_title="Global E-Commerce Logistics Hub",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Global E-Commerce & Supply Chain Logistics Engine")
st.markdown("""
*Developed as a production-grade Analytics Application to evaluate enterprise operational health, carrier efficiency, and profit leakage.*
""")

# -------------------------------------------------------------------------
# 2. DATA INGESTION & PIPELINE CLEANING (Showcasing engineering on-the-fly)
# -------------------------------------------------------------------------
@st.cache_data
def load_and_clean_data():
    # Load raw assets
    df_ord = pd.read_csv("raw_orders.csv")
    df_prod = pd.read_csv("raw_products.csv")
    df_cust = pd.read_csv("raw_customers.csv")
    
    # --- Data Cleaning Routine ---
    # Deduplicate system glitches
    df_ord = df_ord.drop_duplicates(subset=["order_id"])
    
    # Standardize string fields
    df_prod["category"] = df_prod["category"].str.title()
    
    country_mapping = {
        "US": "USA", "United States": "USA", 
        "CA": "Canada", "UK": "United Kingdom"
    }
    df_cust["country"] = df_cust["country"].replace(country_mapping)
    
    # Parse Datetimes safely
    df_ord["order_date"] = pd.to_datetime(df_ord["order_date"])
    df_ord["promised_date"] = pd.to_datetime(df_ord["promised_date"])
    df_ord["actual_delivery_date"] = pd.to_datetime(df_ord["actual_delivery_date"])
    
    # Fix algorithmic time-travel bugs (Delivery before order date)
    corrupted_dates = df_ord["actual_delivery_date"] < df_ord["order_date"]
    df_ord.loc[corrupted_dates, "actual_delivery_date"] = np.nan
    
    # --- Relational Joins & Feature Engineering ---
    df = df_ord.merge(df_prod, on="product_id", how="left")
    df = df.merge(df_cust, on="customer_id", how="left")
    
    # Financial metrics calculations
    df["gross_revenue"] = df["retail_price"] * df["quantity"]
    df["total_cost"] = df["cost_price"] * df["quantity"]
    df["net_merchandise_profit"] = df["gross_revenue"] - df["total_cost"]
    
    # Shipping leakages (Where carrier billed more than company charged customer)
    df["shipping_leakage"] = df["actual_shipping_cost"] - df["shipping_fee_charged"]
    
    # Operational Logistical Flags
    df["days_to_deliver"] = (df["actual_delivery_date"] - df["order_date"]).dt.days
    df["is_lost"] = df["actual_delivery_date"].isna()
    df["is_on_time"] = (df["actual_delivery_date"] <= df["promised_date"]) & (~df["is_lost"])
    
    return df

try:
    df_clean = load_and_clean_data()
except FileNotFoundError:
    st.error("❌ Core raw CSV datasets missing! Please run your `generate_raw_data.py` script first.")
    st.stop()

# -------------------------------------------------------------------------
# 3. GLOBAL INTERACTIVE FILTER SIDEBAR
# -------------------------------------------------------------------------
st.sidebar.header("🎛️ Enterprise Control Filters")

# Filter components
categories = ["All Categories"] + sorted(df_clean["category"].unique().tolist())
selected_category = st.sidebar.selectbox("Product Line Segment", categories)

carriers = ["All Carriers"] + sorted(df_clean["carrier"].dropna().unique().tolist())
selected_carrier = st.sidebar.selectbox("Logistics Providers", carriers)

# Apply global query logic dynamically
df_filtered = df_clean.copy()
if selected_category != "All Categories":
    df_filtered = df_filtered[df_filtered["category"] == selected_category]
if selected_carrier != "All Carriers":
    df_filtered = df_filtered[df_filtered["carrier"] == selected_carrier]

# -------------------------------------------------------------------------
# 4. TABBED APPLICATION LAYOUT
# -------------------------------------------------------------------------
tab1, tab2 = st.tabs(["📊 Executive Summary & Performance", "🚚 Carrier Logistics Deep-Dive"])

# -------------------------------------------------------------------------
# TAB 1: EXECUTIVE SUMMARY
# -------------------------------------------------------------------------
with tab1:
    st.subheader("Corporate Core Financials & SLA Standings")
    
    # Enterprise High-Level Metrics Calculations
    total_rev = df_filtered["gross_revenue"].sum()
    total_shipping_leak = df_filtered["shipping_leakage"].sum()
    net_profit = df_filtered["net_merchandise_profit"].sum() - total_shipping_leak
    
    # Valid completed shipments logic
    delivered_shipments = df_filtered[~df_filtered["is_lost"]]
    avg_delivery_days = delivered_shipments["days_to_deliver"].mean()
    otif_rate = (df_filtered["is_on_time"].sum() / len(df_filtered)) * 100

    # Layout Key Performance Cards
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Gross Revenue", f"${total_rev:,.2f}")
    m_col2.metric("Net Profit (Adjusted)", f"${net_profit:,.2f}")
    m_col3.metric("On-Time In-Full (OTIF) Rate", f"{otif_rate:.1f}%")
    m_col4.metric("Avg Transited Duration", f"{avg_delivery_days:.1f} Days")

    # Flag Alert for hiring managers to see your threshold analytics thinking
    if total_shipping_leak > 0:
        st.warning(f"⚠️ **Margin Leak identified:** Net revenue eroded by **${total_shipping_leak:,.2f}** in shipping fees absorbing costs above standard customer checkout rates.")

    st.markdown("---")
    
    # Visual Layout Split
    g1, g2 = st.columns(2)
    
    with g1:
        st.write("### Product Category Profitability Profile")
        cat_analysis = df_filtered.groupby("category").agg(
            Revenue=("gross_revenue", "sum"),
            Net_Profit=("net_merchandise_profit", "sum")
        ).reset_index()
        fig_cat = px.bar(cat_analysis, x="category", y=["Revenue", "Net_Profit"],
                         barmode="group", labels={"value": "Amount ($)", "category": "Product Category"},
                         color_discrete_sequence=["#1f77b4", "#2ca02c"])
        st.plotly_chart(fig_cat, use_container_width=True)

    with g2:
        st.write("### Regional Customer Concentration Mapping")
        country_analysis = df_filtered.groupby("country")["order_id"].count().reset_index(name="Order Volume")
        fig_map = px.choropleth(country_analysis, locations="country", locationmode="country names",
                                color="Order Volume", color_continuous_scale="Blues")
        st.plotly_chart(fig_map, use_container_width=True)

# -------------------------------------------------------------------------
# TAB 2: CARRIER LOGISTICS DEEP-DIVE
# -------------------------------------------------------------------------
with tab2:
    st.subheader("Logistical Efficiency & Carrier SLA Performance Matrix")
    
    # Calculate performance attributes per logistics delivery network
    carrier_perf = df_clean.groupby("carrier").agg(
        Total_Shipments=("order_id", "count"),
        On_Time_Deliveries=("is_on_time", "sum"),
        Lost_In_Transit=("is_lost", "sum"),
        Avg_Shipping_Leakage=("shipping_leakage", "mean"),
        Avg_Transit_Days=("days_to_deliver", "mean")
    ).reset_index()
    
    carrier_perf["OTIF %"] = (carrier_perf["On_Time_Deliveries"] / carrier_perf["Total_Shipments"]) * 100
    carrier_perf["Lost Rate %"] = (carrier_perf["Lost_In_Transit"] / carrier_perf["Total_Shipments"]) * 100

    # Layout Visual splits for deep logistical auditing
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("### Logistics Provider Delivery Lead Times")
        fig_box = px.box(df_filtered[~df_filtered["is_lost"]], x="carrier", y="days_to_deliver",
                         points="outliers", color="carrier",
                         labels={"days_to_deliver": "Days to Deliver", "carrier": "Carrier Network"})
        st.plotly_chart(fig_box, use_container_width=True)

    with c2:
        st.write("### Carrier Compliance (OTIF) vs Attrition/Lost Risk")
        fig_scat = px.scatter(carrier_perf, x="OTIF %", y="Lost Rate %", text="carrier", size="Total_Shipments",
                              color="carrier", labels={"OTIF %": "On-Time Success Rate (OTIF %)", "Lost Rate %": "Package Loss Rate %"})
        fig_scat.update_traces(textposition='top center')
        st.plotly_chart(fig_scat, use_container_width=True)

    # Output analytical matrix table to prove structural data validation
    st.write("### Performance Audit Overview Ledger")
    st.dataframe(
        carrier_perf[["carrier", "Total_Shipments", "OTIF %", "Lost Rate %", "Avg_Transit_Days", "Avg_Shipping_Leakage"]].style.format({
            "OTIF %": "{:.2f}%",
            "Lost Rate %": "{:.2f}%",
            "Avg_Transit_Days": "{:.1f} Days",
            "Avg_Shipping_Leakage": "${:,.2f}"
        }), use_container_width=True, hide_index=True
    )
