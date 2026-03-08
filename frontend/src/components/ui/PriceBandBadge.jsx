import React from 'react';
import { TrendingDown, TrendingUp, Minus, AlertCircle } from 'lucide-react';
import clsx from 'clsx';
import { bandColor, bandLabel } from '../../utils/formatters';

const bandConfig = {
  brilliant: { icon: TrendingDown, bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400' },
  good:      { icon: TrendingDown, bg: 'bg-green-500/10',   border: 'border-green-500/30',   text: 'text-green-400' },
  fair:      { icon: Minus,        bg: 'bg-amber-500/10',   border: 'border-amber-500/30',   text: 'text-amber-400' },
  bad:       { icon: TrendingUp,   bg: 'bg-red-500/10',     border: 'border-red-500/30',     text: 'text-red-400' },
  unknown:   { icon: AlertCircle,  bg: 'bg-slate-700/50',   border: 'border-slate-600',      text: 'text-slate-400' },
};

export default function PriceBandBadge({ band, size = 'md' }) {
  const cfg = bandConfig[band] || bandConfig.unknown;
  const Icon = cfg.icon;
  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm';

  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 rounded-full border font-semibold',
      cfg.bg, cfg.border, cfg.text, sizeClass
    )}>
      <Icon size={size === 'sm' ? 11 : 13} />
      {bandLabel(band)}
    </span>
  );
}
