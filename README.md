# 🧠 Bubblemap Tool – Visualize Top Token Traders

This Streamlit app allows you to explore token ecosystems by visualizing the top traders of a token and their on-chain connections — like a mini forensic bubblemap.

You input a token address, choose the chain and dates, and the tool builds:
- A ranked table of active trader interactions
- An interactive graph of their connections

Currently supports EVM and Solana tokens via [Flipside Crypto](https://flipsidecrypto.xyz) data.

---

## 🚀 Features

- Identify top traders for a token over a specific time range
- Filter by USD volume, trading activity, and connection thresholds
- Interactive bubblemap (with hoverable addresses)
- Works for multiple chains: Solana, Ethereum, Arbitrum, Optimism, Base, Polygon, Avalanche, BSC

---

## 🛠 Requirements

- Python 3.8+
- A [Flipside Crypto API key](https://flipsidecrypto.xyz)

---

## 📦 Installation


```bash
# Clone the repo
git clone https://github.com/0xmilarepa/bubblemap-tool.git
cd top_traders_bubblemap
```

# Create and activate a virtual environment (optional)
```bash
python -m venv venv
source venv/bin/activate
# On Windows: venv\Scripts\activate
```

# Install dependencies
pip install -r requirements.txt


## Environment Variables
Create a .env file in the root directory of the project and add your Flipside API key:

```bash
FS_API_KEY=your_flipside_api_key_here
```

## Running the App
```bash
streamlit run streamlit_app.py
```

📁 File Structure

```bash
.
├── queries.py             # SQL query builders for Solana and EVM chains
├── graph.py               # PyVis graph visualization
├── stramlit_app.py        # Streamlit app
├── requirements.txt
├── .env                   # Your API key (not included in repo)
└── README.md
```

## Requirements
Minimal working dependencies:

```bash
pandas
streamlit
pyvis
python-dotenv
networkx
flipside
```

## Credits

Built by 0xmilarepa. Uses Flipside Crypto data.
Let me know if you want to include a sample image of the graph or link to a demo video.
