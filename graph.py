import pandas as pd
import networkx as nx
import os
from pyvis.network import Network

def plot_trader_bubblemap(df, output_html="bubblemap.html", base_dir=None):

    """This function creates an interactive bubble map visualization of trader relationships.

    It generates a network graph where nodes represent trader addresses,
    and edges represent trading relationships between them. Node sizes are scaled
    based on the total USD trading volume of each address, and node colors are set
    to orange for high-volume traders (above the median volume) and blue for
    low-volume traders (below the median). The visualization is saved as an HTML file
    using PyVis and can be displayed in a browser or embedded in a Streamlit app.

    Args:
        df (pandas.DataFrame): A DataFrame containing trader relationship data with the
            following columns:
            - type (str): Either 'node' or 'edge', indicating the type of data.
            - address (str): The trader's wallet address (for nodes and edges).
            - target_address (str): The connected address (for edges).
            - total_usd_traded (float): The USD trading volume for the node or edge.
        output_html (str, optional): Filename for the HTML visualization. Defaults to "bubblemap.html".
        base_dir (str, optional): Base directory to save the HTML file. If None, uses current directory.

    Returns:
        None

    Notes:
        - The function expects `total_usd_traded` to be a numerical value (float).
          If it contains formatted strings (e.g., with commas), it attempts to convert
          them to floats, with a fallback weight of 1 if conversion fails.
        - Nodes with missing `address` or `target_address` are removed from the DataFrame.
        - Node sizes are scaled linearly between 10 and 50 based on their total USD trading
          volume.
        - The color threshold is the median volume across all nodes: nodes above the median
          are orange (#FF4500), and nodes below are blue (#1E90FF).
        - The visualization uses the Force Atlas 2 layout algorithm for node positioning.
        - A message is printed indicating the number of nodes and edges in the graph.
    """


    # Removing rows where address or target_address is missing
    df = df.dropna(subset=['address', 'target_address'])

    # Calculating total volume per address (node)
    # Suming total_usd_traded for each address appearing as 'address' or 'target_address'
    volume_from = df.groupby('address')['total_usd_traded'].sum()
    volume_to = df.groupby('target_address')['total_usd_traded'].sum()
    total_volume = volume_from.add(volume_to, fill_value=0).to_dict()

    # Creating empty graph
    G = nx.Graph()

    # Adding nodes
    nodes = pd.unique(df[['address', 'target_address']].values.ravel())
    nodes = [node for node in nodes if pd.notna(node)]  # Remove NaNs

    for node in nodes:
        G.add_node(node)

    # Adding edges
    for idx, row in df.iterrows():
        from_addr = row['address']
        to_addr = row['target_address']

        try:
            weight = float(str(row['total_usd_traded']).replace(',', ''))
        except:
            weight = 1  # Fallback

        G.add_edge(from_addr, to_addr, weight=weight)

    # Building Pyvis network
    net = Network(height="800px", width="100%", bgcolor="#222222", font_color="white", notebook=True, cdn_resources='in_line')

    # Determining node sizes and colors based on total volume
    volumes = [total_volume.get(node, 0) for node in G.nodes()]
    if volumes:
        min_volume = min(volumes)
        max_volume = max(volumes)
        volume_range = max_volume - min_volume if max_volume != min_volume else 1

        # Defining size scaling (e.g., map volumes to sizes between 10 and 50)
        min_size = 10
        max_size = 50
        sizes = [
            min_size + (max_size - min_size) * (total_volume.get(node, 0) - min_volume) / volume_range
            for node in G.nodes()
        ]

        # Defining color threshold (e.g., median volume as the cutoff for "large" vs "small")
        threshold = pd.Series(volumes).median()
        colors = ["#FF4500" if total_volume.get(node, 0) >= threshold else "#1E90FF" for node in G.nodes()]  # Orange for large, Blue for small
    else:
        sizes = [10 for _ in G.nodes()]  # Default size if no volumes
        colors = ["#1E90FF" for _ in G.nodes()]  # Default to blue

    # Adding nodes with sizes and colors
    for node, size, color in zip(G.nodes(), sizes, colors):
        net.add_node(node, label=node[:6] + "..." + node[-4:], title=f"{node}\nVolume: ${total_volume.get(node, 0):,.2f}", size=size, color=color)

    # Adding edges
    for edge in G.edges(data=True):
        net.add_edge(edge[0], edge[1], value=edge[2]['weight'])

    print(f"Graph will be built with {len(nodes)} nodes and {len(df)} edges")

    # Ensuring the output path includes the base directory
    if base_dir:
        os.makedirs(base_dir, exist_ok=True)  # Creating the directory if it doesn't exist
        output_path = os.path.join(base_dir, output_html)
    else:
        output_path = output_html

    # Visualize
    net.force_atlas_2based()
    net.show(output_path)

    return output_path  # Return the path for use in Streamlit
