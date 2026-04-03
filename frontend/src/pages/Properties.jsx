import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Building2, AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react';
import PropertyCard from '../components/ui/PropertyCard';
import PropertyFiltersBar from '../components/filters/PropertyFilters';
import ScoringSliders, { computeWeightedScore } from '../components/filters/ScoringSliders';
import LoadingSpinner from '../components/ui/LoadingSpinner';

const DEFAULT_FILTERS = { sort_by: 'investment_score', sort_dir: 'desc', page: 1, page_size: 18 };
const SAVE_DEBOUNCE_MS = 800;
const LS_KEY = 'assetlens_scoring_weights';

function loadLocalWeights() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

export default function Properties() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [weights, setWeights] = useState(null);
  const [savedWeights, setSavedWeights] = useState(null);
  const [usePersonalScore, setUsePersonalScore] = useState(false);
  const saveTimerRef = useRef(null);

  // Load saved weights on mount
  useEffect(() => {
    const token = localStorage.getItem('assetlens_token');
    if (token) {
      fetch('/api/account/profile', {
        headers: { 'Authorization': `Bearer ${token}` },
      })
        .then(r => r.ok ? r.json() : null)
        .then(profile => {
          if (profile?.scoring_preferences) {
            try {
              const parsed = JSON.parse(profile.scoring_preferences);
              setSavedWeights(parsed);
              setWeights(parsed);
              setUsePersonalScore(true);
            } catch {}
          }
        })
        .catch(() => {});
    } else {
      const local = loadLocalWeights();
      if (local) {
        setSavedWeights(local);
        setWeights(local);
        setUsePersonalScore(true);
      }
    }
  }, []);

  const fetchProperties = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => { if (v != null) params.set(k, v); });
    fetch(`/api/properties?${params}`)
      .then(r => r.json())
      .then(d => { setData(d); setError(null); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => { fetchProperties(); }, [fetchProperties]);

  // Re-sort properties client-side when weights change
  const sortedItems = useMemo(() => {
    if (!data?.items) return [];
    if (!usePersonalScore || !weights) return data.items;

    return [...data.items]
      .map(prop => ({
        ...prop,
        personalScore: computeWeightedScore(prop, weights),
      }))
      .sort((a, b) => (b.personalScore ?? -1) - (a.personalScore ?? -1));
  }, [data?.items, weights, usePersonalScore]);

  // Compute match stats for live counter
  const matchStats = useMemo(() => {
    if (!data?.items || !weights || !usePersonalScore) return null;
    const scores = data.items
      .map(p => computeWeightedScore(p, weights))
      .filter(s => s !== null);
    if (scores.length === 0) return null;
    const above50 = scores.filter(s => s >= 50).length;
    const avg = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
    return { above50, total: scores.length, avg };
  }, [data?.items, weights, usePersonalScore]);

  const handleWeightsChange = useCallback((w) => {
    setWeights(w);
    setUsePersonalScore(true);

    // Debounced save
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      // Always save to localStorage
      localStorage.setItem(LS_KEY, JSON.stringify(w));

      // Save to profile if logged in
      const token = localStorage.getItem('assetlens_token');
      if (token) {
        fetch('/api/account/profile', {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ scoring_preferences: JSON.stringify(w) }),
        }).catch(() => {});
      }
    }, SAVE_DEBOUNCE_MS);
  }, []);

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-white">Properties</h1>
        <p className="text-slate-400 text-sm mt-1">
          {data ? `${data.total.toLocaleString()} properties found` : 'Loading...'}
          {usePersonalScore && weights && (
            <span className="ml-2 text-blue-400">
              — sorted by your preferences
            </span>
          )}
        </p>
      </div>

      <PropertyFiltersBar
        filters={filters}
        onChange={(f) => { setFilters(f); setUsePersonalScore(false); }}
        onReset={() => { setFilters(DEFAULT_FILTERS); setUsePersonalScore(false); }}
      />

      <ScoringSliders
        onWeightsChange={handleWeightsChange}
        initialWeights={savedWeights}
        matchStats={matchStats}
      />

      {loading && (
        <div className="flex items-center justify-center py-24">
          <LoadingSpinner size={40} className="text-emerald-500" />
        </div>
      )}

      {error && !loading && (
        <div className="flex items-center gap-3 p-5 bg-red-500/10 border border-red-500/20 rounded-2xl">
          <AlertTriangle size={20} className="text-red-400" />
          <span className="text-red-300 text-sm">{error}</span>
        </div>
      )}

      {!loading && !error && data && (
        <>
          <AnimatePresence mode="wait">
            <motion.div
              key={JSON.stringify(filters) + String(usePersonalScore)}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
            >
              {sortedItems.length === 0 ? (
                <div className="col-span-3 text-center py-20">
                  <Building2 size={48} className="text-slate-700 mx-auto mb-3" />
                  <p className="text-slate-500">No properties match your filters</p>
                </div>
              ) : (
                sortedItems.map((prop, i) => (
                  <motion.div
                    key={prop.id}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04, duration: 0.3 }}
                  >
                    <PropertyCard property={prop} personalScore={prop.personalScore} />
                  </motion.div>
                ))
              )}
            </motion.div>
          </AnimatePresence>

          {/* Pagination */}
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-3 pt-4">
              <button
                disabled={filters.page <= 1}
                onClick={() => setFilters(f => ({ ...f, page: f.page - 1 }))}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft size={20} />
              </button>
              <span className="text-slate-400 text-sm">
                Page {filters.page} of {data.pages}
              </span>
              <button
                disabled={filters.page >= data.pages}
                onClick={() => setFilters(f => ({ ...f, page: f.page + 1 }))}
                className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight size={20} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
