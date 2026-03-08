import React from 'react';
import { CircularProgressbar, buildStyles } from 'react-circular-progressbar';
import 'react-circular-progressbar/dist/styles.css';

function yieldColor(pct) {
  if (pct == null) return '#64748b';
  if (pct >= 8) return '#10b981';
  if (pct >= 6) return '#22c55e';
  if (pct >= 4) return '#f59e0b';
  return '#ef4444';
}

export default function YieldMeter({ yieldPct, size = 100, label = 'Gross Yield' }) {
  const value = yieldPct != null ? Math.min(15, yieldPct) : 0;
  const maxDisplay = 15;
  const color = yieldColor(yieldPct);

  return (
    <div className="flex flex-col items-center gap-2">
      <div style={{ width: size, height: size }}>
        <CircularProgressbar
          value={value}
          maxValue={maxDisplay}
          text={yieldPct != null ? `${Number(yieldPct).toFixed(1)}%` : '—'}
          styles={buildStyles({
            textSize: '20px',
            textColor: color,
            pathColor: color,
            trailColor: '#1e293b',
            pathTransitionDuration: 1,
          })}
        />
      </div>
      <span className="text-slate-400 text-sm font-medium">{label}</span>
    </div>
  );
}
