import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import toast from 'react-hot-toast';

export default function Account() {
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get('/api/account/profile').then(res => setProfile(res.data)).catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const res = await api.put('/api/account/profile', profile);
      setProfile(res.data);
      toast.success('Profile saved');
    } catch {
      toast.error('Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const openPortal = async () => {
    try {
      const res = await api.post('/api/billing/portal-session');
      window.location.href = res.data.portal_url;
    } catch {
      toast.error('Billing portal unavailable');
    }
  };

  const deleteFinancial = async () => {
    if (!window.confirm('Delete all financial profile data? This cannot be undone.')) return;
    try {
      await api.delete('/api/account/profile/financial');
      const res = await api.get('/api/account/profile');
      setProfile(res.data);
      toast.success('Financial data deleted');
    } catch {
      toast.error('Failed to delete');
    }
  };

  if (!profile) return <div className="p-8 text-slate-400">Loading...</div>;

  const set = (key) => (e) => setProfile(p => ({ ...p, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));

  return (
    <div className="space-y-6 max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-white">Account Settings</h1>

      <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-5">
        <div className="flex justify-between items-center mb-4">
          <div>
            <p className="text-white font-semibold">{user?.full_name}</p>
            <p className="text-slate-400 text-sm">{user?.email}</p>
            <p className="text-emerald-400 text-xs mt-1 capitalize">{user?.subscription_tier || 'Trial'} — {user?.subscription_status}</p>
          </div>
          <button onClick={openPortal}
            className="text-xs bg-slate-700 hover:bg-slate-600 text-white rounded-lg px-3 py-1.5 transition-colors">
            Manage billing
          </button>
        </div>
      </div>

      <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl p-5 space-y-4">
        <h2 className="text-lg font-semibold text-white">Investment Profile</h2>
        <p className="text-slate-500 text-xs">All fields are optional. Used to personalise your deal scores.</p>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Strategy</label>
            <select value={profile.strategy || ''} onChange={set('strategy')}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm">
              <option value="">Not set</option>
              <option value="btl">Buy to Let</option>
              <option value="hmo">HMO</option>
              <option value="flip">Flip / Refurb</option>
              <option value="development">Development</option>
              <option value="brrr">BRRR</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Experience</label>
            <select value={profile.investment_experience || ''} onChange={set('investment_experience')}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm">
              <option value="">Not set</option>
              <option value="first_time">First-time investor</option>
              <option value="1_5_yrs">1-5 years</option>
              <option value="5_plus">5+ years</option>
              <option value="professional">Professional (10+)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Max deposit (£)</label>
            <input type="number" value={profile.max_deposit || ''} onChange={set('max_deposit')}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm" />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Target location</label>
            <input type="text" value={profile.target_location || ''} onChange={set('target_location')} placeholder="e.g. LS6 or Yorkshire"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm" />
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button onClick={save} disabled={saving}
            className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50">
            {saving ? 'Saving...' : 'Save profile'}
          </button>
          <button onClick={deleteFinancial}
            className="bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30 rounded-lg px-4 py-2 text-sm transition-colors">
            Delete financial data
          </button>
        </div>
      </div>
    </div>
  );
}
