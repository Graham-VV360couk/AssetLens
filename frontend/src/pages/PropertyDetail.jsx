import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft, MapPin, Bed, Bath, Square, CheckCircle, Circle,
  ExternalLink, Calendar, Building2, AlertTriangle
} from 'lucide-react';
import toast from 'react-hot-toast';
import ScoreGauge from '../components/ui/ScoreGauge';
import YieldMeter from '../components/ui/YieldMeter';
import PriceBandBadge from '../components/ui/PriceBandBadge';
import SalesHistoryChart from '../components/charts/SalesHistoryChart';
import PriceComparisonChart from '../components/charts/PriceComparisonChart';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { formatCurrency, formatYield, propertyTypeIcon } from '../utils/formatters';

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
