import React, { useEffect, useState, Component } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft, MapPin, Bed, Bath, Square, CheckCircle, Circle,
  ExternalLink, Calendar, Building2, AlertTriangle, Brain,
  ThumbsUp, ThumbsDown, Lightbulb, Play, Droplets, Zap, Pencil, Check, X,
  Flame, TrendingUp, WrenchIcon, PoundSterling, Copy
} from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';
import ScoreGauge from '../components/ui/ScoreGauge';
import YieldMeter from '../components/ui/YieldMeter';
import PriceBandBadge from '../components/ui/PriceBandBadge';
import SalesHistoryChart from '../components/charts/SalesHistoryChart';
import PriceComparisonChart from '../components/charts/PriceComparisonChart';
import ComparableSalesTable from '../components/charts/ComparableSalesTable';
import PriceHistogramChart from '../components/charts/PriceHistogramChart';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ImageGallery from '../components/ui/ImageGallery';
import { formatCurrency, formatYield, propertyTypeIcon } from '../utils/formatters';
import PropertyProfileCard from '../components/profile/PropertyProfileCard';

class ChartErrorBoundary extends Component {
  state = { error: null };
  static getDerivedStateFromError(error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <div className="h-48 flex items-center justify-center text-slate-600 text-sm">
          Chart unavailable
        </div>
      );
    }
    return this.props.children;
  }
}

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

const EPC_RATING_COLORS = {
  A: 'bg-emerald-600 text-white',
  B: 'bg-emerald-500 text-white',
  C: 'bg-green-500 text-white',
  D: 'bg-yellow-400 text-slate-900',
  E: 'bg-amber-500 text-white',
  F: 'bg-orange-600 text-white',
  G: 'bg-red-700 text-white',
};

function EPCRatingBadge({ rating, label }) {
  const cls = EPC_RATING_COLORS[rating?.toUpperCase()] || 'bg-slate-700 text-slate-400';
  return (
    <div className="text-center">
      <div className={`inline-flex items-center justify-center w-10 h-10 rounded-lg text-lg font-extrabold ${cls}`}>
        {rating || '?'}
      </div>
      {label && <div className="text-slate-500 text-xs mt-1">{label}</div>}
    </div>
  );
}

function EPCPanel({ property }) {
  const {
    epc_energy_rating: current,
    epc_potential_rating: potential,
    epc_floor_area_sqm,
    epc_inspection_date,
    epc_compliance_cost_low: costLow,
    epc_compliance_cost_high: costHigh,
  } = property;

  if (!current && !epc_floor_area_sqm) return null;

  const nonCompliant = current && ['F', 'G'].includes(current.toUpperCase());
  const hasCost = costLow != null || costHigh != null;

  const fmt = v => v != null ? `£${v.toLocaleString('en-GB')}` : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.11 }}
      className={`border rounded-2xl p-6 ${nonCompliant
        ? 'bg-red-950/30 border-red-800/40'
        : 'bg-slate-900 border-slate-800'}`}
    >
      <div className="flex items-center gap-2 mb-4">
        <Flame size={16} className={nonCompliant ? 'text-red-400' : 'text-amber-400'} />
        <h2 className="text-white font-semibold">Energy Performance Certificate</h2>
        {epc_inspection_date && (
          <span className="text-xs text-slate-500">
            Inspected {new Date(epc_inspection_date).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })}
          </span>
        )}
        {nonCompliant && (
          <span className="ml-auto flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border bg-red-500/15 border-red-500/40 text-red-300">
            <AlertTriangle size={11} /> Non-compliant for rental
          </span>
        )}
      </div>

      <div className="flex items-center gap-6 mb-5">
        <EPCRatingBadge rating={current} label="Current" />
        {potential && potential !== current && (
          <>
            <div className="flex flex-col items-center gap-1">
              <TrendingUp size={16} className="text-slate-500" />
              <span className="text-slate-600 text-xs">potential</span>
            </div>
            <EPCRatingBadge rating={potential} label="Potential" />
          </>
        )}
        {epc_floor_area_sqm && (
          <div className="ml-4 text-center">
            <div className="text-white font-bold text-lg">{Math.round(epc_floor_area_sqm)} m²</div>
            <div className="text-slate-500 text-xs">Floor Area</div>
          </div>
        )}
      </div>

      {nonCompliant && (
        <div className="rounded-xl border border-red-800/40 bg-red-950/40 p-4 space-y-2">
          <div className="flex items-center gap-2 text-red-300 text-sm font-medium">
            <WrenchIcon size={14} /> EPC Compliance Work Required
          </div>
          <p className="text-slate-400 text-xs leading-relaxed">
            Properties rated {current} cannot be legally rented under the Minimum Energy Efficiency
            Standards (MEES). Improvement work must be completed before letting.
          </p>
          {hasCost && (
            <div className="grid grid-cols-2 gap-3 mt-3">
              <div className="bg-slate-900/60 rounded-lg p-3">
                <div className="text-slate-500 text-xs mb-0.5">Est. Cost (Low)</div>
                <div className="text-amber-400 font-bold">{fmt(costLow) ?? '—'}</div>
              </div>
              <div className="bg-slate-900/60 rounded-lg p-3">
                <div className="text-slate-500 text-xs mb-0.5">Est. Cost (High)</div>
                <div className="text-red-400 font-bold">{fmt(costHigh) ?? '—'}</div>
              </div>
            </div>
          )}
          {!hasCost && (
            <p className="text-slate-600 text-xs">
              Import EPC recommendations data to see estimated improvement costs.
            </p>
          )}
        </div>
      )}

      {!nonCompliant && current && (
        <p className="text-slate-500 text-xs">
          Rating {current} — compliant for rental (minimum E required).
          {potential && potential !== current && ` Could reach ${potential} with improvements.`}
        </p>
      )}
    </motion.div>
  );
}

