import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Set page config
st.set_page_config(page_title="Car Sharing Dashboard", layout="wide")

# Function to load CSV files into dataframes
@st.cache_data
def load_data():
    """Load the car sharing datasets from CSV files."""
    try:
        trips = pd.read_csv("datasets/trips.csv")
        cars = pd.read_csv("datasets/cars.csv")
        cities = pd.read_csv("datasets/cities.csv")
        return trips, cars, cities
    except FileNotFoundError as e:
        st.error(f"Error loading data: {e}")
        st.info("Please make sure the CSV files are in the 'datasets/' folder")
        return None, None, None

# Load data
trips, cars, cities = load_data()

if trips is not None and cars is not None and cities is not None:
    # Merge trips with cars (joining on car_id)
    trips_merged = trips.merge(cars, left_on="car_id", right_on="id", how="left", suffixes=("", "_car"))
    
    # Merge with cities for car's city (joining on city_id)
    trips_merged = trips_merged.merge(cities, left_on="city_id", right_on="city_id", how="left", suffixes=("", "_city"))
    
    # Drop useless id columns
    trips_merged = trips_merged.drop(columns=["id_car", "id_customer"], errors='ignore')
    # Rename id column to trip_id for clarity
    if "id" in trips_merged.columns:
        trips_merged = trips_merged.rename(columns={"id": "trip_id"})
    
    # Update date format - convert pickup_time and dropoff_time to datetime
    trips_merged['pickup_time'] = pd.to_datetime(trips_merged['pickup_time'])
    trips_merged['dropoff_time'] = pd.to_datetime(trips_merged['dropoff_time'])
    
    # Create a new column called "pickup_date" and get the date from pickup_time
    trips_merged['pickup_date'] = trips_merged['pickup_time'].dt.date
    
    # Calculate duration in minutes
    trips_merged['duration_minutes'] = (trips_merged['dropoff_time'] - trips_merged['pickup_time']).dt.total_seconds() / 60
    
    # Title
    st.title("🚗 Car Sharing Dashboard")
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Get unique car brands from the dataframe
    available_brands = sorted(trips_merged['brand'].unique())
    selected_brands = st.sidebar.multiselect(
        "Select Car Brand(s)",
        options=available_brands,
        default=available_brands  # Show all brands by default
    )
    
    # Filter the dataframe based on selected brands
    if selected_brands:
        trips_filtered = trips_merged[trips_merged['brand'].isin(selected_brands)]
    else:
        trips_filtered = trips_merged
    
    # Compute business performance metrics
    total_trips = len(trips_filtered)
    total_distance = trips_filtered['distance'].sum()
    
    # Car model with the highest revenue
    if 'revenue' in trips_filtered.columns:
        revenue_by_model = trips_filtered.groupby('model')['revenue'].sum()
        top_car = revenue_by_model.idxmax() if len(revenue_by_model) > 0 else "N/A"
        top_revenue = revenue_by_model.max() if len(revenue_by_model) > 0 else 0
    else:
        top_car = "N/A"
        top_revenue = 0
    
    # Display metrics in columns
    st.subheader("📊 Key Metrics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Total Trips", value=f"{total_trips:,}")
    
    with col2:
        st.metric(label="Top Car Model by Revenue", value=str(top_car))
    
    with col3:
        st.metric(label="Total Distance (km)", value=f"{total_distance:,.2f}")
    
    # Additional metric for total revenue
    st.metric(label="Total Revenue", value=f"${trips_filtered['revenue'].sum():,.2f}" if 'revenue' in trips_filtered.columns else "N/A")
    
    # Display preview of the dataframe
    st.subheader("📋 Data Preview")
    st.write(f"Showing {len(trips_filtered)} trips")
    st.dataframe(trips_filtered.head(10), use_container_width=True)
    
    # Visualizations
    st.subheader("📈 Data Visualizations")
    
    # Create tabs for different visualizations
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Trips Over Time",
        "Revenue Per Car Model",
        "Cumulative Revenue",
        "Trips Per Car Model",
        "Avg Duration by City",
        "Revenue by City"
    ])
    
    # 1. Trips Over Time
    with tab1:
        st.subheader("Trips Over Time")
        trips_by_date = trips_filtered.groupby('pickup_date').size().reset_index(name='count')
        if len(trips_by_date) > 0:
            fig = px.line(
                trips_by_date,
                x='pickup_date',
                y='count',
                markers=True,
                title="Number of Trips Per Day",
                labels={'pickup_date': 'Date', 'count': 'Number of Trips'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for selected filters")
    
    # 2. Revenue Per Car Model
    with tab2:
        st.subheader("Revenue Per Car Model")
        if 'revenue' in trips_filtered.columns and 'model' in trips_filtered.columns:
            revenue_by_model = trips_filtered.groupby('model')['revenue'].sum().sort_values(ascending=False).head(10)
            if len(revenue_by_model) > 0:
                fig = px.bar(
                    x=revenue_by_model.index,
                    y=revenue_by_model.values,
                    title="Top 10 Car Models by Revenue",
                    labels={'x': 'Car Model', 'y': 'Revenue ($)'}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No revenue data available")
        else:
            st.warning("Required columns not found in dataset")
    
    # 3. Cumulative Revenue Growth Over Time
    with tab3:
        st.subheader("Cumulative Revenue Growth Over Time")
        if 'revenue' in trips_filtered.columns:
            daily_revenue = trips_filtered.groupby('pickup_date')['revenue'].sum().reset_index()
            daily_revenue = daily_revenue.sort_values('pickup_date')
            daily_revenue['cumulative_revenue'] = daily_revenue['price'].cumsum()
            
            if len(daily_revenue) > 0:
                fig = px.area(
                    daily_revenue,
                    x='pickup_date',
                    y='cumulative_revenue',
                    title="Cumulative Revenue Growth",
                    labels={'pickup_date': 'Date', 'cumulative_revenue': 'Cumulative Revenue ($)'}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available for selected filters")
        else:
            st.warning("Price column not found in dataset")
    
    # 4. Number of Trips Per Car Model
    with tab4:
        st.subheader("Number of Trips Per Car Model")
        trips_by_model = trips_filtered.groupby('model').size().sort_values(ascending=False).head(10)
        if len(trips_by_model) > 0:
            fig = px.bar(
                x=trips_by_model.index,
                y=trips_by_model.values,
                title="Top 10 Car Models by Number of Trips",
                labels={'x': 'Car Model', 'y': 'Number of Trips'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available")
    
    # 5. Average Trip Duration by City
    with tab5:
        st.subheader("Average Trip Duration by City")
        if 'duration_minutes' in trips_filtered.columns and 'city_name' in trips_filtered.columns:
            avg_duration_by_city = trips_filtered.groupby('city_name')['duration_minutes'].mean().sort_values(ascending=False)
            if len(avg_duration_by_city) > 0:
                fig = px.bar(
                    x=avg_duration_by_city.index,
                    y=avg_duration_by_city.values,
                    title="Average Trip Duration by City",
                    labels={'x': 'City', 'y': 'Average Duration (minutes)'}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available")
        else:
            st.warning("Required columns (duration_minutes or city_name) not found")
    
    # 6. Revenue by City
    with tab6:
        st.subheader("Revenue by City")
        if 'revenue' in trips_filtered.columns and 'city_name' in trips_filtered.columns:
            revenue_by_city = trips_filtered.groupby('city_name')['revenue'].sum().sort_values(ascending=False)
            if len(revenue_by_city) > 0:
                fig = px.bar(
                    x=revenue_by_city.index,
                    y=revenue_by_city.values,
                    title="Revenue by City",
                    labels={'x': 'City', 'y': 'Revenue ($)'}
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available")
        else:
            st.warning("Required columns not found in dataset")
    
    # Additional helpful information
    st.sidebar.markdown("---")
    st.sidebar.info("💡 Use the filters above to explore different car brands and their performance metrics.")
