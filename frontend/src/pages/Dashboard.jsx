import React, { useEffect, useState } from 'react';
import { Building2, TrendingUp, Star, Eye, Activity, AlertTriangle, RefreshCw, Zap, Brain, MapPin } from 'lucide-react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import StatCard from '../components/ui/StatCard';
import PortfolioDonut from '../components/charts/PortfolioDonut';
import PropertyCard from '../components/ui/PropertyCard';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { propertiesApi, dashboardApi } from '../services/api';

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: i => ({ opacity: 1, y: 0, transition: { delay: i * 0.08, duration: 0.4, ease: 'easeOut' } }),
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [jobRunning, setJobRunning] = useState({});

  useEffect(() => {
    dashboardApi.getStats()
      .then(setStats)
      .catch(e => setError(e.message || 'Failed to load dashboard stats'))
      .finally(() => setLoading(false));
  }, []);

  const runJob = async (key, url, label) => {
    setJobRunning(j => ({ ...j, [key]: true }));
    try {
      const r = await fetch(url, { method: 'POST' });
      const d = await r.json();
      toast.success(d.message || `${label} started`);
    } catch (e) {
      toast.error(`${label} failed: ${e.message}`);
    } finally {
      setJobRunning(j => ({ ...j, [key]: false }));
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center h-full min-h-96">
      <LoadingSpinner size={40} className="text-emerald-500" />
    </div>
  );

  if (error) return (
    <div className="p-8 text-center">
      <AlertTriangle size={40} className="text-amber-400 mx-auto mb-3" />
      <p className="text-slate-400">{error}</p>
    </div>
  );

  return (
    <div className="p-6 space-y-6">
      {/* Page title */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-slate-400 text-sm mt-1">UK property investment intelligence overview</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: 'Active Properties',
            value: stats?.total_active?.toLocaleString() ?? '—',
            icon: Building2,
            color: 'blue',
            sub: `${stats?.total_reviewed?.toLocaleString() ?? 0} reviewed`,
          },
          {
            label: 'High-Value Deals',
            value: stats?.high_value_count?.toLocaleString() ?? '—',
            icon: Star,
            color: 'emerald',
            sub: 'Score ≥ 70',
          },
          {
            label: 'Avg. Score',
            value: stats?.avg_investment_score != null
              ? Math.round(stats.avg_investment_score)
              : '—',
            icon: Activity,
            color: 'amber',
            sub: 'Across portfolio',
          },
          {
            label: 'Avg. Yield',
            value: stats?.avg_yield != null
              ? `${Number(stats.avg_yield).toFixed(1)}%`
              : '—',
            icon: TrendingUp,
            color: 'emerald',
            sub: 'Gross rental yield',
          },
        ].map((s, i) => (
          <motion.div key={s.label} custom={i} initial="hidden" animate="visible" variants={cardVariants}>
            <StatCard {...s} className="h-full" />
          </motion.div>
        ))}
      </div>

      {/* Middle row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Portfolio breakdown */}
        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-5"
        >
          <h2 className="text-white font-semibold mb-1">Price Band Breakdown</h2>
          <p className="text-slate-500 text-xs mb-4">Distribution by investment value</p>
          <PortfolioDonut data={stats?.by_price_band} />
        </motion.div>

        {/* Property type breakdown */}
        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, duration: 0.4 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-5"
        >
          <h2 className="text-white font-semibold mb-1">By Property Type</h2>
          <p className="text-slate-500 text-xs mb-4">Active listings distribution</p>
          <div className="space-y-3 mt-2">
            {stats?.by_property_type && Object.entries(stats.by_property_type)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 5)
              .map(([type, count]) => {
                const total = Object.values(stats.by_property_type).reduce((a, b) => a + b, 0);
                const pct = total > 0 ? (count / total) * 100 : 0;
                return (
                  <div key={type}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-300 capitalize">{type || 'Unknown'}</span>
                      <span className="text-slate-500">{count.toLocaleString()}</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-1.5">
                      <div
                        className="bg-emerald-500 h-1.5 rounded-full transition-all duration-700"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        </motion.div>

        {/* Quick actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.4 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col gap-3"
        >
          <h2 className="text-white font-semibold">Quick Actions</h2>

          <a href="/properties?min_score=70&sort_by=investment_score"
            className="flex items-center gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl hover:bg-emerald-500/20 transition-colors">
            <Star size={16} className="text-emerald-400 shrink-0" />
            <div>
              <div className="text-emerald-300 text-sm font-medium">Top Deals</div>
              <div className="text-slate-500 text-xs">{stats?.high_value_count ?? 0} score ≥ 70</div>
            </div>
          </a>

          <a href="/properties?is_reviewed=false&sort_by=investment_score"
            className="flex items-center gap-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl hover:bg-amber-500/20 transition-colors">
            <Eye size={16} className="text-amber-400 shrink-0" />
            <div>
              <div className="text-amber-300 text-sm font-medium">Unreviewed</div>
              <div className="text-slate-500 text-xs">
                {stats ? (stats.total_active - (stats.total_reviewed ?? 0)).toLocaleString() : '—'} awaiting review
              </div>
            </div>
          </a>

          <div className="border-t border-slate-800 pt-2 space-y-2">
            <div className="text-slate-500 text-xs font-medium uppercase tracking-wider mb-1">Batch Analysis</div>

            <button
              onClick={() => runJob('rescore', '/api/scoring/run', 'Re-score')}
              disabled={jobRunning.rescore}
              className="w-full flex items-center gap-3 p-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl transition-colors disabled:opacity-50 text-left"
            >
              {jobRunning.rescore
                ? <RefreshCw size={16} className="text-slate-400 animate-spin shrink-0" />
                : <RefreshCw size={16} className="text-slate-400 shrink-0" />}
              <div>
                <div className="text-slate-300 text-sm font-medium">Re-score All</div>
                <div className="text-slate-500 text-xs">Recalculate scores using latest LR data</div>
              </div>
            </button>

            <button
              onClick={() => runJob('enrich', '/api/scoring/enrich?min_score=0&limit=50', 'PropertyData enrichment')}
              disabled={jobRunning.enrich}
              className="w-full flex items-center gap-3 p-3 bg-blue-900/20 hover:bg-blue-900/30 border border-blue-800/40 rounded-xl transition-colors disabled:opacity-50 text-left"
            >
              {jobRunning.enrich
                ? <Zap size={16} className="text-blue-400 animate-pulse shrink-0" />
                : <Zap size={16} className="text-blue-400 shrink-0" />}
              <div>
                <div className="text-blue-300 text-sm font-medium">Enrich with PropertyData</div>
                <div className="text-slate-500 text-xs">AVM + rental + flood risk (50 properties, ~150 credits)</div>
              </div>
            </button>

            <button
              onClick={() => runJob('ai', '/api/ai/analyse/batch?limit=20&min_score=50', 'AI analysis')}
              disabled={jobRunning.ai}
              className="w-full flex items-center gap-3 p-3 bg-violet-900/20 hover:bg-violet-900/30 border border-violet-800/40 rounded-xl transition-colors disabled:opacity-50 text-left"
            >
              {jobRunning.ai
                ? <Brain size={16} className="text-violet-400 animate-pulse shrink-0" />
                : <Brain size={16} className="text-violet-400 shrink-0" />}
              <div>
                <div className="text-violet-300 text-sm font-medium">AI Analyse Properties</div>
                <div className="text-slate-500 text-xs">Claude verdict for top 20 unanalysed (score ≥ 50)</div>
              </div>
            </button>

            <button
              onClick={() => runJob('postcodes', '/api/properties/fix-postcodes?limit=20', 'Postcode fix')}
              disabled={jobRunning.postcodes}
              className="w-full flex items-center gap-3 p-3 bg-teal-900/20 hover:bg-teal-900/30 border border-teal-800/40 rounded-xl transition-colors disabled:opacity-50 text-left"
            >
              {jobRunning.postcodes
                ? <MapPin size={16} className="text-teal-400 animate-pulse shrink-0" />
                : <MapPin size={16} className="text-teal-400 shrink-0" />}
              <div>
                <div className="text-teal-300 text-sm font-medium">Fix Missing Postcodes</div>
                <div className="text-slate-500 text-xs">AI infers postcodes for up to 20 untagged properties</div>
              </div>
            </button>
          </div>
        </motion.div>
      </div>

      {/* Recent high-value */}
      {stats?.recent_high_value?.length > 0 && (
        <div>
          <h2 className="text-white font-semibold mb-4">Top Investment Opportunities</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {stats.recent_high_value.map((prop, i) => (
              <motion.div key={prop.id} custom={i} initial="hidden" animate="visible" variants={cardVariants}>
                <PropertyCard property={prop} />
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
