from flask import Flask, request, jsonify
import sys
import os

# Add the current directory to sys.path to import call_swing_scanner
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from call_swing_scanner import run_scan_logic, get_historical_data, RISK_FREE_RATE

app = Flask(__name__)

@app.route("/api/scan", methods=["POST"])
def scan():
    data = request.json
    tickers = data.get("tickers", ["SOFI", "F", "PFE"])
    dte_range = data.get("dte_range", [30, 50])
    delta_range = data.get("delta_range", [0.60, 0.80])
    
    results_df, stock_metrics = run_scan_logic(
        tickers, 
        dte_range[0], dte_range[1], 
        delta_range[0], delta_range[1]
    )
    
    if results_df.empty:
        return jsonify({"opportunities": [], "metrics": {}})
    
    # Convert dates to strings for JSON
    opps = results_df.to_dict(orient="records")
    for op in opps:
        if "expiration" in op and hasattr(op["expiration"], "strftime"):
            op["expiration"] = op["expiration"].strftime("%Y-%m-%d")
            
    return jsonify({
        "opportunities": opps,
        "metrics": {t: {k: (v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else v) 
                    for k, v in m.items()} 
                    for t, m in stock_metrics.items()}
    })

@app.route("/api/simulate", methods=["POST"])
def simulate():
    from call_swing_scanner import monte_carlo_probabilities, estimate_delta, estimate_jump_parameters
    import numpy as np
    import pandas as pd
    
    data = request.json
    ticker = data.get("ticker", "SOFI")
    dte = data.get("dte", 30)
    strike = data.get("strike", 10.0)
    target = data.get("target", 0.0)
    
    hist = get_historical_data(ticker, period="6mo")
    if hist is None or hist.empty:
        return jsonify({"error": "Ticker data not found"}), 404
        
    s_price = hist['Close'].iloc[-1]
    j_lambda, j_mu, j_sigma = estimate_jump_parameters(hist)
    
    returns = np.log(hist['Close'] / hist['Close'].shift(1))
    sigma = returns.tail(20).std() * np.sqrt(252)
    T = dte / 252.0
    
    if target <= 0:
        delta_est = estimate_delta(s_price, strike, T, RISK_FREE_RATE, sigma)
        needed_gain = 0.15 * (s_price * 0.05) 
        final_target = s_price + (needed_gain / max(delta_est, 0.1))
    else:
        final_target = target

    prob_strike, prob_target, paths = monte_carlo_probabilities(
        s_price, strike, final_target, T, RISK_FREE_RATE, sigma, 
        num_sims=10000, return_paths=True,
        j_lambda=j_lambda, j_mu=j_mu, j_sigma=j_sigma
    )
    
    # Advanced Metrics
    epv_score = prob_target * (final_target / s_price)
    dist_to_target = (final_target / s_price) - 1
    theta_risk = dist_to_target / (dte / 30.0)
    
    return jsonify({
        "s_price": float(s_price),
        "final_target": float(final_target),
        "prob_strike": float(prob_strike),
        "prob_target": float(prob_target),
        "epv_score": float(epv_score),
        "theta_risk": "HIGH" if theta_risk > 0.1 else "MODERATE" if theta_risk > 0.05 else "LOW",
        "j_params": {"lambda": float(j_lambda), "mu": float(j_mu), "sigma": float(j_sigma)},
        "distribution": paths[:, -1].tolist() # Final prices for histogram
    })

if __name__ == "__main__":
    app.run(debug=True)
