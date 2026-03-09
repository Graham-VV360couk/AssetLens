import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft, MapPin, Bed, Bath, Square, CheckCircle, Circle,
  ExternalLink, Calendar, Building2, AlertTriangle, Brain,
  ThumbsUp, ThumbsDown, Lightbulb, Play, Droplets, Zap
} from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import ScoreGauge from '../components/ui/ScoreGauge';
import YieldMeter from '../components/ui/YieldMeter';
import PriceBandBadge from '../components/ui/PriceBandBadge';
import SalesHistoryChart from '../components/charts/SalesHistoryChart';
import PriceComparisonChart from '../components/charts/PriceComparisonChart';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { formatCurrency, formatYield, propertyTypeIcon } from '../utils/formatters';

const VERDICT_STYLE = {
  STRONG_BUY: { bg: 'bg-emerald-500/15 border-emerald-500/30', text: 'text-emerald-300', label: 'Strong Buy' },
  BUY:        { bg: 'bg-teal-500/15 border-teal-500/30',       text: 'text-teal-300',    label: 'Buy'        },
  HOLD:       { bg: 'bg-amber-500/15 border-amber-500/30',     text: 'text-amber-300',   label: 'Hold'       },
  AVOID:      { bg: 'bg-red-500/15 border-red-500/30',         text: 'text-red-300',     label: 'Avoid'      },
};

const FLOOD_STYLE = {
  low:       'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  medium:    'text-amber-400 bg-amber-500/10 border-amber-500/30',
  high:      'text-orange-400 bg-orange-500/10 border-orange-500/30',
  'very high': 'text-red-400 bg-red-500/10 border-red-500/30',
};

