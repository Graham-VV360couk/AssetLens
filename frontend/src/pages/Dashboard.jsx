import React, { useEffect, useState, useRef } from 'react';
import { Building2, TrendingUp, Star, Eye, Activity, AlertTriangle, RefreshCw,
  Zap, Brain, MapPin, Image, CheckCircle2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import StatCard from '../components/ui/StatCard';
import ScoreDistributionChart from '../components/charts/ScoreDistributionChart';
import PropertyCard from '../components/ui/PropertyCard';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { dashboardApi } from '../services/api';

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: i => ({ opacity: 1, y: 0, transition: { delay: i * 0.08, duration: 0.4, ease: 'easeOut' } }),
};

// Pipeline stage labels and colours
const STAGES = [
  { key: 'retrieving',   label: 'Retrieving',          color: 'text-sky-400',    bg: 'bg-sky-500' },
  { key: 'scoring',      label: 'LR Scoring',          color: 'text-amber-400',  bg: 'bg-amber-500' },
  { key: 'ai_analysis',  label: 'AI Analysis',         color: 'text-violet-400', bg: 'bg-violet-500' },
  { key: 'pd_enrichment',label: 'PropertyData Enrich', color: 'text-blue-400',   bg: 'bg-blue-500' },
  { key: 'done',         label: 'Complete',            color: 'text-emerald-400',bg: 'bg-emerald-500' },
];

