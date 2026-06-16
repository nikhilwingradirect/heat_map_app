import streamlit as st
import plotly.express as px
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. Streamlit Page Setup ---
st.set_page_config(page_title="Warehouse Floor Plan Heatmap", page_icon="📦", layout="wide")
st.title("📦 Warehouse Floor Plan Heatmap")
st.markdown(
    "Top-down physical view of warehouse performance. Aisles are split into Odd/Even rows, with a main cross-aisle separating sections A-I and J-Z.")


# --- 2. Data Loading & Generation ---
@st.cache_data
def generate_simulated_data():
    """Generates dummy data spanning Aisles A-Z with Odd/Even Bays."""
    np.random.seed(42)
    # Aisles A through Z
    aisles = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
    # Bays 01 through 20 (Odd and Even)
    bays = [f"{i:02d}" for i in range(1, 21)]
    shelves = ['A', 'B', 'C', 'D']
    bins = ['01', '02', '03']

    data = []
    for _ in range(3000):
        loc = f"{np.random.choice(aisles)}.{np.random.choice(bays)}.{np.random.choice(shelves)}.{np.random.choice(bins)}"
        sales = np.random.randint(1, 150)
        data.append({'Item': f"ITEM_{np.random.randint(1000, 9999)}", 'Location': loc, 'Quantity': sales})
    return pd.DataFrame(data)