function PropertyDataPanel({ propertyId, score: initialScore }) {
  const [score, setScore] = useState(initialScore);
  const [loading, setLoading] = useState(false);

  const enrich = async () => {
    setLoading(true);
    try {
      const r = await fetch(`/api/scoring/enrich/${propertyId}`, { method: 'POST' });
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Enrichment failed'); }
      const data = await r.json();
      setScore(s => ({ ...s, ...data }));
      toast.success('PropertyData enrichment complete');
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  const enriched = score?.pd_enriched_at;
  const floodRisk = score?.pd_flood_risk?.toLowerCase();
  const floodStyle = FLOOD_STYLE[floodRisk] || 'text-slate-400 bg-slate-700/30 border-slate-600/30';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.12 }}
      className="bg-slate-900 border border-slate-800 rounded-2xl p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Zap size={16} className="text-blue-400" />
          <h2 className="text-white font-semibold">PropertyData Enrichment</h2>
          {enriched && (
            <span className="text-xs text-slate-500">
              Updated {new Date(enriched).toLocaleDateString('en-GB')}
            </span>
          )}
        </div>
        <button
          onClick={enrich}
          disabled={loading}
          className="flex items-center gap-1.5 text-xs bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 rounded-lg px-3 py-1.5 transition-colors disabled:opacity-50"
        >
          {loading ? <span className="animate-spin">⟳</span> : <Zap size={11} />}
          {enriched ? 'Re-enrich' : 'Enrich (3 credits)'}
        </button>
      </div>

      {!enriched && !loading && (
        <p className="text-slate-600 text-sm py-3 text-center">
          Click "Enrich" to fetch live AVM, rental estimate and flood risk from PropertyData.co.uk.
        </p>
      )}

      {loading && (
        <div className="flex items-center gap-2 text-slate-400 text-sm py-3 justify-center">
          <span className="animate-spin text-blue-400">⟳</span> Fetching from PropertyData…
        </div>
      )}

      {enriched && !loading && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-slate-800/50 rounded-xl p-3">
            <div className="text-slate-500 text-xs mb-1">PD Valuation</div>
            <div className="text-blue-300 font-bold text-sm">
              {score.pd_avm ? formatCurrency(score.pd_avm) : '—'}
            </div>
            {score.pd_avm_lower && score.pd_avm_upper && (
              <div className="text-slate-600 text-xs mt-0.5">
                {formatCurrency(score.pd_avm_lower)} – {formatCurrency(score.pd_avm_upper)}
              </div>
            )}
          </div>
          <div className="bg-slate-800/50 rounded-xl p-3">
            <div className="text-slate-500 text-xs mb-1">PD Rent / mo</div>
            <div className="text-blue-300 font-bold text-sm">
              {score.pd_rental_estimate ? formatCurrency(score.pd_rental_estimate) : '—'}
            </div>
          </div>
          <div className="bg-slate-800/50 rounded-xl p-3">
            <div className="text-slate-500 text-xs mb-1">Flood Risk</div>
            {floodRisk ? (
              <span className={clsx('inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded border capitalize', floodStyle)}>
                <Droplets size={10} /> {floodRisk}
              </span>
            ) : <span className="text-slate-600 text-sm">—</span>}
          </div>
          <div className="bg-slate-800/50 rounded-xl p-3">
            <div className="text-slate-500 text-xs mb-1">Revised Score</div>
            <div className="text-white font-bold text-sm">
              {score.investment_score != null ? `${score.investment_score.toFixed(0)}/100` : '—'}
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}


function AIInsightPanel({ propertyId, insight: initialInsight }) {
  const [insight, setInsight] = useState(initialInsight || null);
  const [loading, setLoading] = useState(false);

  const runAnalysis = async () => {
    setLoading(true);
    try {
      const r = await fetch(`/api/ai/analyse/property/${propertyId}`, { method: 'POST' });
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Analysis failed'); }
      const data = await r.json();
      setInsight({ ...data, positives: JSON.stringify(data.positives || []), risks: JSON.stringify(data.risks || []) });
      toast.success('AI analysis complete');
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  const positives = insight?.positives ? (() => { try { return JSON.parse(insight.positives); } catch { return []; } })() : [];
  const risks     = insight?.risks     ? (() => { try { return JSON.parse(insight.risks);     } catch { return []; } })() : [];
  const vs = insight?.verdict ? VERDICT_STYLE[insight.verdict] : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className="bg-slate-900 border border-slate-800 rounded-2xl p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-violet-400" />
          <h2 className="text-white font-semibold">AI Investment Analysis</h2>
          {vs && (
            <span className={clsx('text-xs font-bold px-2 py-0.5 rounded-full border', vs.bg, vs.text)}>
              {vs.label}
            </span>
          )}
        </div>
        <button
          onClick={runAnalysis}
          disabled={loading}
          className="flex items-center gap-1.5 text-xs bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 border border-violet-500/30 rounded-lg px-3 py-1.5 transition-colors disabled:opacity-50"
        >
          {loading ? <span className="animate-spin">⟳</span> : <Play size={11} />}
          {insight ? 'Re-analyse' : 'Analyse with AI'}
        </button>
      </div>

      {!insight && !loading && (
        <p className="text-slate-600 text-sm py-4 text-center">
          Click "Analyse with AI" to get a Claude-powered investment verdict for this property.
        </p>
      )}

      {loading && (
        <div className="flex items-center gap-2 text-slate-400 text-sm py-4 justify-center">
          <span className="animate-spin text-violet-400">⟳</span> Analysing with Claude…
        </div>
      )}

      {insight && !loading && (
        <div className="space-y-4">
          {/* Confidence */}
          {insight.confidence != null && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              Confidence: <span className="text-slate-300">{Math.round(insight.confidence * 100)}%</span>
              <div className="flex-1 bg-slate-800 rounded-full h-1.5 max-w-[120px]">
                <div className={clsx('h-1.5 rounded-full', vs?.text?.replace('text-', 'bg-') || 'bg-slate-500')}
                  style={{ width: `${Math.round(insight.confidence * 100)}%` }} />
              </div>
            </div>
          )}

          {/* Summary */}
          {insight.summary && (
            <p className="text-slate-300 text-sm leading-relaxed">{insight.summary}</p>
          )}

          {/* Location notes */}
          {insight.location_notes && (
            <div className="bg-slate-800/50 rounded-xl p-3">
              <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1.5 font-medium uppercase tracking-wider">
                <Lightbulb size={11} /> Location Notes
              </div>
              <p className="text-slate-400 text-xs leading-relaxed">{insight.location_notes}</p>
            </div>
          )}

          {/* Positives & Risks */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {positives.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 text-xs text-emerald-400 mb-1.5 font-medium">
                  <ThumbsUp size={11} /> Positives
                </div>
                <ul className="space-y-1">
                  {positives.map((p, i) => (
                    <li key={i} className="text-xs text-slate-400 flex gap-1.5">
                      <span className="text-emerald-600 mt-0.5 shrink-0">✓</span> {p}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {risks.length > 0 && (
              <div>
                <div className="flex items-center gap-1.5 text-xs text-red-400 mb-1.5 font-medium">
                  <ThumbsDown size={11} /> Risks
                </div>
                <ul className="space-y-1">
                  {risks.map((r, i) => (
                    <li key={i} className="text-xs text-slate-400 flex gap-1.5">
                      <span className="text-red-600 mt-0.5 shrink-0">✗</span> {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Footer */}
          {insight.generated_at && (
            <p className="text-slate-700 text-xs border-t border-slate-800 pt-2">
              Analysed {new Date(insight.generated_at).toLocaleString('en-GB')}
              {insight.tokens_used && ` · ${insight.tokens_used.toLocaleString()} tokens`}
            </p>
          )}
        </div>
      )}
    </motion.div>
  );
}

export default function PropertyDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [property, setProperty] = useState(null);
  const [areaData, setAreaData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reviewLoading, setReviewLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`/api/properties/${id}`).then(r => r.json()),
    ])
      .then(([prop]) => {
        setProperty(prop);
        if (prop.postcode) {
          fetch(`/api/areas/${prop.postcode}/trends`)
            .then(r => r.ok ? r.json() : null)
            .then(setAreaData)
            .catch(() => {});
        }
      })
      .catch(e => toast.error(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const toggleReview = async () => {
    setReviewLoading(true);
    try {
      const r = await fetch(`/api/properties/${id}/review`, { method: 'POST' });
      const data = await r.json();
      setProperty(p => ({ ...p, is_reviewed: data.is_reviewed, reviewed_at: data.reviewed_at }));
      toast.success(data.message);
    } catch (e) {
      toast.error('Failed to update review status');
    } finally {
      setReviewLoading(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center min-h-96">
      <LoadingSpinner size={40} className="text-emerald-500" />
    </div>
  );

  if (!property) return (
    <div className="p-8 text-center">
      <AlertTriangle size={40} className="text-amber-400 mx-auto mb-3" />
      <p className="text-slate-400">Property not found</p>
    </div>
  );

  const score = property.score;

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Back + header */}
      <div className="flex items-start gap-4">
        <button
          onClick={() => navigate(-1)}
          className="mt-1 p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-colors"
        >
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center flex-wrap gap-2 mb-2">
            <span className="text-2xl">{propertyTypeIcon(property.property_type)}</span>
            {score && <PriceBandBadge band={score.price_band} />}
            {property.is_reviewed && (
              <span className="inline-flex items-center gap-1.5 text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full">
                <CheckCircle size={13} /> Reviewed
              </span>
            )}
          </div>
          <h1 className="text-xl font-bold text-white leading-snug">{property.address}</h1>
          <div className="flex items-center gap-1.5 mt-1 text-slate-400 text-sm">
            <MapPin size={14} />
            <span>{property.postcode}</span>
            {property.town && <><span>·</span><span>{property.town}</span></>}
            {property.county && <><span>·</span><span>{property.county}</span></>}
          </div>
        </div>
        <button
          onClick={toggleReview}
          disabled={reviewLoading}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
            property.is_reviewed
              ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20'
              : 'bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-700'
          }`}
        >
          {reviewLoading ? <LoadingSpinner size={14} /> : property.is_reviewed ? <CheckCircle size={14} /> : <Circle size={14} />}
          {property.is_reviewed ? 'Reviewed' : 'Mark Reviewed'}
        </button>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: score meters */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-6"
        >
          <h2 className="text-white font-semibold mb-5">Investment Analysis</h2>

          <div className="flex justify-around mb-6">
            <ScoreGauge score={score?.investment_score} size={120} label="Overall Score" />
            <YieldMeter yieldPct={score?.gross_yield_pct} size={100} label="Gross Yield" />
          </div>

          {/* Score breakdown */}
          {score && (
            <div className="space-y-3 border-t border-slate-800 pt-4">
              {[
                { label: 'Price Score', value: score.price_score, max: 40, color: '#10b981' },
                { label: 'Yield Score', value: score.yield_score, max: 30, color: '#22c55e' },
                { label: 'Area Trend', value: score.area_trend_score, max: 20, color: '#f59e0b' },
                { label: 'HMO Score', value: score.hmo_opportunity_score, max: 10, color: '#a78bfa' },
              ].map(({ label, value, max, color }) => (
                <div key={label}>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-slate-400">{label}</span>
                    <span className="font-medium" style={{ color }}>{value?.toFixed(0) ?? '—'}/{max}</span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-1.5">
                    <div
                      className="h-1.5 rounded-full transition-all duration-700"
                      style={{ width: `${value != null ? (value / max) * 100 : 0}%`, backgroundColor: color }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Center: price comparison + details */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-5"
        >
          <h2 className="text-white font-semibold">Price Analysis</h2>

          {/* Price comparison chart */}
          <PriceComparisonChart
            askingPrice={property.asking_price}
            estimatedValue={score?.estimated_value}
          />

          {/* Key figures */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-800/50 rounded-xl p-3">
              <div className="text-slate-500 text-xs mb-1">Asking Price</div>
              <div className="text-amber-400 font-bold">{formatCurrency(property.asking_price)}</div>
            </div>
            <div className="bg-slate-800/50 rounded-xl p-3">
              <div className="text-slate-500 text-xs mb-1">Est. Market Value</div>
              <div className="text-emerald-400 font-bold">{score?.estimated_value ? formatCurrency(score.estimated_value) : '—'}</div>
            </div>
            <div className="bg-slate-800/50 rounded-xl p-3">
              <div className="text-slate-500 text-xs mb-1">Price Deviation</div>
              <div className={`font-bold ${score?.price_deviation_pct < 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {score?.price_deviation_pct != null
                  ? `${(score.price_deviation_pct * 100).toFixed(1)}%`
                  : '—'}
              </div>
            </div>
            <div className="bg-slate-800/50 rounded-xl p-3">
              <div className="text-slate-500 text-xs mb-1">Est. Monthly Rent</div>
              <div className="text-blue-400 font-bold">{formatCurrency(score?.estimated_monthly_rent)}</div>
            </div>
          </div>

          {/* Property specs */}
          <div className="border-t border-slate-800 pt-4 grid grid-cols-3 gap-3 text-center">
            <div>
              <Bed size={18} className="text-slate-400 mx-auto mb-1" />
              <div className="text-white font-semibold">{property.bedrooms ?? '—'}</div>
              <div className="text-slate-500 text-xs">Bedrooms</div>
            </div>
            <div>
              <Bath size={18} className="text-slate-400 mx-auto mb-1" />
              <div className="text-white font-semibold">{property.bathrooms ?? '—'}</div>
              <div className="text-slate-500 text-xs">Bathrooms</div>
            </div>
            <div>
              <Square size={18} className="text-slate-400 mx-auto mb-1" />
              <div className="text-white font-semibold">{property.floor_area_sqm ? `${property.floor_area_sqm}m²` : '—'}</div>
              <div className="text-slate-500 text-xs">Floor Area</div>
            </div>
          </div>
        </motion.div>

        {/* Right: sources & area stats */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.15 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-5"
        >
          <h2 className="text-white font-semibold">Area Statistics</h2>
          {score?.area_avg_price && (
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-800/50 rounded-xl p-3">
                <div className="text-slate-500 text-xs mb-1">Area Avg Price</div>
                <div className="text-white font-bold text-sm">{formatCurrency(score.area_avg_price)}</div>
              </div>
              <div className="bg-slate-800/50 rounded-xl p-3">
                <div className="text-slate-500 text-xs mb-1">10yr Growth</div>
                <div className={`font-bold text-sm ${score.area_growth_10yr_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {score.area_growth_10yr_pct != null ? `${(score.area_growth_10yr_pct * 100).toFixed(1)}%` : '—'}
                </div>
              </div>
            </div>
          )}

          {/* Sources */}
          {property.sources?.length > 0 && (
            <div>
              <div className="text-slate-500 text-xs font-medium uppercase tracking-wider mb-2">Listing Sources</div>
              <div className="space-y-2">
                {property.sources.map((s, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-slate-300 capitalize">{s.source_name}</span>
                    <div className="flex items-center gap-2">
                      <span className={`w-1.5 h-1.5 rounded-full ${s.is_active ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                      {s.source_url && (
                        <a href={s.source_url} target="_blank" rel="noopener noreferrer"
                          className="text-slate-500 hover:text-slate-300">
                          <ExternalLink size={12} />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Last seen */}
          <div className="border-t border-slate-800 pt-4 text-xs text-slate-500 flex items-center gap-1.5">
            <Calendar size={12} />
            Found: {property.date_found ? new Date(property.date_found).toLocaleDateString('en-GB') : '—'}
          </div>
        </motion.div>
      </div>

      {/* PropertyData Enrichment Panel */}
      <PropertyDataPanel propertyId={id} score={property.score} />

      {/* AI Analysis Panel */}
      <AIInsightPanel propertyId={id} insight={property.ai_insight} />

      {/* 10-year history chart */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-slate-900 border border-slate-800 rounded-2xl p-6"
      >
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-white font-semibold">10-Year Price History</h2>
            <p className="text-slate-500 text-xs mt-0.5">Average sold prices in {property.postcode?.split(' ')[0]}</p>
          </div>
        </div>
        <SalesHistoryChart
          data={areaData?.sales_by_year}
          currentPrice={property.asking_price}
        />
        <p className="text-slate-600 text-xs mt-3">
          Source: Land Registry Price Paid Data © Crown copyright and database right 2026
        </p>
      </motion.div>
    </div>
  );
}
