import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from call_swing_scanner import run_scan_logic, get_historical_data, RISK_FREE_RATE

# Institutional Page Configuration
st.set_page_config(
    page_title="Terminal | Call Swing Scanner",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for high-end institutional aesthetic
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --bg-color: #0a0b10;
        --card-bg: rgba(30, 34, 45, 0.7);
        --border-color: rgba(255, 255, 255, 0.1);
        --accent-glow: rgba(0, 255, 128, 0.15);
        --text-main: #e0e0e0;
    }

    .main {
        background-color: var(--bg-color);
        color: var(--text-main);
        font-family: 'Inter', sans-serif;
    }

    /* Glassmorphism Containers */
    div[data-testid="stMetric"], .stDataFrame, div[data-testid="stExpander"], .stPlotlyChart {
        background: var(--card-bg) !important;
        backdrop-filter: blur(10px);
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: all 0.3s ease;
    }
    
    div[data-testid="stMetric"]:hover {
        border: 1px solid rgba(0, 255, 128, 0.3) !important;
        box-shadow: 0 0 20px var(--accent-glow);
    }

    /* Refined Typography */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 600 !important;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, #fff, #888);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .stCaption {
        font-family: 'JetBrains Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 0.75rem !important;
        color: #00ff80 !important;
        opacity: 0.8;
    }

    /* Institutional Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0e1015 !important;
        border-right: 1px solid var(--border-color);
    }

    /* Buttons */
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        transition: all 0.2s ease !important;
    }

    div.stButton > button:first-child {
        background-color: #00ff80;
        color: #000;
        border: none;
    }

    div.stButton > button:first-child:hover {
        background-color: #05ff85;
        box-shadow: 0 0 15px rgba(0, 255, 128, 0.4);
        transform: translateY(-1px);
    }

    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

st.title("SWING SCANNER TERMINAL")
st.caption("Statistical Optimization & Market Intelligence")

# --- NAVIGATION ---
st.sidebar.title("TERMINAL NAVIGATION")
view_mode = st.sidebar.radio("Go to:", ["Scanner Terminal", "Custom Simulator"], label_visibility="collapsed")

# --- SHARED FOOTER GLOSSARY ---
def draw_glossary():
    st.sidebar.divider()
    with st.sidebar.expander("Technical Glossary"):
        st.markdown("""
        **Total Score:** Weighted probability index (0.0 - 1.0).
        **P(Target):** MC simulation probability for +15% contract return.
        **Vol Edge:** Variance premium (Realized HV - Implied IV).
        **Max Pain:** Strike price where most options expire worthless.
        **Vol Skew:** IV difference between current strike and ATM.
        **Kelly %:** Optimal risk-adjusted capital allocation.
        **PCR:** Open Interest Put/Call sentiment balance.
        **Beta:** Systemic correlation coefficient to SPY.
        **Z-Score:** EMA-20 standard deviation distance.
        """)

# --- Caching Layer ---
@st.cache_data(ttl=900)
def get_cached_results(tickers_list, d_min, d_max, dl_min, dl_max):
    return run_scan_logic(tickers_list, d_min, d_max, dl_min, dl_max)

