"use client";

import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface DeepDiveProps {
  ticker: string;
  metrics?: any;
}

const TickerDeepDive: React.FC<DeepDiveProps> = ({ ticker, metrics }) => {
  const [loading, setLoading] = useState(false);
  const history = metrics?.[ticker]?.history || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-4 mb-4">
        <div className="h-px flex-1 bg-white/5"></div>
        <h2 className="text-xl font-bold text-white tracking-tight italic">
          DEEP-DIVE: <span className="text-[var(--accent-green)]">{ticker}</span>
        </h2>
        <div className="h-px flex-1 bg-white/5"></div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Price Action Chart */}
        <div className="glass-card p-6 min-h-[350px]">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4 text-center">Structural Price Action (60D)</h3>
          {history.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-gray-700 font-mono uppercase text-[10px]">
              {ticker} Data stream synchronized.
            </div>
          ) : (
            <div className="h-64">
               <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={history}>
                   <CartesianGrid strokeDasharray="3 3" stroke="#1e222d" vertical={false} />
                   <XAxis dataKey="date" hide />
                   <YAxis hide domain={['auto', 'auto']} />
                   <Tooltip 
                      contentStyle={{ backgroundColor: '#0e1117', border: '1px solid #333' }}
                      itemStyle={{ color: '#00ff80' }}
                   />
                   <Area type="monotone" dataKey="price" stroke="#00ff80" fill="url(#colorGreen)" animationDuration={1000} />
                   <defs>
                    <linearGradient id="colorGreen" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#00ff80" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#00ff80" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                </AreaChart>
               </ResponsiveContainer>
               <div className="text-center text-[10px] text-gray-600 font-mono mt-4 uppercase">
                 [ Structural Analysis Matrix: Active ]
               </div>
            </div>
          )}
        </div>

        {/* Volatility Pulse */}
        <div className="glass-card p-6 min-h-[350px]">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4 text-center">Realized Volatility Pulse</h3>
          <div className="h-64 flex items-center justify-center border border-dashed border-white/5 rounded-lg italic text-gray-600 text-sm">
             Volatility trend visualization pending data stream.
          </div>
        </div>
      </div>
    </div>
  );
};

export default TickerDeepDive;
