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

                {selectedTicker && <TickerDeepDive ticker={selectedTicker} />}
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
             {/* Custom Simulator implementation would go here */}
             <div className="glass-card p-10 text-center text-gray-500">
               Simulator components will be implemented next.
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
