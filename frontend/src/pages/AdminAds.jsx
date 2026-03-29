import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';

export default function AdminAds() {
  const [token, setToken] = useState(() => sessionStorage.getItem('ad_admin_token') || '');
  const [tokenInput, setTokenInput] = useState('');
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (token) fetchConfig();
  }, [token]);

  async function fetchConfig() {
    setLoading(true);
    try {
      const adminRes = await fetch('/api/ads/admin-config', {
        headers: { 'X-Admin-Token': token },
      });
      if (adminRes.status === 401) {
        toast.error('Invalid admin token');
        setToken('');
        sessionStorage.removeItem('ad_admin_token');
        return;
      }
      const full = await adminRes.json();
      setConfig(full);
    } catch {
      toast.error('Failed to load config');
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(action) {
    try {
      const res = await fetch('/api/ads/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
        body: JSON.stringify({ action }),
      });
      const data = await res.json();
      if (!res.ok) { toast.error(data.detail || 'Action failed'); return; }
      toast.success(action === 'approve' ? 'Ad approved and now live' : 'Submission rejected');
      fetchConfig();
    } catch {
      toast.error('Network error');
    }
  }

  async function handleToggleLive() {
    if (!config) return;
    const newEnabled = !config.live.enabled;
    try {
      const res = await fetch('/api/ads/live', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'X-Admin-Token': token },
        body: JSON.stringify({ enabled: newEnabled }),
      });
      if (!res.ok) { toast.error('Failed to update'); return; }
      toast.success(newEnabled ? 'Ad bar enabled' : 'Ad bar disabled');
      fetchConfig();
    } catch {
      toast.error('Network error');
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 max-w-sm w-full">
          <h1 className="text-white text-lg font-bold mb-4">Admin — Ad Management</h1>
          <input
            type="password"
            placeholder="Admin token"
            value={tokenInput}
            onChange={e => setTokenInput(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-sm mb-3 focus:outline-none focus:border-emerald-500"
          />
          <button
            onClick={() => {
              sessionStorage.setItem('ad_admin_token', tokenInput);
              setToken(tokenInput);
            }}
            className="w-full bg-emerald-500 hover:bg-emerald-400 text-white font-semibold py-2 rounded-lg"
          >
            Login
          </button>
        </div>
      </div>
    );
  }

  if (loading || !config) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <p className="text-slate-400">Loading…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-200">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-white text-xl font-bold">Ad Management</h1>
          <button
            onClick={() => { setToken(''); sessionStorage.removeItem('ad_admin_token'); }}
            className="text-slate-500 hover:text-slate-300 text-sm"
          >
            Log out
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Live slot */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-white">Live Ad</h2>
              <button
                onClick={handleToggleLive}
                className={`text-xs font-semibold px-3 py-1 rounded-full border transition-colors ${
                  config.live.enabled
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30'
                    : 'bg-slate-700 text-slate-400 border-slate-600 hover:bg-emerald-500/10 hover:text-emerald-400 hover:border-emerald-500/30'
                }`}
              >
                {config.live.enabled ? 'Enabled — click to disable' : 'Disabled — click to enable'}
              </button>
            </div>
            <AdPreview ad={config.live} />
          </div>

          {/* Pending slot */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="font-semibold text-white mb-4">Pending Submission</h2>
            {config.pending ? (
              <>
                <AdPreview ad={config.pending} />
                <div className="flex gap-3 mt-4">
                  <button
                    onClick={() => handleApprove('approve')}
                    className="flex-1 bg-emerald-500 hover:bg-emerald-400 text-white text-sm font-semibold py-2 rounded-lg"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleApprove('reject')}
                    className="flex-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 text-sm font-semibold py-2 rounded-lg"
                  >
                    Reject
                  </button>
                </div>
              </>
            ) : (
              <p className="text-slate-500 text-sm">No pending submissions.</p>
            )}
          </div>
        </div>

        {/* Bar preview */}
        {config.live.enabled && (
          <div className="mt-6">
            <p className="text-slate-500 text-xs mb-2 uppercase tracking-wider font-semibold">Live bar preview</p>
            <div
              className="w-full flex items-center px-4 gap-3 rounded-lg overflow-hidden"
              style={{ height: '50px', backgroundColor: config.live.background_colour_fallback || '#1a1a2e' }}
            >
              {config.live.logo_url && (
                <img src={config.live.logo_url} alt="" className="h-7 w-auto object-contain flex-shrink-0" />
              )}
              <p className="flex-1 text-center font-medium text-sm leading-tight line-clamp-1" style={{ color: config.live.text_colour || '#fff' }}>
                {config.live.strapline}
              </p>
              {config.live.cta_label && (
                <span className="flex-shrink-0 bg-emerald-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg whitespace-nowrap">
                  {config.live.cta_label} →
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AdPreview({ ad }) {
  if (!ad || !ad.advertiser_name) {
    return <p className="text-slate-500 text-sm">No ad configured.</p>;
  }
  return (
    <div className="space-y-2 text-sm">
      <Row label="Advertiser" value={ad.advertiser_name} />
      <Row label="Strapline" value={ad.strapline} />
      <Row label="CTA" value={`${ad.cta_label} → ${ad.cta_url}`} />
      {ad.logo_url && <Row label="Logo" value={<a href={ad.logo_url} target="_blank" rel="noopener noreferrer" className="text-emerald-400 underline">View</a>} />}
      <Row label="Mobile bg" value={ad.background_image_mobile ? <a href={ad.background_image_mobile} target="_blank" rel="noopener noreferrer" className="text-emerald-400 underline">View</a> : '—'} />
      <Row label="Desktop bg" value={ad.background_image_desktop ? <a href={ad.background_image_desktop} target="_blank" rel="noopener noreferrer" className="text-emerald-400 underline">View</a> : '—'} />
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex gap-2">
      <span className="text-slate-500 w-24 flex-shrink-0">{label}</span>
      <span className="text-slate-300 break-all">{value}</span>
    </div>
  );
}
