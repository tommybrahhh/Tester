"use client";

import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface ChartProps {
  data: any[];
  dataKey: string;
  title: string;
  threshold?: number;
}

const ScoreChart: React.FC<ChartProps> = ({ data, dataKey, title, threshold }) => {
  return (
    <div className="glass-card p-6 h-[350px] flex flex-col">
      <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-6">{title}</h3>
      <div className="flex-1 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e222d" vertical={false} />
            <XAxis 
              dataKey="ticker" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: '#6b7280', fontSize: 11, fontWeight: 600 }}
              dy={10}
            />
            <YAxis 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: '#6b7280', fontSize: 11 }}
            />
            <Tooltip 
              cursor={{ fill: 'rgba(255,255,255,0.05)' }}
              contentStyle={{ 
                backgroundColor: '#0e1117', 
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px',
                fontSize: '12px'
              }}
              itemStyle={{ fontWeight: 'bold' }}
            />
            <Bar dataKey={dataKey} radius={[4, 4, 0, 0]} barSize={35}>
              {data.map((entry, index) => {
                let color = entry[dataKey] > (threshold || 0.8) ? '#00ff80' : '#4f4f4f';
                if (dataKey === 'kelly_pct') color = '#8b5cf6';
                return <Cell key={`cell-${index}`} fill={color} />;
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ScoreChart;
