/**
 * PropertyProfileCard
 *
 * Displays the computed property attribute profile:
 * - Known / Inferred / Estimated / Unknown badges per field
 * - Confidence score + band (colour-coded)
 * - Source badge
 * - Explanation popover on hover
 * - User override panel per field
 * - Recalculation indicator when overrides are applied
 */
import React, { useEffect, useRef, useState } from 'react';
import {
  Bed, Bath, Square, Home, Layers, LayoutGrid, RefreshCw,
  CheckCircle, HelpCircle, AlertCircle, Pencil, Check, X, Info,
  ChevronDown, ChevronUp, AlertTriangle,
} from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STATUS_STYLES = {
  known:     { label: 'Known',     colour: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  inferred:  { label: 'Inferred',  colour: 'bg-teal-500/15 text-teal-300 border-teal-500/30'         },
  estimated: { label: 'Estimated', colour: 'bg-amber-500/15 text-amber-300 border-amber-500/30'      },
  unknown:   { label: 'Unknown',   colour: 'bg-slate-700/50 text-slate-500 border-slate-700'         },
  user_override: { label: 'You', colour: 'bg-violet-500/15 text-violet-300 border-violet-500/30'    },
};

const CONFIDENCE_COLOURS = {
  very_high: 'text-emerald-400',
  high:      'text-teal-400',
  moderate:  'text-amber-400',
  low:       'text-orange-400',
  very_low:  'text-red-400',
};

const CONFIDENCE_LABELS = {
  very_high: 'Very high',
  high:      'High',
  moderate:  'Moderate',
  low:       'Low',
  very_low:  'Very low',
};

const SOURCE_LABELS = {
  listing:               'Listing data',
  land_registry:         'Land Registry',
  listing_text:          'Description text',
  floor_area_heuristic:  'Floor area model',
  bedroom_heuristic:     'Bedroom model',
  type_bedroom_heuristic:'Type + bedroom model',
  user_override:         'Your input',
  epc:                   'EPC',
  none:                  '—',
};

const FIELD_META = {
  property_type:   { icon: Home,       label: 'Property Type',     unit: '' },
  floor_area:      { icon: Square,     label: 'Floor Area',        unit: '' },
  bedrooms:        { icon: Bed,        label: 'Bedrooms',          unit: '' },
  bathrooms:       { icon: Bath,       label: 'Bathrooms',         unit: '' },
  reception_rooms: { icon: LayoutGrid, label: 'Reception Rooms',   unit: '' },
  plot_size:       { icon: Layers,     label: 'Plot Size',         unit: '' },
};

const FIELD_ORDER = ['property_type', 'floor_area', 'bedrooms', 'bathrooms', 'reception_rooms', 'plot_size'];

// ---------------------------------------------------------------------------
// Helper: format a field value for display
// ---------------------------------------------------------------------------

function formatValue(key, field) {
  if (!field || field.status === 'unknown') return '—';
  const v = field.value;
  if (v == null) return '—';

  if (key === 'floor_area' && typeof v === 'object') {
    return `${v.sqm}m² · ${v.sqft?.toLocaleString()} ft²`;
  }
  if (key === 'plot_size' && typeof v === 'object') {
    const parts = [];
    if (v.sqm != null) parts.push(`${v.sqm}m²`);
    if (v.acres != null) parts.push(`${v.acres} acres`);
    return parts.join(' · ') || '—';
  }
  if (key === 'bathrooms' && typeof v === 'object' && v.min != null) {
    return `${v.min}–${v.max}`;
  }
  if (key === 'property_type') {
    return v.charAt(0).toUpperCase() + v.slice(1);
  }
  return String(v);
}

// ---------------------------------------------------------------------------
// ExplanationPopover
// ---------------------------------------------------------------------------

function ExplanationPopover({ explanation }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  if (!explanation) return null;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="text-slate-600 hover:text-slate-400 transition-colors"
        title="Show explanation"
      >
        <Info size={13} />
      </button>
      {open && (
        <div className="absolute z-20 bottom-full left-0 mb-2 w-64 bg-slate-800 border border-slate-700 rounded-xl p-3 shadow-xl text-xs text-slate-300 leading-relaxed">
          {explanation}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ConfidenceBadge
// ---------------------------------------------------------------------------

function ConfidenceBadge({ confidence, confidenceLabel }) {
  if (confidence == null || confidence === 0) return null;
  const colour = CONFIDENCE_COLOURS[confidenceLabel] || 'text-slate-400';
  const pct = Math.round(confidence * 100);
  return (
    <span className={clsx('text-xs font-mono font-medium', colour)} title={CONFIDENCE_LABELS[confidenceLabel]}>
      {pct}%
    </span>
  );
}

// ---------------------------------------------------------------------------
// StatusBadge
// ---------------------------------------------------------------------------

function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.unknown;
  return (
    <span className={clsx(
      'inline-flex items-center text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-md border',
      style.colour
    )}>
      {style.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// OverrideInput — inline edit for a single field
// ---------------------------------------------------------------------------

const OVERRIDE_TYPES = {
  property_type:   { type: 'select', options: ['detached','semi-detached','terraced','end terrace','mid terrace','flat','maisonette','bungalow','chalet bungalow'] },
  bedrooms:        { type: 'number', min: 0, max: 20 },
  bathrooms:       { type: 'number', min: 0, max: 10 },
  reception_rooms: { type: 'number', min: 0, max: 10 },
  floor_area_sqm:  { type: 'number', min: 0, max: 2000, step: 0.5, placeholder: 'e.g. 85' },
  plot_size_sqm:   { type: 'number', min: 0, max: 100000, placeholder: 'e.g. 250' },
};

function OverrideInput({ fieldKey, currentValue, onSave, onCancel }) {
  const meta = OVERRIDE_TYPES[fieldKey] || { type: 'text' };
  const initial = typeof currentValue === 'object' ? '' : (currentValue ?? '');
  const [val, setVal] = useState(String(initial));

  const handleSave = () => {
    const v = meta.type === 'number' ? parseFloat(val) : val;
    if (meta.type === 'number' && isNaN(v)) {
      toast.error('Please enter a valid number');
      return;
    }
    onSave(v);
  };

  return (
    <div className="flex items-center gap-2 mt-2">
      {meta.type === 'select' ? (
        <select
          value={val}
          onChange={e => setVal(e.target.value)}
          className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-2 py-1 text-xs text-white focus:outline-none focus:border-violet-400"
        >
          <option value="">Select…</option>
          {meta.options.map(o => (
            <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1)}</option>
          ))}
        </select>
      ) : (
        <input
          type={meta.type || 'text'}
          min={meta.min} max={meta.max} step={meta.step || 1}
          placeholder={meta.placeholder || ''}
          value={val}
          onChange={e => setVal(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSave()}
          className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-2 py-1 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-violet-400"
          autoFocus
        />
      )}
      <button onClick={handleSave} className="p-1 text-emerald-400 hover:text-emerald-300">
        <Check size={14} />
      </button>
      <button onClick={onCancel} className="p-1 text-slate-500 hover:text-slate-300">
        <X size={14} />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AttributeRow — a single field row
// ---------------------------------------------------------------------------

function AttributeRow({ fieldKey, field, hasOverride, onOverrideSave, onOverrideRemove }) {
  const [editing, setEditing] = useState(false);
  const meta = FIELD_META[fieldKey];
  if (!meta) return null;

  const Icon = meta.icon;
  const valueStr = formatValue(fieldKey, field);
  const isUnknown = !field || field.status === 'unknown';

  const handleSave = (val) => {
    onOverrideSave(fieldKey, val);
    setEditing(false);
  };

  return (
    <div className={clsx(
      'flex items-start gap-3 px-4 py-3 border-b border-slate-800/60 last:border-0',
      isUnknown && 'opacity-60',
    )}>
      {/* Icon */}
      <div className="mt-0.5 text-slate-500 shrink-0">
        <Icon size={15} />
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Label */}
          <span className="text-xs text-slate-400 font-medium w-28 shrink-0">{meta.label}</span>

          {/* Value */}
          <span className={clsx(
            'text-sm font-semibold',
            isUnknown ? 'text-slate-600' : 'text-white',
          )}>
            {valueStr}
          </span>

          {/* Status badge */}
          {field && <StatusBadge status={field.source === 'user_override' ? 'user_override' : field.status} />}

          {/* Confidence */}
          {field && field.status !== 'unknown' && (
            <ConfidenceBadge confidence={field.confidence} confidenceLabel={field.confidence_label} />
          )}

          {/* Source */}
          {field && field.source && field.source !== 'none' && field.status !== 'unknown' && (
            <span className="text-[10px] text-slate-600 font-medium hidden sm:inline">
              {SOURCE_LABELS[field.source] || field.source}
            </span>
          )}

          {/* Explanation popover */}
          {field && field.explanation && field.status !== 'unknown' && (
            <ExplanationPopover explanation={field.explanation} />
          )}

          {/* Override / edit button */}
          <button
            type="button"
            onClick={() => setEditing(e => !e)}
            className="ml-auto text-slate-600 hover:text-violet-400 transition-colors p-0.5"
            title="Override this value"
          >
            <Pencil size={12} />
          </button>

          {/* Remove override button */}
          {hasOverride && (
            <button
              type="button"
              onClick={() => onOverrideRemove(fieldKey)}
              className="text-slate-600 hover:text-red-400 transition-colors p-0.5"
              title="Remove your override"
            >
              <X size={12} />
            </button>
          )}
        </div>

        {/* Override input */}
        {editing && (
          <OverrideInput
            fieldKey={fieldKey}
            currentValue={field?.value}
            onSave={handleSave}
            onCancel={() => setEditing(false)}
          />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function PropertyProfileCard({ propertyId }) {
  const [profile, setProfile]       = useState(null);
  const [loading, setLoading]       = useState(true);
  const [recalculating, setRecalc]  = useState(false);
  const [warnings, setWarnings]     = useState([]);
  const [overrides, setOverrides]   = useState({});
  const [recalcFlag, setRecalcFlag] = useState(false);  // show "recalculated using your update"
  const [showDebug, setShowDebug]   = useState(false);
  const [debug, setDebug]           = useState(null);

  const load = async (force = false) => {
    setLoading(true);
    try {
      const url = force
        ? `/api/properties/${propertyId}/profile/recalculate`
        : `/api/properties/${propertyId}/profile`;
      const method = force ? 'POST' : 'GET';
      const r = await fetch(url, { method });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setProfile(data.profile || {});
      setOverrides(data.overrides || {});
    } catch (e) {
      toast.error('Failed to load property profile');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [propertyId]);

  // Extract warnings from the profile when loaded
  useEffect(() => {
    if (!profile) return;
    const warns = [];
    if (debug?.warnings) warns.push(...debug.warnings);
    setWarnings(warns);
  }, [profile, debug]);

  const handleOverrideSave = async (fieldName, value) => {
    setRecalc(true);
    try {
      const r = await fetch(`/api/properties/${propertyId}/profile/override`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field: fieldName, value }),
      });
      if (!r.ok) {
        const err = await r.json();
        throw new Error(err.detail || 'Override failed');
      }
      const data = await r.json();
      setProfile(data.profile || {});
      setOverrides(data.overrides || {});
      setRecalcFlag(true);
      setTimeout(() => setRecalcFlag(false), 4000);
      toast.success('Profile updated with your correction');
    } catch (e) {
      toast.error(e.message || 'Failed to save override');
    } finally {
      setRecalc(false);
    }
  };

  const handleOverrideRemove = async (fieldName) => {
    setRecalc(true);
    try {
      const r = await fetch(
        `/api/properties/${propertyId}/profile/override/${fieldName}`,
        { method: 'DELETE' }
      );
      if (!r.ok) throw new Error('Failed to remove override');
      const data = await r.json();
      setProfile(data.profile || {});
      setOverrides(data.overrides || {});
      toast.success('Override removed');
    } catch (e) {
      toast.error(e.message || 'Failed to remove override');
    } finally {
      setRecalc(false);
    }
  };

  const loadDebug = async () => {
    if (debug) { setShowDebug(d => !d); return; }
    try {
      const r = await fetch(`/api/properties/${propertyId}/profile/debug`);
      if (!r.ok) throw new Error();
      const data = await r.json();
      setDebug(data.debug || {});
      setShowDebug(true);
    } catch {
      toast.error('Failed to load debug info');
    }
  };

  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex items-center gap-3 text-slate-500 text-sm">
        <RefreshCw size={16} className="animate-spin" /> Loading property profile…
      </div>
    );
  }

  const hasAnyData = profile && Object.values(profile).some(f => f?.status !== 'unknown');

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-white font-semibold flex items-center gap-2">
            <Home size={16} className="text-violet-400" />
            Property Profile
          </h2>
          <p className="text-slate-500 text-xs mt-0.5">
            Estimated attributes with confidence and source traceability.
            Click <Pencil size={10} className="inline mx-0.5 text-slate-400" /> to correct any value.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {recalculating && <RefreshCw size={14} className="text-violet-400 animate-spin" />}
          <button
            onClick={() => load(true)}
            disabled={recalculating}
            className="text-slate-500 hover:text-slate-300 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
            title="Recompute profile"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* "Recalculated using your update" banner */}
      {recalcFlag && (
        <div className="px-5 py-2 bg-violet-500/10 border-b border-violet-500/20 flex items-center gap-2 text-xs text-violet-300">
          <CheckCircle size={12} className="text-violet-400" />
          Recalculated using your update
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="px-5 py-3 bg-amber-500/5 border-b border-amber-500/20 space-y-1">
          {warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-amber-300">
              <AlertTriangle size={12} className="shrink-0 mt-0.5 text-amber-400" />
              {w}
            </div>
          ))}
        </div>
      )}

      {/* Attribute rows */}
      {!hasAnyData ? (
        <div className="px-5 py-8 text-center text-slate-600 text-sm">
          <HelpCircle size={28} className="mx-auto mb-2 text-slate-700" />
          No attribute data available for this property.
          <br />
          <span className="text-xs">Add a description or floor area to enable estimation.</span>
        </div>
      ) : (
        <div>
          {FIELD_ORDER.map(key => (
            <AttributeRow
              key={key}
              fieldKey={key}
              field={profile[key]}
              hasOverride={key in overrides || key + '_sqm' in overrides}
              onOverrideSave={handleOverrideSave}
              onOverrideRemove={handleOverrideRemove}
            />
          ))}
        </div>
      )}

      {/* Legend + debug toggle */}
      <div className="px-5 py-3 border-t border-slate-800 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3 flex-wrap">
          {['known', 'inferred', 'estimated', 'unknown'].map(s => (
            <span key={s} className={clsx(
              'inline-flex items-center text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-md border',
              STATUS_STYLES[s]?.colour,
            )}>
              {STATUS_STYLES[s]?.label}
            </span>
          ))}
        </div>
        <button
          onClick={loadDebug}
          className="text-xs text-slate-600 hover:text-slate-400 flex items-center gap-1 transition-colors"
        >
          {showDebug ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          Debug
        </button>
      </div>

      {/* Debug panel */}
      {showDebug && debug && (
        <div className="border-t border-slate-800 bg-slate-950 px-5 py-4 font-mono text-xs text-slate-400 space-y-3 max-h-64 overflow-y-auto">
          <div className="text-slate-300 font-semibold">Input Facts</div>
          {Object.entries(debug.facts || {}).map(([k, v]) => (
            <div key={k} className="flex gap-3">
              <span className="text-slate-600 w-48 shrink-0">{k}</span>
              <span className="text-slate-300 break-all">{JSON.stringify(v)}</span>
            </div>
          ))}
          {debug.warnings?.length > 0 && (
            <>
              <div className="text-amber-400 font-semibold mt-2">Warnings</div>
              {debug.warnings.map((w, i) => <div key={i} className="text-amber-300">{w}</div>)}
            </>
          )}
        </div>
      )}
    </div>
  );
}