const WHARF_URL = 'https://propertyfundingplatform.com/WharfFinancial#!/allloans';

function FundingQuoteButton({ property, score }) {
  const [open, setOpen] = useState(false);

  const isBmv = score?.price_band === 'brilliant' || score?.price_band === 'good';
  const isHmo = property.property_type?.toLowerCase().includes('hmo') ||
    (score?.hmo_opportunity_score > 5);
  const purchaseCosts = property.asking_price ? Math.round(property.asking_price * 0.05) : null;

  const rows = [
    { label: 'Loan type',       value: 'Bridging → PURCHASE/RE-FI' },
    { label: 'Main residence',  value: 'No' },
    { label: 'Postcode',        value: property.postcode || '—' },
    { label: 'Plot type',       value: 'Existing Build' },
    { label: 'Current use',     value: isHmo ? 'Licenced HMO' : 'Pure Residential' },
    { label: 'BMV purchase',    value: isBmv ? 'Yes' : 'No' },
    { label: 'Purchase price',  value: property.asking_price ? `£${property.asking_price.toLocaleString('en-GB')}` : '—' },
    { label: 'Purchase costs',  value: purchaseCosts ? `£${purchaseCosts.toLocaleString('en-GB')} (5%)` : '—' },
    { label: 'Loan term',       value: '12 months' },
    { label: 'Max loan',        value: 'Yes' },
  ];

  const copyAll = () => {
    const text = rows.map(r => `${r.label}: ${r.value}`).join('\n');
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 text-xs bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded-lg px-3 py-1.5 transition-colors"
      >
        <PoundSterling size={11} /> Get Funding Quote
      </button>

      {open && (
        <>
          {/* backdrop */}
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-9 z-50 w-72 bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-white text-sm font-semibold">Wharf Financial — enter these values</span>
              <button onClick={() => setOpen(false)} className="text-slate-500 hover:text-white"><X size={14} /></button>
            </div>

            <div className="space-y-1.5 mb-3">
              {rows.map(({ label, value }) => (
                <div key={label} className="flex justify-between text-xs">
                  <span className="text-slate-500">{label}</span>
                  <span className="text-slate-200 font-medium text-right max-w-[150px]">{value}</span>
                </div>
              ))}
            </div>

            <div className="flex gap-2 border-t border-slate-800 pt-3">
              <button
                onClick={copyAll}
                className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white border border-slate-700 rounded-lg px-2.5 py-1.5 transition-colors"
              >
                <Copy size={10} /> Copy
              </button>
              <a
                href={WHARF_URL}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setOpen(false)}
                className="flex-1 flex items-center justify-center gap-1.5 text-xs bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg px-3 py-1.5 transition-colors font-medium"
              >
                <ExternalLink size={10} /> Open Wharf Financial
              </a>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

const UK_POSTCODE = /^[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}$/i;

function PostcodeEditor({ propertyId, currentPostcode, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState('');
  const [saving, setSaving] = useState(false);

  const open = () => { setValue(currentPostcode || ''); setEditing(true); };
  const cancel = () => setEditing(false);

  const save = async () => {
    const pc = value.trim().toUpperCase();
    if (!UK_POSTCODE.test(pc)) {
      toast.error('Enter a valid UK postcode (e.g. NG1 5AB)');
      return;
    }
    setSaving(true);
    try {
      const r = await fetch(`/api/properties/${propertyId}/postcode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ postcode: pc }),
      });
      if (!r.ok) { const e = await r.json(); throw new Error(e.detail || 'Failed'); }
      toast.success('Postcode saved — property re-scored');
      setEditing(false);
      onSaved(pc);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (editing) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <input
          autoFocus
          value={value}
          onChange={e => setValue(e.target.value.toUpperCase())}
          onKeyDown={e => { if (e.key === 'Enter') save(); if (e.key === 'Escape') cancel(); }}
          placeholder="e.g. NG1 5AB"
          maxLength={8}
          className="bg-slate-800 border border-slate-600 focus:border-emerald-500 text-white text-sm rounded-lg px-2 py-0.5 w-28 outline-none"
        />
        <button onClick={save} disabled={saving} className="text-emerald-400 hover:text-emerald-300 disabled:opacity-50">
          {saving ? <span className="animate-spin inline-block">⟳</span> : <Check size={14} />}
        </button>
        <button onClick={cancel} className="text-slate-500 hover:text-slate-300"><X size={14} /></button>
      </span>
    );
  }

  if (currentPostcode) {
    return (
      <span className="inline-flex items-center gap-1 group">
        <span>{currentPostcode}</span>
        <button onClick={open} className="opacity-0 group-hover:opacity-100 text-slate-600 hover:text-slate-400 transition-opacity">
          <Pencil size={11} />
        </button>
      </span>
    );
  }

  return (
    <button
      onClick={open}
      className="inline-flex items-center gap-1 text-amber-400 hover:text-amber-300 border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 rounded-lg px-2 py-0.5 text-xs transition-colors"
    >
      <MapPin size={11} /> Add postcode
    </button>
  );
}


export default function PropertyDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [property, setProperty] = useState(null);
  const [areaData, setAreaData] = useState(null);
  const [areaStats, setAreaStats] = useState(null);
  const [nationalData, setNationalData] = useState(null);
  const [comparables, setComparables] = useState(null);
  const [priceDistribution, setPriceDistribution] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reviewLoading, setReviewLoading] = useState(false);

  const loadAreaData = (pc, pt, gp) => {
    const enc = encodeURIComponent(pc);
    Promise.allSettled([
      fetch(`/api/areas/${enc}/trends`).then(r => r.ok ? r.json() : null),
      fetch(`/api/areas/${enc}/stats`).then(r => r.ok ? r.json() : null),
      fetch(`/api/areas/national/trends`).then(r => r.ok ? r.json() : null),
      fetch(`/api/areas/${enc}/comparables?property_type=${encodeURIComponent(pt)}`).then(r => r.ok ? r.json() : null),
      fetch(`/api/areas/${enc}/price-distribution?guide_price=${gp}`).then(r => r.ok ? r.json() : null),
    ]).then(([trends, stats, national, comps, dist]) => {
      if (trends.value) setAreaData(trends.value);
      if (stats.value) setAreaStats(stats.value);
      if (national.value) setNationalData(national.value);
      if (comps.value) setComparables(comps.value);
      if (dist.value) setPriceDistribution(dist.value);
    });
  };

  useEffect(() => {
    fetch(`/api/properties/${id}`)
      .then(r => r.json())
      .then(prop => {
        setProperty(prop);
        if (prop.postcode) {
          loadAreaData(prop.postcode, prop.property_type || '', prop.asking_price || '');
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
    <div className="space-y-6 max-w-6xl mx-auto pb-10">
      <ImageGallery
        imageUrl={property.image_url}
        imageUrls={property.image_urls}
        alt={property.address}
      />

      <div className="px-6 space-y-6">
      {/* Property description */}
      {property.description && (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-2">Description</h3>
          <p className="text-sm text-slate-400 leading-relaxed whitespace-pre-line">
            {property.description}
          </p>
        </div>
      )}

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
            <MapPin size={14} className={property.postcode ? '' : 'text-amber-400'} />
            <PostcodeEditor
              propertyId={id}
              currentPostcode={property.postcode}
              onSaved={pc => {
                setProperty(p => ({ ...p, postcode: pc }));
                loadAreaData(pc, property.property_type || '', property.asking_price || '');
              }}
            />
            {property.town && <><span>·</span><span>{property.town}</span></>}
            {property.county && <><span>·</span><span>{property.county}</span></>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <FundingQuoteButton property={property} score={score} />
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
          {(areaStats || score?.area_avg_price) ? (
            <div className="space-y-3">
              <div className="text-slate-500 text-xs font-medium uppercase tracking-wider">
                {areaData?.district || property.postcode?.split(' ')[0]} · Land Registry
              </div>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: 'Avg (1yr)',  value: areaStats?.avg_price_1yr  || score?.area_avg_price, fmt: true },
                  { label: 'Avg (5yr)',  value: areaStats?.avg_price_5yr,  fmt: true },
                  { label: '5yr Growth', value: areaStats?.growth_pct_5yr  || score?.area_growth_10yr_pct,
                    render: v => <span className={v >= 0 ? 'text-emerald-400' : 'text-red-400'}>{v >= 0 ? '+' : ''}{(v * 100).toFixed(1)}%</span> },
                  { label: '10yr Growth',value: areaStats?.growth_pct_10yr,
                    render: v => <span className={v >= 0 ? 'text-emerald-400' : 'text-red-400'}>{v >= 0 ? '+' : ''}{(v * 100).toFixed(1)}%</span> },
                  { label: 'Sales (1yr)',value: areaStats?.transaction_count_1yr,
                    render: v => <span className="text-slate-200">{v?.toLocaleString()}</span> },
                  { label: 'Sales (10yr)',value: areaStats?.transaction_count_10yr,
                    render: v => <span className="text-slate-200">{v?.toLocaleString()}</span> },
                ].map(({ label, value, fmt, render }) => value != null && (
                  <div key={label} className="bg-slate-800/50 rounded-xl p-2.5">
                    <div className="text-slate-500 text-[10px] mb-0.5">{label}</div>
                    <div className="font-bold text-sm">
                      {render ? render(value) : fmt ? formatCurrency(value, true) : value}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : property.postcode ? (
            <p className="text-slate-600 text-sm">Loading area data…</p>
          ) : (
            <p className="text-slate-600 text-sm">Add a postcode to see area statistics.</p>
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

      {/* Property Attribute Profile */}
      <PropertyProfileCard propertyId={id} />

      {/* EPC Panel */}
      <EPCPanel property={property} />

      {/* PropertyData Enrichment Panel */}
      <PropertyDataPanel propertyId={id} score={property.score} />

      {/* AI Analysis Panel */}
      <AIInsightPanel propertyId={id} insight={property.ai_insight} />

      {/* 10-year history chart + volume + national comparison */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-slate-900 border border-slate-800 rounded-2xl p-6"
      >
        <div className="flex items-center justify-between mb-1">
          <div>
            <h2 className="text-white font-semibold">10-Year Price History</h2>
            <p className="text-slate-500 text-xs mt-0.5">
              District avg vs national — bars show annual transaction volume
            </p>
          </div>
          {areaData && (
            <div className="flex items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-emerald-500 inline-block rounded" /> District
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-indigo-400 inline-block rounded border-dashed border-b border-indigo-400" /> National
              </span>
            </div>
          )}
        </div>
        <ChartErrorBoundary>
          <SalesHistoryChart
            data={areaData?.sales_by_year}
            currentPrice={property.asking_price}
            nationalData={nationalData}
          />
        </ChartErrorBoundary>
        <p className="text-slate-600 text-xs mt-3">
          Source: Land Registry Price Paid Data © Crown copyright and database right 2026
        </p>
      </motion.div>

      {/* Price distribution + comparable sales — side by side on wide screens */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Price distribution histogram */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-6"
        >
          <h2 className="text-white font-semibold mb-1">District Price Distribution</h2>
          <p className="text-slate-500 text-xs mb-4">
            All sold prices in {property.postcode?.split(' ')[0]} · last 3 years
            {priceDistribution?.percentile != null && (
              <span className={`ml-2 font-medium ${priceDistribution.percentile < 30 ? 'text-emerald-400' : priceDistribution.percentile > 70 ? 'text-red-400' : 'text-amber-400'}`}>
                · Guide at {priceDistribution.percentile}th percentile
              </span>
            )}
          </p>
          <ChartErrorBoundary>
            <PriceHistogramChart data={priceDistribution} guidePrice={property.asking_price} />
          </ChartErrorBoundary>
        </motion.div>

        {/* Comparable sales table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-slate-900 border border-slate-800 rounded-2xl p-6"
        >
          <h2 className="text-white font-semibold mb-1">Comparable Sales</h2>
          <p className="text-slate-500 text-xs mb-4">
            Recent {property.property_type || ''} sales in {property.postcode?.split(' ')[0]} · last 3 years
          </p>
          <ChartErrorBoundary>
            <ComparableSalesTable
              data={comparables}
              guidePrice={property.asking_price}
            />
          </ChartErrorBoundary>
        </motion.div>
      </div>
      </div> {/* end px-6 */}
    </div>
  );
}
