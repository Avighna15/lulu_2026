import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="LuLu Sales Performance Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ------------------------------------------------------------
# VISUAL STYLE
# ------------------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
            max-width: 1500px;
        }

        .dashboard-title {
            font-size: 2.15rem;
            font-weight: 800;
            margin-bottom: 0.1rem;
            letter-spacing: -0.02em;
        }

        .dashboard-subtitle {
            color: #667085;
            font-size: 0.98rem;
            margin-bottom: 1.1rem;
        }

        .section-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin-top: 0.4rem;
            margin-bottom: 0.3rem;
        }

        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid #EAECF0;
            padding: 16px 18px;
            border-radius: 14px;
            box-shadow: 0 2px 8px rgba(16,24,40,0.05);
        }

        div[data-testid="stMetricLabel"] {
            color: #667085;
            font-weight: 600;
        }

        div[data-testid="stMetricValue"] {
            font-weight: 800;
        }

        div[data-testid="stMetricDelta"] {
            font-weight: 600;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid #EAECF0;
            border-radius: 12px;
            overflow: hidden;
        }

        .filter-note {
            color: #667085;
            font-size: 0.86rem;
            margin-top: -0.2rem;
        }

        .small-note {
            color: #667085;
            font-size: 0.82rem;
        }

        hr {
            margin-top: 1rem;
            margin-bottom: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("lulu_sales_data.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    return df

df = load_data()

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def fmt_aed(value):
    if abs(value) >= 1_000_000:
        return f"AED {value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"AED {value / 1_000:.1f}K"
    return f"AED {value:,.0f}"

def pct_change(current, previous):
    if previous is None or previous == 0:
        return None
    return (current - previous) / previous * 100

def apply_dimension_filters(data, emirates, stores, categories, channels):
    return data[
        data["Emirate"].isin(emirates)
        & data["Store_Name"].isin(stores)
        & data["Category"].isin(categories)
        & data["Sales_Channel"].isin(channels)
    ].copy()

# ------------------------------------------------------------
# HEADER
# ------------------------------------------------------------
st.markdown('<div class="dashboard-title">🛒 LuLu Sales Performance Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="dashboard-subtitle">Sales performance across stores, categories, emirates and channels</div>',
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# FILTERS
# ------------------------------------------------------------
with st.container(border=True):
    st.markdown("#### Filters")

    min_date = df["Date"].min().date()
    max_date = df["Date"].max().date()

    f1, f2, f3 = st.columns([1.25, 1, 1])

    with f1:
        date_range = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

    with f2:
        emirate_options = sorted(df["Emirate"].dropna().unique().tolist())
        selected_emirates = st.multiselect(
            "Emirate",
            emirate_options,
            default=emirate_options,
            placeholder="Select emirates",
        )

    with f3:
        category_options = sorted(df["Category"].dropna().unique().tolist())
        selected_categories = st.multiselect(
            "Category",
            category_options,
            default=category_options,
            placeholder="Select categories",
        )

    f4, f5, f6 = st.columns([1.35, 1, 0.85])

    with f4:
        store_pool = df[df["Emirate"].isin(selected_emirates)] if selected_emirates else df.iloc[0:0]
        store_options = sorted(store_pool["Store_Name"].dropna().unique().tolist())

        selected_stores = st.multiselect(
            "Store",
            store_options,
            default=store_options,
            placeholder="Select stores",
        )

    with f5:
        channel_options = sorted(df["Sales_Channel"].dropna().unique().tolist())
        selected_channels = st.multiselect(
            "Sales channel",
            channel_options,
            default=channel_options,
            placeholder="Select channels",
        )

    with f6:
        time_view = st.selectbox(
            "Time view",
            ["Monthly", "Weekly", "Daily"],
            index=0,
        )

    st.markdown(
        '<div class="filter-note">Tip: select one or more values in any filter. Store choices automatically follow the selected emirate.</div>',
        unsafe_allow_html=True,
    )

# Date selection protection
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date = pd.Timestamp(date_range[0])
    end_date = pd.Timestamp(date_range[1])
else:
    start_date = pd.Timestamp(date_range)
    end_date = start_date

# Ensure empty selections produce no data rather than silently showing all
if not selected_emirates or not selected_stores or not selected_categories or not selected_channels:
    st.warning("Select at least one Emirate, Store, Category and Sales Channel.")
    st.stop()

dimension_filtered = apply_dimension_filters(
    df,
    selected_emirates,
    selected_stores,
    selected_categories,
    selected_channels,
)

filtered = dimension_filtered[
    (dimension_filtered["Date"] >= start_date)
    & (dimension_filtered["Date"] <= end_date)
].copy()

if filtered.empty:
    st.warning("No sales records match the selected filters.")
    st.stop()

# ------------------------------------------------------------
# PRIOR PERIOD FOR KPI COMPARISON
# ------------------------------------------------------------
period_days = (end_date - start_date).days + 1
previous_end = start_date - pd.Timedelta(days=1)
previous_start = previous_end - pd.Timedelta(days=period_days - 1)

previous = dimension_filtered[
    (dimension_filtered["Date"] >= previous_start)
    & (dimension_filtered["Date"] <= previous_end)
].copy()

# ------------------------------------------------------------
# KPI CALCULATIONS
# ------------------------------------------------------------
sales = filtered["Net_Sales_AED"].sum()
profit = filtered["Profit_AED"].sum()
units = int(filtered["Units_Sold"].sum())
transactions = filtered["Transaction_ID"].nunique()
margin = (profit / sales * 100) if sales else 0
avg_txn = sales / transactions if transactions else 0

prev_sales = previous["Net_Sales_AED"].sum() if not previous.empty else None
prev_profit = previous["Profit_AED"].sum() if not previous.empty else None
sales_delta = pct_change(sales, prev_sales)
profit_delta = pct_change(profit, prev_profit)

# ------------------------------------------------------------
# KPI CARDS
# ------------------------------------------------------------
st.markdown('<div class="section-title">Performance overview</div>', unsafe_allow_html=True)

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric(
    "Net Sales",
    fmt_aed(sales),
    f"{sales_delta:+.1f}% vs prior period" if sales_delta is not None else None,
)
k2.metric(
    "Profit",
    fmt_aed(profit),
    f"{profit_delta:+.1f}% vs prior period" if profit_delta is not None else None,
)
k3.metric("Profit Margin", f"{margin:.1f}%")
k4.metric("Transactions", f"{transactions:,}")
k5.metric("Units Sold", f"{units:,}")
k6.metric("Avg. Transaction", fmt_aed(avg_txn))

st.divider()

# ------------------------------------------------------------
# TIME SERIES
# ------------------------------------------------------------
st.markdown('<div class="section-title">Sales trend</div>', unsafe_allow_html=True)

if time_view == "Monthly":
    filtered["Period"] = filtered["Date"].dt.to_period("M").dt.to_timestamp()
elif time_view == "Weekly":
    filtered["Period"] = filtered["Date"].dt.to_period("W-MON").apply(lambda x: x.start_time)
else:
    filtered["Period"] = filtered["Date"].dt.floor("D")

trend = (
    filtered.groupby("Period", as_index=False)
    .agg(
        Net_Sales_AED=("Net_Sales_AED", "sum"),
        Profit_AED=("Profit_AED", "sum"),
    )
    .sort_values("Period")
)

fig_trend = go.Figure()
fig_trend.add_trace(
    go.Scatter(
        x=trend["Period"],
        y=trend["Net_Sales_AED"],
        mode="lines+markers",
        name="Net Sales",
        line=dict(width=3),
        hovertemplate="Sales: AED %{y:,.0f}<extra></extra>",
    )
)
fig_trend.add_trace(
    go.Scatter(
        x=trend["Period"],
        y=trend["Profit_AED"],
        mode="lines+markers",
        name="Profit",
        line=dict(width=2),
        hovertemplate="Profit: AED %{y:,.0f}<extra></extra>",
    )
)
fig_trend.update_layout(
    height=390,
    margin=dict(l=10, r=10, t=20, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    hovermode="x unified",
    xaxis_title="",
    yaxis_title="AED",
)
st.plotly_chart(fig_trend, use_container_width=True)

# ------------------------------------------------------------
# CATEGORY + EMIRATE
# ------------------------------------------------------------
left, right = st.columns([1.25, 1])

with left:
    st.markdown('<div class="section-title">Sales by category</div>', unsafe_allow_html=True)
    cat = (
        filtered.groupby("Category", as_index=False)["Net_Sales_AED"]
        .sum()
        .sort_values("Net_Sales_AED", ascending=True)
    )
    fig_cat = px.bar(
        cat,
        x="Net_Sales_AED",
        y="Category",
        orientation="h",
        labels={"Net_Sales_AED": "Net Sales (AED)", "Category": ""},
    )
    fig_cat.update_traces(
        hovertemplate="%{y}<br>AED %{x:,.0f}<extra></extra>"
    )
    fig_cat.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
    )
    st.plotly_chart(fig_cat, use_container_width=True)

with right:
    st.markdown('<div class="section-title">Category contribution</div>', unsafe_allow_html=True)
    cat_share = (
        filtered.groupby("Category", as_index=False)["Net_Sales_AED"]
        .sum()
        .sort_values("Net_Sales_AED", ascending=False)
    )
    fig_donut = px.pie(
        cat_share,
        names="Category",
        values="Net_Sales_AED",
        hole=0.58,
    )
    fig_donut.update_traces(
        textposition="inside",
        textinfo="percent",
        hovertemplate="%{label}<br>AED %{value:,.0f}<br>%{percent}<extra></extra>",
    )
    fig_donut.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="top", y=-0.05),
    )
    st.plotly_chart(fig_donut, use_container_width=True)

# ------------------------------------------------------------
# STORE PERFORMANCE
# ------------------------------------------------------------
st.markdown('<div class="section-title">Store performance</div>', unsafe_allow_html=True)

store_perf = (
    filtered.groupby(["Store_Name", "Emirate"], as_index=False)
    .agg(
        Sales_AED=("Net_Sales_AED", "sum"),
        Profit_AED=("Profit_AED", "sum"),
        Transactions=("Transaction_ID", "nunique"),
        Units=("Units_Sold", "sum"),
    )
)

store_perf["Profit_Margin_Pct"] = (
    store_perf["Profit_AED"] / store_perf["Sales_AED"] * 100
).fillna(0)

store_perf["Avg_Transaction_AED"] = (
    store_perf["Sales_AED"] / store_perf["Transactions"]
).fillna(0)

store_perf = store_perf.sort_values("Sales_AED", ascending=False).reset_index(drop=True)
store_perf.insert(0, "Rank", range(1, len(store_perf) + 1))

st.dataframe(
    store_perf,
    use_container_width=True,
    hide_index=True,
    height=380,
    column_config={
        "Rank": st.column_config.NumberColumn("Rank", format="%d"),
        "Store_Name": "Store",
        "Emirate": "Emirate",
        "Sales_AED": st.column_config.NumberColumn("Sales", format="AED %.0f"),
        "Profit_AED": st.column_config.NumberColumn("Profit", format="AED %.0f"),
        "Profit_Margin_Pct": st.column_config.NumberColumn("Margin", format="%.1f%%"),
        "Transactions": st.column_config.NumberColumn("Transactions", format="%d"),
        "Units": st.column_config.NumberColumn("Units", format="%d"),
        "Avg_Transaction_AED": st.column_config.NumberColumn("Avg. Transaction", format="AED %.0f"),
    },
)

# ------------------------------------------------------------
# EMIRATE + CHANNEL PERFORMANCE
# ------------------------------------------------------------
left2, right2 = st.columns(2)

with left2:
    st.markdown('<div class="section-title">Sales by emirate</div>', unsafe_allow_html=True)
    emirate_perf = (
        filtered.groupby("Emirate", as_index=False)["Net_Sales_AED"]
        .sum()
        .sort_values("Net_Sales_AED", ascending=False)
    )
    fig_emirate = px.bar(
        emirate_perf,
        x="Emirate",
        y="Net_Sales_AED",
        labels={"Net_Sales_AED": "Net Sales (AED)", "Emirate": ""},
    )
    fig_emirate.update_traces(
        hovertemplate="%{x}<br>AED %{y:,.0f}<extra></extra>"
    )
    fig_emirate.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
    )
    st.plotly_chart(fig_emirate, use_container_width=True)