if view_mode == "Scanner Terminal":
    # --- SIDEBAR (Institutional Controls) ---
    st.sidebar.header("PARAMETER CONFIGURATION")

    tickers_input = st.sidebar.text_area("Asset Watchlist", value="SOFI, F, PFE, KHC, BAC, T, VZ, NU", help="Comma separated tickers")
    tickers = [t.strip().upper() for t in tickers_input.split(",")]

    st.sidebar.subheader("Execution Parameters")
    dte_min, dte_max = st.sidebar.slider("Duration (DTE)", 10, 120, (30, 50))
    delta_min, delta_max = st.sidebar.slider("Sensitivity (Delta)", 0.10, 0.95, (0.60, 0.80))

    run_button = st.sidebar.button("EXECUTE ANALYSIS", use_container_width=True, type="primary")
    force_refresh = st.sidebar.button("FORCE REFRESH (Clear Cache)", use_container_width=True)

    if force_refresh:
        st.cache_data.clear()
        st.info("Cache cleared. Please click 'EXECUTE ANALYSIS' to see updated metrics.")
    
    draw_glossary()

    if run_button:
        with st.spinner("Processing multi-path simulations and macro correlations..."):
            results_df, stock_metrics = get_cached_results(tuple(tickers), dte_min, dte_max, delta_min, delta_max)
            
            spy_hist = get_historical_data('SPY', period="1mo")
            spy_price = spy_hist['Close'].iloc[-1]
            spy_ema = spy_hist['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
            spy_dist = (spy_price / spy_ema - 1) * 100
        
        if results_df.empty:
            st.warning("No opportunities detected within current parameter constraints.")
        else:
            # --- EXECUTIVE METRICS ---
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Opportunities", len(results_df))
            col2.metric("Primary Ticker", results_df.iloc[0]['ticker'])
            col3.metric("Alpha Score", f"{results_df.iloc[0]['total_score']:.2f}")
            col4.metric("Max Allocation", f"{results_df['kelly_pct'].max():.1f}%")

            # --- CONSOLIDATED ANALYSIS INTERFACE ---
            st.subheader("Top Alpha Opportunities")
            
            def format_opp_df(df_to_format):
                f_df = df_to_format.copy()
                if 'strike' in f_df.columns: f_df['strike'] = f_df['strike'].map('${:,.1f}'.format)
                if 'last_price' in f_df.columns: f_df['last_price'] = f_df['last_price'].map('${:,.2f}'.format)
                if 'vol_edge' in f_df.columns: f_df['vol_edge'] = (f_df['vol_edge'] * 100).map('{:+.1f}%'.format)
                if 'vol_skew' in f_df.columns: f_df['vol_skew'] = (f_df['vol_skew'] * 100).map('{:+.1f}%'.format)
                if 'max_pain' in f_df.columns: f_df['max_pain'] = f_df['max_pain'].map('${:,.1f}'.format)
                if 'kelly_pct' in f_df.columns: f_df['kelly_pct'] = f_df['kelly_pct'].map('{:.1f}%'.format)
                if 'prob_target' in f_df.columns: f_df['prob_target'] = (f_df['prob_target'] * 100).map('{:.0f}%'.format)
                if 'total_score' in f_df.columns: f_df['total_score'] = f_df['total_score'].map('{:.2f}'.format)
                
                # Definir columnas de salida deseadas
                desired_cols = ['rank', 'ticker', 'expiration', 'dte', 'strike', 'last_price', 'max_pain', 'vol_skew', 'pcr', 'vol_edge', 'beta', 'kelly_pct', 'prob_target', 'total_score']
                available_output = [c for c in desired_cols if c in f_df.columns]
                return f_df[available_output]

            # Define column configuration for tooltips (Glossary)
            OPPORTUNITY_CONFIG = {
                "rank": st.column_config.NumberColumn("Rank", help="Opportunity ranking based on total score."),
                "ticker": st.column_config.TextColumn("Ticker", help="Stock ticker symbol."),
                "expiration": st.column_config.TextColumn("Expiration", help="Option contract expiration date."),
                "dte": st.column_config.NumberColumn("DTE", help="Days To Expiration."),
                "strike": st.column_config.TextColumn("Strike", help="Option strike price."),
                "last_price": st.column_config.TextColumn("Last Price", help="Last traded price of the option contract."),
                "max_pain": st.column_config.TextColumn("Max Pain", help="Strike price where the most options (puts and calls) expire worthless."),
                "vol_skew": st.column_config.TextColumn("Vol Skew", help="Implied Volatility difference between current strike and ATM."),
                "pcr": st.column_config.NumberColumn("PCR", help="Open Interest Put/Call sentiment balance."),
                "vol_edge": st.column_config.TextColumn("Vol Edge", help="Variance premium (Realized Historical Volatility - Implied Volatility)."),
                "beta": st.column_config.NumberColumn("Beta", help="Systemic correlation coefficient to SPY (Market sensitivity)."),
                "kelly_pct": st.column_config.TextColumn("Kelly %", help="Optimal risk-adjusted capital allocation percentage."),
                "prob_target": st.column_config.TextColumn("P(Target)", help="Monte Carlo simulation probability for +15% contract return."),
                "total_score": st.column_config.TextColumn("Total Score", help="Weighted probability index (0.0 - 1.0) for the opportunity.")
            }

            top_10 = results_df.head(10)
            st.dataframe(
                format_opp_df(top_10), 
                use_container_width=True, 
                hide_index=True,
                column_config=OPPORTUNITY_CONFIG
            )
            
            if len(results_df) > 10:
                with st.expander("Secondary Opportunities"):
                    rest_df = results_df.iloc[10:]
                    st.dataframe(
                        format_opp_df(rest_df), 
                        use_container_width=True, 
                        hide_index=True,
                        column_config=OPPORTUNITY_CONFIG
                    )
            
            st.divider()
            # --- Analytics Row 1 ---
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Alpha Score Ranking")
                fig_scores = px.bar(
                    top_10, x="ticker", y="total_score", 
                    color="total_score",
                    color_continuous_scale="RdYlGn",
                    range_color=[0.5, 0.9],
                    template="plotly_dark",
                    labels={"total_score": "Total Score", "ticker": "Asset"}
                )
                fig_scores.add_hline(y=0.80, line_dash="dash", line_color="#00ff00", annotation_text="80% Threshold")
                fig_scores.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False)
                st.plotly_chart(fig_scores, use_container_width=True)
            with c2:
                st.subheader("Capital Allocation (Kelly)")
                fig_kelly = px.bar(
                    top_10, x="ticker", y="kelly_pct", color="total_score", 
                    template="plotly_dark", color_continuous_scale="Viridis"
                )
                fig_kelly.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_kelly, use_container_width=True)

            # --- Analytics Row 2 ---
            st.subheader("Technical Health Matrix")
            cols_needed = ['rsi', 'z_score', 'pcr', 'vol_edge', 'beta']
            available_cols = [c for c in cols_needed if c in results_df.columns]
            
            if available_cols:
                heatmap_df = results_df.head(15).groupby('ticker')[available_cols].first()
                
                # Map metric names to descriptions for tooltips
                metric_desc = {
                    'rsi': 'Relative Strength Index (Momentum)',
                    'z_score': 'Std Dev Distance from EMA-20',
                    'pcr': 'Put/Call Ratio Sentiment',
                    'vol_edge': 'HV minus IV Premium',
                    'beta': 'Market Correlation (SPY)'
                }
                
                # Create hover text matrix
                hover_text = []
                for metric in heatmap_df.columns:
                    row_hover = []
                    desc = metric_desc.get(metric, 'Metric Value')
                    for ticker in heatmap_df.index:
                        val = heatmap_df.loc[ticker, metric]
                        row_hover.append(f"Ticker: {ticker}<br>Metric: {metric}<br>Definition: {desc}<br>Value: {val:.2f}")
                    hover_text.append(row_hover)

                fig_hm = go.Figure(data=go.Heatmap(
                    z=heatmap_df.T.values, 
                    x=heatmap_df.index, 
                    y=heatmap_df.columns,
                    colorscale='RdYlGn', 
                    texttemplate="%{z:.2f}", 
                    hoverinfo="text",
                    hovertext=hover_text
                ))
                fig_hm.update_layout(
                    template="plotly_dark", 
                    height=400, 
                    margin=dict(l=10, r=10, t=30, b=10), 
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_hm, use_container_width=True)
            else:
                st.warning("Insufficient technical telemetry for matrix generation.")

            # --- TICKER DEEP DIVE SECTION ---
            st.divider()
            st.header("🔬 TICKER INTELLIGENCE DEEP-DIVE")
            
            # Ticker selection (Defaults to highest score)
            top_tickers = results_df['ticker'].unique().tolist()
            
            @st.fragment
            def draw_deep_dive(tickers_list):
                selected_deep_dive = st.selectbox("Select Asset for Detailed Intelligence", options=tickers_list, index=0)

                if selected_deep_dive:
                    with st.spinner(f"Retrieving deep telemetry for {selected_deep_dive}..."):
                        deep_hist = get_historical_data(selected_deep_dive, period="6mo")
                        if deep_hist is not None:
                            # 1. Price & Trend Chart
                            deep_hist['EMA_20'] = deep_hist['Close'].ewm(span=20, adjust=False).mean()
                            fig_price = go.Figure()
                            fig_price.add_trace(go.Scatter(x=deep_hist['Date'], y=deep_hist['Close'], name='Spot Price', line=dict(color='#ffffff', width=2)))
                            fig_price.add_trace(go.Scatter(x=deep_hist['Date'], y=deep_hist['EMA_20'], name='EMA-20 (Trend)', line=dict(color='#00ff80', width=1, dash='dash')))
                            fig_price.update_layout(
                                title=f"{selected_deep_dive} | Price Action & Structural Trend", 
                                template="plotly_dark", 
                                paper_bgcolor='rgba(0,0,0,0)', 
                                plot_bgcolor='rgba(0,0,0,0)', 
                                height=400,
                                showlegend=True,
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                            )
                            st.plotly_chart(fig_price, use_container_width=True)

                            # 2. Volatility Pulse
                            deep_hist['Returns'] = np.log(deep_hist['Close'] / deep_hist['Close'].shift(1))
                            deep_hist['HV_20'] = deep_hist['Returns'].rolling(window=20).std() * np.sqrt(252)
                            
                            fig_vol = px.line(deep_hist, x='Date', y='HV_20', title=f"{selected_deep_dive} | Realized Volatility Pulse (20D)", template="plotly_dark")
                            fig_vol.update_traces(line_color='#ff7f0e', name="HV 20D")
                            fig_vol.update_layout(
                                paper_bgcolor='rgba(0,0,0,0)', 
                                plot_bgcolor='rgba(0,0,0,0)', 
                                height=300,
                                showlegend=True
                            )
                            st.plotly_chart(fig_vol, use_container_width=True)
                        else:
                            st.error("Failed to retrieve historical data for deep-dive.")

            draw_deep_dive(top_tickers)

    else:
        st.info("System Ready. Configure assets and duration in the terminal sidebar to initiate analysis.")

