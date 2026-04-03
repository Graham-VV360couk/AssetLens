import React, { useEffect, useState, useCallback } from 'react';
import { Bell, Settings, Star, TrendingUp, SlidersHorizontal, Save } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import PropertyCard from '../components/ui/PropertyCard';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { formatCurrency } from '../utils/formatters';

const FREQUENCY_OPTIONS = [
  { value: 'immediate', label: 'Immediately' },
  { value: 'daily', label: 'Daily digest' },
  { value: 'weekly', label: 'Weekly summary' },
];

function MatchBadge({ pct }) {
  const color = pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-blue-500' : 'bg-amber-500';
  return (
    <span className={`${color} text-white text-xs font-bold px-2 py-0.5 rounded-full`}>
      {pct}% match
    </span>
  );
}

export default function Alerts() {
  const [matches, setMatches] = useState([]);
  const [prefs, setPrefs] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const token = localStorage.getItem('assetlens_token');
  const headers = token ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } : {};

  // Load preferences and matches
  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    Promise.all([
      fetch('/api/alerts/preferences', { headers }).then(r => r.ok ? r.json() : null),
      fetch('/api/alerts/matches', { headers }).then(r => r.ok ? r.json() : []),
    ])
      .then(([prefData, matchData]) => {
        if (prefData) setPrefs(prefData);
        setMatches(matchData || []);
      })
      .catch(e => toast.error(e.message))
      .finally(() => setLoading(false));
  }, []);

  const savePrefs = useCallback(async () => {
    if (!prefs) return;
    setSaving(true);
    try {
      const res = await fetch('/api/alerts/preferences', {
        method: 'PUT',
        headers,
        body: JSON.stringify(prefs),
      });
      if (res.ok) {
        const updated = await res.json();
        setPrefs(updated);
        toast.success('Alert preferences saved');
        // Refresh matches with new prefs
        const matchRes = await fetch('/api/alerts/matches', { headers });
        if (matchRes.ok) setMatches(await matchRes.json());
      }
    } catch (e) {
      toast.error('Failed to save preferences');
    } finally {
      setSaving(false);
    }
  }, [prefs]);

  if (!token) {
    return (
      <div className="p-6 text-center py-20">
        <Bell size={48} className="text-slate-700 mx-auto mb-3" />
        <p className="text-slate-400">Log in to set up personalised property alerts</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
            <Bell size={20} className="text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Property Alerts</h1>
            <p className="text-slate-400 text-sm">
              Properties matching your preferences
              {prefs && <span className="text-blue-400"> ({prefs.min_match_pct}%+ threshold)</span>}
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 hover:text-white hover:border-slate-600 transition"
        >
          <Settings size={14} />
          Settings
        </button>
      </div>

      {/* Settings panel */}
      <AnimatePresence>
        {showSettings && prefs && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 space-y-4 overflow-hidden"
          >
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <SlidersHorizontal size={14} className="text-blue-400" />
              Alert Settings
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Active toggle */}
              <div>
                <label className="text-xs text-slate-500 block mb-1">Alerts active</label>
                <button
                  onClick={() => setPrefs(p => ({ ...p, is_active: !p.is_active }))}
                  className={`w-full px-4 py-2 rounded-lg text-sm font-medium transition ${
                    prefs.is_active
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-slate-700 text-slate-500 border border-slate-600'
                  }`}
                >
                  {prefs.is_active ? 'ON' : 'OFF'}
                </button>
              </div>

              {/* Min match % */}
              <div>
                <label className="text-xs text-slate-500 block mb-1">
                  Min match: {prefs.min_match_pct}%
                </label>
                <input
                  type="range"
                  min={30}
                  max={95}
                  step={5}
                  value={prefs.min_match_pct}
                  onChange={e => setPrefs(p => ({ ...p, min_match_pct: parseInt(e.target.value) }))}
                  className="w-full accent-blue-500"
                  style={{
                    background: `linear-gradient(to right, #3b82f6 ${(prefs.min_match_pct - 30) / 65 * 100}%, #334155 ${(prefs.min_match_pct - 30) / 65 * 100}%)`,
                  }}
                />
              </div>

              {/* Frequency */}
              <div>
                <label className="text-xs text-slate-500 block mb-1">Frequency</label>
                <select
                  value={prefs.alert_frequency}
                  onChange={e => setPrefs(p => ({ ...p, alert_frequency: e.target.value }))}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white"
                >
                  {FREQUENCY_OPTIONS.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>

              {/* Max price */}
              <div>
                <label className="text-xs text-slate-500 block mb-1">Max price</label>
                <input
                  type="number"
                  value={prefs.max_price || ''}
                  onChange={e => setPrefs(p => ({ ...p, max_price: e.target.value ? parseInt(e.target.value) : null }))}
                  placeholder="No limit"
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white placeholder-slate-500"
                />
              </div>

              {/* Min beds */}
              <div>
                <label className="text-xs text-slate-500 block mb-1">Min bedrooms</label>
                <select
                  value={prefs.min_beds || ''}
                  onChange={e => setPrefs(p => ({ ...p, min_beds: e.target.value ? parseInt(e.target.value) : null }))}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white"
                >
                  <option value="">Any</option>
                  {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n}+</option>)}
                </select>
              </div>

              {/* Location filter */}
              <div className="sm:col-span-2">
                <label className="text-xs text-slate-500 block mb-1">Location (postcodes, comma-separated)</label>
                <input
                  type="text"
                  value={prefs.location_filter || ''}
                  onChange={e => setPrefs(p => ({ ...p, location_filter: e.target.value || null }))}
                  placeholder="e.g. WD25, NG1, LS6"
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white placeholder-slate-500"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={savePrefs}
                disabled={saving}
                className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 text-sm font-medium"
              >
                <Save size={14} />
                {saving ? 'Saving...' : 'Save Preferences'}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {loading ? (
        <div className="flex justify-center py-20">
          <LoadingSpinner size={36} className="text-blue-500" />
        </div>
      ) : (
        <>
          {/* Summary */}
          <div className="flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-xl px-4 py-2.5">
            <Star size={14} className="text-blue-400" />
            <span className="text-blue-300 text-sm font-medium">
              {matches.length} propert{matches.length !== 1 ? 'ies' : 'y'} matching your criteria
            </span>
          </div>

          {/* Matched properties */}
          <div className="space-y-3">
            {matches.length === 0 ? (
              <div className="text-center py-16">
                <Bell size={48} className="text-slate-700 mx-auto mb-3" />
                <p className="text-slate-500">No matches yet</p>
                <p className="text-slate-600 text-sm mt-1">
                  Adjust your scoring sliders on the Properties page, then set your threshold here
                </p>
              </div>
            ) : (
              matches.map((m, i) => (
                <motion.a
                  key={m.id}
                  href={`/properties/${m.id}`}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="flex items-center gap-4 bg-slate-900 border border-slate-800 rounded-xl p-4 hover:border-slate-600 transition cursor-pointer"
                >
                  {m.image_url && (
                    <div className="w-20 h-20 rounded-lg overflow-hidden bg-slate-800 flex-shrink-0">
                      <img src={m.image_url} alt="" className="w-full h-full object-cover" onError={e => e.target.style.display = 'none'} />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <MatchBadge pct={m.match_pct} />
                      <span className="text-emerald-400 font-bold">{m.asking_price ? formatCurrency(m.asking_price) : '—'}</span>
                    </div>
                    <div className="text-sm text-white font-medium truncate">{m.address || 'Address not available'}</div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {m.postcode} · {m.property_type} · {m.bedrooms ? `${m.bedrooms} bed` : ''}
                    </div>
                    {m.match_reasons?.length > 0 && (
                      <div className="flex gap-1 mt-1.5 flex-wrap">
                        {m.match_reasons.map((r, j) => (
                          <span key={j} className="text-[10px] px-1.5 py-0.5 bg-slate-800 text-slate-400 rounded">
                            {r}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </motion.a>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
