import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from flipside import Flipside
from queries import *
from graph import plot_trader_bubblemap
from datetime import date, datetime

# Load API key
load_dotenv()
api_key = os.getenv("FS_API_KEY")
print(f"API Key loaded: {'Yes' if api_key else 'No'}")
flipside = Flipside(api_key, "https://api-v2.flipsidecrypto.xyz")

# Streamlit UI
st.title("Top Traders Bubblemap Tool")

chain = st.selectbox("Select Blockchain", ['Solana', 'Ethereum', 'Base', 'Arbitrum', 'Optimism', 'Avalanche', 'BSC', 'Polygon'])
contract_address = st.text_input("Token Contract Address (CA)")
start_date = st.date_input("Start Date (Format: YYYY-MM-DD)")
end_date = st.date_input("End Date (Format: YYYY-MM-DD)")
min_usd = st.number_input(
    "Minimum USD Volume (per trader)",
    min_value=0.0,
    value=1.0,
    help="Exclude addresses whose total traded volume (buying/selling) is below this amount during the selected time period."
)
max_usd = st.number_input(
    "Maximum USD Volume (per trader)",
    min_value=min_usd,
    value=10_000_000.0,
    help="Exclude addresses whose total traded volume exceeds this amount. Useful to filter out whales, MEV bots, or liquidity pools."
)
min_days = st.slider(
    "Minimum Active Days",
    1, 100, 3,
    help="Only include addresses that were active (made or received trades) on at least this many different days during the selected period."
)
limit = st.slider(
    "Number of Top Traders Considered",
    10, 500, 200,
    help="Initial pool of top traders (ranked by USD volume) to analyze for connections. These are filtered further for the graph."
)

# Validation errors
if st.button("Run Analysis"):
    if not contract_address:
        st.error("Please enter a valid token contract address. Make sure the CA matches the blockchain.")
    elif start_date >= end_date:
        st.error("Start date must be before end date.")
    elif end_date > date.today():
        st.error("End date cannot be in the future.")
    elif min_usd > max_usd:
        st.error("Minimum USD Volume must be less than Maximum USD Volume.")
    else:
        if chain.lower() == "solana":
            query = get_solana_traders_and_connections(
                contract_address,
                start_date,
                end_date,
                min_usd_amount=min_usd,
                max_usd_amount=max_usd,
                min_active_days=min_days,
                limit=limit
            )
        else:
            query = get_evm_traders_and_connections(
                chain.lower(),
                contract_address,
                start_date,
                end_date,
                min_usd_amount=min_usd,
                max_usd_amount=max_usd,
                min_active_days=min_days,
                limit=limit
            )

        st.info("⏳ This might take a few seconds depending on the chain and date range...")

        with st.spinner("Querying Flipside..."):
            try:
                result = flipside.query(query)
                df = pd.DataFrame(result.records)

                if df.empty:
                    st.warning("No data found for the given inputs.")
                else:
                    st.subheader("Connections Between Top Traders")

                    # Filter only edge rows
                    edges_df = df[df["type"] == "edge"].copy()

                    # Format numeric fields
                    edges_df["total_usd_traded"] = pd.to_numeric(edges_df["total_usd_traded"], errors="coerce")
                    edges_df["total_tokens_traded"] = pd.to_numeric(edges_df["total_tokens_traded"], errors="coerce")

                    edges_df["total_usd_traded"] = edges_df["total_usd_traded"].map(lambda x: f"${x:,.2f}" if pd.notnull(x) else "")
                    edges_df["total_tokens_traded"] = edges_df["total_tokens_traded"].map(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")

                    edges_df = edges_df.sort_values("total_usd_traded", ascending=False)

                    st.dataframe(
                        edges_df.reset_index(drop=True)[
                            ["address", "target_address", "trade_count", "total_tokens_traded", "total_usd_traded"]
                        ].rename(columns={
                            "address": "From",
                            "target_address": "To",
                            "trade_count": "Trades",
                            "total_tokens_traded": "Tokens",
                            "total_usd_traded": "USD Volume"
                        })
                    )

                    # Plot bubblemap
                    st.subheader("Bubblemap Visualization")
                    html_path = plot_trader_bubblemap(df)
                    with open(html_path, 'r', encoding='utf-8') as f:
                        html = f.read()
                        st.components.v1.html(html, height=600, width=1200, scrolling=True)

            except Exception as e:
                st.error(f"Error running query or connecting to API: {e}")
