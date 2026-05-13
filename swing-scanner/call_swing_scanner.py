#!/usr/bin/env python3
"""
CALL SWING SCANNER 15% v3.0
============================
Mini app para escanear oportunidades de compra de calls.
Objetivo: +15% en el contrato, DTE 30-50 días, Delta > 0.55, IV < P35.

Dependencias:
    pip install yfinance pandas numpy scipy matplotlib

Uso:
    python call_swing_scanner.py

Configuración: edita la sección CONFIG al inicio del script.
"""

import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
import json
import os
import sys

# ============================================
# CONFIGURACIÓN — Edita aquí tus parámetros
# ============================================

TICKERS = ['SOFI', 'F', 'PFE', 'KHC', 'BAC', 'T', 'VZ', 'NU']
TARGET_GAIN_PCT = 0.15      # Objetivo: +15% en contrato
DTE_MIN = 30                # Días mínimos a expiración
DTE_MAX = 50                # Días máximos a expiración
DELTA_MIN = 0.60            # Delta mínimo (ATM/ITM)
DELTA_MAX = 0.80
MIN_OI = 50                 # Open Interest mínimo
MIN_VOLUME = 10             # Volumen mínimo
MAX_IV_PERCENTILE = 0.35    # IV Percentile máximo
RISK_FREE_RATE = 0.045      # Tasa libre de riesgo
OUTPUT_DIR = './scanner_output'  # Directorio de salida

# Filtros de Eventos Corporativos
EARNINGS_DAYS_FILTER = 10   # Días mínimos hasta earnings
DIVIDEND_DAYS_FILTER = 5    # Días buffer para ex-dividend

# Ponderaciones del Score (deben sumar 1.0)
SCORE_WEIGHTS = {
    'mc_prob_target': 0.28,   # Prob. de alcanzar precio para +15% (Monte Carlo)
    'mc_prob_strike': 0.08,   # Prob. de tocar el Strike (Monte Carlo)
    'vol_edge': 0.15,         # Ventaja IV vs HV
    'macro_beta': 0.10,       # Filtro Macro (SPY + Beta)
    'pcr_sentiment': 0.08,
    'zscore_ema': 0.08,
    'momentum_rsi': 0.08,
    'liquidity': 0.05,
    'max_pain': 0.05,         # Proximidad a Max Pain
    'vol_skew': 0.05,         # Skew relativo (Strike vs ATM)
}

# Parámetros Jump-Diffusion (Merton)
JUMP_LAMBDA = 10.0          # Saltos esperados por año
JUMP_MU = -0.01             # Media del salto (un poco sesgado a la baja)
JUMP_SIGMA = 0.05           # Desviación estándar del salto

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def estimate_jump_parameters(hist_df):
    """
    Analiza gaps históricos para parametrizar el modelo de Merton.
    Busca retornos que excedan 2 desviaciones estándar.
    """
    try:
        returns = np.log(hist_df['Close'] / hist_df['Close'].shift(1)).dropna()
        mu_ret = returns.mean()
        std_ret = returns.std()
        
        # Definimos "salto" como cualquier movimiento > 2 sigma
        jumps = returns[np.abs(returns - mu_ret) > 2 * std_ret]
        
        if len(jumps) > 0:
            # Lambda: Frecuencia de saltos anualizada
            # (Num saltos / Num días totales) * 252
            lambda_est = (len(jumps) / len(returns)) * 252
            mu_j = jumps.mean()
            sigma_j = jumps.std() if len(jumps) > 1 else 0.05
        else:
            lambda_est = 5.0  # Default conservador
            mu_j = 0.0
            sigma_j = 0.05
            
        return lambda_est, mu_j, sigma_j
    except:
        return 10.0, -0.01, 0.05

