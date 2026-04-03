import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';

const ROLES = [
  { value: 'investor', label: 'I want to evaluate properties', sublabel: 'Investor — £99/mo' },
  { value: 'auction_house', label: 'I represent an auction house', sublabel: 'Auction House — £55/mo' },
  { value: 'deal_source', label: 'I source properties for investors', sublabel: 'Deal Source — £55/mo' },
];

export default function Register() {
  const [form, setForm] = useState({ email: '', password: '', full_name: '', role: 'investor', company_name: '' });
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const isUploader = form.role === 'auction_house' || form.role === 'deal_source';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register(form);
      toast.success('Account created — welcome to AssetLens!');
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }));

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-8">
        <h1 className="text-2xl font-bold text-white mb-6 text-center">Create your account</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Full name</label>
            <input type="text" value={form.full_name} onChange={set('full_name')} required
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500" />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Email</label>
            <input type="email" value={form.email} onChange={set('email')} required
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500" />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Password</label>
            <input type="password" value={form.password} onChange={set('password')} required minLength={8}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500" />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-2">I am a...</label>
            <div className="space-y-2">
              {ROLES.map(r => (
                <label key={r.value} className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  form.role === r.value ? 'border-emerald-500 bg-emerald-500/10' : 'border-slate-700 hover:border-slate-600'
                }`}>
                  <input type="radio" name="role" value={r.value} checked={form.role === r.value}
                    onChange={set('role')} className="accent-emerald-500" />
                  <div>
                    <div className="text-white text-sm">{r.label}</div>
                    <div className="text-slate-500 text-xs">{r.sublabel}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>
          {isUploader && (
            <div>
              <label className="block text-sm text-slate-400 mb-1">Company name</label>
              <input type="text" value={form.company_name} onChange={set('company_name')}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-emerald-500" />
            </div>
          )}
          <button type="submit" disabled={loading}
            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg py-2.5 font-medium transition-colors disabled:opacity-50">
            {loading ? 'Creating account...' : 'Create account'}
          </button>
        </form>
        <p className="text-center text-slate-500 text-sm mt-4">
          Already have an account? <Link to="/login" className="text-emerald-400 hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