function ScrapeProgressWidget({ progress }) {
  if (!progress) return null;
  const { running, source_name, stage, counts, started_at } = progress;
  if (!running && stage !== 'done' && stage !== 'error') return null;

  const stageIdx = STAGES.findIndex(s => s.key === stage);
  const c = counts || {};

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -12 }}
        className={`border rounded-2xl p-5 ${
          running
            ? 'bg-slate-900 border-slate-700'
            : stage === 'done'
            ? 'bg-emerald-950/30 border-emerald-800/40'
            : 'bg-red-950/30 border-red-800/40'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            {running
              ? <RefreshCw size={14} className="text-sky-400 animate-spin" />
              : stage === 'done'
              ? <CheckCircle2 size={14} className="text-emerald-400" />
              : <AlertTriangle size={14} className="text-red-400" />}
            <span className="text-white text-sm font-semibold">
              {running ? `Scraping: ${source_name}` : stage === 'done' ? `Completed: ${source_name}` : 'Scrape Error'}
            </span>
            {started_at && (
              <span className="text-slate-500 text-xs">
                {new Date(started_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>
        </div>

        {/* Stage progress bar */}
        <div className="flex items-center gap-1 mb-4">
          {STAGES.filter(s => s.key !== 'error').map((s, i) => {
            const done = stageIdx > i || stage === 'done';
            const active = stageIdx === i && running;
            return (
              <React.Fragment key={s.key}>
                <div className="flex flex-col items-center gap-1 flex-1">
                  <div className={`h-1.5 w-full rounded-full transition-all duration-500 ${
                    done ? s.bg : active ? `${s.bg} opacity-60 animate-pulse` : 'bg-slate-800'
                  }`} />
                  <span className={`text-[9px] hidden sm:block ${done || active ? s.color : 'text-slate-600'}`}>
                    {s.label}
                  </span>
                </div>
                {i < STAGES.length - 2 && <div className="w-1 h-px bg-slate-700 shrink-0" />}
              </React.Fragment>
            );
          })}
        </div>

        {/* Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Found', value: c.scraped ?? 0, sub: `${c.new ?? 0} new · ${c.merged ?? 0} merged` },
            { label: 'LR Scored', value: c.scored ?? 0 },
            { label: 'AI Analysis', value: `${c.ai_done ?? 0}/${c.ai_total ?? 0}`,
              active: stage === 'ai_analysis' && running },
            { label: 'PD Enriched', value: `${c.pd_done ?? 0}/${c.pd_total ?? 0}`,
              active: stage === 'pd_enrichment' && running },
          ].map(item => (
            <div key={item.label} className={`rounded-xl p-3 ${item.active ? 'bg-slate-700/60' : 'bg-slate-800/50'}`}>
              <div className="text-slate-500 text-xs mb-0.5">{item.label}</div>
              <div className={`font-bold text-sm ${item.active ? 'text-white' : 'text-slate-300'}`}>
                {item.value}
              </div>
              {item.sub && <div className="text-slate-600 text-[10px] mt-0.5">{item.sub}</div>}
            </div>
          ))}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [jobRunning, setJobRunning] = useState({});
  const [scrapeProgress, setScrapeProgress] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    dashboardApi.getStats()
      .then(setStats)
      .catch(e => setError(e.message || 'Failed to load dashboard stats'))
      .finally(() => setLoading(false));

    // Poll scrape status every 4 seconds
    const poll = async () => {
      try {
        const r = await fetch('/api/scrapers/status');
        if (r.ok) setScrapeProgress(await r.json());
      } catch { /* silent */ }
    };
    poll();
    pollRef.current = setInterval(poll, 4000);
    return () => clearInterval(pollRef.current);
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

      {/* Live scrape progress — only shown when running or just finished */}
      {(scrapeProgress?.running || scrapeProgress?.stage === 'done') && (
        <ScrapeProgressWidget progress={scrapeProgress} />
      )}

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: 'Active Properties',
            value: stats?.total_active?.toLocaleString() ?? '—',
            icon: Building2, color: 'blue',
            sub: `${stats?.total_reviewed?.toLocaleString() ?? 0} reviewed`,
          },
          {
            label: 'High-Value Deals',
            value: stats?.high_value_count?.toLocaleString() ?? '—',
            icon: Star, color: 'emerald',
            sub: 'Score ≥ 60',
          },
          {
            label: 'Avg. Score',
            value: stats?.avg_investment_score != null ? Math.round(stats.avg_investment_score) : '—',
            icon: Activity, color: 'amber',
            sub: 'Across portfolio',
          },
          {
            label: 'Avg. Yield',
            value: stats?.avg_yield != null ? `${Number(stats.avg_yield).toFixed(1)}%` : '—',
            icon: TrendingUp, color: 'emerald',
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
        {/* Score distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-5"
        >
          <h2 className="text-white font-semibold mb-1">Score Distribution</h2>
          <p className="text-slate-500 text-xs mb-3">
            How properties spread across investment score bands
          </p>
          <ScoreDistributionChart data={stats?.score_distribution} />
          <div className="mt-3 grid grid-cols-3 gap-2 text-[10px]">
            {[
              { label: '< 40', desc: 'Neutral / weak', color: 'text-orange-400' },
              { label: '40–60', desc: 'Developing', color: 'text-slate-400' },
              { label: '≥ 60', desc: 'High potential', color: 'text-emerald-400' },
            ].map(b => (
              <div key={b.label} className="text-center">
                <div className={`font-semibold ${b.color}`}>{b.label}</div>
                <div className="text-slate-600">{b.desc}</div>
              </div>
            ))}
          </div>
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
              .slice(0, 6)
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
                      <div className="bg-emerald-500 h-1.5 rounded-full transition-all duration-700"
                        style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
          </div>
        </motion.div>

        {/* Batch actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.4 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col gap-3"
        >
          <h2 className="text-white font-semibold">Quick Actions</h2>

          <a href="/properties?min_score=60&sort_by=investment_score"
            className="flex items-center gap-3 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl hover:bg-emerald-500/20 transition-colors">
            <Star size={16} className="text-emerald-400 shrink-0" />
            <div>
              <div className="text-emerald-300 text-sm font-medium">Top Deals</div>
              <div className="text-slate-500 text-xs">{stats?.high_value_count ?? 0} score ≥ 60</div>
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
            <div className="text-slate-500 text-xs font-medium uppercase tracking-wider mb-1">Batch Jobs</div>

            {[
              { key: 'rescore',   url: '/api/scoring/run',                               label: 'Re-score All',           sub: 'Refresh LR scores for all active properties', icon: RefreshCw,  cls: 'bg-slate-800 hover:bg-slate-700 border-slate-700',          iconCls: 'text-slate-400' },
              { key: 'enrich',    url: '/api/scoring/enrich?min_score=0&limit=50',        label: 'Enrich with PropertyData',sub: 'AVM + rental + flood risk (~150 credits)',    icon: Zap,        cls: 'bg-blue-900/20 hover:bg-blue-900/30 border-blue-800/40',    iconCls: 'text-blue-400' },
              { key: 'ai',        url: '/api/ai/analyse/batch?limit=20&min_score=38',     label: 'AI Analyse Properties',  sub: 'Claude verdict for top 20 unanalysed',        icon: Brain,      cls: 'bg-violet-900/20 hover:bg-violet-900/30 border-violet-800/40', iconCls: 'text-violet-400' },
              { key: 'postcodes', url: '/api/properties/fix-postcodes?limit=20',          label: 'Fix Missing Postcodes',  sub: 'AI infers postcodes for untagged properties', icon: MapPin,     cls: 'bg-teal-900/20 hover:bg-teal-900/30 border-teal-800/40',    iconCls: 'text-teal-400' },
              { key: 'images',    url: '/api/properties/fetch-images?limit=30',           label: 'Fetch Property Images',  sub: 'Backfill images for existing properties',     icon: Image,      cls: 'bg-pink-900/20 hover:bg-pink-900/30 border-pink-800/40',    iconCls: 'text-pink-400' },
            ].map(({ key, url, label, sub, icon: Icon, cls, iconCls }) => (
              <button key={key}
                onClick={() => runJob(key, url, label)}
                disabled={jobRunning[key]}
                className={`w-full flex items-center gap-3 p-3 border rounded-xl transition-colors disabled:opacity-50 text-left ${cls}`}
              >
                <Icon size={16} className={`${iconCls} shrink-0 ${jobRunning[key] ? 'animate-pulse' : ''}`} />
                <div>
                  <div className={`text-sm font-medium ${iconCls.replace('text-', 'text-').replace('-400', '-300')}`}>{label}</div>
                  <div className="text-slate-500 text-xs">{sub}</div>
                </div>
              </button>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Properties scoring ≥ 60 */}
      {stats?.recent_high_value?.length > 0 ? (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-white font-semibold">
                Investment Properties
                <span className="ml-2 text-sm font-normal text-slate-500">
                  {stats.high_value_count} scoring ≥ 60
                </span>
              </h2>
              <p className="text-slate-500 text-xs mt-0.5">Sorted by score — best opportunities first</p>
            </div>
            <a href="/properties?min_score=60&sort_by=investment_score"
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
              View all in table →
            </a>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {stats.recent_high_value.map((prop, i) => (
              <motion.div key={prop.id} custom={i} initial="hidden" animate="visible" variants={cardVariants}>
                <PropertyCard property={prop} />
              </motion.div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center py-12 text-slate-600">
          <p className="text-sm">No properties scoring ≥ 60 yet.</p>
          <p className="text-xs mt-1">Run a scrape or use the batch actions above to enrich existing properties.</p>
        </div>
      )}
    </div>
  );
}
