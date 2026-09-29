import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# LuLu Sales Dashboard - simple version
# ---------------------------------------------------------
st.set_page_config(
    page_title="LuLu Sales Dashboard",
    page_icon="📊",
    layout="wide",
)

# Load data
@st.cache_data
def load_data():
    df = pd.read_csv("lulu_sales_data.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    return df

df = load_data()

# ---------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------
st.sidebar.header("Filters")

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

categories = st.sidebar.multiselect(
    "Category",
    sorted(df["Category"].dropna().unique()),
    default=sorted(df["Category"].dropna().unique()),
)

stores = st.sidebar.multiselect(
    "Store",
    sorted(df["Store_Name"].dropna().unique()),
    default=sorted(df["Store_Name"].dropna().unique()),
)

view = st.sidebar.radio(
    "Sales trend",
    ["Monthly", "Weekly"],
)

# Handle date selection
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date = pd.Timestamp(date_range[0])
    end_date = pd.Timestamp(date_range[1])
else:
    start_date = pd.Timestamp(date_range)
    end_date = start_date

# ---------------------------------------------------------
# Apply filters
# ---------------------------------------------------------
filtered = df[
    (df["Date"] >= start_date)
    & (df["Date"] <= end_date)
    & (df["Category"].isin(categories))
    & (df["Store_Name"].isin(stores))
].copy()

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.title("📊 LuLu Sales Dashboard")
st.caption("Sales performance by category, store and time period")

if filtered.empty:
    st.warning("No sales data matches the selected filters.")
    st.stop()

# ---------------------------------------------------------
# KPI cards
# ---------------------------------------------------------
total_sales = filtered["Net_Sales_AED"].sum()
total_profit = filtered["Profit_AED"].sum()
total_units = filtered["Units_Sold"].sum()
transactions = filtered["Transaction_ID"].nunique()
profit_margin = (total_profit / total_sales * 100) if total_sales else 0
avg_transaction = total_sales / transactions if transactions else 0

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Net Sales", f"AED {total_sales:,.0f}")
c2.metric("Profit", f"AED {total_profit:,.0f}")
c3.metric("Units Sold", f"{total_units:,}")
c4.metric("Transactions", f"{transactions:,}")
c5.metric("Profit Margin", f"{profit_margin:.1f}%")

st.divider()

# ---------------------------------------------------------
# Sales trend
# ---------------------------------------------------------
st.subheader(f"{view} Sales")

if view == "Monthly":
    trend = (
        filtered.assign(Period=filtered["Date"].dt.to_period("M").astype(str))
        .groupby("Period", as_index=False)["Net_Sales_AED"]
        .sum()
    )
else:
    trend = (
        filtered.assign(
            Period=filtered["Date"].dt.to_period("W-MON").apply(lambda x: x.start_time)
        )
        .groupby("Period", as_index=False)["Net_Sales_AED"]
        .sum()
    )
    trend["Period"] = trend["Period"].dt.strftime("%d %b %Y")

st.line_chart(
    trend.set_index("Period")["Net_Sales_AED"],
    use_container_width=True,
)

# ---------------------------------------------------------
# Category and store analysis
# ---------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Sales by Category")
    category_sales = (
        filtered.groupby("Category", as_index=False)["Net_Sales_AED"]
        .sum()
        .sort_values("Net_Sales_AED", ascending=False)
    )
    st.bar_chart(
        category_sales.set_index("Category")["Net_Sales_AED"],
        use_container_width=True,
    )

with col2:
    st.subheader("Sales by Store")
    store_sales = (
        filtered.groupby("Store_Name", as_index=False)["Net_Sales_AED"]
        .sum()
        .sort_values("Net_Sales_AED", ascending=False)
    )
    st.bar_chart(
        store_sales.set_index("Store_Name")["Net_Sales_AED"],
        use_container_width=True,
    )

# ---------------------------------------------------------
# Summary table
# ---------------------------------------------------------
st.subheader("Category Summary")

summary = (
    filtered.groupby("Category")
    .agg(
        Sales_AED=("Net_Sales_AED", "sum"),
        Profit_AED=("Profit_AED", "sum"),
        Units=("Units_Sold", "sum"),
        Transactions=("Transaction_ID", "nunique"),
    )
    .reset_index()
)

summary["Profit_Margin"] = (
    summary["Profit_AED"] / summary["Sales_AED"] * 100
).round(1)

summary = summary.sort_values("Sales_AED", ascending=False)

st.dataframe(
    summary,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Sales_AED": st.column_config.NumberColumn(
            "Sales (AED)", format="AED %.2f"
        ),
        "Profit_AED": st.column_config.NumberColumn(
            "Profit (AED)", format="AED %.2f"
        ),
        "Units": st.column_config.NumberColumn("Units"),
        "Transactions": st.column_config.NumberColumn("Transactions"),
        "Profit_Margin": st.column_config.NumberColumn(
            "Profit Margin", format="%.1f%%"
        ),
    },
)

# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------
st.caption("Use the filters on the left to explore sales performance.")
