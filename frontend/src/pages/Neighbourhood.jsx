import React, { useState, lazy, Suspense } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Search, MapPin, Shield, Wifi, GraduationCap, Train, Bus,
  AlertTriangle, TrendingUp, TrendingDown, Minus, Home,
  Building2, TreePine, Landmark, Droplets, ShieldAlert
} from 'lucide-react';
import toast from 'react-hot-toast';
import { formatCurrency } from '../utils/formatters';

const NeighbourhoodMap = lazy(() => import('../components/maps/NeighbourhoodMap'));

const CRIME_BAND_COLORS = {
  'Low': 'text-emerald-400 bg-emerald-500/15',
  'Below Average': 'text-green-400 bg-green-500/15',
  'Average': 'text-amber-400 bg-amber-500/15',
  'Above Average': 'text-orange-400 bg-orange-500/15',
  'High': 'text-red-400 bg-red-500/15',
};

const TREND_ICONS = {
  'Improving': <TrendingDown className="w-4 h-4 text-emerald-400" />,
  'Stable': <Minus className="w-4 h-4 text-slate-400" />,
  'Worsening': <TrendingUp className="w-4 h-4 text-orange-400" />,
  'Rising Fast': <TrendingUp className="w-4 h-4 text-red-400" />,
};

const PLANNING_ICONS = {
  'conservation-area': <Landmark className="w-4 h-4" />,
  'flood-risk-zone': <Droplets className="w-4 h-4" />,
  'green-belt': <TreePine className="w-4 h-4" />,
  'article-4-direction-area': <ShieldAlert className="w-4 h-4" />,
  'listed-building': <Building2 className="w-4 h-4" />,
  'brownfield-land': <Building2 className="w-4 h-4" />,
  'ancient-woodland': <TreePine className="w-4 h-4" />,
};

function Section({ title, icon: Icon, children }) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
        {Icon && <Icon className="w-4 h-4 text-blue-400" />}
        {title}
      </h3>
      {children}
    </div>
  );
}

function StatCard({ label, value, sub, color = 'text-white' }) {
  return (
    <div className="bg-slate-900/50 rounded-lg p-3">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className={`text-lg font-bold ${color}`}>{value ?? '—'}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  );
}

