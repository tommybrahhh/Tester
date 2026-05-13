from flask import Flask, request, jsonify
import sys
import os
import traceback

# LIGHTWEIGHT MATH SERVICE (No Pandas, No yFinance)
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from call_swing_scanner import compute_option_score
except Exception as e:
    print(f"IMPORT ERROR: {e}")
    compute_option_score = None

app = Flask(__name__)

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "math_ready": compute_option_score is not None})

@app.route("/api/compute-score", methods=["POST"])
def compute():
    try:
        data = request.json
        ticker = data.get("ticker")
        S = data.get("S")
        K = data.get("K")
        T = data.get("T")
        sigma = data.get("sigma")
        contract_price = data.get("contract_price")
        returns = data.get("returns", [])
        dte = data.get("dte")
        
        result = compute_option_score(S, K, T, sigma, contract_price, returns, dte)
        result["ticker"] = ticker
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

if __name__ == "__main__":
    app.run(debug=True)