with right2:
    st.markdown('<div class="section-title">Sales channel performance</div>', unsafe_allow_html=True)
    channel_perf = (
        filtered.groupby("Sales_Channel", as_index=False)
        .agg(
            Sales_AED=("Net_Sales_AED", "sum"),
            Profit_AED=("Profit_AED", "sum"),
            Transactions=("Transaction_ID", "nunique"),
        )
    )
    channel_perf["Avg_Transaction_AED"] = (
        channel_perf["Sales_AED"] / channel_perf["Transactions"]
    ).fillna(0)

    fig_channel = px.bar(
        channel_perf,
        x="Sales_Channel",
        y=["Sales_AED", "Profit_AED"],
        barmode="group",
        labels={"value": "AED", "Sales_Channel": "", "variable": ""},
    )
    fig_channel.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    st.plotly_chart(fig_channel, use_container_width=True)

# ------------------------------------------------------------
# PERIOD PERFORMANCE TABLE
# ------------------------------------------------------------
st.markdown(f'<div class="section-title">{time_view} performance</div>', unsafe_allow_html=True)

period_perf = (
    filtered.groupby("Period", as_index=False)
    .agg(
        Sales_AED=("Net_Sales_AED", "sum"),
        Profit_AED=("Profit_AED", "sum"),
        Transactions=("Transaction_ID", "nunique"),
        Units=("Units_Sold", "sum"),
    )
    .sort_values("Period")
)

