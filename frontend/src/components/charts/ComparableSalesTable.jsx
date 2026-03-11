import React from 'react';
import clsx from 'clsx';
import { formatCurrency } from '../../utils/formatters';

export default function ComparableSalesTable({ data, guidePrice }) {
  if (!data?.length) {
    return (
      <div className="text-slate-600 text-sm py-6 text-center">
        No comparable sales found in this area
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-slate-500 border-b border-slate-800">
            <th className="text-left pb-2 font-medium">Address</th>
            <th className="text-left pb-2 font-medium">Type</th>
            <th className="text-left pb-2 font-medium">Date</th>
            <th className="text-right pb-2 font-medium">Sold Price</th>
            <th className="text-right pb-2 font-medium">vs Guide</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60">
          {data.map((row, i) => {
            const diff = guidePrice && row.sale_price
              ? ((row.sale_price - guidePrice) / guidePrice)
              : null;
            return (
              <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                <td className="py-2 pr-3">
                  <div className="text-slate-300 truncate max-w-[200px]">{row.address}</div>
                  <div className="text-slate-600">{row.postcode}</div>
                </td>
                <td className="py-2 pr-3">
                  <span className="text-slate-400">{row.property_type}</span>
                  {row.new_build && (
                    <span className="ml-1 text-[10px] text-amber-500 bg-amber-500/10 px-1 rounded">NEW</span>
                  )}
                </td>
                <td className="py-2 pr-3 text-slate-400">
                  {row.sale_date ? new Date(row.sale_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '—'}
                </td>
                <td className="py-2 pr-3 text-right font-semibold text-slate-200">
                  {formatCurrency(row.sale_price, true)}
                </td>
                <td className="py-2 text-right">
                  {diff != null ? (
                    <span className={clsx('font-medium', diff < 0 ? 'text-emerald-400' : 'text-red-400')}>
                      {diff >= 0 ? '+' : ''}{(diff * 100).toFixed(0)}%
                    </span>
                  ) : <span className="text-slate-600">—</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
