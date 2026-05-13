"use client";

import React from 'react';

interface Opportunity {
  rank: number;
  ticker: string;
  expiration: string;
  dte: number;
  strike: number;
  last_price: number;
  max_pain: number;
  vol_skew: number;
  pcr: number;
  vol_edge: number;
  beta: number;
  kelly_pct: number;
  prob_target: number;
  total_score: number;
}

interface DataTableProps {
  data: Opportunity[];
  onTickerSelect: (ticker: string) => void;
}

const DataTable: React.FC<DataTableProps> = ({ data, onTickerSelect }) => {
  return (
    <div className="glass-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/5 bg-white/5 text-[10px] uppercase tracking-widest text-gray-500 font-bold">
              <th className="px-6 py-4">Rank</th>
              <th className="px-6 py-4">Ticker</th>
              <th className="px-6 py-4">Exp</th>
              <th className="px-6 py-4">DTE</th>
              <th className="px-6 py-4">Strike</th>
              <th className="px-6 py-4">Price</th>
              <th className="px-6 py-4">Vol Edge</th>
              <th className="px-6 py-4">Prob Target</th>
              <th className="px-6 py-4 text-[var(--accent-green)]">Alpha Score</th>
            </tr>
          </thead>
          <tbody className="text-sm font-medium">
            {data.map((row, idx) => (
              <tr 
                key={idx} 
                onClick={() => onTickerSelect(row.ticker)}
                className="border-b border-white/5 hover:bg-white/[0.03] transition-colors cursor-pointer group"
              >
                <td className="px-6 py-4 text-gray-500 font-mono text-xs">{row.rank}</td>
                <td className="px-6 py-4 text-white font-bold group-hover:text-[var(--accent-green)] transition-colors">{row.ticker}</td>
                <td className="px-6 py-4 text-gray-400">{row.expiration}</td>
                <td className="px-6 py-4 text-gray-400">{row.dte}</td>
                <td className="px-6 py-4 text-white">${row.strike.toFixed(1)}</td>
                <td className="px-6 py-4 text-white">${row.last_price.toFixed(2)}</td>
                <td className={`px-6 py-4 ${row.vol_edge > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {(row.vol_edge * 100).toFixed(1)}%
                </td>
                <td className="px-6 py-4 text-gray-300">{(row.prob_target * 100).toFixed(0)}%</td>
                <td className="px-6 py-4">
                  <span className="bg-[var(--accent-glow)] text-[var(--accent-green)] px-3 py-1 rounded-full text-xs font-bold border border-[rgba(0,255,128,0.2)]">
                    {row.total_score.toFixed(2)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DataTable;
