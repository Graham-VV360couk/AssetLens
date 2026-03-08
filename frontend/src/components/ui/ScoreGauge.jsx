import React from 'react';
import { scoreColor } from '../../utils/formatters';

const RADIUS = 54;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function getArcDash(score, max = 100) {
  const pct = Math.min(1, Math.max(0, score / max));
  return {
    dasharray: `${pct * CIRCUMFERENCE * 0.75} ${CIRCUMFERENCE}`,
    dashoffset: CIRCUMFERENCE * 0.125, // start at 7 o'clock
  };
}

export default function ScoreGauge({ score, size = 140, label = 'Investment Score' }) {
  const color = scoreColor(score);
  const arc = score != null ? getArcDash(score) : null;
  const bgArc = getArcDash(100);

  return (
    <div className="flex flex-col items-center gap-2">
      <div style={{ width: size, height: size }} className="relative">
        <svg viewBox="0 0 120 120" className="w-full h-full -rotate-[135deg]">
          {/* Background track */}
          <circle
            cx="60" cy="60" r={RADIUS}
            fill="none"
            stroke="#1e293b"
            strokeWidth="10"
            strokeDasharray={`${bgArc.dasharray}`}
            strokeDashoffset={-bgArc.dashoffset}
            strokeLinecap="round"
          />
          {/* Score arc */}
          {arc && (
            <circle
              cx="60" cy="60" r={RADIUS}
              fill="none"
              stroke={color}
              strokeWidth="10"
              strokeDasharray={arc.dasharray}
              strokeDashoffset={-arc.dashoffset}
              strokeLinecap="round"
              style={{ filter: `drop-shadow(0 0 6px ${color}60)`, transition: 'stroke-dasharray 1s ease' }}
            />
          )}
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-3xl font-bold leading-none"
            style={{ color: score != null ? color : '#64748b' }}
          >
            {score != null ? Math.round(score) : '—'}
          </span>
          <span className="text-slate-500 text-xs mt-1">/ 100</span>
        </div>
      </div>
      <span className="text-slate-400 text-sm font-medium">{label}</span>
    </div>
  );
}
