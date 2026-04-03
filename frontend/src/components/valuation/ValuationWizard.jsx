import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, ArrowRight, AlertTriangle, CheckCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { formatCurrency } from '../../utils/formatters';

const SECTIONS = ['Basics', 'Features', 'Condition', 'Situation', 'Review'];

const PARKING = [
  { value: 'none', label: 'None' },
  { value: 'on_street_permit', label: 'On-street permit' },
  { value: 'allocated_on_street', label: 'Allocated on-street' },
  { value: 'driveway', label: 'Driveway' },
  { value: 'single_garage', label: 'Single garage' },
  { value: 'double_garage', label: 'Double garage' },
];

const GARDEN = [
  { value: 'none', label: 'None' },
  { value: 'communal', label: 'Communal' },
  { value: 'small_private', label: 'Small private' },
  { value: 'medium_private', label: 'Medium private' },
  { value: 'large_private', label: 'Large private' },
];

const ASPECTS = [
  { value: 'unknown', label: 'Unknown' }, { value: 'north', label: 'North' },
  { value: 'east', label: 'East' }, { value: 'south', label: 'South' },
  { value: 'west', label: 'West' }, { value: 'south_west', label: 'South-west' },
];

const HEATING = [
  { value: 'gas_central', label: 'Gas central heating' },
  { value: 'electric', label: 'Electric' },
  { value: 'heat_pump', label: 'Heat pump' },
  { value: 'other', label: 'Other' },
  { value: 'none', label: 'None' },
];

const EXTENSIONS = [
  { value: 'none', label: 'No extension' },
  { value: 'single_storey_rear', label: 'Single storey rear' },
  { value: 'double_storey_rear', label: 'Double storey rear' },
  { value: 'loft_conversion', label: 'Loft conversion' },
  { value: 'side_return', label: 'Side return' },
  { value: 'other', label: 'Other' },
];

const CONDITION_ATTRS = [
  { key: 'kitchen', label: 'Kitchen', weight: 'High' },
  { key: 'bathrooms', label: 'Bathrooms', weight: 'Medium-high' },
  { key: 'boiler', label: 'Boiler / Heating System', weight: 'High' },
  { key: 'windows', label: 'Windows', weight: 'Medium' },
  { key: 'roof', label: 'Roof', weight: 'High' },
  { key: 'decoration', label: 'General Decoration', weight: 'Low' },
  { key: 'garden_condition', label: 'Garden Condition', weight: 'Low-medium' },
];

const EMOJIS = [
  { value: 'poor', emoji: '\uD83D\uDE1E', label: 'Poor' },
  { value: 'below_average', emoji: '\uD83D\uDE10', label: 'Below average' },
  { value: 'average', emoji: '\uD83D\uDE42', label: 'Average' },
  { value: 'good', emoji: '\uD83D\uDE0A', label: 'Good' },
  { value: 'excellent', emoji: '\uD83D\uDE04', label: 'Excellent' },
];

const MOTIVATIONS = [
  { value: 'upsizing', label: 'Upsizing' }, { value: 'downsizing', label: 'Downsizing' },
  { value: 'relocating', label: 'Relocating' }, { value: 'financial', label: 'Financial reasons' },
  { value: 'inherited', label: 'Inherited property' }, { value: 'investment_exit', label: 'Investment exit' },
  { value: 'curious', label: 'Just curious' },
];

const TIMELINES = [
  { value: 'asap', label: 'As soon as possible' }, { value: '3_months', label: 'Within 3 months' },
  { value: '6_months', label: 'Within 6 months' }, { value: '12_months', label: 'Within 12 months' },
  { value: 'no_urgency', label: 'No urgency' },
];

const CHAINS = [
  { value: 'no', label: 'No — nothing to buy' }, { value: 'yes_found', label: 'Yes — found a property' },
  { value: 'yes_looking', label: 'Yes — still looking' }, { value: 'unsure', label: 'Not sure' },
];

const OCCUPANCY = [
  { value: 'owner_occupied', label: 'Owner-occupied' }, { value: 'tenanted_ast', label: 'Tenanted — AST' },
  { value: 'tenanted_sitting', label: 'Tenanted — sitting tenant' }, { value: 'vacant', label: 'Vacant' },
];

function SelectGrid({ options, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map(o => (
        <button key={o.value} type="button" onClick={() => onChange(o.value)}
          className={`px-3 py-1.5 rounded-lg text-sm transition ${
            value === o.value ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-400 hover:text-white'
          }`}>{o.label}</button>
      ))}
    </div>
  );
}

