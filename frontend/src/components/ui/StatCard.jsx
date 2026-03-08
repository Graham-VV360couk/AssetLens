import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import clsx from 'clsx';

export default function StatCard({ label, value, sub, trend, icon: Icon, color = 'emerald', className }) {
  const colorMap = {
    emerald: 'text-emerald-400 bg-emerald-500/10',
    amber: 'text-amber-400 bg-amber-500/10',
    blue: 'text-blue-400 bg-blue-500/10',
    red: 'text-red-400 bg-red-500/10',
    slate: 'text-slate-400 bg-slate-700/50',
  };
  const [textCol, bgCol] = colorMap[color]?.split(' ') || ['text-emerald-400', 'bg-emerald-500/10'];

  return (
    <div className={clsx(
      'bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col gap-3',
      className
    )}>
      <div className="flex items-center justify-between">
        <span className="text-slate-400 text-sm font-medium">{label}</span>
        {Icon && (
          <div className={clsx('w-9 h-9 rounded-xl flex items-center justify-center', bgCol)}>
            <Icon size={18} className={textCol} />
          </div>
        )}
      </div>
      <div>
        <div className={clsx('text-3xl font-bold', textCol)}>{value}</div>
        {sub && <div className="text-slate-500 text-sm mt-1">{sub}</div>}
      </div>
      {trend != null && (
        <div className={clsx(
          'flex items-center gap-1 text-xs font-medium',
          trend > 0 ? 'text-emerald-400' : trend < 0 ? 'text-red-400' : 'text-slate-400'
        )}>
          {trend > 0 ? <TrendingUp size={13} /> : trend < 0 ? <TrendingDown size={13} /> : <Minus size={13} />}
          {trend > 0 ? '+' : ''}{trend}% vs last month
        </div>
      )}
    </div>
  );
}
