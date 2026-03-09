import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const BAND_COLORS = {
  '0–20':  '#ef4444',
  '20–40': '#f97316',
  '40–60': '#94a3b8',
  '60–75': '#22c55e',
  '75–90': '#10b981',
  '90+':   '#06d6a0',
};

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-3 shadow-xl text-xs">
      <p className="text-slate-400 mb-1">Score {d.label}</p>
      <p className="text-white font-semibold">{d.count.toLocaleString()} properties</p>
    </div>
  );
};

export default function ScoreDistributionChart({ data }) {
  if (!data?.length) return null;
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
        <XAxis dataKey="label" stroke="#475569" tick={{ fill: '#64748b', fontSize: 11 }} />
        <YAxis stroke="#475569" tick={{ fill: '#64748b', fontSize: 10 }} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={BAND_COLORS[d.label] || '#64748b'} fillOpacity={0.85} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
