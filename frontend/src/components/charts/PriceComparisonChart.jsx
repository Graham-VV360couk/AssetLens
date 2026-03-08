import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { formatCurrency } from '../../utils/formatters';

export default function PriceComparisonChart({ askingPrice, estimatedValue }) {
  if (!askingPrice && !estimatedValue) return null;

  const data = [
    { name: 'Asking Price', value: askingPrice, color: '#f59e0b' },
    { name: 'Est. Market Value', value: estimatedValue, color: '#10b981' },
  ].filter(d => d.value);

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-3 shadow-xl">
        <p className="text-slate-300 text-sm font-semibold">{payload[0].payload.name}</p>
        <p className="font-bold text-lg mt-1" style={{ color: payload[0].payload.color }}>
          {formatCurrency(payload[0].value)}
        </p>
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }} barCategoryGap="40%">
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
        <XAxis dataKey="name" stroke="#475569" tick={{ fill: '#94a3b8', fontSize: 12 }} />
        <YAxis
          stroke="#475569"
          tick={{ fill: '#64748b', fontSize: 11 }}
          tickFormatter={v => `£${(v / 1000).toFixed(0)}K`}
          width={60}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="value" radius={[6, 6, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