def ensure_output_dir():
    """Crear directorio de salida si no existe."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def estimate_delta(S, K, T, r, sigma):
    """Cálculo simple de Delta (Black-Scholes) para estimaciones de movimiento."""
    if T <= 0 or sigma <= 0:
        return 1.0 if S > K else 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return stats.norm.cdf(d1)

def monte_carlo_probabilities(S, K, target_price, T, r, sigma, num_sims=5000, return_paths=False, j_lambda=None, j_mu=None, j_sigma=None):
    """
    Simulación Monte Carlo optimizada con Jump-Diffusion y Antithetic Variates.
    """
    np.random.seed(42)
    
    # Usar parámetros dinámicos si se proveen, si no usar constantes globales
    L = j_lambda if j_lambda is not None else JUMP_LAMBDA
    MJ = j_mu if j_mu is not None else JUMP_MU
    SJ = j_sigma if j_sigma is not None else JUMP_SIGMA

    if T <= 0:
        if return_paths:
            return (1.0 if S >= K else 0.0), (1.0 if S >= target_price else 0.0), np.array([[S]])
        return (1.0 if S >= K else 0.0), (1.0 if S >= target_price else 0.0)

    trading_days = max(1, int(T * 252))
    dt = T / trading_days
    
    # Reducir varianza: Antithetic Variates (usamos la mitad de sims y sus espejos)
    n_half = num_sims // 2
    
    drift = (r - 0.5 * sigma**2 - L * (np.exp(MJ + 0.5 * SJ**2) - 1)) * dt
    
    # Inicializar caminos (Original + Antithetic)
    paths = np.zeros((num_sims, trading_days + 1))
    paths[:, 0] = S
    
    for t in range(1, trading_days + 1):
        # Componente normal con Antithetic Variates
        Z_half = np.random.standard_normal(n_half)
        Z = np.concatenate([Z_half, -Z_half])
        
        # Componente de Saltos
        N = np.random.poisson(L * dt, num_sims)
        J = np.zeros(num_sims)
        # Vectorizar saltos: solo iteramos sobre sims que tuvieron saltos (eficiencia)
        jump_indices = np.where(N > 0)[0]
        for idx in jump_indices:
            J[idx] = np.sum(np.random.normal(MJ, SJ, N[idx]))
        
        paths[:, t] = paths[:, t-1] * np.exp(drift + sigma * np.sqrt(dt) * Z + J)
    
    touched_strike = np.any(paths >= K, axis=1)
    touched_target = np.any(paths >= target_price, axis=1)
    
    p_strike, p_target = np.mean(touched_strike), np.mean(touched_target)
    
    if return_paths:
        return p_strike, p_target, paths
    return p_strike, p_target

def prob_stock_reaches(S0, target, T, sigma):
    """Probabilidad de que el stock toque 'target' en tiempo T (ever-touch aprox)."""
    if target <= S0:
        return 1.0
    z = (np.log(target / S0) - (-0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    p_close = 1 - norm_cdf(z)
    return min(2 * p_close, 1.0)

def get_corporate_events(ticker):
    """Obtener próximas fechas de earnings y dividendos."""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        
        # Earnings
        earnings_date = None
        if stock.calendar is not None and 'Earnings Date' in stock.calendar:
            dates = stock.calendar['Earnings Date']
            if isinstance(dates, list) and len(dates) > 0:
                earnings_date = dates[0]
        
        # Dividends
        ex_div_date = None
        if stock.info is not None and 'exDividendDate' in stock.info:
            ex_div_timestamp = stock.info['exDividendDate']
            if ex_div_timestamp:
                ex_div_date = datetime.fromtimestamp(ex_div_timestamp)
        
        return earnings_date, ex_div_date
    except Exception:
        return None, None

def calc_stock_metrics(ticker, hist_df, spy_df=None):
    """Calcular métricas históricas de un ticker y Beta vs SPY."""
    df = hist_df.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    df['Return'] = df['Close'].pct_change()

    current_price = df['Close'].iloc[-1]

    # Beta vs SPY
    beta = 1.0
    spy_trend = 1.0 # Multiplicador de salud macro
    if spy_df is not None:
        spy = spy_df.copy()
        spy['Date'] = pd.to_datetime(spy['Date'])
        spy = spy.sort_values('Date').reset_index(drop=True)
        spy['Return'] = spy['Close'].pct_change()
        
        # Merge returns para alinear fechas
        merged = pd.merge(df[['Date', 'Return']], spy[['Date', 'Return']], on='Date', suffixes=('_stock', '_spy')).dropna()
        if len(merged) > 20:
            cov = merged['Return_stock'].cov(merged['Return_spy'])
            var = merged['Return_spy'].var()
            beta = cov / var if var > 0 else 1.0
            
        # SPY Trend (distancia a EMA 20)
        spy['EMA_20'] = spy['Close'].ewm(span=20, adjust=False).mean()
        spy_current = spy['Close'].iloc[-1]
        spy_ema = spy['EMA_20'].iloc[-1]
        spy_trend = 1.2 if spy_current > spy_ema else 0.7 # Bonus si SPY está alcista

    # Volatilidades
    vol_20d = df['Return'].dropna().tail(20).std() * np.sqrt(252)
    vol_60d = df['Return'].dropna().tail(60).std() * np.sqrt(252)

    # Z-Score vs EMA 20 (Refined for responsiveness)
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['STD_20'] = df['Close'].rolling(window=20).std()
    
    current_ema = df['EMA_20'].iloc[-1]
    current_std = df['STD_20'].iloc[-1]
    z_score = (current_price - current_ema) / current_std if current_std > 0 else 0

    # RSI 14
    delta_close = df['Close'].diff()
    gain = delta_close.where(delta_close > 0, 0)
    loss = (-delta_close).where(delta_close < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # Momentum
    mom_5d = (current_price / df['Close'].iloc[-5] - 1) * 100
    mom_20d = (current_price / df['Close'].iloc[-20] - 1) * 100

    # Corporate Events
    earnings_date, ex_div_date = get_corporate_events(ticker)

    return {
        'ticker': ticker,
        'current_price': current_price,
        'ema_20': current_ema,
        'z_score_20': z_score,
        'vol_20d': vol_20d,
        'vol_60d': vol_60d,
        'rsi': rsi.iloc[-1],
        'momentum_5d': mom_5d,
        'momentum_20d': mom_20d,
        'earnings_date': earnings_date,
        'ex_div_date': ex_div_date,
        'beta': beta,
        'spy_trend_score': spy_trend
    }

def get_historical_data(ticker, period="3mo"):
    """Obtener datos históricos usando yfinance con User-Agent custom."""
    try:
        import yfinance as yf
        # Use a session with a custom user-agent to avoid being blocked
        import requests
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        
        stock = yf.Ticker(ticker, session=session)
        hist = stock.history(period=period)
        hist = hist.reset_index()
        hist.columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'] + list(hist.columns[6:])
        return hist
    except ImportError:
        print(f"ERROR: yfinance no está instalado. Ejecuta: pip install yfinance")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR obteniendo datos de {ticker}: {e}")
        return None

def get_option_chain(ticker, expiration_date):
    """Obtener chain de opciones para una fecha de expiración."""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        chain = stock.option_chain(expiration_date)
        calls = chain.calls.copy()
        puts = chain.puts.copy()
        return calls, puts
    except Exception as e:
        print(f"ERROR obteniendo options para {ticker} {expiration_date}: {e}")
        return None, None

def get_option_expirations(ticker):
    """Obtener fechas de expiración disponibles."""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        return stock.options
    except Exception as e:
        print(f"ERROR obteniendo expiraciones para {ticker}: {e}")
        return []

def filter_expirations(expirations, dte_min=DTE_MIN, dte_max=DTE_MAX):
    """Filtrar expiraciones en rango DTE."""
    today = datetime.now()
    valid = []
    for exp_str in expirations:
        exp_date = datetime.strptime(exp_str, '%Y-%m-%d')
        dte = (exp_date - today).days
        if dte_min <= dte <= dte_max:
            valid.append((exp_str, dte))
    return valid

def calc_iv_threshold(ticker, all_calls_data):
    """Calcular P35 de IV para un ticker."""
    all_ivs = []
    for calls in all_calls_data:
        ivs = calls['impliedVolatility'].dropna()
        ivs = ivs[ivs < 2.0]
        all_ivs.extend(ivs.tolist())

    if len(all_ivs) > 0:
        return np.percentile(all_ivs, 35)
    return 0.50

def calculate_max_pain(calls, puts):
    """Calcular el strike de Max Pain para una chain de opciones."""
    try:
        # Combinar strikes únicos
        all_strikes = sorted(list(set(calls['strike'].tolist() + puts['strike'].tolist())))
        
        # Pre-filtrar datos con Open Interest válido
        c = calls[calls['openInterest'] > 0].copy()
        p = puts[puts['openInterest'] > 0].copy()
        
        pain_results = []
        for s_exp in all_strikes:
            # Valor total intrínseco que los compradores perderían (o vendedores ahorrarían)
            call_payout = (c[c['strike'] < s_exp]['openInterest'] * (s_exp - c['strike'])).sum()
            put_payout = (p[p['strike'] > s_exp]['openInterest'] * (p['strike'] - s_exp)).sum()
            pain_results.append(call_payout + put_payout)
            
        return all_strikes[np.argmin(pain_results)]
    except:
        return None

def score_opportunity(row, stock_metrics, dte, iv_threshold, pcr_value, max_pain=None, atm_iv=None):
    """Calcular score avanzado con Jump-Diffusion, Vol Edge, Macro, Kelly, Max Pain y Skew."""
    S = stock_metrics['current_price']
    K = row['strike']
    sigma = stock_metrics['vol_20d']
    T = dte / 365

    contract_price = row['lastPrice']
    iv = row['impliedVolatility']
    oi = row['openInterest'] if pd.notna(row['openInterest']) else 0
    vol = row['volume'] if pd.notna(row['volume']) else 0

    if contract_price <= 0.05 or oi < MIN_OI or vol < MIN_VOLUME or iv >= iv_threshold:
        return None

    delta = estimate_delta(S, K, T, RISK_FREE_RATE, sigma)
    if not (DELTA_MIN <= delta <= DELTA_MAX):
        return None

    # Target para +15%
    target_contract = contract_price * (1 + TARGET_GAIN_PCT)
    stock_move_needed = (target_contract - contract_price) / delta
    target_stock = S + stock_move_needed
    pct_move_needed = (target_stock / S - 1) * 100

    # 1. MONTE CARLO (Jump-Diffusion)
    prob_strike, prob_target = monte_carlo_probabilities(S, K, target_stock, T, RISK_FREE_RATE, sigma)

    # 2. VOLATILITY EDGE (IV vs HV)
    vol_edge = sigma - iv
    vol_edge_score = min(1.0, max(0, 0.5 + vol_edge * 2))

    # 3. MACRO & BETA
    beta = stock_metrics['beta']
    spy_trend = stock_metrics['spy_trend_score']
    beta_score = min(1.0, 1.0 / abs(beta - 1.2)) if beta != 1.2 else 1.0
    macro_score = beta_score * spy_trend
    macro_score = min(1.0, macro_score)

    # 4. KELLY CRITERION
    W = prob_target
    B = 0.3
    kelly_f = W - ((1 - W) / B) if W > 0 else 0
    kelly_pct = max(0, kelly_f * 0.25) * 100

    # 5. MAX PAIN & SKEW (Nuevos)
    # Score Max Pain: Premiamos si Max Pain está por encima del precio actual (imán alcista)
    max_pain_score = 0.5
    if max_pain:
        dist_to_pain = (max_pain / S - 1) * 100
        max_pain_score = min(1.0, max(0, 0.5 + dist_to_pain / 10)) # +5% dist = Score 1.0
        
    # Score Skew: Premiamos si la IV de nuestro strike es menor que la ATM (opción "barata" relativa)
    skew_score = 0.5
    vol_skew_val = 0
    if atm_iv and atm_iv > 0:
        vol_skew_val = iv - atm_iv
        skew_score = min(1.0, max(0, 0.5 - vol_skew_val * 2))

    # 6. OTROS FACTORES
    pcr_score = max(0, 1.0 - abs(pcr_value - 1.0) / 0.5)
    z_score = stock_metrics['z_score_20']
    zscore_ema_score = max(0, 1.0 - abs(z_score - (-0.75)) / 2.0)
    rsi = stock_metrics['rsi']
    rsi_score = max(0, 1.0 - abs(rsi - 45) / 35)
    momentum_score = 0.6 * rsi_score + 0.4 * max(0, min(1, 0.5 + (stock_metrics['momentum_5d'] / 15) * 0.5))
    liq_score = min(1.0, (oi / 500) * 0.5 + (vol / 100) * 0.5)

    # SCORE TOTAL
    total_score = (
        prob_target * SCORE_WEIGHTS['mc_prob_target'] +
        prob_strike * SCORE_WEIGHTS['mc_prob_strike'] +
        vol_edge_score * SCORE_WEIGHTS['vol_edge'] +
        macro_score * SCORE_WEIGHTS['macro_beta'] +
        pcr_score * SCORE_WEIGHTS['pcr_sentiment'] +
        zscore_ema_score * SCORE_WEIGHTS['zscore_ema'] +
        momentum_score * SCORE_WEIGHTS['momentum_rsi'] +
        liq_score * SCORE_WEIGHTS['liquidity'] +
        max_pain_score * SCORE_WEIGHTS['max_pain'] +
        skew_score * SCORE_WEIGHTS['vol_skew']
    )

    return {
        'dte': dte,
        'strike': K,
        'last_price': contract_price,
        'pcr': pcr_value,
        'vol_edge': vol_edge,
        'beta': beta,
        'kelly_pct': kelly_pct,
        'max_pain': max_pain,
        'vol_skew': vol_skew_val,
        'prob_strike': prob_strike,
        'prob_target': prob_target,
        'open_interest': oi,
        'volume': vol,
        'total_score': total_score,
        'expected_move_pct': iv * np.sqrt(T) * 100,
        'z_score': z_score,
        'rsi': rsi
    }

def run_scan_logic(tickers_list, dte_min, dte_max, delta_min, delta_max):
    """Ejecutar la lógica central del scanner y retornar resultados."""
    ensure_output_dir()
    
    # 1. Obtener datos históricos y Macro SPY en BATCH (mucho más rápido)
    import yfinance as yf
    import requests
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    
    all_tickers = tickers_list + ['SPY']
    # yf.download es más eficiente para múltiples tickers
    data = yf.download(all_tickers, period="6mo", session=session, group_by='ticker', progress=False)
    
    spy_df = data['SPY'].reset_index()
    
    stock_metrics = {}
    for ticker in tickers_list:
        if ticker in data and not data[ticker].empty:
            hist = data[ticker].reset_index()
            # Incluir últimos 60 días de precios para el gráfico del frontend
            history_data = hist.tail(60).apply(lambda row: {
                'date': row['Date'].strftime('%Y-%m-%d'),
                'price': float(row['Close'])
            }, axis=1).tolist()
            
            metrics = calc_stock_metrics(ticker, hist, spy_df)
            metrics['history'] = history_data
            stock_metrics[ticker] = metrics
    
    # 2. Obtener expiraciones y chains (esto sigue siendo secuencial por ticker)
    all_opportunities = []

    for ticker in tickers_list:
        if ticker not in stock_metrics:
            continue

        # Filtros de Eventos Corporativos
        next_earnings = stock_metrics[ticker]['earnings_date']
        if next_earnings:
            if hasattr(next_earnings, 'timestamp'):
                days_to_earnings = (next_earnings.replace(tzinfo=None) - datetime.now()).days
            else:
                days_to_earnings = 999
            if 0 <= days_to_earnings <= EARNINGS_DAYS_FILTER:
                continue

        next_div = stock_metrics[ticker]['ex_div_date']
        if next_div:
            days_to_div = (next_div.replace(tzinfo=None) - datetime.now()).days
            if 0 <= days_to_div <= DIVIDEND_DAYS_FILTER:
                continue

        expirations = get_option_expirations(ticker)
        valid_exps = []
        today = datetime.now()
        for exp_str in expirations:
            exp_date = datetime.strptime(exp_str, '%Y-%m-%d')
            dte = (exp_date - today).days
            if dte_min <= dte <= dte_max:
                valid_exps.append((exp_str, dte))

        if not valid_exps:
            continue

        # Calcular IV threshold y PCR
        all_calls_for_iv = []
        for exp_date, dte in valid_exps:
            calls, _ = get_option_chain(ticker, exp_date)
            if calls is not None:
                all_calls_for_iv.append(calls)

        iv_threshold = calc_iv_threshold(ticker, all_calls_for_iv)

        # Escanear cada expiración
        for exp_date, dte in valid_exps:
            calls, puts = get_option_chain(ticker, exp_date)
            if calls is None or puts is None:
                continue
            
            # Métricas de Expiración
            call_oi = calls['openInterest'].sum()
            put_oi = puts['openInterest'].sum()
            pcr_value = put_oi / call_oi if call_oi > 0 else 1.0
            
            max_pain = calculate_max_pain(calls, puts)
            
            # ATM IV (Call más cercana al precio actual)
            S_current = stock_metrics[ticker]['current_price']
            calls['dist_atm'] = abs(calls['strike'] - S_current)
            atm_row = calls.sort_values('dist_atm').iloc[0]
            atm_iv = atm_row['impliedVolatility']

            for _, row in calls.iterrows():
                # Temporalmente sobrescribir deltas globales para esta llamada
                global DELTA_MIN, DELTA_MAX
                orig_min, orig_max = DELTA_MIN, DELTA_MAX
                DELTA_MIN, DELTA_MAX = delta_min, delta_max
                
                result = score_opportunity(row, stock_metrics[ticker], dte, iv_threshold, pcr_value, max_pain, atm_iv)
                
                DELTA_MIN, DELTA_MAX = orig_min, orig_max
                
                if result is not None:
                    result['ticker'] = ticker
                    result['expiration'] = exp_date
                    all_opportunities.append(result)

    if not all_opportunities:
        return pd.DataFrame(), stock_metrics

    opps_df = pd.DataFrame(all_opportunities)
    opps_df = opps_df.sort_values('total_score', ascending=False).reset_index(drop=True)
    opps_df['rank'] = range(1, len(opps_df) + 1)
    
    return opps_df, stock_metrics

def run_scanner():
    """Ejecutar el scanner completo (CLI)."""
    ensure_output_dir()
    
    print("="*70)
    print("CALL SWING SCANNER 15% v3.0")
    print("="*70)
    print(f"Tickers: {', '.join(TICKERS)}")
    print(f"Objetivo: +{TARGET_GAIN_PCT*100:.0f}% en contrato")
    print(f"DTE: {DTE_MIN}-{DTE_MAX} días | Delta: >{DELTA_MIN}")
    print(f"IV Percentile: < P35 por ticker")
    print("="*70)

    opps_df, stock_metrics = run_scan_logic(TICKERS, DTE_MIN, DTE_MAX, DELTA_MIN, DELTA_MAX)

    if opps_df.empty:
        print("  No se encontraron oportunidades con los criterios actuales.")
        return

    # Mostrar TOP 10
    print("\n" + "="*145)
    print("TOP 10 OPORTUNIDADES (INSTITUCIONAL: JUMP-DIFFUSION + VOL EDGE + MACRO + KELLY)")
    print("="*145)

    display_cols = ['rank', 'ticker', 'expiration', 'dte', 'strike', 'last_price', 'pcr', 
                    'vol_edge', 'beta', 'kelly_pct', 'prob_target', 'total_score']

    display_df = opps_df[display_cols].head(10).copy()
    display_df['strike'] = display_df['strike'].apply(lambda x: f"${x:.1f}")
    display_df['last_price'] = display_df['last_price'].apply(lambda x: f"${x:.2f}")
    display_df['pcr'] = display_df['pcr'].apply(lambda x: f"{x:.2f}")
    display_df['vol_edge'] = display_df['vol_edge'].apply(lambda x: f"{x:+.1%}")
    display_df['beta'] = display_df['beta'].apply(lambda x: f"{x:.2f}")
    display_df['kelly_pct'] = display_df['kelly_pct'].apply(lambda x: f"{x:.1f}%")
    display_df['prob_target'] = display_df['prob_target'].apply(lambda x: f"{x:.0%}")
    display_df['total_score'] = display_df['total_score'].apply(lambda x: f"{x:.2f}")

    print(display_df.to_string(index=False))

    # 4. Guardar resultados
    if os.environ.get('VERCEL'):
        print("\n[4/4] Vercel detectado: Saltando guardado de archivos.")
        return

    print("\n[4/4] Guardando resultados...")
    
    # CSV
    csv_path = os.path.join(OUTPUT_DIR, 'scanner_results.csv')
    try:
        opps_df.to_csv(csv_path, index=False)
        print(f"  CSV: {csv_path}")
    except PermissionError:
        print(f"  ERROR: No se pudo guardar el CSV (Permiso denegado). Cierra el archivo si está abierto.")

    # Gráfico
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    colors_map = {
        'SOFI': '#e74c3c', 'F': '#3498db', 'PFE': '#2ecc71', 'KHC': '#f39c12',
        'BAC': '#9b59b6', 'T': '#1abc9c', 'VZ': '#e67e22', 'NU': '#8e44ad'
    }

    # Score vs Expected Move
    ax1 = axes[0, 0]
    for ticker in TICKERS:
        mask = opps_df['ticker'] == ticker
        subset = opps_df[mask]
        if len(subset) > 0:
            ax1.scatter(subset['expected_move_pct'], subset['total_score'], 
                        s=subset['open_interest']/100, c=colors_map.get(ticker, 'gray'), 
                        alpha=0.7, edgecolors='black', linewidth=0.5, label=ticker)
    ax1.axhline(y=0.70, color='gray', linestyle='--', alpha=0.5)
    ax1.set_xlabel('Expected Move (%)')
    ax1.set_ylabel('Score Total')
    ax1.set_title('Score vs Expected Move')
    ax1.legend(loc='lower right', fontsize=8, ncol=2)
    ax1.grid(True, alpha=0.3)

    # Score por ticker
    ax2 = axes[0, 1]
    ticker_scores = opps_df.groupby('ticker')['total_score'].max().sort_values(ascending=True)
    bars = ax2.barh(ticker_scores.index, ticker_scores.values, 
                    color=[colors_map.get(t, 'gray') for t in ticker_scores.index], 
                    edgecolor='black', alpha=0.85)
    ax2.set_xlabel('Mejor Score')
    ax2.set_title('Mejor Oportunidad por Ticker')
    ax2.axvline(x=0.70, color='gray', linestyle='--', alpha=0.5)
    for bar, score in zip(bars, ticker_scores.values):
        ax2.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2, 
                 f'{score:.2f}', va='center', fontsize=10, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='x')

    # Z-Score vs Score
    ax3 = axes[1, 0]
    for ticker in TICKERS:
        mask = opps_df['ticker'] == ticker
        subset = opps_df[mask]
        if len(subset) > 0:
            ax3.scatter(subset['z_score'], subset['total_score'], 
                        s=100, c=colors_map.get(ticker, 'gray'), alpha=0.7, 
                        edgecolors='black', label=ticker)
    ax3.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax3.axhline(y=0.70, color='gray', linestyle='--', alpha=0.5)
    ax3.set_xlabel('Z-Score')
    ax3.set_ylabel('Score Total')
    ax3.set_title('Z-Score vs Score')
    ax3.legend(loc='lower left', fontsize=8, ncol=2)
    ax3.grid(True, alpha=0.3)

    # Tabla TOP 10
    ax4 = axes[1, 1]
    ax4.axis('off')

    table_data = []
    for i in range(min(10, len(opps_df))):
        row = opps_df.iloc[i]
        table_data.append([
            f"#{i+1}", row['ticker'], f"${row['strike']:.1f}", f"${row['last_price']:.2f}",
            f"{row['vol_edge']:+.1%}", f"{row['kelly_pct']:.1f}%", f"{row['prob_target']:.0%}", f"{row['total_score']:.2f}"
        ])

    table = ax4.table(cellText=table_data,
                      colLabels=['Rank', 'Ticker', 'Strike', 'Price', 'Vol Edge', 'Kelly %', 'P(Target)', 'Score'],
                      cellLoc='center', loc='center', colColours=['#2c3e50']*8)
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.8)

    for i in range(len(table_data)):
        ticker = table_data[i][1]
        for j in range(8):
            table[(i+1, j)].set_facecolor(colors_map.get(ticker, 'white'))
            table[(i+1, j)].set_alpha(0.12)

    ax4.set_title('TOP 10 Oportunidades', fontsize=12, fontweight='bold', pad=20)

    plt.tight_layout()
    chart_path = os.path.join(OUTPUT_DIR, 'scanner_chart.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    print(f"  Chart: {chart_path}")
    plt.show()

    print("\n✅ Scanner completado!")


if __name__ == "__main__":
    run_scanner()
_chart.png')
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    print(f"  Chart: {chart_path}")
    plt.show()

    print("\n✅ Scanner completado!")


if __name__ == "__main__":
    run_scanner()
nches='tight')
    print(f"  Chart: {chart_path}")
    plt.show()

    print("\n✅ Scanner completado!")


if __name__ == "__main__":
    run_scanner()
