import React from 'react';
import { useNavigate } from 'react-router-dom';
import { MapPin, Bed, Bath, CheckCircle, Clock } from 'lucide-react';
import clsx from 'clsx';
import ScoreGauge from './ScoreGauge';
import YieldMeter from './YieldMeter';
import PriceBandBadge from './PriceBandBadge';
import { formatCurrency, propertyTypeIcon } from '../../utils/formatters';

const VERDICT_STYLE = {
  STRONG_BUY: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
  BUY:        'bg-teal-500/20 text-teal-300 border-teal-500/40',
  HOLD:       'bg-amber-500/20 text-amber-300 border-amber-500/40',
  AVOID:      'bg-red-500/20 text-red-300 border-red-500/40',
};

export default function PropertyCard({ property, personalScore }) {
  const navigate = useNavigate();
  const score = property.score;
  const verdict = property.ai_insight?.verdict;

  return (
    <div
      onClick={() => navigate(`/properties/${property.id}`)}
      className={clsx(
        'bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden cursor-pointer transition-all duration-200 hover:border-slate-600 hover:shadow-lg hover:shadow-black/20 hover:-translate-y-0.5',
        property.is_reviewed && 'opacity-60'
      )}
    >
      {/* Property image */}
      {property.image_url && (
        <div className="h-36 w-full overflow-hidden bg-slate-800">
          <img
            src={property.image_url}
            alt={property.address}
            className="w-full h-full object-cover"
            onError={e => { e.target.parentElement.style.display = 'none'; }}
          />
        </div>
      )}

      {/* Card body */}
      <div className="p-5">

      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">{propertyTypeIcon(property.property_type)}</span>
            {score && <PriceBandBadge band={score.price_band} size="sm" />}
            {property.status === 'stc' && (
              <span className="inline-flex items-center text-[10px] font-semibold px-1.5 py-0.5 rounded border bg-amber-500/20 text-amber-300 border-amber-500/40">
                STC
              </span>
            )}
            {verdict && (
              <span className={clsx('inline-flex items-center text-[10px] font-semibold px-1.5 py-0.5 rounded border', VERDICT_STYLE[verdict])}>
                AI: {verdict.replace('_', ' ')}
              </span>
            )}
            {property.is_reviewed && (
              <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                <CheckCircle size={11} /> Reviewed
              </span>
            )}
          </div>
          <h3 className="text-slate-200 font-semibold text-sm leading-snug truncate">
            {property.address}
          </h3>
          <div className="flex items-center gap-1 mt-1 text-slate-500 text-xs">
            <MapPin size={11} />
            <span>{property.postcode}</span>
            {property.town && <span>· {property.town}</span>}
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-emerald-400 font-bold text-lg">{formatCurrency(property.asking_price, true)}</div>
          {score?.estimated_value && (
            <div className="text-slate-500 text-xs">
              Est. {formatCurrency(score.estimated_value, true)}
            </div>
          )}
        </div>
      </div>

      {/* Specs */}
      <div className="flex items-center gap-4 mb-4 text-slate-400 text-xs">
        {property.bedrooms && (
          <span className="flex items-center gap-1"><Bed size={12} />{property.bedrooms} bed</span>
        )}
        {property.bathrooms && (
          <span className="flex items-center gap-1"><Bath size={12} />{property.bathrooms} bath</span>
        )}
        <span className="flex items-center gap-1 ml-auto">
          <Clock size={11} />
          {property.date_found ? new Date(property.date_found).toLocaleDateString('en-GB') : '—'}
        </span>
      </div>

      {/* Meters */}
      <div className="flex items-center justify-around pt-3 border-t border-slate-800">
        {personalScore != null ? (
          <ScoreGauge score={personalScore} size={80} label="Your Score" />
        ) : (
          <ScoreGauge score={score?.investment_score} size={80} label="Score" />
        )}
        <YieldMeter yieldPct={score?.gross_yield_pct} size={80} label="Yield" />
        {score && (
          <div className="text-center">
            <div className="text-slate-400 text-xs mb-1">vs Market</div>
            {score.price_deviation_pct != null ? (
              <div className={clsx(
                'text-xl font-bold',
                score.price_deviation_pct < 0 ? 'text-emerald-400' : 'text-red-400'
              )}>
                {score.price_deviation_pct < 0 ? '' : '+'}
                {(score.price_deviation_pct * 100).toFixed(1)}%
              </div>
            ) : (
              <div className="text-slate-600 text-xl font-bold">—</div>
            )}
            <div className="text-slate-500 text-xs">deviation</div>
          </div>
        )}
      </div>

      </div> {/* end card body */}
    </div>
  );
}
