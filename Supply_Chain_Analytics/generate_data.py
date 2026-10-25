
import random
from pathlib import Path

import numpy as np
import pandas as pd

# Make the generated dataset reproducible
random.seed(42)
np.random.seed(42)

# Save data inside the project's data folder
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Sample master data
products = [
    ("P001", "Laptop", "Electronics", 65000),
    ("P002", "Mouse", "Electronics", 800),
    ("P003", "Keyboard", "Electronics", 1800),
    ("P004", "Office Chair", "Furniture", 7500),
    ("P005", "Desk", "Furniture", 12000),
    ("P006", "Notebook", "Stationery", 80),
    ("P007", "Printer", "Electronics", 15000),
    ("P008", "Monitor", "Electronics", 14000),
    ("P009", "Pen Pack", "Stationery", 150),
    ("P010", "Storage Rack", "Furniture", 5000),
]

suppliers = [
    "Supplier A",
    "Supplier B",
    "Supplier C",
    "Supplier D",
    "Supplier E",
]

warehouses = ["Chennai", "Bengaluru", "Mumbai", "Delhi", "Hyderabad"]
transport_modes = ["Road", "Rail", "Air", "Ship"]

rows = []
start_date = pd.Timestamp("2025-01-01")
end_date = pd.Timestamp("2026-10-01")

for order_number in range(1, 501):
    product_id, product_name, category, unit_price = random.choice(products)
    supplier = random.choice(suppliers)
    warehouse = random.choice(warehouses)
    transport = random.choices(
        transport_modes,
        weights=[50, 20, 20, 10],
        k=1
    )[0]

    order_date = start_date + pd.Timedelta(
        days=random.randint(0, (end_date - start_date).days)
    )

    quantity = random.randint(1, 30)
    inventory_stock = random.randint(0, 250)
    reorder_level = random.randint(30, 80)
    lead_time_days = random.randint(2, 15)

    # Shipping cost depends partly on transport mode and quantity
    transport_cost = {
        "Road": 500,
        "Rail": 350,
        "Air": 1500,
        "Ship": 250,
    }[transport]

    shipping_cost = round(
        transport_cost + quantity * random.uniform(10, 60), 2
    )

    # Some orders are deliberately delayed
    delay_days = random.choices(
        [0, 1, 2, 3, 5, 7, 10],
        weights=[45, 15, 12, 10, 7, 6, 5],
        k=1
    )[0]

    promised_days = random.randint(3, 10)
    delivery_days = promised_days + delay_days
    promised_date = order_date + pd.Timedelta(days=promised_days)
    delivery_date = order_date + pd.Timedelta(days=delivery_days)

    rows.append({
        "Order_ID": f"ORD{order_number:04d}",
        "Order_Date": order_date,
        "Product_ID": product_id,
        "Product": product_name,
        "Category": category,
        "Supplier": supplier,
        "Warehouse": warehouse,
        "Transport_Mode": transport,
        "Quantity": quantity,
        "Unit_Price_INR": unit_price,
        "Order_Value_INR": quantity * unit_price,
        "Inventory_Stock": inventory_stock,
        "Reorder_Level": reorder_level,
        "Lead_Time_Days": lead_time_days,
        "Shipping_Cost_INR": shipping_cost,
        "Promised_Date": promised_date,
        "Delivery_Date": delivery_date,
        "Delivery_Days": delivery_days,
        "Delay_Days": delay_days,
        "Delivery_Status": (
            "On Time" if delivery_date <= promised_date else "Delayed"
        ),
    })

# Create the DataFrame
df = pd.DataFrame(rows)

# Save the dataset
csv_path = DATA_DIR / "supply_chain_data.csv"
excel_path = DATA_DIR / "supply_chain_data.xlsx"

df.to_csv(csv_path, index=False)
df.to_excel(excel_path, index=False)

print("Supply chain dataset generated successfully!")
print(f"Total orders: {len(df)}")
print(f"CSV file: {csv_path}")
print(f"Excel file: {excel_path}")
print("\nDataset preview:")
print(df.head())
print("\nDelivery status summary:")
print(df["Delivery_Status"].value_counts())

# --------------------------------------------------
# 11. GENERATE A SEPARATE INVENTORY DATASET
# --------------------------------------------------

inventory_rows = []

for product_id, product_name, category, unit_price in products:
    for warehouse in warehouses:
        stock = random.randint(5, 300)
        reorder_level = random.randint(30, 80)
        daily_demand = round(random.uniform(1, 8), 2)
        supplier = random.choice(suppliers)
        lead_time = random.randint(2, 15)

        inventory_rows.append({
            "Product_ID": product_id,
            "Product": product_name,
            "Category": category,
            "Warehouse": warehouse,
            "Supplier": supplier,
            "Unit_Cost_INR": unit_price,
            "Current_Stock": stock,
            "Reorder_Level": reorder_level,
            "Daily_Demand": daily_demand,
            "Lead_Time_Days": lead_time,
            "Days_of_Stock": round(stock / daily_demand, 1),
            "Inventory_Value_INR": stock * unit_price,
            "Reorder_Status": (
                "Reorder Required"
                if stock <= reorder_level
                else "Sufficient Stock"
            ),
        })

inventory_df = pd.DataFrame(inventory_rows)

inventory_path = DATA_DIR / "inventory_data.csv"
inventory_df.to_csv(inventory_path, index=False)

print("\nInventory dataset generated successfully!")
print(f"Inventory records: {len(inventory_df)}")
print(f"Inventory file: {inventory_path}")
print("\nInventory preview:")
print(inventory_df.head())
print("\nInventory status:")
print(inventory_df["Reorder_Status"].value_counts())

