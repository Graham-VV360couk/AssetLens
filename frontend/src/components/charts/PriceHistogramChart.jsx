import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts';
import { formatCurrency } from '../../utils/formatters';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-3 shadow-xl text-xs">
      <p className="text-slate-400 mb-1">{formatCurrency(d.from)} – {formatCurrency(d.to)}</p>
      <p className="text-white font-semibold">{d.count.toLocaleString()} sales</p>
    </div>
  );
};

export default function PriceHistogramChart({ data, guidePrice }) {
  if (!data?.buckets?.length) {
    return (
      <div className="h-48 flex items-center justify-center text-slate-600 text-sm">
        No price data available
      </div>
    );
  }

  const { buckets, percentile, total, median } = data;

  // Colour bars: buckets containing the guide price in amber, others in slate/emerald
  const midBucket = guidePrice
    ? buckets.findIndex(b => guidePrice >= b.from && guidePrice < b.to)
    : -1;

  return (
    <div>
      {/* Summary row */}
      <div className="flex gap-4 text-xs mb-4">
        <div className="bg-slate-800/50 rounded-lg px-3 py-2">
          <div className="text-slate-500 mb-0.5">Median sold</div>
          <div className="text-white font-semibold">{formatCurrency(median, true)}</div>
        </div>
        <div className="bg-slate-800/50 rounded-lg px-3 py-2">
          <div className="text-slate-500 mb-0.5">Transactions (3yr)</div>
          <div className="text-white font-semibold">{total?.toLocaleString()}</div>
        </div>
        {percentile != null && (
          <div className={`rounded-lg px-3 py-2 ${percentile < 30 ? 'bg-emerald-500/10 border border-emerald-500/20' : percentile > 70 ? 'bg-red-500/10 border border-red-500/20' : 'bg-amber-500/10 border border-amber-500/20'}`}>
            <div className="text-slate-500 mb-0.5">Guide price at</div>
            <div className={`font-semibold ${percentile < 30 ? 'text-emerald-400' : percentile > 70 ? 'text-red-400' : 'text-amber-400'}`}>
              {percentile}th percentile
            </div>
          </div>
        )}
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={buckets} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis
            dataKey="label"
            stroke="#475569"
            tick={{ fill: '#64748b', fontSize: 10 }}
            interval="preserveStartEnd"
          />
          <YAxis
            stroke="#475569"
            tick={{ fill: '#64748b', fontSize: 10 }}
            width={35}
          />
          <Tooltip content={<CustomTooltip />} />
          {guidePrice && (
            <ReferenceLine
              x={buckets[midBucket]?.label}
              stroke="#f59e0b"
              strokeWidth={2}
              strokeDasharray="4 3"
              label={{ value: 'Guide', fill: '#f59e0b', fontSize: 10, position: 'top' }}
            />
          )}
          <Bar dataKey="count" radius={[3, 3, 0, 0]}>
            {buckets.map((b, i) => (
              <Cell
                key={i}
                fill={i === midBucket ? '#f59e0b' : '#10b981'}
                fillOpacity={i === midBucket ? 0.9 : 0.55}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