elif view_mode == "Custom Simulator":
    st.header("🎯 CUSTOM PROBABILITY SIMULATOR")
    st.markdown("Run high-fidelity Monte Carlo simulations for specific contracts to evaluate feasibility.")
    
    col_in1, col_in2, col_in3, col_in4 = st.columns(4)
    with col_in1: calc_ticker = st.text_input("Asset Ticker", value="SOFI").upper()
    with col_in2: calc_dte = st.number_input("Days to Expiry (DTE)", value=30, min_value=1)
    with col_in3: calc_strike = st.number_input("Strike Price", value=10.0, step=0.5)
    with col_in4: calc_target = st.number_input("Price Target (Optional)", value=0.0, step=0.5, help="Set to 0 for +15% gain default")
    
    run_calc = st.button("RUN SIMULATION", use_container_width=True, type="primary")
    
    draw_glossary()

    if run_calc:
        from call_swing_scanner import monte_carlo_probabilities, estimate_delta, estimate_jump_parameters
        import yfinance as yf
        
        with st.spinner(f"Running high-fidelity simulation for {calc_ticker}..."):
            try:
                # 1. Fetch current telemetry
                hist = get_historical_data(calc_ticker, period="6mo") # Usamos 6 meses para mejores parámetros de saltos
                if hist is not None and not hist.empty:
                    s_price = hist['Close'].iloc[-1]
                    
                    # Estimate Dynamic Jump Parameters
                    j_lambda, j_mu, j_sigma = estimate_jump_parameters(hist)
                    
                    # Annualized Volatility (20-day)
                    returns = np.log(hist['Close'] / hist['Close'].shift(1))
                    sigma = returns.tail(20).std() * np.sqrt(252)
                    T = calc_dte / 252.0
                    
                    # 2. Determine Target
                    if calc_target <= 0:
                        delta_est = estimate_delta(s_price, calc_strike, T, RISK_FREE_RATE, sigma)
                        needed_gain = 0.15 * (s_price * 0.05) 
                        final_target = s_price + (needed_gain / max(delta_est, 0.1))
                    else:
                        final_target = calc_target

                    # 3. Run Simulation (Increased to 50,000 sims for high precision)
                    prob_strike, prob_target, paths = monte_carlo_probabilities(
                        s_price, calc_strike, final_target, T, RISK_FREE_RATE, sigma, 
                        num_sims=50000, return_paths=True,
                        j_lambda=j_lambda, j_mu=j_mu, j_sigma=j_sigma
                    )
                    
                    st.divider()
                    # 4. Display Results
                    res1, res2, res3 = st.columns(3)
                    
                    epv_score = prob_target * (final_target / s_price)
                    dist_to_target = (final_target / s_price) - 1
                    theta_risk = dist_to_target / (calc_dte / 30.0)
                    
                    res1.metric("Prob. of Touch", f"{prob_strike*100:.2f}%")
                    res2.metric("Prob. of Target", f"{prob_target*100:.2f}%")
                    res3.metric("Expected Value (EPV)", f"{epv_score:.3f}")

                    st.markdown(f"""
                    <div style="background: rgba(0, 255, 128, 0.05); border: 1px solid rgba(0, 255, 128, 0.2); border-radius: 10px; padding: 15px; margin: 10px 0;">
                        <span style="color: #00ff80; font-weight: 600;">📊 STATISTICAL PRECISION:</span><br>
                        <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; color: #e0e0e0;">
                            Merton Jump-Diffusion (N=50,000) with Antithetic Variates.<br>
                            Dynamic Jump Params: λ={j_lambda:.1f}, μ={j_mu:.2f}, σ={j_sigma:.2f}.<br>
                            Target Price: <b>${final_target:.2f}</b> | Time Decay Risk: <b>{ 'HIGH' if theta_risk > 0.1 else 'MODERATE' if theta_risk > 0.05 else 'LOW' }</b>
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Distribution Plot
                    final_prices = paths[:, -1]
                    fig_dist = px.histogram(
                        final_prices, nbins=70, 
                        title=f"Price Distribution at Expiry: {calc_ticker}",
                        labels={'value': 'Stock Price'},
                        template="plotly_dark",
                        color_discrete_sequence=['#1f77b4']
                    )
                    fig_dist.add_vline(x=s_price, line_dash="dot", line_color="white", annotation_text="Spot")
                    fig_dist.add_vline(x=calc_strike, line_dash="dash", line_color="orange", annotation_text="Strike")
                    fig_dist.add_vline(x=final_target, line_dash="dash", line_color="#00ff00", annotation_text="Target")
                    fig_dist.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_dist, use_container_width=True)
                else:
                    st.error(f"Error: Could not retrieve data for {calc_ticker}. Check ticker symbol.")
            except Exception as e:
                st.error(f"Simulation Error: {str(e)}")
