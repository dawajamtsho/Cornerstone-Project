#!/usr/bin/env python3
# main_v4.py - Energy MIS Dashboard v4.0 with Official APIs as Primary Sources
# Primary: ENTSO-E, Electricity Maps, IEA, World Bank, UN COMTRADE
# Secondary: Web Scraping (Interconnections, News, Fallback Data)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import logging

from api_clients import (
    ENTSOEClient, ElectricityMapsClient, IEAClient, 
    WorldBankClient, UNComtradeClient, validate_api_tokens
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="
    IIT Delhi - ISA
    Energy MIS Dashboard v4.0",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CSS STYLING ====================
st.markdown("""
    <style>
        .main-header {
            color: #1f77b4;
            font-size: 2.5rem;
            font-weight: bold;
            text-align: center;
            margin-bottom: 1rem;
            padding: 1rem;
            border-bottom: 3px solid #1f77b4;
        }
        .data-source-tag {
            display: inline-block;
            background: #2ca02c;
            color: white;
            padding: 0.3rem 0.8rem;
            border-radius: 1rem;
            font-size: 0.85rem;
            margin-right: 0.5rem;
            font-weight: bold;
        }
        .api-source {
            background: #d4e6f1;
            border-left: 4px solid #1f77b4;
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 0.5rem;
        }
        .scrape-source {
            background: #f9e79f;
            border-left: 4px solid #f39c12;
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)

# ==================== SESSION STATE ====================
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'
if 'api_tokens' not in st.session_state:
    st.session_state.api_tokens = {
        'entsoe': '',
        'emaps': '',
        'iea': '',
        'world_bank': '',
        'un_comtrade': ''
    }

# ==================== SIDEBAR - API CONFIGURATION ====================
with st.sidebar:
    st.markdown("## ⚙️ Dashboard Configuration")
    
    # API Tokens Section
    with st.expander("🔑 API Tokens (Required for Primary Data)"):
        st.info("Enter your API tokens to access primary data sources")
        
        st.session_state.api_tokens['entsoe'] = st.text_input(
            "ENTSO-E Token",
            value=st.session_state.api_tokens['entsoe'],
            type="password",
            help="Get from https://transparency.entsoe.eu"
        )
        
        st.session_state.api_tokens['emaps'] = st.text_input(
            "Electricity Maps Token",
            value=st.session_state.api_tokens['emaps'],
            type="password",
            help="Get from https://api.electricitymaps.com"
        )
        
        st.session_state.api_tokens['iea'] = st.text_input(
            "IEA API Key",
            value=st.session_state.api_tokens['iea'],
            type="password",
            help="Get from https://data.iea.org"
        )
        
        st.session_state.api_tokens['world_bank'] = st.text_input(
            "World Bank API Key (Optional)",
            value=st.session_state.api_tokens['world_bank'],
            help="Public API - no key needed"
        )

        # in sidebar config
        st.session_state.api_tokens['newsapi'] = st.text_input(
            "NewsAPI.org key",
            value=st.session_state.api_tokens.get('newsapi', ''),
            type="password",
            help="Get from https://newsapi.org"
        )

        
        # Validate tokens
        if st.button("✓ Validate Tokens"):
            validation = validate_api_tokens(st.session_state.api_tokens)
            for service, status in validation.items():
                if status == 'Valid':
                    st.success(f"✓ {service.upper()}: {status}")
                elif status == 'Missing':
                    st.warning(f"⚠ {service.upper()}: {status}")
                else:
                    st.error(f"✗ {service.upper()}: {status}")
    
    st.divider()
    
    # Theme Toggle
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Theme:**")
    with col2:
        new_theme = st.radio("", ["Light", "Dark"], label_visibility="collapsed", horizontal=True)
        st.session_state.theme = new_theme.lower()
    
    st.divider()
    
    # Refresh Controls
    if st.button("🔄 Refresh All Data", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache cleared!")
        st.rerun()
    
    st.divider()
    
    # Data Source Legend
    st.markdown("### 📊 Data Sources")
    st.markdown("""
    <div class="api-source">
    <b>🔌 Primary (API)</b><br>
    • ENTSO-E Transparency<br>
    • Electricity Maps<br>
    • IEA<br>
    • World Bank WDI<br>
    • UN COMTRADE
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="scrape-source">
    <b>🕷️ Secondary (Scraping)</b><br>
    • Interconnections<br>
    • Energy News<br>
    • Commodity Prices<br>
    • Fallback Data
    </div>
    """, unsafe_allow_html=True)

# ==================== MAIN HEADER ====================
st.markdown(
    '<div class="main-header">⚡ Energy MIS Dashboard v4.0</div>',
    unsafe_allow_html=True
)

# ==================== KEY METRICS ====================
st.markdown("## 📈 System Status")

col1, col2, col3, col4 = st.columns(4)

with col1:
    entsoe_status = "✅ Connected" if st.session_state.api_tokens['entsoe'] else "❌ Not Configured"
    st.metric("ENTSO-E API", entsoe_status.split()[0])

with col2:
    emaps_status = "✅ Connected" if st.session_state.api_tokens['emaps'] else "❌ Not Configured"
    st.metric("Electricity Maps", emaps_status.split()[0])

with col3:
    iea_status = "✅ Connected" if st.session_state.api_tokens['iea'] else "❌ Not Configured"
    st.metric("IEA API", iea_status.split()[0])

with col4:
    wb_status = "✅ Available" if True else "❌ Unavailable"
    st.metric("World Bank WDI", "✅")

st.divider()

# ==================== TABS ====================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 ENTSO-E Europe Grid",
    "🌍 Global Interconnections", 
    "📉 Electricity Analysis",
    "💹 Trade & Economics",
    "📰 News & Articles",
    "🕷️ Web Scraped Data"
])

# ==================== TAB 1: ENTSO-E EUROPE GRID ====================
with tab1:
    st.markdown("### 🇪🇺 ENTSO-E European Grid Data (Primary API)")
    
    if not st.session_state.api_tokens['entsoe']:
        st.warning("⚠️ Please configure ENTSO-E API token in sidebar to access this data")
    else:
        try:
            entsoe_client = ENTSOEClient(st.session_state.api_tokens['entsoe'])
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                selected_country = st.selectbox(
                    "Select European Country",
                    ["Germany", "France", "Spain", "Italy", "Netherlands", "Belgium", "Poland"],
                    key="entsoe_country"
                )
            
            with col2:
                time_range = st.selectbox(
                    "Time Range",
                    ["24 hours", "7 days", "30 days"],
                    key="entsoe_range"
                )
            
            with col3:
                metric_type = st.selectbox(
                    "Metric",
                    ["Generation Forecast", "Load Forecast", "Cross-Border Flows"],
                    key="entsoe_metric"
                )
            
            # Get data
            start_time = datetime.now() - timedelta(days=1)
            end_time = datetime.now()
            start_str = start_time.strftime('%Y%m%d%H%M')
            end_str = end_time.strftime('%Y%m%d%H%M')
            
            area_codes = {
                "Germany": "10YDE-VE-------2",
                "France": "10YFR-RTE------C",
                "Spain": "10YES-REE------0",
                "Italy": "10YIT-GRTN-----B",
                "Netherlands": "10YNL----------L",
                "Belgium": "10YBE----------2",
                "Poland": "10YPL-AREA-----S"
            }
            
            area_code = area_codes.get(selected_country, "10YDE-VE-------2")
            
            if metric_type == "Generation Forecast":
                data = entsoe_client.get_generation_forecast(area_code, start_str, end_str)
                if data is not None and not data.empty:
                    fig = px.line(
                        data, x='timestamp', y='generation_mw',
                        title=f"Generation Forecast - {selected_country}",
                        template='plotly_white' if st.session_state.theme == 'light' else 'plotly_dark'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.info(f"✅ Data from ENTSO-E Transparency Platform API")
                else:
                    st.warning("No data available from ENTSO-E API")
            
            elif metric_type == "Load Forecast":
                data = entsoe_client.get_load_forecast(area_code, start_str, end_str)
                if data is not None and not data.empty:
                    fig = px.line(
                        data, x='timestamp', y='load_mw',
                        title=f"Load Forecast - {selected_country}",
                        template='plotly_white' if st.session_state.theme == 'light' else 'plotly_dark'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.info(f"✅ Data from ENTSO-E Transparency Platform API")
                else:
                    st.warning("No data available from ENTSO-E API")
            
            else:  # Cross-Border Flows
                st.info("Select flow direction for cross-border analysis")
                col1, col2 = st.columns(2)
                with col1:
                    from_country = st.selectbox("From", ["Germany", "France", "Spain"], key="from_country")
                with col2:
                    to_country = st.selectbox("To", ["France", "Spain", "Italy"], key="to_country")
                
                if from_country != to_country:
                    from_code = area_codes.get(from_country)
                    to_code = area_codes.get(to_country)
                    
                    if from_code and to_code:
                        data = entsoe_client.get_cross_border_flows(from_code, to_code, start_str, end_str)
                        if data is not None and not data.empty:
                            fig = px.line(
                                data, x='timestamp', y='flow_mw',
                                title=f"Cross-Border Flow: {from_country} → {to_country}",
                                template='plotly_white' if st.session_state.theme == 'light' else 'plotly_dark'
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            st.info(f"✅ Data from ENTSO-E Transparency Platform API")
                        else:
                            st.warning("No flow data available")
        
        except Exception as e:
            st.error(f"Error fetching ENTSO-E data: {e}")

# ==================== TAB 2: GLOBAL INTERCONNECTIONS ====================
with tab2:
    st.markdown("### 🌍 Global Electricity Interconnections Map")
    
    st.info("Primary: Global Energy Monitor API | Fallback: Web Scraping")
    
    col1, col2 = st.columns([2, 1])
    with col2:
        map_center = st.selectbox(
            "Map Center",
            ["Global", "Asia", "Europe", "Americas"],
            key="map_center"
        )
    
    # Get interconnections data
    interconnections = InterconnectionScraper.get_global_interconnections()
    
    if interconnections:
        df_interconnections = pd.DataFrame(interconnections)
        
        # Filter by region
        if map_center != "Global":
            region_map = {
                "Asia": ["SAARC", "ASEAN", "EAST_ASIA"],
                "Europe": ["ENTSO-E"],
                "Americas": ["NORTH_AMERICA"]
            }
            df_interconnections = df_interconnections[
                df_interconnections['region'].isin(region_map.get(map_center, []))
            ]
        
        # Map centers
        if map_center == "Asia":
            center = [20, 78]
            zoom = 4
        elif map_center == "Europe":
            center = [54, 25]
            zoom = 4
        elif map_center == "Americas":
            center = [0, -100]
            zoom = 3
        else:
            center = [20, 0]
            zoom = 2
        
        m = folium.Map(location=center, zoom_start=zoom, tiles='OpenStreetMap')
        
        # Add country markers
        zones = set(df_interconnections['from'].unique()) | set(df_interconnections['to'].unique())
        zone_coords = {
            'India': (20.5937, 78.9629), 'China': (35.8617, 104.1954),
            'Bangladesh': (23.6850, 90.3563), 'Pakistan': (30.3753, 69.3451),
            'Germany': (51.1657, 10.4515), 'France': (46.2276, 2.2137),
            'Spain': (40.4637, -3.7492), 'Italy': (41.8719, 12.5674),
            'Japan': (36.2048, 138.2529), 'Thailand': (15.8700, 100.9925),
            'Vietnam': (14.0583, 108.2772), 'Iran': (32.4279, 53.6880),
            'Turkey': (38.9637, 35.2433), 'Indonesia': (-0.7893, 113.9213),
            'Malaysia': (3.1390, 101.6869)
        }
        
        for zone in zones:
            if zone in zone_coords:
                lat, lon = zone_coords[zone]
                folium.CircleMarker(
                    location=[lat, lon], radius=8, popup=zone,
                    color='#1f77b4', fill=True, fillColor='#1f77b4', fillOpacity=0.7
                ).add_to(m)
        
        # Add interconnection lines
        for _, row in df_interconnections.iterrows():
            color = '#2ca02c' if row['status'] == 'operating' else '#d62728'
            weight = min(5, int(row['capacity_mw'] / 500))
            
            folium.PolyLine(
                locations=[[row['from_lat'], row['from_lon']], [row['to_lat'], row['to_lon']]],
                color=color,
                weight=weight,
                opacity=0.8,
                popup=f"{row['from']}-{row['to']}<br>{row['capacity_mw']}MW {row['type']}<br>Status: {row['status']}"
            ).add_to(m)
        
        st_folium(m, width=1400, height=700)
        
        # Display table
        st.markdown("#### Interconnection Details")
        display_df = df_interconnections[[
            'from', 'to', 'capacity_mw', 'voltage_kv', 'type', 'status', 'commissioning_year'
        ]].copy()
        display_df.columns = ['From', 'To', 'Capacity (MW)', 'Voltage (kV)', 'Type', 'Status', 'Year']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.success(f"✅ Data from Global Energy Monitor (Web Scraping)")
    else:
        st.error("Unable to fetch interconnections data")

# ==================== TAB 3: CARBON INTENSITY - FIXED ====================
with tab3:
    st.markdown("### 📉 Carbon Intensity & Electricity Mix Analysis")
    
    st.info("""
    **Electricity Maps API Integration**
    Primary source for real-time carbon data and electricity mix analysis
    """)
    
    if not st.session_state.api_tokens['emaps']:
        st.warning("⚠️ Please configure Electricity Maps token in sidebar to access this data")
    else:
        try:
            emaps_client = ElectricityMapsClient(st.session_state.api_tokens['emaps'])
            
            # ==================== PARAMETER SELECTION ====================
            st.markdown("#### 📊 Select Parameters to Display")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                selected_country = st.selectbox(
                    "🌍 Select Country/Zone",
                    ["India", "China", "Germany", "France", "Spain", "Italy", 
                     "Japan", "USA", "Brazil", "UK", "Canada", "Australia"],
                    key="emaps_country"
                )
            
            with col2:
                # CRITICAL FIX: Multi-select for metrics (not just Carbon Intensity)
                selected_metrics = st.multiselect(
                    "📊 Select Metrics to Display",
                    [
                        "Carbon Intensity",
                        "Renewable %",
                        "Fossil Fuel %",
                        "Coal %",
                        "Gas %",
                        "Nuclear %",
                        "Hydro %",
                        "Wind %",
                        "Solar %",
                        "Biomass %",
                        "Electricity Mix",
                        "7-Day Carbon Trend",
                        "Emissions Rate"
                    ],
                    default=["Carbon Intensity", "Renewable %"],
                    key="emaps_metrics"
                )
            
            # If no metrics selected, use defaults
            if not selected_metrics:
                selected_metrics = ["Carbon Intensity", "Renewable %"]
            
            st.divider()
            
            # ==================== ZONE MAPPING ====================
            zone_map = {
                'India': 'IN', 'China': 'CN', 'Germany': 'DE',
                'France': 'FR', 'Spain': 'ES', 'Italy': 'IT',
                'Japan': 'JP', 'USA': 'US', 'Brazil': 'BR',
                'UK': 'GB', 'Canada': 'CA', 'Australia': 'AU'
            }
            zone = zone_map.get(selected_country, 'IN')
            
            # ==================== GET DATA ONCE ====================
            try:
                current_data = emaps_client.get_current_carbon_intensity(zone)
                
                # Get historical data for trends
                start_date = datetime.now() - timedelta(days=7)
                end_date = datetime.now()
                start_str = start_date.strftime('%Y-%m-%dT00:00:00Z')
                end_str = end_date.strftime('%Y-%m-%dT23:59:59Z')
                
                ci_data = emaps_client.get_carbon_intensity_history(zone, start_str, end_str)
                
            except Exception as e:
                st.error(f"Error fetching data: {e}")
                current_data = None
                ci_data = None
            
            # ==================== DISPLAY SELECTED METRICS DYNAMICALLY ====================
            
            if current_data is None:
                st.warning("⚠️ Unable to fetch data for selected country")
            else:
                # CRITICAL FIX: Create visualizations for EACH selected metric
                
                # ========== METRIC 1: CARBON INTENSITY ==========
                if "Carbon Intensity" in selected_metrics:
                    st.markdown("#### 🌍 Carbon Intensity")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        ci = current_data.get('carbonIntensity', 'N/A')
                        st.metric(
                            "Current CI",
                            f"{ci} gCO₂/kWh" if ci != 'N/A' else ci,
                            delta="↓ Clean" if ci and ci < 200 else "↑ Check"
                        )
                    
                    with col2:
                        st.metric("Status", current_data.get('status', 'Unknown'))
                    
                    with col3:
                        st.metric("Zone", selected_country)
                    
                    with col4:
                        st.metric("Updated", "Now")
                    
                    st.success(f"✅ Data from Electricity Maps API")
                    st.divider()
                
                # ========== METRIC 2: RENEWABLE % ==========
                if "Renewable %" in selected_metrics:
                    st.markdown("#### ♻️ Renewable Energy Percentage")
                    
                    if current_data and 'electricity' in current_data:
                        electricity = current_data['electricity']
                        renewables = electricity.get('renewables', 0)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Gauge chart for renewable percentage
                            fig_renewable = go.Figure(go.Indicator(
                                mode="gauge+number+delta",
                                value=renewables,
                                title={'text': f"Renewable % - {selected_country}"},
                                domain={'x': [0, 1], 'y': [0, 1]},
                                gauge={
                                    'axis': {'range': [0, 100]},
                                    'bar': {'color': "green"},
                                    'steps': [
                                        {'range': [0, 30], 'color': "lightcoral"},
                                        {'range': [30, 60], 'color': "lightyellow"},
                                        {'range': [60, 100], 'color': "lightgreen"}
                                    ],
                                    'threshold': {
                                        'line': {'color': "darkgreen", 'width': 4},
                                        'thickness': 0.75,
                                        'value': 75
                                    }
                                }
                            ))
                            fig_renewable.update_layout(height=350)
                            st.plotly_chart(fig_renewable, use_container_width=True)
                        
                        with col2:
                            # Breakdown of renewable sources
                            renewable_sources = {
                                'Hydro': electricity.get('hydro', 0),
                                'Wind': electricity.get('wind', 0),
                                'Solar': electricity.get('solar', 0),
                                'Biomass': electricity.get('biomass', 0),
                                'Geothermal': electricity.get('geothermal', 0)
                            }
                            renewable_sources = {k: v for k, v in renewable_sources.items() if v > 0}
                            
                            if renewable_sources:
                                fig_renewable_pie = px.pie(
                                    values=list(renewable_sources.values()),
                                    names=list(renewable_sources.keys()),
                                    title=f"Renewable Mix - {selected_country}",
                                )
                                st.plotly_chart(fig_renewable_pie, use_container_width=True)
                        
                        st.success(f"✅ Data from Electricity Maps API")
                    st.divider()
                
                # ========== METRIC 3: FOSSIL FUEL % ==========
                if "Fossil Fuel %" in selected_metrics:
                    st.markdown("#### ⛽ Fossil Fuel Percentage")
                    
                    if current_data and 'electricity' in current_data:
                        electricity = current_data['electricity']
                        fossil = electricity.get('fossil', 0) or (
                            electricity.get('coal', 0) + 
                            electricity.get('gas', 0) + 
                            electricity.get('oil', 0)
                        )
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            fig_fossil = go.Figure(go.Indicator(
                                mode="gauge+number",
                                value=fossil,
                                title={'text': f"Fossil Fuel % - {selected_country}"},
                                gauge={
                                    'axis': {'range': [0, 100]},
                                    'bar': {'color': "darkred"},
                                    'steps': [
                                        {'range': [0, 30], 'color': "lightgreen"},
                                        {'range': [30, 70], 'color': "lightyellow"},
                                        {'range': [70, 100], 'color': "lightcoral"}
                                    ]
                                }
                            ))
                            fig_fossil.update_layout(height=350)
                            st.plotly_chart(fig_fossil, use_container_width=True)
                        
                        with col2:
                            # Breakdown by fuel type
                            fossil_sources = {
                                'Coal': electricity.get('coal', 0),
                                'Gas': electricity.get('gas', 0),
                                'Oil': electricity.get('oil', 0)
                            }
                            fossil_sources = {k: v for k, v in fossil_sources.items() if v > 0}
                            
                            if fossil_sources:
                                fig_fossil_pie = px.pie(
                                    values=list(fossil_sources.values()),
                                    names=list(fossil_sources.keys()),
                                    title=f"Fossil Fuel Mix - {selected_country}",
                                )
                                st.plotly_chart(fig_fossil_pie, use_container_width=True)
                        
                        st.success(f"✅ Data from Electricity Maps API")
                    st.divider()
                
                # ========== METRIC 4: INDIVIDUAL FUEL TYPES ==========
                if any(m in selected_metrics for m in ["Coal %", "Gas %", "Nuclear %", "Hydro %", "Wind %", "Solar %", "Biomass %"]):
                    
                    if current_data and 'electricity' in current_data:
                        electricity = current_data['electricity']
                        
                        st.markdown("#### 📊 Electricity Generation Sources")
                        
                        # Create data for all sources
                        fuel_data = {
                            'Coal': electricity.get('coal', 0),
                            'Gas': electricity.get('gas', 0),
                            'Nuclear': electricity.get('nuclear', 0),
                            'Hydro': electricity.get('hydro', 0),
                            'Wind': electricity.get('wind', 0),
                            'Solar': electricity.get('solar', 0),
                            'Biomass': electricity.get('biomass', 0),
                            'Geothermal': electricity.get('geothermal', 0),
                            'Oil': electricity.get('oil', 0)
                        }
                        
                        # Filter based on selected metrics
                        fuel_data_filtered = {}
                        if "Coal %" in selected_metrics:
                            fuel_data_filtered['Coal'] = fuel_data['Coal']
                        if "Gas %" in selected_metrics:
                            fuel_data_filtered['Gas'] = fuel_data['Gas']
                        if "Nuclear %" in selected_metrics:
                            fuel_data_filtered['Nuclear'] = fuel_data['Nuclear']
                        if "Hydro %" in selected_metrics:
                            fuel_data_filtered['Hydro'] = fuel_data['Hydro']
                        if "Wind %" in selected_metrics:
                            fuel_data_filtered['Wind'] = fuel_data['Wind']
                        if "Solar %" in selected_metrics:
                            fuel_data_filtered['Solar'] = fuel_data['Solar']
                        if "Biomass %" in selected_metrics:
                            fuel_data_filtered['Biomass'] = fuel_data['Biomass']
                        
                        # If no specific fuel selected but this section triggered, show all non-zero
                        if not fuel_data_filtered:
                            fuel_data_filtered = {k: v for k, v in fuel_data.items() if v > 0}
                        
                        # Remove zero values
                        fuel_data_filtered = {k: v for k, v in fuel_data_filtered.items() if v > 0}
                        
                        if fuel_data_filtered:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Bar chart of selected fuels
                                df_fuel = pd.DataFrame(list(fuel_data_filtered.items()), columns=['Fuel', 'Percentage'])
                                fig_bar = px.bar(
                                    df_fuel,
                                    x='Fuel',
                                    y='Percentage',
                                    title=f"Electricity Sources - {selected_country}",
                                    color='Percentage',
                                    color_continuous_scale='Viridis'
                                )
                                st.plotly_chart(fig_bar, use_container_width=True)
                            
                            with col2:
                                # Table view
                                st.markdown("**Fuel Source Breakdown**")
                                st.dataframe(df_fuel, use_container_width=True, hide_index=True)
                            
                            st.success(f"✅ Data from Electricity Maps API")
                        st.divider()
                
                # ========== METRIC 5: ELECTRICITY MIX (PIE CHART) ==========
                if "Electricity Mix" in selected_metrics:
                    st.markdown("#### 🥧 Complete Electricity Mix")
                    
                    if current_data and 'electricity' in current_data:
                        electricity = current_data['electricity']
                        
                        # Create pie chart with all sources
                        df_mix = pd.DataFrame(list(electricity.items()), columns=['Source', 'Percentage'])
                        df_mix = df_mix[df_mix['Percentage'] > 0]  # Remove zero values
                        
                        if len(df_mix) > 0:
                            fig_pie = px.pie(
                                df_mix,
                                values='Percentage',
                                names='Source',
                                title=f"Complete Electricity Mix - {selected_country}",
                                hole=0  # Set to 0 for full pie, or 0.3 for donut
                            )
                            st.plotly_chart(fig_pie, use_container_width=True)
                            
                            # Show as table
                            st.markdown("**Mix Breakdown**")
                            st.dataframe(df_mix.sort_values('Percentage', ascending=False), 
                                       use_container_width=True, hide_index=True)
                            
                            st.success(f"✅ Data from Electricity Maps API")
                        st.divider()
                
                # ========== METRIC 6: 7-DAY CARBON TREND ==========
                if "7-Day Carbon Trend" in selected_metrics:
                    st.markdown("#### 📈 7-Day Carbon Intensity Trend")
                    
                    if ci_data is not None and not ci_data.empty:
                        # Line chart with moving average
                        fig = go.Figure()
                        
                        fig.add_trace(go.Scatter(
                            x=ci_data['datetime'],
                            y=ci_data['carbonIntensity'],
                            name="Daily CI",
                            line=dict(color='#1f77b4', width=2),
                            hovertemplate='%{x|%Y-%m-%d %H:%M}<br>%{y:.0f} gCO₂/kWh<extra></extra>'
                        ))
                        
                        # Add moving average if enough data
                        if len(ci_data) > 7:
                            ma7 = ci_data['carbonIntensity'].rolling(window=7).mean()
                            fig.add_trace(go.Scatter(
                                x=ci_data['datetime'],
                                y=ma7,
                                name="7-Day Moving Avg",
                                line=dict(color='#ff7f0e', width=2, dash='dash')
                            ))
                        
                        fig.update_layout(
                            title=f"7-Day Carbon Intensity Trend - {selected_country}",
                            xaxis_title="Date",
                            yaxis_title="Carbon Intensity (gCO₂/kWh)",
                            height=450,
                            template='plotly_white' if st.session_state.theme == 'light' else 'plotly_dark',
                            hovermode='x unified'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Statistics
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Average CI", f"{ci_data['carbonIntensity'].mean():.0f} gCO₂/kWh")
                        with col2:
                            st.metric("Peak CI", f"{ci_data['carbonIntensity'].max():.0f} gCO₂/kWh")
                        with col3:
                            st.metric("Min CI", f"{ci_data['carbonIntensity'].min():.0f} gCO₂/kWh")
                        with col4:
                            trend = "↓ Improving" if ci_data['carbonIntensity'].iloc[-1] < ci_data['carbonIntensity'].iloc[0] else "↑ Rising"
                            st.metric("Trend", trend)
                        
                        st.success("✅ Data from Electricity Maps API")
                    else:
                        st.warning("No historical data available")
                    st.divider()
                
                # ========== METRIC 7: EMISSIONS RATE ==========
                if "Emissions Rate" in selected_metrics:
                    st.markdown("#### 🌡️ Emissions Rate")
                    
                    if current_data:
                        emissions = current_data.get('carbonIntensity', 0) / 1000  # Convert to kg/kWh
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric(
                                "Emissions Rate",
                                f"{emissions:.3f} kg CO₂/kWh",
                                delta="Lower is better"
                            )
                        
                        with col2:
                            # Comparison context
                            st.info("""
                            **Reference Values:**
                            - 🟢 Clean: <0.2 kg/kWh
                            - 🟡 Moderate: 0.2-0.5 kg/kWh
                            - 🔴 High: >0.5 kg/kWh
                            """)
                        
                        st.success("✅ Data from Electricity Maps API")
                    st.divider()

        except Exception as e:
            st.error(f"Critical error: {e}")
            logger.exception("Tab 3 error")

# ==================== TAB 4: TRADE & ECONOMICS ====================
with tab4:
    st.markdown("### 💹 Trade & Economic Data (IEA, World Bank, UN COMTRADE)")
    
    st.info("Primary: Official APIs (IEA, World Bank, UN COMTRADE) | Fallback: Web Scraping")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        data_type = st.selectbox(
            "Select Data Type",
            ["Electricity Trade", "Renewable Generation", "Electricity Access", "Electricity Consumption"]
        )
    
    with col2:
        country = st.selectbox(
            "Country",
            ["India", "Germany", "France", "China", "Japan", "Brazil"]
        )
    
    with col3:
        year = st.slider("Year", 2015, 2023, 2023)
    
    if data_type == "Electricity Trade":
        try:
            if st.session_state.api_tokens['iea']:
                iea_client = IEAClient(st.session_state.api_tokens['iea'])
                trade_data = iea_client.get_electricity_trade(country, year)
                if trade_data:
                    st.success("✅ Data from IEA API")
                    st.json(trade_data)
                else:
                    st.info("Using UN COMTRADE as fallback...")
                    un_client = UNComtradeClient()
                    comtrade_data = un_client.get_electricity_trade(country, country, year)
                    if comtrade_data:
                        st.success("✅ Data from UN COMTRADE API")
                        st.dataframe(pd.DataFrame(comtrade_data.get('dataset', [])))
            else:
                st.warning("Configure IEA API token for this data")
        except Exception as e:
            st.error(f"Error: {e}")
    
    elif data_type == "Renewable Generation":
        try:
            if st.session_state.api_tokens['iea']:
                iea_client = IEAClient(st.session_state.api_tokens['iea'])
                renewable_data = iea_client.get_renewable_generation(country, year)
                if renewable_data:
                    st.success("✅ Data from IEA API")
                    st.json(renewable_data)
            else:
                st.warning("Configure IEA API token for this data")
        except Exception as e:
            st.error(f"Error: {e}")
    
    elif data_type == "Electricity Access":
        try:
            country_codes = {
                "India": "IND", "Germany": "DEU", "France": "FRA",
                "China": "CHN", "Japan": "JPN", "Brazil": "BRA"
            }
            country_code = country_codes.get(country, "IND")
            
            wb_client = WorldBankClient()
            access_data = wb_client.get_electricity_access(country_code)
            if access_data is not None and not access_data.empty:
                fig = px.line(
                    access_data, x='year', y='electricity_access',
                    title=f"Electricity Access - {country}",
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)
                st.success("✅ Data from World Bank WDI API")
                st.dataframe(access_data, use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")
    
    else:  # Electricity Consumption
        try:
            country_codes = {
                "India": "IND", "Germany": "DEU", "France": "FRA",
                "China": "CHN", "Japan": "JPN", "Brazil": "BRA"
            }
            country_code = country_codes.get(country, "IND")
            
            wb_client = WorldBankClient()
            consumption_data = wb_client.get_electricity_consumption(country_code)
            if consumption_data is not None and not consumption_data.empty:
                fig = px.line(
                    consumption_data, x='year', y='consumption_kwh',
                    title=f"Electricity Consumption - {country}",
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)
                st.success("✅ Data from World Bank WDI API")
                st.dataframe(consumption_data, use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")


# ==================== TAB 5: NEWS & ARTICLES ====================
with tab5:
    st.markdown("### 📰 Energy News & Articles")
    
    st.info("Primary: RSS Feeds & Official Sources | Fallback: Web Scraping")
    
    col1, col2 = st.columns([2, 1])
    with col2:
        news_category = st.selectbox(
            "Category",
            ["All", "Grid Operations", "Renewables", "Policy", "Trade", "Prices"],
            key="news_category"
        )
    
    # Get news
    with st.spinner("Fetching latest energy news..."):
        news = EnergyNewsScraper.get_energy_news()
    
    articles = []

    with st.spinner("Fetching latest energy news..."):
        # Primary: NewsAPI.org
        if st.session_state.api_tokens.get("newsapi"):
            try:
                news_client = NewsAPIClient(st.session_state.api_tokens["newsapi"])
                articles = news_client.get_energy_news()
            except Exception as e:
                st.warning(f"NewsAPI.org failed: {e}")
        # Fallback: existing scraper
        if not articles:
            try:
                articles = EnergyNewsScraper.get_energy_news()
            except Exception as e:
                st.error(f"Fallback scraper also failed: {e}")
                articles = []

    if not articles:
        st.info("No news available right now.")
    else:
        # Optional category post-filtering (if you add categorization)
        if news_category != "All":
            filtered = [a for a in articles if a.get("category") == news_category]
            if filtered:
                articles = filtered

        st.success(f"Showing {len(articles[:20])} articles")

        for idx, article in enumerate(articles[:20], 1):
            with st.container():
                st.markdown(f"**{idx}. [{article['title']}]({article['link']})**")
                col_a, col_b, col_c = st.columns([3, 2, 2])
                with col_a:
                    st.caption(f"Source: {article.get('source', 'Unknown')}")
                with col_b:
                    st.caption(f"Category: {article.get('category', 'Energy')}")
                with col_c:
                    ts = article.get("timestamp")
                    st.caption(ts.strftime("%Y-%m-%d %H:%M") if ts else "")
            st.divider()

# ==================== TAB 6: WEB SCRAPED DATA ====================
with tab6:
    st.markdown("### 🕷️ Web Scraped Data (Secondary/Fallback Source)")
    
    st.warning("""
    **Important:** This tab uses web scraping as a secondary data source when APIs are unavailable.
    Primary data sources (ENTSO-E, Electricity Maps, IEA, World Bank) are preferred.
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        scrape_type = st.selectbox(
            "Select Data Type",
            ["Commodity Prices", "Interconnections", "Regional News"],
            key="scrape_type"
        )
    
    if scrape_type == "Commodity Prices":
        st.markdown("#### Energy Commodity Prices (Web Scraping)")
        
        with st.spinner("Fetching commodity prices..."):
            prices = CommodityPriceScraper.get_commodity_prices()
        
        if prices:
            col1, col2, col3 = st.columns(3)
            
            if 'oil' in prices and prices['oil']:
                with col1:
                    st.metric(
                        "Brent Crude Oil",
                        f"${prices['oil'].get('brent_crude_usd_bbl', 'N/A')}/bbl"
                    )
            
            if 'natural_gas' in prices and prices['natural_gas']:
                with col2:
                    st.metric(
                        "Natural Gas",
                        f"${prices['natural_gas'].get('natural_gas_usd_mmbtu', 'N/A')}/MMBtu"
                    )
            
            if 'coal' in prices and prices['coal']:
                with col3:
                    st.metric(
                        "Coal",
                        f"${prices['coal'].get('coal_usd_per_ton', 'N/A')}/ton"
                    )
            
            st.info("✅ Data from commodity price websites (Web Scraping)")
        else:
            st.warning("Unable to fetch commodity prices")
    
    elif scrape_type == "Interconnections":
        st.markdown("#### Global Interconnections from Web Sources")
        
        with st.spinner("Scraping interconnection data..."):
            interconnections = InterconnectionScraper.get_global_interconnections()
        
        if interconnections:
            df = pd.DataFrame(interconnections)
            
            # Statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Interconnections", len(df))
            with col2:
                st.metric("Operating", len(df[df['status'] == 'operating']))
            with col3:
                st.metric("Total Capacity", f"{df['capacity_mw'].sum():,.0f} MW")
            with col4:
                st.metric("Regions", df['region'].nunique())
            
            st.dataframe(df, use_container_width=True)
            
            st.info("✅ Data from Global Energy Monitor & Web Sources (Web Scraping)")
    
    else:  # Regional News
        st.markdown("#### Regional Energy News from Web Sources")
        
        region = st.selectbox(
            "Select Region",
            ["Asia-Pacific", "Europe", "Americas", "Middle East & Africa"],
            key="news_region"
        )
        
        with st.spinner("Scraping regional news..."):
            news = EnergyNewsScraper.get_energy_news()
        
        if news:
            # Filter by region if needed
            for idx, article in enumerate(news[:15], 1):
                with st.container():
                    st.markdown(f"**{idx}. [{article['title']}]({article['link']})**")
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.caption(f"Source: {article.get('source', 'Unknown')} | {article['timestamp'].strftime('%Y-%m-%d')}")
                    with col2:
                        st.caption(f"Category: {article.get('category', 'General')}")
                st.divider()
            
            st.success("✅ Data from news websites (Web Scraping)")
        else:
            st.info("No regional news available")

# ==================== FOOTER ====================
st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.caption("**Primary Sources:** ENTSO-E · Electricity Maps · IEA · World Bank · UN COMTRADE")
with col2:
    st.caption("**Secondary Source:** Global Energy Monitor · Web Scraping")
with col3:
    st.caption(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")

st.markdown("""
    <div style='text-align: center; color: #999; font-size: 0.85rem; margin-top: 2rem;'>
    Energy MIS Dashboard v4.0 | Official APIs First with Web Scraping Fallback | 
    All data from verified sources
    </div>
""", unsafe_allow_html=True)
