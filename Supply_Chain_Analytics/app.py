from pathlib import Path
import math
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Supply Chain Analytics Dashboard",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Supply Chain Analytics Dashboard")
st.caption("Analyze orders, inventory risk, suppliers, and logistics performance.")

# ---------------------------------------------------------
# 2. FILE PATHS AND DATA LOADING
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ORDERS_FILE = DATA_DIR / "supply_chain_data.csv"
INVENTORY_FILE = DATA_DIR / "inventory_data.csv"


@st.cache_data
def load_orders(file_path):
    df = pd.read_csv(file_path)
    for col in ["Order_Date", "Promised_Date", "Delivery_Date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


@st.cache_data
def load_inventory(file_path):
    return pd.read_csv(file_path)


# Verify files exist before loading them
missing_files = []
if not ORDERS_FILE.exists():
    missing_files.append(str(ORDERS_FILE))
if not INVENTORY_FILE.exists():
    missing_files.append(str(INVENTORY_FILE))

if missing_files:
    st.error("The following required data file(s) were not found:")
    for file_path in missing_files:
        st.code(file_path)
    st.info(
        "Check that both CSV files are inside the project's data folder. "
        "If necessary, run `python generate_data.py` from the project folder."
    )
    st.stop()

try:
    orders = load_orders(str(ORDERS_FILE))
    inventory = load_inventory(str(INVENTORY_FILE))
except Exception as exc:
    st.error(f"Could not load the data files: {exc}")
    st.stop()

# Normalize column headers to avoid issues caused by spaces or a BOM
orders.columns = orders.columns.astype(str).str.replace("\ufeff", "", regex=False).str.strip()
inventory.columns = inventory.columns.astype(str).str.replace("\ufeff", "", regex=False).str.strip()

required_order_columns = [
    "Order_ID", "Order_Date", "Supplier", "Warehouse", "Category",
    "Quantity", "Order_Value_INR", "Shipping_Cost_INR",
    "Promised_Date", "Delivery_Date"
]
required_inventory_columns = [
    "Product_ID", "Product", "Category", "Warehouse", "Supplier",
    "Current_Stock", "Reorder_Level", "Daily_Demand", "Lead_Time_Days"
]

missing_order_columns = [c for c in required_order_columns if c not in orders.columns]
missing_inventory_columns = [c for c in required_inventory_columns if c not in inventory.columns]

if missing_order_columns or missing_inventory_columns:
    st.error("One or more expected columns are missing from your CSV files.")
    if missing_order_columns:
        st.write("Missing from supply_chain_data.csv:", missing_order_columns)
        st.write("Available order columns:", orders.columns.tolist())
    if missing_inventory_columns:
        st.write("Missing from inventory_data.csv:", missing_inventory_columns)
        st.write("Available inventory columns:", inventory.columns.tolist())
    st.info("Check the CSV headers or regenerate the files using `python generate_data.py`.")
    st.stop()

# Ensure numeric fields are numeric
for col in [
    "Quantity", "Order_Value_INR", "Shipping_Cost_INR",
    "Delivery_Days", "Delay_Days", "Inventory_Stock"
]:
    if col in orders.columns:
        orders[col] = pd.to_numeric(orders[col], errors="coerce")

for col in [
    "Current_Stock", "Reorder_Level", "Daily_Demand",
    "Lead_Time_Days", "Unit_Cost_INR", "Inventory_Value_INR",
    "Days_of_Stock"
]:
    if col in inventory.columns:
        inventory[col] = pd.to_numeric(inventory[col], errors="coerce")

# ---------------------------------------------------------
# 3. CALCULATE DELIVERY PERFORMANCE
# ---------------------------------------------------------
if "Promised_Date" in orders.columns and "Delivery_Date" in orders.columns:
    orders["Delay_Days_Calculated"] = (
        orders["Delivery_Date"] - orders["Promised_Date"]
    ).dt.days
    orders["Delay_Days_Calculated"] = orders["Delay_Days_Calculated"].clip(lower=0)
    orders["Delivery_Status_Calculated"] = "Unknown"
    valid_delivery = orders["Delivery_Date"].notna() & orders["Promised_Date"].notna()
    orders.loc[valid_delivery, "Delivery_Status_Calculated"] = (
        orders.loc[valid_delivery, "Delay_Days_Calculated"].le(0)
        .map({True: "On Time", False: "Delayed"})
    )
else:
    orders["Delay_Days_Calculated"] = pd.to_numeric(
        orders.get("Delay_Days", pd.Series(index=orders.index, dtype=float)),
        errors="coerce"
    )
    orders["Delivery_Status_Calculated"] = orders.get(
        "Delivery_Status", pd.Series("Unknown", index=orders.index)
    ).fillna("Unknown")

# ---------------------------------------------------------
# 4. SIDEBAR FILTERS
# ---------------------------------------------------------
st.sidebar.header("🔎 Dashboard Filters")

warehouse_options = sorted(
    set(orders["Warehouse"].dropna().astype(str))
    | set(inventory["Warehouse"].dropna().astype(str))
)
category_options = sorted(
    set(orders["Category"].dropna().astype(str))
    | set(inventory["Category"].dropna().astype(str))
)
supplier_options = sorted(
    set(orders["Supplier"].dropna().astype(str))
    | set(inventory["Supplier"].dropna().astype(str))
)

selected_warehouses = st.sidebar.multiselect(
    "Warehouse", warehouse_options, default=warehouse_options
)
selected_categories = st.sidebar.multiselect(
    "Category", category_options, default=category_options
)
selected_suppliers = st.sidebar.multiselect(
    "Supplier", supplier_options, default=supplier_options
)

if orders["Order_Date"].notna().any():
    min_date = orders["Order_Date"].dropna().min().date()
    max_date = orders["Order_Date"].dropna().max().date()
    date_range = st.sidebar.date_input(
        "Order date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
else:
    date_range = None

# Apply filters
filtered_orders = orders.copy()
if selected_warehouses:
    filtered_orders = filtered_orders[
        filtered_orders["Warehouse"].astype(str).isin(selected_warehouses)
    ]
else:
    filtered_orders = filtered_orders.iloc[0:0]

if selected_categories:
    filtered_orders = filtered_orders[
        filtered_orders["Category"].astype(str).isin(selected_categories)
    ]
else:
    filtered_orders = filtered_orders.iloc[0:0]

if selected_suppliers:
    filtered_orders = filtered_orders[
        filtered_orders["Supplier"].astype(str).isin(selected_suppliers)
    ]
else:
    filtered_orders = filtered_orders.iloc[0:0]

if date_range and len(date_range) == 2:
    start_date, end_date = date_range
    filtered_orders = filtered_orders[
        filtered_orders["Order_Date"].dt.date.between(start_date, end_date)
    ]

filtered_inventory = inventory.copy()
if selected_warehouses:
    filtered_inventory = filtered_inventory[
        filtered_inventory["Warehouse"].astype(str).isin(selected_warehouses)
    ]
else:
    filtered_inventory = filtered_inventory.iloc[0:0]

if selected_categories:
    filtered_inventory = filtered_inventory[
        filtered_inventory["Category"].astype(str).isin(selected_categories)
    ]
else:
    filtered_inventory = filtered_inventory.iloc[0:0]

if selected_suppliers:
    filtered_inventory = filtered_inventory[
        filtered_inventory["Supplier"].astype(str).isin(selected_suppliers)
    ]
else:
    filtered_inventory = filtered_inventory.iloc[0:0]

# ---------------------------------------------------------
# 5. OVERVIEW KPIs
# ---------------------------------------------------------
st.header("📊 Supply Chain Overview")

total_orders = len(filtered_orders)
total_order_value = filtered_orders["Order_Value_INR"].sum()
total_shipping_cost = filtered_orders["Shipping_Cost_INR"].sum()

known_delivery = filtered_orders[
    filtered_orders["Delivery_Status_Calculated"].isin(["On Time", "Delayed"])
]
if len(known_delivery):
    on_time_rate = (
        known_delivery["Delivery_Status_Calculated"].eq("On Time").mean() * 100
    )
else:
    on_time_rate = 0.0

inventory_value = (
    filtered_inventory["Inventory_Value_INR"].sum()
    if "Inventory_Value_INR" in filtered_inventory.columns
    else (
        filtered_inventory["Current_Stock"].fillna(0)
        * filtered_inventory.get("Unit_Cost_INR", pd.Series(0, index=filtered_inventory.index)).fillna(0)
    ).sum()
)

reorder_count = int(
    (
        filtered_inventory["Current_Stock"].fillna(0)
        <= filtered_inventory["Reorder_Level"].fillna(0)
    ).sum()
)

k1, k2, k3 = st.columns(3)
k1.metric("Total Orders", f"{total_orders:,}")
k2.metric("Total Order Value", f"₹{total_order_value:,.0f}")
k3.metric("Total Shipping Cost", f"₹{total_shipping_cost:,.0f}")

k4, k5, k6 = st.columns(3)
k4.metric("On-Time Delivery", f"{on_time_rate:.1f}%")
k5.metric("Inventory Value", f"₹{inventory_value:,.0f}")
k6.metric("Items at Reorder Level", f"{reorder_count:,}")

if filtered_orders.empty:
    st.warning("No orders match the selected filters. Change the sidebar filters to see results.")

# ---------------------------------------------------------
# 6. ORDER AND SALES ANALYTICS
# ---------------------------------------------------------
st.header("📈 Order and Sales Analytics")
left, right = st.columns(2)

with left:
    if not filtered_orders.empty and filtered_orders["Order_Date"].notna().any():
        monthly = filtered_orders.dropna(subset=["Order_Date"]).copy()
        monthly["Month"] = monthly["Order_Date"].dt.to_period("M").astype(str)
        monthly_orders = monthly.groupby("Month", as_index=False).agg(
            Orders=("Order_ID", "nunique"),
            Order_Value_INR=("Order_Value_INR", "sum")
        )
        fig = px.line(
            monthly_orders, x="Month", y="Orders", markers=True,
            title="Monthly Order Volume"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No dated order records are available for this chart.")

with right:
    if not filtered_orders.empty and filtered_orders["Order_Date"].notna().any():
        monthly_value = monthly.groupby("Month", as_index=False)["Order_Value_INR"].sum()
        fig = px.bar(
            monthly_value, x="Month", y="Order_Value_INR",
            title="Monthly Order Value (₹)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No order value data available.")

# ---------------------------------------------------------
# 7. INVENTORY INTELLIGENCE AND RISK
# ---------------------------------------------------------
st.header("📦 Inventory Intelligence")

risk_df = filtered_inventory.copy()
if not risk_df.empty:
    risk_df["Current_Stock"] = risk_df["Current_Stock"].fillna(0)
    risk_df["Reorder_Level"] = risk_df["Reorder_Level"].fillna(0)
    risk_df["Daily_Demand"] = risk_df["Daily_Demand"].fillna(0)
    risk_df["Lead_Time_Days"] = risk_df["Lead_Time_Days"].fillna(0)

    calculated_days = risk_df["Current_Stock"] / risk_df["Daily_Demand"].replace(0, float("nan"))
    if "Days_of_Stock" in risk_df.columns:
        risk_df["Days_of_Stock"] = risk_df["Days_of_Stock"].fillna(calculated_days)
    else:
        risk_df["Days_of_Stock"] = calculated_days
    risk_df["Days_of_Stock"] = risk_df["Days_of_Stock"].fillna(9999)

    risk_df["Reorder_Point"] = (
        risk_df["Daily_Demand"] * risk_df["Lead_Time_Days"]
    ).apply(math.ceil)
    risk_df["Estimated_Stock_Gap"] = (
        risk_df["Reorder_Point"] - risk_df["Current_Stock"]
    ).clip(lower=0)

    def classify_risk(row):
        if row["Current_Stock"] <= row["Reorder_Level"] or row["Current_Stock"] <= row["Reorder_Point"]:
            return "High"
        if row["Days_of_Stock"] <= 1.5 * row["Lead_Time_Days"]:
            return "Medium"
        return "Low"

    risk_df["Risk_Level"] = risk_df.apply(classify_risk, axis=1)

    risk_a, risk_b = st.columns(2)
    with risk_a:
        risk_counts = (
            risk_df["Risk_Level"].value_counts()
            .reindex(["High", "Medium", "Low"], fill_value=0)
            .rename_axis("Risk_Level").reset_index(name="Items")
        )
        fig = px.bar(
            risk_counts, x="Risk_Level", y="Items", color="Risk_Level",
            title="Inventory Risk Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)

    with risk_b:
        fig = px.scatter(
            risk_df, x="Daily_Demand", y="Current_Stock",
            color="Risk_Level", hover_name="Product",
            hover_data=["Warehouse", "Days_of_Stock", "Reorder_Point"],
            title="Current Stock vs Daily Demand"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Inventory Risk Table")
    risk_columns = [
        "Product", "Category", "Warehouse", "Supplier", "Current_Stock",
        "Reorder_Level", "Daily_Demand", "Lead_Time_Days", "Days_of_Stock",
        "Reorder_Point", "Estimated_Stock_Gap", "Risk_Level"
    ]
    risk_columns = [c for c in risk_columns if c in risk_df.columns]
    st.dataframe(
        risk_df[risk_columns].sort_values(
            ["Risk_Level", "Estimated_Stock_Gap"],
            ascending=[True, False]
        ),
        use_container_width=True,
        hide_index=True
    )
    st.download_button(
        "⬇️ Download Inventory Risk Report",
        data=risk_df.to_csv(index=False).encode("utf-8"),
        file_name="inventory_risk_report.csv",
        mime="text/csv"
    )
else:
    st.info("No inventory records match the selected filters.")

# Additional stock charts
if not filtered_inventory.empty:
    inv_left, inv_right = st.columns(2)
    with inv_left:
        fig = px.bar(
            filtered_inventory, x="Product", y="Current_Stock",
            color="Warehouse", barmode="group",
            title="Current Stock by Product and Warehouse"
        )
        st.plotly_chart(fig, use_container_width=True)

    with inv_right:
        if "Days_of_Stock" in filtered_inventory.columns:
            fig = px.bar(
                filtered_inventory, x="Product", y="Days_of_Stock",
                color="Warehouse", barmode="group",
                title="Estimated Days of Stock"
            )
            st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# 8. SUPPLIER PERFORMANCE
# ---------------------------------------------------------
st.header("🏭 Supplier Performance")

if not filtered_orders.empty:
    supplier_summary = filtered_orders.groupby("Supplier", as_index=False).agg(
        Total_Orders=("Order_ID", "nunique"),
        Order_Value_INR=("Order_Value_INR", "sum"),
        Shipping_Cost_INR=("Shipping_Cost_INR", "sum"),
        On_Time_Rate=("Delivery_Status_Calculated", lambda x: (x == "On Time").mean() * 100)
    )
    supplier_left, supplier_right = st.columns(2)
    with supplier_left:
        fig = px.bar(
            supplier_summary, x="Supplier", y="Order_Value_INR",
            title="Order Value by Supplier"
        )
        st.plotly_chart(fig, use_container_width=True)
    with supplier_right:
        fig = px.bar(
            supplier_summary, x="Supplier", y="On_Time_Rate",
            title="Supplier-Related On-Time Delivery (%)",
            range_y=[0, 100]
        )
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(supplier_summary, use_container_width=True, hide_index=True)
else:
    st.info("No order data available for supplier analysis.")

# ---------------------------------------------------------
# 9. LOGISTICS ANALYTICS
# ---------------------------------------------------------
st.header("🚚 Logistics Analytics")

if not filtered_orders.empty:
    logistics_left, logistics_right = st.columns(2)
    with logistics_left:
        mode_summary = filtered_orders.groupby("Transport_Mode", as_index=False).agg(
            Orders=("Order_ID", "nunique"),
            Shipping_Cost_INR=("Shipping_Cost_INR", "sum")
        ) if "Transport_Mode" in filtered_orders.columns else pd.DataFrame()
        if not mode_summary.empty:
            fig = px.pie(
                mode_summary, names="Transport_Mode", values="Orders",
                title="Orders by Transport Mode"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Transport_Mode is not available in the order data.")

    with logistics_right:
        if not mode_summary.empty:
            fig = px.bar(
                mode_summary, x="Transport_Mode", y="Shipping_Cost_INR",
                title="Shipping Cost by Transport Mode"
            )
            st.plotly_chart(fig, use_container_width=True)

    if "Delivery_Days" in filtered_orders.columns:
        fig = px.histogram(
            filtered_orders.dropna(subset=["Delivery_Days"]),
            x="Delivery_Days", nbins=20,
            title="Distribution of Delivery Time (Days)"
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No order data available for logistics analysis.")

# ---------------------------------------------------------
# 10. BUSINESS RECOMMENDATIONS
# ---------------------------------------------------------
st.header("💡 Business Recommendations")

recommendations = []
if not risk_df.empty:
    high_risk = risk_df[risk_df["Risk_Level"] == "High"]
    medium_risk = risk_df[risk_df["Risk_Level"] == "Medium"]

    if not high_risk.empty:
        recommendations.append(
            f"**Prioritize replenishment:** {len(high_risk)} inventory record(s) are at high risk. "
            "Review the inventory risk table and arrange replenishment for critical products."
        )
    if not medium_risk.empty:
        recommendations.append(
            f"**Monitor medium-risk inventory:** {len(medium_risk)} record(s) may need closer monitoring "
            "against daily demand and supplier lead time."
        )
    if high_risk.empty and medium_risk.empty:
        recommendations.append(
            "Inventory risk is low under the current thresholds. Continue monitoring demand and lead times."
        )

if not filtered_orders.empty:
    delayed_count = int((filtered_orders["Delivery_Status_Calculated"] == "Delayed").sum())
    if delayed_count:
        recommendations.append(
            f"**Improve delivery reliability:** {delayed_count} filtered order(s) were delivered late. "
            "Review supplier and transport-mode performance to identify potential causes."
        )

    if "Transport_Mode" in filtered_orders.columns:
        mode_cost = filtered_orders.groupby("Transport_Mode")["Shipping_Cost_INR"].mean().dropna()
        if len(mode_cost) >= 2:
            highest_mode = mode_cost.idxmax()
            lowest_mode = mode_cost.idxmin()
            recommendations.append(
                f"**Review transport costs:** {highest_mode} has the highest average shipping cost, "
                f"while {lowest_mode} has the lowest in this filtered dataset. Compare delivery speed "
                "and reliability before changing transport allocation."
            )

if recommendations:
    for recommendation in recommendations:
        st.markdown(f"- {recommendation}")
else:
    st.info("Select filters that include order or inventory records to generate recommendations.")

# ---------------------------------------------------------
# 11. ORDER DETAILS
# ---------------------------------------------------------
st.header("🧾 Order Details")
if not filtered_orders.empty:
    display_columns = [
        "Order_ID", "Order_Date", "Product", "Category", "Supplier",
        "Warehouse", "Transport_Mode", "Quantity", "Order_Value_INR",
        "Shipping_Cost_INR", "Promised_Date", "Delivery_Date",
        "Delay_Days_Calculated", "Delivery_Status_Calculated"
    ]
    display_columns = [c for c in display_columns if c in filtered_orders.columns]
    st.dataframe(
        filtered_orders[display_columns].sort_values("Order_Date", ascending=False),
        use_container_width=True,
        hide_index=True
    )
    st.download_button(
        "⬇️ Download Filtered Orders",
        data=filtered_orders.to_csv(index=False).encode("utf-8"),
        file_name="filtered_supply_chain_orders.csv",
        mime="text/csv"
    )
else:
    st.info("No orders to display for the current filters.")

# ---------------------------------------------------------
# 12. DATA QUALITY REPORT
# ---------------------------------------------------------
st.header("🧹 Data Quality Report")

quality_rows = [
    {
        "Check": "Duplicate Order IDs",
        "Issues Found": int(orders["Order_ID"].duplicated().sum()),
        "Status": "Pass" if not orders["Order_ID"].duplicated().any() else "Review"
    },
    {
        "Check": "Missing Order IDs",
        "Issues Found": int(orders["Order_ID"].isna().sum()),
        "Status": "Pass" if not orders["Order_ID"].isna().any() else "Review"
    },
    {
        "Check": "Missing Order Dates",
        "Issues Found": int(orders["Order_Date"].isna().sum()),
        "Status": "Pass" if not orders["Order_Date"].isna().any() else "Review"
    },
    {
        "Check": "Missing Delivery Dates",
        "Issues Found": int(orders["Delivery_Date"].isna().sum()),
        "Status": "Pass" if not orders["Delivery_Date"].isna().any() else "Review"
    },
    {
        "Check": "Invalid or Missing Quantities",
        "Issues Found": int((orders["Quantity"].isna() | (orders["Quantity"] <= 0)).sum()),
        "Status": "Pass" if not (orders["Quantity"].isna() | (orders["Quantity"] <= 0)).any() else "Review"
    },
    {
        "Check": "Negative or Missing Shipping Costs",
        "Issues Found": int((orders["Shipping_Cost_INR"].isna() | (orders["Shipping_Cost_INR"] < 0)).sum()),
        "Status": "Pass" if not (orders["Shipping_Cost_INR"].isna() | (orders["Shipping_Cost_INR"] < 0)).any() else "Review"
    }
]

quality_df = pd.DataFrame(quality_rows)
st.dataframe(quality_df, use_container_width=True, hide_index=True)

if "Delay_Days_Calculated" in orders.columns:
    delay_data = orders["Delay_Days_Calculated"].dropna()
    if not delay_data.empty:
        fig = px.histogram(
            pd.DataFrame({"Delay_Days": delay_data}),
            x="Delay_Days", nbins=20,
            title="Delivery Delay Distribution (Days)"
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# 13. DOWNLOAD DATA AND FOOTER
# ---------------------------------------------------------
with st.expander("View loaded data information"):
    st.write("Orders file:", str(ORDERS_FILE))
    st.write("Orders shape:", orders.shape)
    st.write("Inventory file:", str(INVENTORY_FILE))
    st.write("Inventory shape:", inventory.shape)
    st.write("Inventory columns:", inventory.columns.tolist())
    st.write("Sample inventory records:")
    st.dataframe(inventory.head(), use_container_width=True)

st.caption("Supply Chain Analytics Dashboard | Built with Python, Pandas, Streamlit, and Plotly")
