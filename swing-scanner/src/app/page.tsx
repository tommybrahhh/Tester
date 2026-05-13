"use client";

import React, { useState, useEffect } from 'react';
import Sidebar from '@/components/Sidebar';
import DataTable from '@/components/DataTable';
import ScoreChart from '@/components/ScoreChart';
import TickerDeepDive from '@/components/TickerDeepDive';
import { Search, TrendingUp, ShieldAlert, PieChart, RefreshCcw, Activity } from 'lucide-react';

export default function Home() {
  const [viewMode, setViewMode] = useState<'scanner' | 'simulator'>('scanner');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>({});
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  // Default parameters
  const [tickers, setTickers] = useState("SOFI, F, PFE, KHC, BAC, T, VZ, NU");
  const [dteRange, setDteRange] = useState([30, 50]);
  const [deltaRange, setDeltaRange] = useState([0.60, 0.80]);

  const runScan = async () => {
    setLoading(true);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 25000); // 25s timeout for Vercel Hobby

    try {
      const response = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tickers: tickers.split(',').map(t => t.trim()),
          dte_range: dteRange,
          delta_range: deltaRange
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }

      const result = await response.json();
      setData(result.opportunities || []);
      setMetrics(result.metrics || {});
      if (result.opportunities?.length > 0) {
        setSelectedTicker(result.opportunities[0].ticker);
      }
    } catch (err: any) {
      console.error("Scan failed:", err);
      alert(err.name === 'AbortError' 
        ? "Request timed out. Try fewer tickers." 
        : `Scan failed: ${err.message}`);
    } finally {
      clearTimeout(timeoutId);
      setLoading(false);
    }
  };

  const onRefresh = () => {
    runScan();
  };

  return (
    <main className="flex min-h-screen bg-[#0a0b10]">
      <Sidebar viewMode={viewMode} setViewMode={setViewMode} onRefresh={onRefresh} />
      
      <div className="flex-1 ml-64 p-8">
        <header className="flex justify-between items-start mb-10">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-gray-400 to-gray-700 bg-clip-text text-transparent mb-2">
              SWING SCANNER TERMINAL
            </h1>
            <p className="text-xs text-gray-500 font-mono uppercase tracking-[0.2em] flex items-center gap-2">
              <Activity size={14} className="text-[var(--accent-green)]" />
              Statistical Market Intelligence Engine
            </p>
          </div>
          
          <div className="flex gap-4">
             {/* Simple inputs for now, could be in a popover */}
             <div className="glass-card px-4 py-2 flex items-center gap-4">
               <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Live Watchlist:</span>
               <input 
                 className="bg-transparent border-none text-white text-xs font-mono focus:ring-0 w-64"
                 value={tickers}
                 onChange={(e) => setTickers(e.target.value)}
               />
               <button 
                onClick={runScan}
                disabled={loading}
                className="bg-[var(--accent-green)] text-black text-[10px] font-bold px-4 py-1 rounded hover:scale-105 transition-transform disabled:opacity-50"
               >
                 {loading ? 'ANALYZING...' : 'RUN SCAN'}
               </button>
             </div>
          </div>
        </header>

        {viewMode === 'scanner' ? (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {/* Executive Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { label: 'Opportunities', value: data.length.toString(), icon: Search, color: 'text-blue-400' },
                { label: 'Primary Ticker', value: data[0]?.ticker || '---', icon: TrendingUp, color: 'text-emerald-400' },
                { label: 'Alpha Score', value: data[0]?.total_score.toFixed(2) || '0.00', icon: ShieldAlert, color: 'text-orange-400' },
                { label: 'Max Allocation', value: `${Math.max(...data.map(d => d.kelly_pct), 0).toFixed(1)}%`, icon: PieChart, color: 'text-purple-400' },
              ].map((metric, i) => (
                <div key={i} className="glass-card p-6 flex flex-col group">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-xs font-bold text-gray-500 uppercase tracking-tighter">{metric.label}</span>
                    <metric.icon size={18} className={`${metric.color} opacity-70 group-hover:opacity-100 transition-opacity`} />
                  </div>
                  <div className="text-3xl font-bold text-white group-hover:text-[var(--accent-green)] transition-colors tracking-tight">
                    {loading ? '...' : metric.value}
                  </div>
                </div>
              ))}
            </div>

            {/* Data Table */}
            {data.length > 0 ? (
              <>
                <DataTable data={data} onTickerSelect={(t) => setSelectedTicker(t)} />
                
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <ScoreChart 
                    data={data.slice(0, 10)} 
                    dataKey="total_score" 
                    title="Alpha Score Ranking" 
                    threshold={0.8}
                  />
                  <ScoreChart 
                    data={data.slice(0, 10)} 
                    dataKey="kelly_pct" 
                    title="Capital Allocation (Kelly %)" 
                  />
                </div>

                {selectedTicker && <TickerDeepDive ticker={selectedTicker} metrics={metrics} />}
              </>
            ) : (
              <div className="glass-card min-h-[400px] flex items-center justify-center text-gray-500 border-dashed">
                <div className="text-center">
                  <RefreshCcw className={`mx-auto mb-4 ${loading ? 'animate-spin' : 'opacity-20'}`} size={48} />
                  <p className="text-sm font-mono uppercase tracking-widest opacity-40">
                    {loading ? 'Crunching Market Data...' : 'System Ready for Analysis'}
                  </p>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
             <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
               <div className="lg:col-span-1 space-y-6">
                 <div className="glass-card p-6">
                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">Simulation Parameters</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="text-[10px] text-gray-500 uppercase font-bold mb-2 block">Ticker Symbol</label>
                        <input 
                          className="w-full bg-white/5 border border-white/10 rounded px-4 py-2 text-white font-mono focus:ring-1 focus:ring-[var(--accent-green)] transition-all"
                          defaultValue="SOFI"
                          id="sim-ticker"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-[10px] text-gray-500 uppercase font-bold mb-2 block">DTE</label>
                          <input type="number" className="w-full bg-white/5 border border-white/10 rounded px-4 py-2 text-white font-mono" defaultValue="30" id="sim-dte" />
                        </div>
                        <div>
                          <label className="text-[10px] text-gray-500 uppercase font-bold mb-2 block">Strike</label>
                          <input type="number" className="w-full bg-white/5 border border-white/10 rounded px-4 py-2 text-white font-mono" defaultValue="10" id="sim-strike" />
                        </div>
                      </div>
                      <button 
                        onClick={async () => {
                          const ticker = (document.getElementById('sim-ticker') as HTMLInputElement).value;
                          const dte = (document.getElementById('sim-dte') as HTMLInputElement).value;
                          const strike = (document.getElementById('sim-strike') as HTMLInputElement).value;
                          
                          setLoading(true);
                          try {
                            const res = await fetch('/api/simulate', {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ ticker, dte: parseInt(dte), strike: parseFloat(strike) })
                            });
                            const result = await res.json();
                            alert(`Success! Probability of touch: ${(result.prob_strike * 100).toFixed(2)}%`);
                          } catch (e) {
                            alert("Simulation failed.");
                          } finally {
                            setLoading(false);
                          }
                        }}
                        className="w-full bg-[var(--accent-green)] text-black font-bold py-3 rounded-lg hover:shadow-[0_0_20px_rgba(0,255,128,0.3)] transition-all uppercase text-xs"
                      >
                        {loading ? 'Simulating Path...' : 'Execute Monte Carlo'}
                      </button>
                    </div>
                 </div>
               </div>
               <div className="lg:col-span-2">
                 <div className="glass-card p-10 flex flex-col items-center justify-center text-gray-600 border-dashed min-h-[400px]">
                    <Activity size={48} className="mb-4 opacity-20" />
                    <p className="text-sm font-mono uppercase tracking-widest opacity-40">Visual projections will appear here</p>
                 </div>
               </div>
             </div>
          </div>
        )}
      </div>
    </main>
  );
}
