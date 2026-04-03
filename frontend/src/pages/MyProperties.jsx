import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Home, Plus, Trash2, TrendingUp, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { formatCurrency } from '../utils/formatters';
import ValuationWizard from '../components/valuation/ValuationWizard';

const PROPERTY_TYPES = [
  { value: 'detached', label: 'Detached' },
  { value: 'semi_detached', label: 'Semi-detached' },
  { value: 'terraced', label: 'Terraced' },
  { value: 'end_of_terrace', label: 'End of terrace' },
  { value: 'bungalow', label: 'Bungalow' },
  { value: 'flat', label: 'Flat' },
  { value: 'maisonette', label: 'Maisonette' },
];

const RELATIONSHIPS = [
  { value: 'owner_occupier', label: 'Owner-occupier' },
  { value: 'landlord', label: 'Landlord' },
  { value: 'executor', label: 'Executor' },
  { value: 'developer', label: 'Developer' },
  { value: 'other', label: 'Other' },
];

function AddPropertyForm({ onSave, onCancel }) {
  const [form, setForm] = useState({
    address_line1: '', address_line2: '', town: '', postcode: '',
    property_type: 'detached', bedrooms: 3, bathrooms: 1,
    relationship_to_property: 'owner_occupier', tenure: 'freehold',
    lease_years_remaining: null,
  });

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.address_line1 || !form.town || !form.postcode) {
      toast.error('Please fill in address, town, and postcode');
      return;
    }
    onSave(form);
  };

  return (
    <form onSubmit={handleSubmit} className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 space-y-4">
      <h3 className="text-white font-semibold">Add Property</h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <input value={form.address_line1} onChange={e => set('address_line1', e.target.value)}
          placeholder="Address line 1 *" className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white placeholder-slate-500" />
        <input value={form.address_line2} onChange={e => set('address_line2', e.target.value)}
          placeholder="Address line 2" className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white placeholder-slate-500" />
        <input value={form.town} onChange={e => set('town', e.target.value)}
          placeholder="Town/City *" className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white placeholder-slate-500" />
        <input value={form.postcode} onChange={e => set('postcode', e.target.value)}
          placeholder="Postcode *" className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white placeholder-slate-500" />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <select value={form.property_type} onChange={e => set('property_type', e.target.value)}
          className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white">
          {PROPERTY_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
        <select value={form.bedrooms} onChange={e => set('bedrooms', parseInt(e.target.value))}
          className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white">
          {[1,2,3,4,5,6,7,8,9,10].map(n => <option key={n} value={n}>{n} bed</option>)}
        </select>
        <select value={form.relationship_to_property} onChange={e => set('relationship_to_property', e.target.value)}
          className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white">
          {RELATIONSHIPS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>
        <select value={form.tenure} onChange={e => set('tenure', e.target.value)}
          className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white">
          <option value="freehold">Freehold</option>
          <option value="leasehold">Leasehold</option>
        </select>
      </div>

      {form.tenure === 'leasehold' && (
        <input type="number" value={form.lease_years_remaining || ''} onChange={e => set('lease_years_remaining', parseInt(e.target.value) || null)}
          placeholder="Years remaining on lease" className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white placeholder-slate-500 w-48" />
      )}

      <div className="flex gap-3 justify-end">
        <button type="button" onClick={onCancel} className="px-4 py-2 text-sm text-slate-400 hover:text-white transition">Cancel</button>
        <button type="submit" className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium">Save Property</button>
      </div>
    </form>
  );
}

export default function MyProperties() {
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [valuatingId, setValuatingId] = useState(null);

  const token = localStorage.getItem('assetlens_token');
  const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };

  const fetchProperties = () => {
    fetch('/api/valuation/properties', { headers })
      .then(r => r.ok ? r.json() : [])
      .then(setProperties)
      .finally(() => setLoading(false));
  };

  useEffect(fetchProperties, []);

  const handleAdd = async (form) => {
    try {
      const res = await fetch('/api/valuation/properties', {
        method: 'POST', headers, body: JSON.stringify(form),
      });
      if (res.ok) {
        toast.success('Property added');
        setShowAdd(false);
        fetchProperties();
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Failed to add property');
      }
    } catch (e) {
      toast.error(e.message);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Remove this property from your portfolio?')) return;
    await fetch(`/api/valuation/properties/${id}`, { method: 'DELETE', headers });
    fetchProperties();
  };

  if (valuatingId) {
    const prop = properties.find(p => p.id === valuatingId);
    return (
      <ValuationWizard
        property={prop}
        onClose={() => { setValuatingId(null); fetchProperties(); }}
      />
    );
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center">
            <Home size={20} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">My Properties</h1>
            <p className="text-slate-400 text-sm">Properties you own or manage</p>
          </div>
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium"
        >
          {showAdd ? <X size={14} /> : <Plus size={14} />}
          {showAdd ? 'Cancel' : 'Add Property'}
        </button>
      </div>

      <AnimatePresence>
        {showAdd && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
            <AddPropertyForm onSave={handleAdd} onCancel={() => setShowAdd(false)} />
          </motion.div>
        )}
      </AnimatePresence>

      {loading ? (
        <div className="text-center py-20 text-slate-500">Loading...</div>
      ) : properties.length === 0 ? (
        <div className="text-center py-20">
          <Home size={48} className="text-slate-700 mx-auto mb-3" />
          <p className="text-slate-500">No properties in your portfolio yet</p>
          <p className="text-slate-600 text-sm mt-1">Add a property to get started with valuations</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {properties.map(prop => (
            <motion.div
              key={prop.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-slate-900 border border-slate-800 rounded-xl p-5"
            >
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="text-white font-medium">{prop.address_line1}</h3>
                  <p className="text-slate-500 text-sm">{prop.town}, {prop.postcode}</p>
                  <p className="text-slate-600 text-xs mt-1">
                    {prop.property_type} · {prop.bedrooms} bed · {prop.tenure}
                    {prop.relationship_to_property && ` · ${prop.relationship_to_property.replace('_', ' ')}`}
                  </p>
                </div>
                <button onClick={() => handleDelete(prop.id)} className="text-slate-600 hover:text-red-400 transition">
                  <Trash2 size={16} />
                </button>
              </div>

              {prop.latest_valuation ? (
                <div className="bg-slate-800/60 rounded-lg p-3 mb-3">
                  <div className="text-xs text-slate-500 mb-1">Latest Valuation</div>
                  <div className="text-lg font-bold text-emerald-400">
                    {formatCurrency(prop.latest_valuation.range_low)} — {formatCurrency(prop.latest_valuation.range_high)}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    Midpoint: {formatCurrency(prop.latest_valuation.range_mid)}
                    {prop.latest_valuation.created_at && (
                      <span> · {new Date(prop.latest_valuation.created_at).toLocaleDateString('en-GB')}</span>
                    )}
                  </div>
                </div>
              ) : null}

              <button
                onClick={() => setValuatingId(prop.id)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition text-sm font-medium"
              >
                <TrendingUp size={14} />
                {prop.latest_valuation ? 'Recalculate Value' : 'Get an Indicative Value'}
              </button>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
