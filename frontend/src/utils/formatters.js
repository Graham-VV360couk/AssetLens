export const formatCurrency = (value, compact = false) => {
  if (value == null) return '—';
  if (compact && value >= 1_000_000) {
    const m = value / 1_000_000;
    // Show 2dp only if needed (e.g. £1.25M), otherwise 1dp or whole
    const formatted = m % 1 === 0 ? m.toFixed(0) : m.toFixed(2).replace(/\.?0+$/, '');
    return `£${formatted}M`;
  }
  if (compact && value >= 1_000) return `£${(value / 1_000).toFixed(0)}K`;
  return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(value);
};

export const formatPct = (value, decimals = 1) => {
  if (value == null) return '—';
  return `${(value * 100).toFixed(decimals)}%`;
};

export const formatYield = (value) => {
  if (value == null) return '—';
  return `${Number(value).toFixed(2)}%`;
};

export const formatScore = (value) => {
  if (value == null) return '—';
  return Math.round(value);
};

export const scoreColor = (score) => {
  if (score == null) return '#64748b';
  if (score >= 70) return '#10b981';
  if (score >= 50) return '#f59e0b';
  if (score >= 30) return '#f97316';
  return '#ef4444';
};

export const bandColor = (band) => {
  const map = {
    brilliant: '#10b981',
    good: '#22c55e',
    fair: '#f59e0b',
    bad: '#ef4444',
    unknown: '#64748b',
  };
  return map[band] || '#64748b';
};

export const bandLabel = (band) => {
  const map = {
    brilliant: 'Brilliant Deal',
    good: 'Good Value',
    fair: 'Fair Price',
    bad: 'Overpriced',
    unknown: 'Unscored',
  };
  return map[band] || band;
};

export const propertyTypeIcon = (type) => {
  const map = {
    detached: '🏡',
    'semi-detached': '🏠',
    terraced: '🏘️',
    flat: '🏢',
    unknown: '🏗️',
  };
  return map[type] || '🏗️';
};
