import React, { useState, useCallback, useEffect } from 'react';
import { SlidersHorizontal, RotateCcw } from 'lucide-react';

const DIMENSIONS = [
  { key: 'price',      label: 'Price vs Valuation',    defaultWeight: 9, description: 'Below market value' },
  { key: 'yield',      label: 'Rental Yield',          defaultWeight: 8, description: 'Gross yield %' },
  { key: 'crime',      label: 'Low Crime',             defaultWeight: 7, description: 'Crime rate and trend' },
  { key: 'broadband',  label: 'Broadband Speed',       defaultWeight: 5, description: 'Gigabit availability' },
  { key: 'schools',    label: 'School Proximity',       defaultWeight: 4, description: 'Nearest primary & secondary' },
  { key: 'transport',  label: 'Transport Links',        defaultWeight: 6, description: 'Nearest station distance' },
  { key: 'flood',      label: 'No Flood Risk',          defaultWeight: 8, description: 'Not in flood zone' },
  { key: 'epc',        label: 'Energy Rating',          defaultWeight: 5, description: 'EPC A-G rating' },
  { key: 'planning',   label: 'No Planning Restrictions', defaultWeight: 3, description: 'Conservation, Article 4, etc.' },
  { key: 'deprivation', label: 'Low Deprivation',       defaultWeight: 4, description: 'IMD rank' },
];

function SliderRow({ dim, weight, onChange }) {
  const barColor = weight === 0
    ? 'bg-slate-700'
    : weight <= 3
      ? 'bg-blue-500/40'
      : weight <= 6
        ? 'bg-blue-500/60'
        : 'bg-blue-500';

  return (
    <div className="flex items-center gap-3 py-2">
      <div className="w-44 flex-shrink-0">
        <div className="text-sm text-white font-medium">{dim.label}</div>
        <div className="text-xs text-slate-500">{dim.description}</div>
      </div>
      <input
        type="range"
        min={0}
        max={10}
        value={weight}
        onChange={(e) => onChange(dim.key, parseInt(e.target.value))}
        className="flex-1 h-2 rounded-lg appearance-none cursor-pointer accent-blue-500"
        style={{
          background: `linear-gradient(to right, #3b82f6 ${weight * 10}%, #334155 ${weight * 10}%)`,
        }}
      />
      <span className={`w-8 text-center text-sm font-mono font-bold ${weight === 0 ? 'text-slate-600' : 'text-white'}`}>
        {weight}
      </span>
    </div>
  );
}

export default function ScoringSliders({ onWeightsChange, initialWeights = null, matchStats = null }) {
  const [weights, setWeights] = useState(() => {
    if (initialWeights) return initialWeights;
    const defaults = {};
    DIMENSIONS.forEach(d => { defaults[d.key] = d.defaultWeight; });
    return defaults;
  });

  const [expanded, setExpanded] = useState(false);

  // Sync from async initialWeights (e.g. profile loaded after mount)
  useEffect(() => {
    if (initialWeights) {
      setWeights(initialWeights);
    }
  }, [initialWeights]);

  const handleChange = useCallback((key, value) => {
    setWeights(prev => {
      const next = { ...prev, [key]: value };
      return next;
    });
  }, []);

  // Notify parent when weights change
  useEffect(() => {
    if (onWeightsChange) {
      onWeightsChange(weights);
    }
  }, [weights, onWeightsChange]);

  const resetToDefaults = () => {
    const defaults = {};
    DIMENSIONS.forEach(d => { defaults[d.key] = d.defaultWeight; });
    setWeights(defaults);
  };

  const totalWeight = Object.values(weights).reduce((a, b) => a + b, 0);

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-slate-800/80 transition"
      >
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
            What Matters To You
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">
            {totalWeight > 0 ? `${DIMENSIONS.filter(d => weights[d.key] > 0).length} active` : 'All off'}
          </span>
          <span className={`text-xs transition-transform ${expanded ? 'rotate-180' : ''}`}>
            &#9660;
          </span>
        </div>
      </button>

      {expanded && (
        <div className="px-5 pb-4 border-t border-slate-700/50">
          <div className="flex items-center justify-between py-2 mb-1">
            <p className="text-xs text-slate-500">
              Adjust how important each factor is to you. 0 = don't care, 10 = essential.
            </p>
            <button
              onClick={resetToDefaults}
              className="flex items-center gap-1 text-xs text-slate-500 hover:text-white transition"
            >
              <RotateCcw className="w-3 h-3" /> Reset
            </button>
          </div>

          {DIMENSIONS.map(dim => (
            <SliderRow
              key={dim.key}
              dim={dim}
              weight={weights[dim.key] || 0}
              onChange={handleChange}
            />
          ))}

          {/* Live match counter */}
          {matchStats && (
            <div className="flex items-center gap-4 pt-3 mt-2 border-t border-slate-700/50">
              <span className="text-sm text-emerald-400 font-semibold">
                {matchStats.above50} of {matchStats.total} properties score 50+
              </span>
              <span className="text-xs text-slate-500">
                Average match: {matchStats.avg}%
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Utility: compute a weighted score for a property given weights
export function computeWeightedScore(property, weights) {
  if (!weights) return null;

  const scores = {};

  // Price: lower asking vs estimated = better
  if (property.score?.price_deviation_pct != null) {
    scores.price = Math.max(0, Math.min(100, 50 + property.score.price_deviation_pct));
  }

  // Yield
  if (property.score?.gross_yield_pct != null) {
    scores.yield = Math.min(100, (property.score.gross_yield_pct / 12) * 100);
  }

  // Crime: Low = 100, High = 0
  const crimeBands = { 'Low': 100, 'Below Average': 75, 'Average': 50, 'Above Average': 25, 'High': 0 };
  if (property.crime_rate_band) {
    scores.crime = crimeBands[property.crime_rate_band] ?? 50;
  }

  // Broadband: gigabit %
  if (property.broadband_gigabit_pct != null) {
    scores.broadband = property.broadband_gigabit_pct;
  }

  // Schools: closer = better (max 5mi, 0mi = 100)
  if (property.nearest_primary_distance_mi != null) {
    scores.schools = Math.max(0, 100 - (property.nearest_primary_distance_mi / 5) * 100);
  }

  // Transport: closer station = better
  if (property.nearest_station_distance_mi != null) {
    scores.transport = Math.max(0, 100 - (property.nearest_station_distance_mi / 5) * 100);
  }

  // Flood: not in flood zone = 100
  scores.flood = property.in_flood_zone ? 0 : 100;

  // EPC: A=100, G=0
  const epcScores = { 'A': 100, 'B': 85, 'C': 70, 'D': 55, 'E': 40, 'F': 20, 'G': 0 };
  if (property.epc_energy_rating) {
    scores.epc = epcScores[property.epc_energy_rating] ?? 50;
  }

  // Planning: no restrictions = 100
  const planningPenalties = [
    property.in_conservation_area, property.has_article4,
    property.in_green_belt, property.is_listed_building,
  ].filter(Boolean).length;
  scores.planning = Math.max(0, 100 - planningPenalties * 25);

  // Deprivation: higher rank (less deprived) = better. Max rank ~32844
  if (property.imd_rank) {
    scores.deprivation = (property.imd_rank / 32844) * 100;
  }

  // Weighted average
  let totalWeighted = 0;
  let totalWeight = 0;
  for (const [key, weight] of Object.entries(weights)) {
    if (weight > 0 && scores[key] != null) {
      totalWeighted += scores[key] * weight;
      totalWeight += weight;
    }
  }

  return totalWeight > 0 ? Math.round(totalWeighted / totalWeight) : null;
}