st.sidebar.header("Data Source")
uploaded_file = st.sidebar.file_uploader("Upload your warehouse CSV", type=['csv'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.sidebar.success("File successfully loaded!")
else:
    st.info("Upload your own CSV in the sidebar to update the map.")
    #df = generate_simulated_data()

# --- 3. Data Processing (Physical Mapping) ---
try:
    # --- Outlier Adjustment Line ---
    # Sort by sales descending to compare each sale to the next largest
    df = df.sort_values(by='Quantity', ascending=False).reset_index(drop=True)

    # Calculate the gap between the current sale and the next largest sale
    # (.diff(-1) looks at the row below it in a descending sorted list)
    sales_gap = df['Quantity'].diff(-1)

    # If the gap is > 1000, reduce the quantity 5x (Sales / 5), otherwise keep it as is
    df['Quantity'] = np.where(sales_gap > 1000, df['Quantity'] / 5, df['Quantity'])

    # Split the location string
    df[['Aisle', 'Bay', 'Shelf', 'Bin']] = df['Location'].str.split('.', expand=True)

    # Convert Bay to integer to calculate Parity (Odd/Even) and physical Depth
    df['Bay_Num'] = df['Bay'].astype(int)

    # Identify if the row is on the Odd or Even side of the aisle
    df['Row_Side'] = np.where(df['Bay_Num'] % 2 != 0, 'Odd', 'Even')

    # Combine Aisle and Side for X-axis (e.g., "A (Odd)", "A (Even)")
    df['Aisle_Row'] = df['Aisle'] + " " + df['Row_Side']

    # Calculate "Bay Depth" so Bay 1 and 2 align at Depth 1; Bays 3 and 4 align at Depth 2
    #if (df["Bay_Num"] == 0 | df["Bay_Num" == 1]):
        #df["Bay_Depth"] = 0
    df['Bay_Depth'] = np.where(df['Bay_Num'] == 0, 0, (df['Bay_Num'] // 2) - 5)
    # Aggregate sales by the new physical coordinates
    physical_agg = df.groupby(['Aisle', 'Aisle_Row', 'Bay_Depth'])['Quantity'].sum().reset_index()

    # Split data into the two sides of the warehouse
    side1_df = physical_agg[physical_agg['Aisle'] <= 'I']
    side2_df = physical_agg[physical_agg['Aisle'] >= 'J']

    # Pivot both sides into 2D matrices
    matrix1 = side1_df.pivot(index='Bay_Depth', columns='Aisle_Row', values='Quantity').fillna(0)
    matrix2 = side2_df.pivot(index='Bay_Depth', columns='Aisle_Row', values='Quantity').fillna(0)

    # Sort Y-axis descending so Depth 1 (front of warehouse) is at the bottom
    matrix1 = matrix1.sort_index(ascending=False)
    matrix2 = matrix2.sort_index(ascending=False)

    # Ensure X-axis columns are sorted alphabetically (A Odd, A Even, B Odd, B Even...)
    matrix1 = matrix1[sorted(matrix1.columns)]
    matrix2 = matrix2[sorted(matrix2.columns)]

    # --- 4. Plotly Interactive Visualization (Subplots) ---
    # Create a 1x2 grid for the two sides of the warehouse
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("⬅️ Warehouse Side 1 (Aisles A - I)", "Warehouse Side 2 (Aisles J - Z) ➡️"),
        horizontal_spacing=0.05,  # Gap between the two sides
        shared_yaxes=True  # Lock the Y-axis so depths align visually
    )

    # Add Side 1 (A-I) Heatmap
    fig.add_trace(
        go.Heatmap(
            z=matrix1.values,
            x=matrix1.columns,
            y=matrix1.index,
            colorscale='YlOrRd',
            coloraxis="coloraxis",  # Share the color scale between both maps
            text=matrix1.values,  # Add values as text on hover/display
            texttemplate="%{text}",
            hovertemplate="Row: %{x}<br>Depth: %{y}<br>Sales: %{z}<extra></extra>"
        ),
        row=1, col=1
    )

    # Add Side 2 (J-Z) Heatmap
    fig.add_trace(
        go.Heatmap(
            z=matrix2.values,
            x=matrix2.columns,
            y=matrix2.index,
            colorscale='YlOrRd',
            coloraxis="coloraxis",
            text=matrix2.values,
            texttemplate="%{text}",
            hovertemplate="Row: %{x}<br>Depth: %{y}<br>Sales: %{z}<extra></extra>"
        ),
        row=1, col=2
    )

    # Formatting and layout updates
    fig.update_layout(
        height=800,
        coloraxis=dict(colorscale='YlOrRd', colorbar_title="Total Sales"),
        hovermode="closest",
        margin=dict(l=20, r=20, t=60, b=20)
    )

    # Move X-axes to the top for a floor plan feel
    fig.update_xaxes(side="bottom", tickangle=-45)

    # Label the Y-axes clearly
    fig.update_yaxes(title_text="Bay Depth (Distance into Aisle)", row=1, col=1)

    # Display the chart
    st.plotly_chart(fig, use_container_width=True)


    st.markdown("---")
    st.header("🔍 Macro Drill-Down: Shelf & Bin Blueprint")
    st.markdown(
        "Pick a specific coordinate below to inspect exactly which **shelves (vertical levels)** and **bins (horizontal openings)** are selling.")

    # Selectboxes to let user target a location
    col1, col2 = st.columns(2)
    with col1:
        distinct_aisle_rows = sorted(df['Aisle_Row'].unique())
        selected_row = st.selectbox("🎯 Target Aisle & Row Side:", distinct_aisle_rows)
    with col2:
        row_filtered_df = df[df['Aisle_Row'] == selected_row]
        distinct_bays = sorted(row_filtered_df['Bay_Num'].unique())

        selected_bay = st.selectbox("🔢 Target Bay Number:", distinct_bays)

        # Filter data down to that exact physical zone using the Bay Number
    sub_df = df[(df['Aisle_Row'] == selected_row) & (df['Bay_Num'] == selected_bay)]

    if not sub_df.empty:
        # Group sales by Shelf level and Bin number
        sub_agg = sub_df.groupby(['Shelf', 'Bin'])['Quantity'].sum().reset_index()
        sub_matrix = sub_agg.pivot(index='Shelf', columns='Bin', values='Quantity').fillna(0)

        # Sort shelves descending so Shelf D is physically above Shelf A on screen
        sub_matrix = sub_matrix.sort_index(ascending=False)
        sub_matrix = sub_matrix[sorted(sub_matrix.columns)]

        # Build secondary heatmap
        sub_fig = px.imshow(
            sub_matrix,
            labels=dict(x="Bin Number", y="Shelf Level", color="Units Sold"),
            x=sub_matrix.columns,
            y=sub_matrix.index,
            text_auto=True,
            color_continuous_scale="Viridis",  # Different color matrix so it stands out
            aspect="auto"
        )

        sub_fig.update_layout(
            title=f"Detailed Micro-Map for {selected_row} | Bay Number: {selected_bay}",
            height=350,
            margin=dict(l=20, r=20, t=50, b=20)
         )

        st.plotly_chart(sub_fig, use_container_width=True)
    else:
        st.warning("No sales inventory data registered at this specific coordinate.")

except Exception as e:
    st.error(
        f"Error processing data. Ensure your CSV locations are formatted 'A.10.B.03' and have numerical bays. Details: {e}")