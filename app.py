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

    # Tokenize UTM strings
    token_lists = utm_series.str.replace("_", " ").str.lower().str.split()
    tokens_flat = list(itertools.chain.from_iterable(token_lists))

    # Use whichever columns exist
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

    # Convert video time to seconds
    def convert_time_to_seconds(val):
        if isinstance(val, str):
            match = re.match(r"(\d+):(\d+):(\d+)", val)
            if match:
                h, m, s = map(int, match.groups())
                return h * 3600 + m * 60 + s
        return 0

    meta_df['Video average play time (s)'] = meta_df['Video average play time'].apply(convert_time_to_seconds)

    # Define engagement metrics
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

    for col in metrics:
        if col in meta_df.columns:
