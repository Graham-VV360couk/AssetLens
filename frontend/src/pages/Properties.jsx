import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Building2, AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react';
import PropertyCard from '../components/ui/PropertyCard';
import PropertyFiltersBar from '../components/filters/PropertyFilters';
import ScoringSliders from '../components/filters/ScoringSliders';
import LoadingSpinner from '../components/ui/LoadingSpinner';

const DEFAULT_FILTERS = { sort_by: 'investment_score', sort_dir: 'desc', page: 1, page_size: 18 };

export default function Properties() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-white">Properties</h1>
        <p className="text-slate-400 text-sm mt-1">
          {data ? `${data.total.toLocaleString()} properties found` : 'Loading...'}
        </p>
      </div>

      <PropertyFiltersBar
        filters={filters}
        onChange={setFilters}
        onReset={() => setFilters(DEFAULT_FILTERS)}
      />

      <ScoringSliders onWeightsChange={(w) => {
        // Store weights for future use — scoring will be applied client-side
        // once property data includes enrichment fields
        window.__assetlens_weights = w;
      }} />

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
              key={JSON.stringify(filters)}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
            >
              {data.items.length === 0 ? (
                <div className="col-span-3 text-center py-20">
                  <Building2 size={48} className="text-slate-700 mx-auto mb-3" />
                  <p className="text-slate-500">No properties match your filters</p>
                </div>
              ) : (
                data.items.map((prop, i) => (
                  <motion.div
                    key={prop.id}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04, duration: 0.3 }}
                  >
                    <PropertyCard property={prop} />
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
