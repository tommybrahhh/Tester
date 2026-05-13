import { NextResponse } from 'next/server';
import yahooFinance from 'yahoo-finance2';

export async function POST(request: Request) {
  try {
    const { tickers, dte_range } = await request.json();
    const results: any[] = [];
    const metrics: any = {};

    const baseUrl = process.env.VERCEL_URL 
      ? `https://${process.env.VERCEL_URL}` 
      : 'http://localhost:3000';

    for (const ticker of tickers) {
      try {
        const quote = await yahooFinance.quote(ticker) as any;
        const options = await yahooFinance.options(ticker);
        const history = await yahooFinance.historical(ticker, { 
          period1: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0] 
        });

        const S = quote.regularMarketPrice || quote.bid || quote.ask;
        if (!S) continue;

        // Calculate Sigma (Volatility) manually
        const prices = history.map(h => h.close);
        const returns = [];
        for (let i = 1; i < prices.length; i++) {
          returns.push(Math.log(prices[i] / prices[i-1]));
        }
        const meanReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
        const variance = returns.reduce((a, b) => a + Math.pow(b - meanReturn, 2), 0) / (returns.length - 1);
        const sigma = Math.sqrt(variance * 252);

        metrics[ticker] = {
          current_price: S,
          ticker: ticker,
          history: history.map(h => ({ date: h.date.toISOString().split('T')[0], price: h.close }))
        };

        const today = new Date();
        const validExps = options.expirations.filter(expStr => {
          const expDate = new Date(expStr);
          const dte = Math.floor((expDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
          return dte >= dte_range[0] && dte <= dte_range[1];
        });

        // Limit to 2 expirations to avoid timeouts
        for (const expDate of validExps.slice(0, 2)) {
          const chain = await yahooFinance.options(ticker, { date: expDate });
          // Take top 5 calls by OI
          const calls = chain.calls
            .filter(c => c.openInterest && c.openInterest > 50)
            .sort((a, b) => (b.openInterest || 0) - (a.openInterest || 0))
            .slice(0, 5);

          for (const call of calls) {
            const dte = Math.floor((new Date(expDate).getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
            
            // Call Python Nano-Service for the math
            try {
              const mathRes = await fetch(`${baseUrl}/api/compute-score`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  ticker, S, K: call.strike, T: dte / 365,
                  sigma, contract_price: call.lastPrice,
                  returns, dte
                })
              });
              
              if (mathRes.ok) {
                const scoreResult = await mathRes.json();
                results.push({
                  ...scoreResult,
                  expiration: expDate,
                  open_interest: call.openInterest,
                  volume: call.volume
                });
              }
            } catch (e) {
              console.error("Math service failed", e);
            }
          }
        }
      } catch (e) {
        console.error(`Error processing ${ticker}:`, e);
      }
    }

    return NextResponse.json({ 
      opportunities: results.sort((a, b) => b.total_score - a.total_score), 
      metrics 
    });
  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
