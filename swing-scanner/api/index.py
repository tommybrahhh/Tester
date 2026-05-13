from flask import Flask, request, jsonify
import sys
import os
import traceback

# Add the current directory to sys.path to import call_swing_scanner
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from call_swing_scanner import run_scan_logic, get_historical_data, RISK_FREE_RATE
except Exception as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    run_scan_logic = None

app = Flask(__name__)

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok", 
        "python": sys.version,
        "scanner_loaded": run_scan_logic is not None
    })

@app.route("/api/scan", methods=["POST"])
def scan():
    if not run_scan_logic:
        return jsonify({"error": "Scanner logic failed to load. Check logs."}), 500
        
    try:
        data = request.json or {}
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
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

if __name__ == "__main__":
    app.run(debug=True)
