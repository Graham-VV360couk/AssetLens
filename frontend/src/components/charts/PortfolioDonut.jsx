import React from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { bandColor, bandLabel } from '../../utils/formatters';

export default function PortfolioDonut({ data }) {
  if (!data || Object.keys(data).length === 0) return null;

  const chartData = Object.entries(data)
    .filter(([, v]) => v > 0)
    .map(([band, count]) => ({
      name: bandLabel(band),
      value: count,
      color: bandColor(band),
    }));

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-3 shadow-xl">
        <p className="font-semibold text-sm" style={{ color: payload[0].payload.color }}>
          {payload[0].name}
        </p>
        <p className="text-slate-300 text-sm">{payload[0].value.toLocaleString()} properties</p>
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={55}
          outerRadius={85}
          paddingAngle={3}
          dataKey="value"
        >
          {chartData.map((entry, i) => (
            <Cell key={i} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={(value) => <span style={{ color: '#94a3b8', fontSize: 12 }}>{value}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
