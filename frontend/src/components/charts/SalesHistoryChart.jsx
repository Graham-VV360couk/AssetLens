import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { formatCurrency } from '../../utils/formatters';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-3 shadow-xl">
      <p className="text-slate-400 text-xs mb-2">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="font-semibold text-sm" style={{ color: p.color }}>
          {formatCurrency(p.value)}
        </p>
      ))}
    </div>
  );
};

export default function SalesHistoryChart({ data, currentPrice }) {
  if (!data?.length) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-600">
        No sales history available
      </div>
    );
  }

  const chartData = data.map(d => ({
    year: d.year,
    price: Math.round(d.avg_price),
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="year" stroke="#475569" tick={{ fill: '#64748b', fontSize: 11 }} />
        <YAxis
          stroke="#475569"
          tick={{ fill: '#64748b', fontSize: 11 }}
          tickFormatter={v => `£${(v / 1000).toFixed(0)}K`}
          width={60}
        />
        <Tooltip content={<CustomTooltip />} />
        {currentPrice && (
          <ReferenceLine y={currentPrice} stroke="#f59e0b" strokeDasharray="4 4"
            label={{ value: 'Asking', fill: '#f59e0b', fontSize: 11 }} />
        )}
        <Area
          type="monotone" dataKey="price" stroke="#10b981" strokeWidth={2.5}
          fill="url(#priceGrad)" dot={{ fill: '#10b981', r: 3 }} activeDot={{ r: 5 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