function ConditionInput({ attr, value, onChange }) {
  const v = value || { year_installed: null, condition: 'average' };
  return (
    <div className="bg-slate-800/60 rounded-lg p-4">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm text-white font-medium">{attr.label}</span>
        <span className="text-xs text-slate-500">{attr.weight} impact</span>
      </div>
      <div className="flex items-center gap-4">
        <div>
          <label className="text-xs text-slate-500 block mb-1">Year installed/replaced</label>
          <input type="number" min={1950} max={2026} value={v.year_installed || ''}
            onChange={e => onChange({ ...v, year_installed: parseInt(e.target.value) || null })}
            placeholder="e.g. 2019" className="w-28 px-2 py-1.5 bg-slate-700 border border-slate-600 rounded text-sm text-white placeholder-slate-500" />
        </div>
        <div>
          <label className="text-xs text-slate-500 block mb-1">Condition</label>
          <div className="flex gap-1">
            {EMOJIS.map(e => (
              <button key={e.value} type="button" onClick={() => onChange({ ...v, condition: e.value })}
                title={e.label}
                className={`text-xl px-1 rounded transition ${
                  v.condition === e.value ? 'bg-blue-600/30 ring-1 ring-blue-500' : 'hover:bg-slate-700'
                }`}>{e.emoji}</button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ValuationWizard({ property, onClose }) {
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const [answers, setAnswers] = useState({
    basics: {
      bathrooms: property.bathrooms || 1,
      extension_type: 'none',
    },
    features: {
      parking: 'none',
      garden: 'small_private',
      garden_aspect: 'unknown',
      epc_rating: 'unknown',
      heating: 'gas_central',
    },
    condition: {},
    situation: {
      motivation: 'curious',
      timeline: 'no_urgency',
      chain: 'no',
      occupancy: 'owner_occupied',
    },
    supporting: {
      walkthrough_interest: false,
      notes: '',
    },
  });

  const set = (section, key, value) => {
    setAnswers(a => ({ ...a, [section]: { ...a[section], [key]: value } }));
  };

  const setCondition = (attr, value) => {
    setAnswers(a => ({ ...a, condition: { ...a.condition, [attr]: value } }));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const token = localStorage.getItem('assetlens_token');
      const res = await fetch(`/api/valuation/properties/${property.id}/value`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(answers),
      });
      if (res.ok) {
        setResult(await res.json());
      } else {
        const err = await res.json();
        toast.error(err.detail || 'Valuation failed');
      }
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  // Result screen
  if (result) {
    return (
      <div className="p-6 max-w-2xl mx-auto space-y-6">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center">
          <CheckCircle size={48} className="text-emerald-400 mx-auto mb-4" />
          <p className="text-slate-400 text-sm mb-2">
            Based on comparable sales in {property.postcode} and the information you've provided
          </p>
          <h2 className="text-3xl font-bold text-white mb-1">
            {formatCurrency(result.range_low)} — {formatCurrency(result.range_high)}
          </h2>
          <p className="text-emerald-400 font-semibold text-lg">
            Midpoint: {formatCurrency(result.range_mid)}
          </p>
          {result.situation_band && (
            <p className="text-xs text-slate-500 mt-2">{result.situation_band}</p>
          )}
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-3">
          <h3 className="text-white font-semibold mb-3">Breakdown</h3>
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">AVM Baseline ({result.avm_source})</span>
            <span className="text-white font-medium">{formatCurrency(result.avm_baseline)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Feature adjustments</span>
            <span className={`font-medium ${result.feature_adjustment >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {result.feature_adjustment >= 0 ? '+' : ''}{formatCurrency(result.feature_adjustment)}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Condition adjustments</span>
            <span className={`font-medium ${result.condition_adjustment >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {result.condition_adjustment >= 0 ? '+' : ''}{formatCurrency(result.condition_adjustment)}
            </span>
          </div>
          <div className="border-t border-slate-700 pt-2 flex justify-between text-sm font-bold">
            <span className="text-white">Final Range</span>
            <span className="text-emerald-400">{formatCurrency(result.range_low)} — {formatCurrency(result.range_high)}</span>
          </div>
        </div>

        <p className="text-xs text-slate-600 text-center italic">
          This is an indicative estimate only, not a formal valuation. It is based on comparable sales data
          adjusted for the features and condition information you have provided.
          For a formal RICS valuation, please consult a qualified surveyor.
        </p>

        <div className="flex gap-3 justify-center">
          <button onClick={() => { setResult(null); setStep(0); }}
            className="px-5 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 transition text-sm">
            Recalculate
          </button>
          <button onClick={onClose}
            className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm">
            Done
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      {/* Header + progress */}
      <div className="flex items-center justify-between">
        <button onClick={onClose} className="text-slate-400 hover:text-white transition flex items-center gap-1 text-sm">
          <ArrowLeft size={14} /> Back to portfolio
        </button>
        <div className="flex gap-1">
          {SECTIONS.map((s, i) => (
            <div key={s} className={`h-1.5 w-12 rounded-full ${i <= step ? 'bg-blue-500' : 'bg-slate-700'}`} />
          ))}
        </div>
        <span className="text-xs text-slate-500">Step {step + 1} of {SECTIONS.length}</span>
      </div>

      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-2">
        <p className="text-xs text-slate-500 text-center">{property.address_line1}, {property.town}, {property.postcode}</p>
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={step} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>

          {/* Section 1: Basics */}
          {step === 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-white">Property Basics</h2>
              <p className="text-sm text-slate-400">Confirm or edit the pre-populated details.</p>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Bathrooms</label>
                  <select value={answers.basics.bathrooms} onChange={e => set('basics', 'bathrooms', parseInt(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white">
                    {[1,2,3,4].map(n => <option key={n} value={n}>{n}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Extension</label>
                  <SelectGrid options={EXTENSIONS} value={answers.basics.extension_type}
                    onChange={v => set('basics', 'extension_type', v)} />
                </div>
              </div>
            </div>
          )}

          {/* Section 2: Features */}
          {step === 1 && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-white">Key Features</h2>
              {[
                { label: 'Parking', key: 'parking', options: PARKING },
                { label: 'Garden', key: 'garden', options: GARDEN },
                { label: 'Garden Aspect', key: 'garden_aspect', options: ASPECTS },
                { label: 'EPC Rating', key: 'epc_rating', options: ['A','B','C','D','E','F','G','unknown'].map(v => ({ value: v, label: v === 'unknown' ? 'Unknown' : v })) },
                { label: 'Heating', key: 'heating', options: HEATING },
              ].map(({ label, key, options }) => (
                <div key={key}>
                  <label className="text-xs text-slate-500 block mb-1">{label}</label>
                  <SelectGrid options={options} value={answers.features[key]} onChange={v => set('features', key, v)} />
                </div>
              ))}
            </div>
          )}

          {/* Section 3: Condition */}
          {step === 2 && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-white">Condition Scoring</h2>
              <p className="text-sm text-slate-400">
                Enter the year each item was last replaced and rate its current condition.
              </p>
              {CONDITION_ATTRS.map(attr => (
                <ConditionInput key={attr.key} attr={attr}
                  value={answers.condition[attr.key]}
                  onChange={v => setCondition(attr.key, v)} />
              ))}
            </div>
          )}

          {/* Section 4: Situation */}
          {step === 3 && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-white">Your Situation</h2>
              <p className="text-sm text-slate-400">This affects the confidence range, not the market value estimate.</p>
              {[
                { label: 'Why are you considering selling?', key: 'motivation', options: MOTIVATIONS },
                { label: 'What is your timeline?', key: 'timeline', options: TIMELINES },
                { label: 'Are you in a chain?', key: 'chain', options: CHAINS },
                { label: 'Is the property currently occupied?', key: 'occupancy', options: OCCUPANCY },
              ].map(({ label, key, options }) => (
                <div key={key}>
                  <label className="text-xs text-slate-500 block mb-1">{label}</label>
                  <SelectGrid options={options} value={answers.situation[key]} onChange={v => set('situation', key, v)} />
                </div>
              ))}
            </div>
          )}

          {/* Section 5: Review + Submit */}
          {step === 4 && (
            <div className="space-y-4">
              <h2 className="text-lg font-bold text-white">Review & Calculate</h2>

              <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle size={18} className="text-amber-400 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-amber-200">
                    The accuracy of your indicative value depends on the accuracy of your answers.
                    Overstating condition or features will produce an inflated estimate that won't reflect
                    what buyers will offer. We're not here to flatter your property — we're here to give
                    you a useful number.
                  </p>
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-500 block mb-1">Additional notes (optional)</label>
                <textarea value={answers.supporting.notes} onChange={e => set('supporting', 'notes', e.target.value)}
                  maxLength={500} rows={3} placeholder="Anything else about the property..."
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm text-white placeholder-slate-500 resize-none" />
              </div>

              <div>
                <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
                  <input type="checkbox" checked={answers.supporting.walkthrough_interest}
                    onChange={e => set('supporting', 'walkthrough_interest', e.target.checked)}
                    className="rounded border-slate-600" />
                  I'm interested in a 360° virtual walkthrough
                </label>
              </div>
            </div>
          )}

        </motion.div>
      </AnimatePresence>

      {/* Navigation */}
      <div className="flex justify-between pt-4 border-t border-slate-800">
        <button onClick={() => setStep(s => Math.max(0, s - 1))} disabled={step === 0}
          className="flex items-center gap-1 px-4 py-2 text-sm text-slate-400 hover:text-white disabled:opacity-30 transition">
          <ArrowLeft size={14} /> Back
        </button>

        {step < SECTIONS.length - 1 ? (
          <button onClick={() => setStep(s => s + 1)}
            className="flex items-center gap-1 px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm font-medium">
            Next <ArrowRight size={14} />
          </button>
        ) : (
          <button onClick={handleSubmit} disabled={submitting}
            className="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition text-sm font-medium disabled:opacity-50">
            {submitting ? 'Calculating...' : 'Calculate My Indicative Value'}
          </button>
        )}
      </div>
    </div>
  );
}