export default function Neighbourhood() {
  const { postcode: urlPostcode } = useParams();
  const [postcode, setPostcode] = useState(urlPostcode || '');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  // Auto-search if postcode in URL
  React.useEffect(() => {
    if (urlPostcode && !report) {
      setPostcode(urlPostcode);
      handleSearchDirect(urlPostcode);
    }
  }, [urlPostcode]);

  const handleSearchDirect = async (pc) => {
    pc = pc.trim().toUpperCase();
    if (!pc) return;
    setLoading(true);
    setReport(null);
    try {
      const res = await fetch(`/api/neighbourhood/${encodeURIComponent(pc)}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Postcode not found');
      }
      setReport(await res.json());
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    handleSearchDirect(postcode);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Neighbourhood Report</h1>
        <p className="text-slate-400 text-sm mt-1">Enter any UK postcode for full area intelligence</p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={postcode}
            onChange={(e) => setPostcode(e.target.value)}
            placeholder="e.g. WD25 0HH"
            className="w-full pl-10 pr-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 font-medium"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {report && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Header */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-3">
              <MapPin className="w-5 h-5 text-blue-400" />
              <h2 className="text-xl font-bold text-white">{report.postcode}</h2>
              {report.imd_band && (
                <span className="text-xs px-2 py-1 bg-slate-700 rounded-full text-slate-300">
                  IMD: {report.imd_band}
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatCard label="Avg Price (1yr)" value={report.avg_price_1yr ? formatCurrency(report.avg_price_1yr) : null} />
              <StatCard label="Avg Price (5yr)" value={report.avg_price_5yr ? formatCurrency(report.avg_price_5yr) : null} />
              <StatCard label="IMD Rank" value={report.imd_rank ? `${report.imd_rank.toLocaleString()} / 32,844` : null} />
              <StatCard label="Classification" value={report.rural_urban || null} />
            </div>
          </div>

          {/* Map */}
          {report.latitude && report.longitude && (
            <Suspense fallback={<div className="h-[500px] bg-slate-800/50 rounded-xl animate-pulse" />}>
              <NeighbourhoodMap
                center={{ lat: report.latitude, lng: report.longitude }}
                schools={report.schools || []}
                transport={report.transport || []}
                planning={report.planning || []}
                crimePoints={report.crime_heatmap || []}
                nearbyProperties={report.nearby_for_sale || []}
                height="500px"
              />
            </Suspense>
          )}

          {/* Broadband */}
          <Section title="Broadband" icon={Wifi}>
            <div className="grid grid-cols-3 gap-3">
              <StatCard
                label="Gigabit Available"
                value={report.broadband_gigabit_pct != null ? `${report.broadband_gigabit_pct}%` : null}
                color={report.broadband_gigabit_pct >= 80 ? 'text-emerald-400' : report.broadband_gigabit_pct >= 30 ? 'text-amber-400' : 'text-red-400'}
              />
              <StatCard
                label="Superfast (30Mb+)"
                value={report.broadband_sfbb_pct != null ? `${report.broadband_sfbb_pct}%` : null}
                color={report.broadband_sfbb_pct >= 90 ? 'text-emerald-400' : 'text-amber-400'}
              />
              <StatCard
                label="Below USO"
                value={report.broadband_below_uso_pct != null ? `${report.broadband_below_uso_pct}%` : null}
                color={report.broadband_below_uso_pct === 0 ? 'text-emerald-400' : 'text-red-400'}
              />
            </div>
          </Section>

          {/* Crime */}
          {report.crime && (
            <Section title="Crime" icon={Shield}>
              <div className="grid grid-cols-3 gap-3 mb-4">
                <StatCard label="Total (12 months)" value={report.crime.total_1yr} />
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-xs text-slate-500 mb-1">Rate</div>
                  <span className={`text-sm font-bold px-2 py-1 rounded ${CRIME_BAND_COLORS[report.crime.rate_band] || 'text-slate-400'}`}>
                    {report.crime.rate_band}
                  </span>
                </div>
                <div className="bg-slate-900/50 rounded-lg p-3">
                  <div className="text-xs text-slate-500 mb-1">Trend</div>
                  <div className="flex items-center gap-2">
                    {TREND_ICONS[report.crime.trend]}
                    <span className="text-sm font-bold text-white">{report.crime.trend}</span>
                  </div>
                </div>
              </div>
              {report.crime.by_type?.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs text-slate-500 uppercase tracking-wider">Breakdown</div>
                  {report.crime.by_type.slice(0, 8).map((t, i) => (
                    <div key={i} className="flex justify-between items-center">
                      <span className="text-sm text-slate-300">{t.type}</span>
                      <span className="text-sm font-mono text-slate-400">{t.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </Section>
          )}

          {/* Schools */}
          {report.schools?.length > 0 && (
            <Section title="Nearest Schools" icon={GraduationCap}>
              <div className="space-y-2">
                {report.schools.map((s, i) => (
                  <div key={i} className="flex items-center justify-between bg-slate-900/50 rounded-lg px-4 py-2.5">
                    <div>
                      <div className="text-sm font-medium text-white">{s.name}</div>
                      <div className="text-xs text-slate-500 flex gap-3 mt-0.5">
                        <span>{s.phase}</span>
                        {s.is_selective && <span className="text-amber-400">Selective</span>}
                        {s.is_boarding && <span className="text-purple-400">Boarding</span>}
                        {s.religious_character && s.religious_character !== 'None' && (
                          <span className="text-blue-400">{s.religious_character}</span>
                        )}
                        {s.number_of_pupils && <span>{s.number_of_pupils} pupils</span>}
                      </div>
                    </div>
                    <span className="text-sm font-mono text-slate-400 whitespace-nowrap">{s.distance_mi} mi</span>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Transport */}
          {report.transport?.length > 0 && (
            <Section title="Transport" icon={Train}>
              <div className="space-y-2">
                {report.transport.map((t, i) => (
                  <div key={i} className="flex items-center justify-between bg-slate-900/50 rounded-lg px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      {t.stop_type === 'BCT' ? <Bus className="w-4 h-4 text-green-400" /> : <Train className="w-4 h-4 text-blue-400" />}
                      <span className="text-sm text-white">{t.name}</span>
                    </div>
                    <span className="text-sm font-mono text-slate-400">{t.distance_mi} mi</span>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Planning */}
          {report.planning?.length > 0 && (
            <Section title="Planning Constraints" icon={AlertTriangle}>
              <div className="space-y-2">
                {report.planning.map((p, i) => (
                  <div key={i} className="flex items-center justify-between bg-slate-900/50 rounded-lg px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      {PLANNING_ICONS[p.dataset] || <AlertTriangle className="w-4 h-4" />}
                      <div>
                        <div className="text-sm text-white">
                          {p.dataset.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                        </div>
                        {p.name && <div className="text-xs text-slate-500">{p.name}</div>}
                        {p.flood_risk_level && <span className="text-xs text-red-400">Level {p.flood_risk_level}</span>}
                        {p.listed_building_grade && <span className="text-xs text-amber-400">Grade {p.listed_building_grade}</span>}
                      </div>
                    </div>
                    {p.distance_mi != null && (
                      <span className="text-sm font-mono text-slate-400">{p.distance_mi} mi</span>
                    )}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Sales History */}
          {report.sales_history?.length > 0 && (
            <Section title="Recent Sales" icon={Home}>
              <div className="space-y-2">
                {report.sales_history.slice(0, 10).map((s, i) => (
                  <div key={i} className="flex items-center justify-between bg-slate-900/50 rounded-lg px-4 py-2.5">
                    <div>
                      <div className="text-sm text-white">{s.address}</div>
                      <div className="text-xs text-slate-500">{s.sale_date} &middot; {s.property_type}</div>
                    </div>
                    <span className="text-sm font-bold text-emerald-400">{formatCurrency(s.sale_price)}</span>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Nearby For Sale */}
          {report.nearby_for_sale?.length > 0 && (
            <Section title="Nearby For Sale" icon={Building2}>
              <div className="space-y-2">
                {report.nearby_for_sale.map((p, i) => (
                  <a key={i} href={`/properties/${p.id}`} className="flex items-center justify-between bg-slate-900/50 rounded-lg px-4 py-2.5 hover:bg-slate-900/80 transition">
                    <div>
                      <div className="text-sm text-white">{p.address}</div>
                      <div className="text-xs text-slate-500">
                        {p.property_type} &middot; {p.bedrooms ? `${p.bedrooms} bed` : ''} &middot; {p.distance_mi} mi away
                      </div>
                    </div>
                    <span className="text-sm font-bold text-blue-400">{formatCurrency(p.asking_price)}</span>
                  </a>
                ))}
              </div>
            </Section>
          )}
        </motion.div>
      )}
    </div>
  );
}
