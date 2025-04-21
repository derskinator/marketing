import streamlit as st
import pandas as pd
import numpy as np
import re
from sklearn.preprocessing import MinMaxScaler

st.set_page_config(layout="wide", page_title="Ad Engagement Dashboard")

st.title("📊 Ad Engagement Impact Dashboard")
st.markdown("Upload your Meta Ads CSV and Shopify Sales Excel files to analyze engagement effectiveness by ad.")

# ---------------------------
# File Upload
# ---------------------------
meta_file = st.file_uploader("Upload Meta Ads CSV", type=["csv"])
shopify_file = st.file_uploader("Upload Shopify Sales Excel", type=["xlsx"])

if meta_file and shopify_file:
    # Load Meta Ads data
    meta_df = pd.read_csv(meta_file, encoding='utf-8', engine='python', on_bad_lines='skip')

    # Fix video time format
    def convert_time_to_seconds(val):
        if isinstance(val, str):
            match = re.match(r"(\d+):(\d+):(\d+)", val)
            if match:
                h, m, s = map(int, match.groups())
                return h * 3600 + m * 60 + s
        return 0

    meta_df['Video average play time (s)'] = meta_df['Video average play time'].apply(convert_time_to_seconds)

    # Engagement metrics to evaluate
    metrics = [
        'Frequency',
        'CPC (cost per link click) (USD)',
        'CTR (link click-through rate)',
        'Video average play time (s)',
        '% of Plays at 25%',
        'Video plays at 50%',
        'Video plays at 100%',
        'ThruPlays'
    ]

    # Coerce to numeric and fill NaNs
    for col in metrics:
        if col in meta_df.columns:
            meta_df[col] = pd.to_numeric(meta_df[col], errors='coerce').fillna(0)

    # Load Shopify sales data
    shopify_df = pd.read_excel(shopify_file)
    shopify_df = shopify_df.rename(columns={
        "Order UTM campaign": "Ad name",
        "Total sales": "Shopify Revenue"
    })
    shopify_df["Orders"] = pd.to_numeric(shopify_df["Orders"], errors='coerce').fillna(0)

    # Merge on Ad name
    df = pd.merge(shopify_df, meta_df, on="Ad name", how="inner")

    # Aggregate per ad
    agg_df = df.groupby("Ad name").agg({
        **{col: 'mean' for col in metrics},
        "Orders": "sum",
        "Shopify Revenue": "sum",
        "Amount spent (USD)": "sum"
    }).reset_index()

    # Correlation analysis
    corr_data = []
    for col in metrics:
        if agg_df[col].nunique() > 1:
            corr = agg_df[col].corr(agg_df["Orders"])
            corr_data.append({"Engagement Metric": col, "Correlation with Orders": corr})

    # Create and scale Impact Score
    corr_df = pd.DataFrame(corr_data)
    if not corr_df.empty:
        scaler = MinMaxScaler(feature_range=(1, 10))
        corr_df["Impact Score (1-10)"] = scaler.fit_transform(corr_df[["Correlation with Orders"]])
        corr_df = corr_df.sort_values(by="Impact Score (1-10)", ascending=False)

# Top 50 ads by Orders
top_ads = agg_df.sort_values(by="Orders", ascending=False).head(50)
top_ads["ROAS"] = top_ads["Shopify Revenue"] / top_ads["Amount spent (USD)"]

st.subheader("🏆 Top 50 Ads by Orders")
st.dataframe(top_ads, use_container_width=True)

else:
    st.info("👆 Upload both files to get started.")
