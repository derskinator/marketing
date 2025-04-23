import streamlit as st
import pandas as pd
import numpy as np
import re
import itertools
from collections import Counter
from sklearn.preprocessing import MinMaxScaler

st.set_page_config(layout="wide", page_title="Ad Engagement Dashboard")

st.title("📊 Ad Engagement Impact Dashboard")
st.markdown("Upload your Meta Ads CSV and Shopify Sales Excel files to analyze engagement effectiveness by ad.")

# --- UTM Campaign Analysis ---
def generate_utm_analysis_paragraph(shopify_df):
    if "Order UTM campaign" not in shopify_df.columns:
        return "UTM analysis not available — missing UTM campaign column."

    utm_series = shopify_df["Order UTM campaign"].dropna().astype(str)
    token_lists = utm_series.str.replace("_", " ").str.lower().str.split()
    tokens_flat = list(itertools.chain.from_iterable(token_lists))

    revenue_col = "Shopify Revenue" if "Shopify Revenue" in shopify_df.columns else "Total sales"
    orders_col = "Orders" if "Orders" in shopify_df.columns else None

    if orders_col is None or orders_col not in shopify_df.columns:
        return "UTM analysis not available — missing order data."

    try:
        utm_sales_df = shopify_df.groupby("Order UTM campaign").agg({
            orders_col: "sum",
            revenue_col: "sum"
        }).reset_index()
    except Exception:
        return "UTM analysis not available — data format issue."

    top_utms = utm_sales_df.sort_values(by=orders_col, ascending=False).head(20)["Order UTM campaign"]
    top_tokens = list(itertools.chain.from_iterable(
        top_utms.dropna().astype(str).str.replace("_", " ").str.lower().str.split()
    ))

    top_token_counts = Counter(top_tokens)
    common_tokens = [word for word, count in top_token_counts.items() if count > 1 and word.isalpha()]

    if common_tokens:
        examples = ", ".join(common_tokens[:4]) + ("..." if len(common_tokens) > 4 else "")
        return (
            f"🧠 **UTM Campaign Analysis:** Based on UTM parameters, we found that ads containing the keywords "
            f"**{examples}** were most strongly associated with high-performing campaigns in terms of sales. "
            f"These terms consistently appeared in the top UTM campaigns and may reflect strong audience targeting, "
            f"effective offers, or creative hooks worth exploring further."
        )
    else:
        return (
            "🧠 **UTM Campaign Analysis:** No strong recurring keywords were detected among the top-performing UTM campaigns. "
            "Consider using more consistent and descriptive UTM naming to better understand what drives success."
        )

# --- File Upload ---
meta_file = st.file_uploader("Upload Meta Ads CSV", type=["csv"])
shopify_file = st.file_uploader("Upload Shopify Sales Excel", type=["xlsx"])

if meta_file and shopify_file:
    # Load Meta Ads data
    meta_df = pd.read_csv(meta_file, encoding='utf-8', engine='python', on_bad_lines='skip')

    def convert_time_to_seconds(val):
        if isinstance(val, str):
            match = re.match(r"(\d+):(\d+):(\d+)", val)
            if match:
                h, m, s = map(int, match.groups())
                return h * 3600 + m * 60 + s
        return 0

    meta_df['Video average play time (s)'] = meta_df['Video average play time'].apply(convert_time_to_seconds)

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

    # Convert engagement columns to numeric
    for col in metrics:
        if col in meta_df.columns:
            meta_df[col] = pd.to_numeric(meta_df[col], errors='coerce').fillna(0)

    # Load Shopify data
    shopify_df = pd.read_excel(shopify_file)

    # Show UTM analysis BEFORE renaming
    st.markdown(generate_utm_analysis_paragraph(shopify_df))

    # Rename columns for merging
    shopify_df = shopify_df.rename(columns={
        "Order UTM campaign": "Ad name",
        "Total sales": "Shopify Revenue"
    })
    shopify_df["Orders"] = pd.to_numeric(shopify_df["Orders"], errors='coerce').fillna(0)

    # Merge datasets
    df = pd.merge(shopify_df, meta_df, on="Ad name", how="inner")

    # Aggregate per ad
    agg_df = df.groupby("Ad name").agg({
        **{col: 'mean' for col in metrics},
        "Orders": "sum",
        "Shopify Revenue": "sum",
        "Amount spent (USD)": "sum"
    }).reset_index()

    # Calculate ROAS
    agg_df["ROAS"] = agg_df["Shopify Revenue"] / agg_df["Amount spent (USD)"]

    # Calculate impact score
    corr_data = []
    for col in metrics:
        if agg_df[col].nunique() > 1:
            corr = agg_df[col].corr(agg_df["Orders"])
            corr_data.append({"Engagement Metric": col, "Correlation with Orders": corr})

    if corr_data:
        corr_df = pd.DataFrame(corr_data)
        scaler = MinMaxScaler(feature_range=(1, 10))
        corr_df["Impact Score (1-10)"] = scaler.fit_transform(corr_df[["Correlation with Orders"]])
        corr_df = corr_df.sort_values(by="Impact Score (1-10)", ascending=False)

        st.subheader("🔥 Engagement Metric Impact Scores (Across All Ads)")
        st.dataframe(corr_df, use_container_width=True)

    # Show top ads
    top_ads = agg_df.sort_values(by="Orders", ascending=False).head(50)
    st.subheader("🏆 Top 50 Ads by Orders (with ROAS)")
    st.dataframe(top_ads, use_container_width=True)

else:
    st.info("👆 Upload both files to get started.")

