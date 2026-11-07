import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Set random seed for reproducibility
np.random.seed(42)
num_records = 5000

print("🚀 Generating messy enterprise datasets...")

# -------------------------------------------------------------------------
# 1. GENERATE DIM_PRODUCTS (Clean base, but mixed casing)
# -------------------------------------------------------------------------
products_data = {
    "product_id": [f"PROD_{i:03d}" for i in range(1, 21)],
    "product_name": [
        "Wireless Mouse", "Mechanical Keyboard", "4K Monitor", "USB-C Hub", "Ergonomic Chair",
        "Desk Mat", "LED Desk Lamp", "Bluetooth Speaker", "Noise Cancelling Headphones", "Webcam 1080p",
        "External SSD 1TB", "Laptop Stand", "Graphics Tablet", "Smart Smartwatch", "Wireless Earbuds",
        "Gaming Microphone", "Vertical Mouse", "Dual Monitor Arm", "Ring Light", "Cable Organizer"
    ],
    "category": [
        "Electronics", "Electronics", "Office Supply", "Electronics", "Furniture",
        "office supply", "Office Supply", "Electronics", "Electronics", "Electronics",
        "Electronics", "Office Supply", "Electronics", "Electronics", "Electronics",
        "Electronics", "Electronics", "Furniture", "Electronics", "office supply"
    ], # Intentionally left mixed-case categories to test cleaning skills
    "cost_price": np.round(np.random.uniform(5.0, 150.0, 20), 2),
}
df_products = pd.DataFrame(products_data)
# Calculate retail price with a realistic margin
df_products["retail_price"] = np.round(df_products["cost_price"] * np.random.uniform(1.4, 2.2, 20), 2)


# -------------------------------------------------------------------------
# 2. GENERATE DIM_CUSTOMERS (Contains formatting variations)
# -------------------------------------------------------------------------
countries = ["USA", "US", "United States", "Canada", "CA", "United Kingdom", "UK"]
df_customers = pd.DataFrame({
    "customer_id": [f"CUST_{i:04d}" for i in range(1, 801)],
    "customer_name": [f"Customer User {i}" for i in range(1, 801)],
    "country": np.random.choice(countries, size=800, p=[0.4, 0.2, 0.1, 0.1, 0.05, 0.1, 0.05]),
    "signup_date": [datetime(2024, 1, 1) + timedelta(days=int(np.random.randint(0, 365))) for _ in range(800)]
})


# -------------------------------------------------------------------------
# 3. GENERATE FACT_ORDERS (The core transactional file with intentional bugs)
# -------------------------------------------------------------------------
order_ids = [f"ORD_{i:06d}" for i in range(100001, 100001 + num_records)]
customer_pool = df_customers["customer_id"].tolist()
product_pool = df_products["product_id"].tolist()
carriers = ["FedEx", "UPS", "DHL", "USPS"]

start_date = datetime(2025, 1, 1)

order_dates = [start_date + timedelta(days=int(np.random.randint(0, 300)), 
                                     hours=int(np.random.randint(0, 24)), 
                                     minutes=int(np.random.randint(0, 60))) for _ in range(num_records)]

df_orders = pd.DataFrame({
    "order_id": order_ids,
    "customer_id": np.random.choice(customer_pool, size=num_records),
    "product_id": np.random.choice(product_pool, size=num_records),
    "carrier": np.random.choice(carriers, size=num_records, p=[0.35, 0.35, 0.15, 0.15]),
    "order_date": order_dates,
    "quantity": np.random.choice([1, 2, 3, 4], size=num_records, p=[0.7, 0.15, 0.1, 0.05]),
    "shipping_fee_charged": np.round(np.random.uniform(0.0, 25.0, num_records), 2)
})

# Logic-driven timestamps for supply chain tracking
df_orders["promised_delivery_days"] = np.random.choice([2, 3, 5, 7], size=num_records, p=[0.2, 0.4, 0.3, 0.1])
df_orders["promised_date"] = df_orders.apply(lambda row: row["order_date"] + timedelta(days=int(row["promised_delivery_days"])), axis=1)

# Generate actual delivery timelines (with some delays built in)
def calculate_actual_delivery(row):
    # 12% of shipments experience bottleneck delays
    is_delayed = np.random.rand() < 0.12
    if is_delayed:
        actual_days = row["promised_delivery_days"] + np.random.randint(2, 9)
    else:
        actual_days = row["promised_delivery_days"] + np.random.randint(-1, 2)
        if actual_days < 1: actual_days = 1
        
    return row["order_date"] + timedelta(days=int(actual_days), hours=int(np.random.randint(-4, 12)))

df_orders["actual_delivery_date"] = df_orders.apply(calculate_actual_delivery, axis=1)

# Generate messy carrier costs (sometimes causing financial leakage)
df_orders["actual_shipping_cost"] = np.round(df_orders["shipping_fee_charged"] * np.random.uniform(0.6, 1.8, num_records), 2)

# -------------------------------------------------------------------------
# 🚨 INJECTING REAL-WORLD MESSINESS & ANOMALIES
# -------------------------------------------------------------------------

# 1. Missing data: 4% of packages are lost/in-transit (Actual Delivery Date is NaN)
lost_indices = np.random.choice(df_orders.index, size=int(num_records * 0.04), replace=False)
df_orders.loc[lost_indices, "actual_delivery_date"] = np.nan
# Lost items shouldn't have an actual shipping cost finalized uniformly
df_orders.loc[lost_indices, "actual_shipping_cost"] = np.nan 

# 2. Duplicate entries: Simulate 50 system retry/double-click duplicate entries
dup_indices = np.random.choice(df_orders.index, size=50, replace=False)
df_duplicates = df_orders.loc[dup_indices].copy()
df_orders = pd.concat([df_orders, df_duplicates], ignore_index=True)

# 3. Structural out-of-bounds anomaly: 5 orders have actual delivery dates BEFORE order dates due to a clock sync bug
bug_indices = np.random.choice(df_orders.index, size=5, replace=False)
df_orders.loc[bug_indices, "actual_delivery_date"] = df_orders.loc[bug_indices, "order_date"] - timedelta(days=2)

# Convert datetimes to strings to mimic standard raw flat-file loads
df_orders["order_date"] = df_orders["order_date"].dt.strftime('%Y-%m-%d %H:%M:%S')
df_orders["promised_date"] = df_orders["promised_date"].dt.strftime('%Y-%m-%d %H:%M:%S')
df_orders["actual_delivery_date"] = df_orders["actual_delivery_date"].dt.strftime('%Y-%m-%d %H:%M:%S')
df_customers["signup_date"] = df_customers["signup_date"].dt.strftime('%Y-%m-%d')

# -------------------------------------------------------------------------
# SAVE DATASETS TO CSV
# -------------------------------------------------------------------------
df_products.to_csv("raw_products.csv", index=False)
df_customers.to_csv("raw_customers.csv", index=False)
df_orders.to_csv("raw_orders.csv", index=False)

print("✅ Success! Generated 3 files:")
print("   - `raw_products.csv` (Product baseline catalogs)")
print("   - `raw_customers.csv` (Customer geography/profiles)")
print("   - `raw_orders.csv` (Messy logistical transaction records)")
print("\nYour next step is to write a script to ingest, clean, and model this into a database schema!")
