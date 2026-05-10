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

# Custom CSS for high-end aesthetic
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #2d3139;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    div[data-testid="stExpander"] {
        border: none;
        background-color: #1e2130;
        border-radius: 8px;
    }
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        color: #e0e0e0;
    }
    .reportview-container .main .block-container {
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("SWING SCANNER TERMINAL")
st.caption("Statistical Optimization & Market Intelligence | Version 3.0")

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

# --- FOOTER GLOSSARY ---
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

        # --- TABULAR & ANALYTICAL INTERFACE ---
        tab1, tab2, tab3 = st.tabs(["Active Opportunities", "Risk Intelligence", "Macro & Events"])

        with tab1:
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

            top_10 = results_df.head(10)
            st.dataframe(format_opp_df(top_10), use_container_width=True, hide_index=True)
            
            if len(results_df) > 10:
                with st.expander("Secondary Opportunities"):
                    rest_df = results_df.iloc[10:]
                    st.dataframe(format_opp_df(rest_df), use_container_width=True, hide_index=True)
            
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Volatility Edge Analysis")
                fig_scatter = px.scatter(
                    results_df, x="vol_edge", y="total_score", size="open_interest", 
                    color="ticker", hover_name="ticker", template="plotly_dark"
                )
                fig_scatter.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_scatter, use_container_width=True)
            with c2:
                st.subheader("Capital Allocation (Kelly)")
                fig_kelly = px.bar(
                    top_10, x="ticker", y="kelly_pct", color="total_score", 
                    template="plotly_dark", color_continuous_scale="Viridis"
                )
                fig_kelly.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_kelly, use_container_width=True)

        with tab2:
            st.subheader("Risk Intelligence Matrix")
            r1, r2 = st.columns(2)
            
            with r1:
                st.subheader("Efficiency Frontier (Beta vs Reward)")
                fig_rr = px.scatter(
                    results_df, x="beta", y="prob_target", size="kelly_pct", 
                    color="ticker", template="plotly_dark"
                )
                fig_rr.add_vline(x=1.0, line_dash="dash", line_color="#4f4f4f")
                fig_rr.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_rr, use_container_width=True)
            
            with r2:
                st.subheader("Technical Health Heatmap")
                cols_needed = ['rsi', 'z_score', 'pcr', 'vol_edge']
                available_cols = [c for c in cols_needed if c in results_df.columns]
                
                if available_cols:
                    heatmap_df = results_df.groupby('ticker')[available_cols].first()
                    fig_hm = go.Figure(data=go.Heatmap(
                        z=heatmap_df.T.values, x=heatmap_df.index, y=heatmap_df.columns,
                        colorscale='RdYlGn', texttemplate="%{z:.2f}", hoverinfo="z"
                    ))
                    fig_hm.update_layout(template="plotly_dark", height=350, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_hm, use_container_width=True)
                else:
                    st.warning("Insufficient technical telemetry for matrix generation.")

        with tab3:
            st.subheader("Macro Sentiment & Calendar")
            e1, e2 = st.columns([1, 2])
            
            with e1:
                st.subheader("Macro Pulse (SPY)")
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number", value = spy_dist,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    gauge = {
                        'axis': {'range': [-5, 5], 'tickwidth': 1, 'tickcolor': "#4f4f4f"},
                        'bar': {'color': "#ffffff"},
                        'steps': [
                            {'range': [-5, -1.5], 'color': "#3d0a0a"},
                            {'range': [-1.5, 1.5], 'color': "#2d2d0a"},
                            {'range': [1.5, 5], 'color': "#0a2d0a"}
                        ],
                        'threshold': {'line': {'color': "#00ff00", 'width': 2}, 'thickness': 0.75, 'value': 0}
                    }
                ))
                fig_gauge.update_layout(template="plotly_dark", height=300, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_gauge, use_container_width=True)
                st.caption(f"Index Level: ${spy_price:.2f} | EMA-20 Baseline: ${spy_ema:.2f}")

            with e2:
                st.subheader("Corporate Events Timeline")
                def safe_days_to(date_obj):
                    if date_obj is None: return 99
                    try:
                        if isinstance(date_obj, str): dt = pd.to_datetime(date_obj).to_pydatetime()
                        elif hasattr(date_obj, 'to_pydatetime'): dt = date_obj.to_pydatetime()
                        else: dt = date_obj
                        return (dt.replace(tzinfo=None) - datetime.now()).days
                    except: return 99

                event_data = []
                for t in tickers:
                    if t in stock_metrics:
                        m = stock_metrics[t]
                        event_data.append({'ticker': t, 'type': 'Earnings', 'days': safe_days_to(m['earnings_date'])})
                        event_data.append({'ticker': t, 'type': 'Dividend', 'days': safe_days_to(m['ex_div_date'])})
                
                event_df = pd.DataFrame(event_data)
                event_df = event_df[event_df['days'] < 60]
                
                fig_timeline = px.bar(
                    event_df, x="ticker", y="days", color="type", barmode="group",
                    template="plotly_dark", color_discrete_map={'Earnings': '#1f77b4', 'Dividend': '#2ca02c'}
                )
                fig_timeline.add_hline(y=10, line_dash="dot", line_color="#ff7f0e")
                fig_timeline.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_timeline, use_container_width=True)

else:
    st.info("System Ready. Configure assets and duration in the terminal sidebar to initiate analysis.")
