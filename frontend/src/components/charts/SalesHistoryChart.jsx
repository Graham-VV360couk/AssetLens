import React from 'react';
import {
  ComposedChart, Area, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts';
import { formatCurrency } from '../../utils/formatters';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-3 shadow-xl text-xs space-y-1">
      <p className="text-slate-400 mb-1.5 font-medium">{label}</p>
      {payload.map((p, i) => {
        if (p.dataKey === 'transactions') {
          return <p key={i} style={{ color: p.color }}>{p.value?.toLocaleString()} sales</p>;
        }
        if (p.dataKey === 'national') {
          return <p key={i} style={{ color: p.color }}>National avg: {formatCurrency(p.value, true)}</p>;
        }
        return <p key={i} style={{ color: p.color }}>District avg: {formatCurrency(p.value, true)}</p>;
      })}
    </div>
  );
};

export default function SalesHistoryChart({ data, currentPrice, nationalData }) {
  if (!data?.length) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-600">
        No sales history available
      </div>
    );
  }

  // Merge national into district data by year
  // nationalData may be an array or an object {sales_by_year:[...]} depending on API version
  const nationalArray = Array.isArray(nationalData)
    ? nationalData
    : (Array.isArray(nationalData?.sales_by_year) ? nationalData.sales_by_year : []);
  const nationalByYear = {};
  nationalArray.forEach(n => { nationalByYear[n.year] = n.avg_price; });

  const chartData = data.map(d => ({
    year: d.year,
    price: Math.round(d.avg_price),
    transactions: d.transactions || 0,
    national: nationalByYear[d.year] ? Math.round(nationalByYear[d.year]) : undefined,
  }));

  const maxTransactions = Math.max(...chartData.map(d => d.transactions));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey="year" stroke="#475569" tick={{ fill: '#64748b', fontSize: 11 }} />

        {/* Left axis: price */}
        <YAxis
          yAxisId="price"
          stroke="#475569"
          tick={{ fill: '#64748b', fontSize: 11 }}
          tickFormatter={v => `£${(v / 1000).toFixed(0)}K`}
          width={60}
        />

        {/* Right axis: transaction count */}
        <YAxis
          yAxisId="vol"
          orientation="right"
          stroke="#475569"
          tick={{ fill: '#475569', fontSize: 10 }}
          tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v}
          width={38}
          domain={[0, maxTransactions * 2.5]}
        />

        <Tooltip content={<CustomTooltip />} />

        {currentPrice && (
          <ReferenceLine
            yAxisId="price"
            y={currentPrice}
            stroke="#f59e0b"
            strokeDasharray="4 4"
            label={{ value: 'Asking', fill: '#f59e0b', fontSize: 11 }}
          />
        )}

        {/* Volume bars behind the lines */}
        <Bar
          yAxisId="vol"
          dataKey="transactions"
          fill="#334155"
          opacity={0.7}
          radius={[2, 2, 0, 0]}
          name="Sales volume"
        />

        {/* District area */}
        <Area
          yAxisId="price"
          type="monotone"
          dataKey="price"
          stroke="#10b981"
          strokeWidth={2.5}
          fill="url(#priceGrad)"
          dot={{ fill: '#10b981', r: 3 }}
          activeDot={{ r: 5 }}
          name="District avg"
        />

        {/* National average line (dashed) */}
        {nationalArray.length > 0 && (
          <Line
            yAxisId="price"
            type="monotone"
            dataKey="national"
            stroke="#6366f1"
            strokeWidth={1.5}
            strokeDasharray="5 3"
            dot={false}
            name="National avg"
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