period_perf["Growth_Pct"] = period_perf["Sales_AED"].pct_change() * 100
period_perf["Profit_Margin_Pct"] = (
    period_perf["Profit_AED"] / period_perf["Sales_AED"] * 100
).fillna(0)

if time_view == "Monthly":
    period_perf["Period"] = period_perf["Period"].dt.strftime("%b %Y")
elif time_view == "Weekly":
    period_perf["Period"] = period_perf["Period"].dt.strftime("Week of %d %b %Y")
else:
    period_perf["Period"] = period_perf["Period"].dt.strftime("%d %b %Y")

st.dataframe(
    period_perf.sort_index(ascending=False),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Period": time_view[:-2] if time_view.endswith("ly") else "Period",
        "Sales_AED": st.column_config.NumberColumn("Sales", format="AED %.0f"),
        "Growth_Pct": st.column_config.NumberColumn("Sales Growth", format="%.1f%%"),
        "Profit_AED": st.column_config.NumberColumn("Profit", format="AED %.0f"),
        "Profit_Margin_Pct": st.column_config.NumberColumn("Margin", format="%.1f%%"),
        "Transactions": st.column_config.NumberColumn("Transactions", format="%d"),
        "Units": st.column_config.NumberColumn("Units", format="%d"),
    },
)

