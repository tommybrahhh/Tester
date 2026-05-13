import numpy as np
import math

def norm_cdf(x):
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

RISK_FREE_RATE = 0.045
TARGET_GAIN_PCT = 0.15

def estimate_jump_parameters(returns):
    if not returns or len(returns) < 5: return 10.0, -0.01, 0.05
    ret_arr = np.array(returns)
    mu_ret = np.mean(ret_arr)
    std_ret = np.std(ret_arr)
    jumps = ret_arr[np.abs(ret_arr - mu_ret) > 2 * std_ret]
    if len(jumps) > 0:
        lambda_est = (len(jumps) / len(ret_arr)) * 252
        mu_j = np.mean(jumps)
        sigma_j = np.std(jumps) if len(jumps) > 1 else 0.05
    else:
        lambda_est, mu_j, sigma_j = 5.0, 0.0, 0.05
    return float(lambda_est), float(mu_j), float(sigma_j)

def monte_carlo_probabilities(S, K, target_price, T, r, sigma, num_sims=5000, j_lambda=None, j_mu=None, j_sigma=None):
    np.random.seed(42)
    L = j_lambda if j_lambda is not None else 10.0
    MJ = j_mu if j_mu is not None else -0.01
    SJ = j_sigma if j_sigma is not None else 0.05
    
    if T <= 0: return (1.0 if S >= K else 0.0), (1.0 if S >= target_price else 0.0)
    
    trading_days = max(1, int(T * 252))
    dt = T / trading_days
    n_half = num_sims // 2
    
    drift = (r - 0.5 * sigma**2 - L * (np.exp(MJ + 0.5 * SJ**2) - 1)) * dt
    paths = np.zeros((num_sims, trading_days + 1))
    paths[:, 0] = S
    
    for t in range(1, trading_days + 1):
        Z = np.concatenate([np.random.standard_normal(n_half), -np.random.standard_normal(n_half)])
        N = np.random.poisson(L * dt, num_sims)
        J = np.zeros(num_sims)
        jump_indices = np.where(N > 0)[0]
        for idx in jump_indices:
            J[idx] = np.sum(np.random.normal(MJ, SJ, N[idx]))
        paths[:, t] = paths[:, t-1] * np.exp(drift + sigma * np.sqrt(dt) * Z + J)
    
    p_strike = np.mean(np.any(paths >= K, axis=1))
    p_target = np.mean(np.any(paths >= target_price, axis=1))
    return float(p_strike), float(p_target)

def compute_option_score(S, K, T, sigma, contract_price, returns_list, dte, pcr_value=1.0):
    j_lambda, j_mu, j_sigma = estimate_jump_parameters(returns_list)
    
    # Delta
    d1 = (np.log(S / K) + (RISK_FREE_RATE + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    delta = norm_cdf(d1)
    
    # Target
    target_contract = contract_price * (1 + TARGET_GAIN_PCT)
    stock_move_needed = (target_contract - contract_price) / max(delta, 0.1)
    target_stock = S + stock_move_needed
    
    p_strike, p_target = monte_carlo_probabilities(S, K, target_stock, T, RISK_FREE_RATE, sigma, j_lambda=j_lambda, j_mu=j_mu, j_sigma=j_sigma)
    
    # Simplified total score logic
    total_score = (p_target * 0.4) + (p_strike * 0.2) + (min(1.0, sigma/0.5) * 0.4)
    
    return {
        "ticker": "", # Filled by caller
        "dte": dte,
        "strike": float(K),
        "last_price": float(contract_price),
        "prob_strike": p_strike,
        "prob_target": p_target,
        "total_score": float(total_score),
        "kelly_pct": float(max(0, (p_target - 0.5) / 0.3 * 100)) # Simple kelly
    }