# ------------------------------------------------------------
# TOP PERFORMERS + DOWNLOAD
# ------------------------------------------------------------
st.divider()
a, b = st.columns([1, 1])

with a:
    st.markdown('<div class="section-title">Top 5 stores by sales</div>', unsafe_allow_html=True)
    top5 = store_perf[["Rank", "Store_Name", "Emirate", "Sales_AED", "Profit_AED"]].head(5)
    st.dataframe(
        top5,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Rank": "Rank",
            "Store_Name": "Store",
            "Emirate": "Emirate",
            "Sales_AED": st.column_config.NumberColumn("Sales", format="AED %.0f"),
            "Profit_AED": st.column_config.NumberColumn("Profit", format="AED %.0f"),
        },
    )

with b:
    st.markdown('<div class="section-title">Export</div>', unsafe_allow_html=True)
    st.write(
        "Download the transaction-level data currently represented by your selected filters."
    )
    csv_data = filtered.drop(columns=["Period"], errors="ignore").to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download filtered data",
        data=csv_data,
        file_name="lulu_filtered_sales.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.markdown(
    f'<div class="small-note">Showing {len(filtered):,} transactions from {start_date.strftime("%d %b %Y")} to {end_date.strftime("%d %b %Y")}.</div>',
    unsafe_allow_html=True,
)
