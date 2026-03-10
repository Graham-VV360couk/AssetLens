import React, { useEffect, useRef, useState } from 'react';
import { Search, X } from 'lucide-react';

const TYPES = ['', 'detached', 'semi-detached', 'terraced', 'flat'];
const SORTS = [
  { value: 'investment_score', label: 'Score' },
  { value: 'asking_price', label: 'Price' },
  { value: 'yield', label: 'Yield' },
  { value: 'date_found', label: 'Date Found' },
];

export default function PropertyFilters({ filters, onChange, onReset }) {
  const [sources, setSources] = useState([]);
  const [postcodeInput, setPostcodeInput] = useState('');
  const postcodeInputRef = useRef(null);
  const handleChange = (key, value) => onChange({ ...filters, [key]: value || undefined, page: 1 });

  // Parse comma-separated postcodes from filters into an array of tags
  const postcodeTags = filters.postcode
    ? filters.postcode.split(',').map(p => p.trim().toUpperCase()).filter(Boolean)
    : [];

  const addPostcodeTag = (raw) => {
    const tag = raw.trim().toUpperCase();
    if (!tag) return;
    const next = [...new Set([...postcodeTags, tag])];
    onChange({ ...filters, postcode: next.join(',') || undefined, page: 1 });
    setPostcodeInput('');
  };

  const removePostcodeTag = (tag) => {
    const next = postcodeTags.filter(t => t !== tag);
    onChange({ ...filters, postcode: next.length ? next.join(',') : undefined, page: 1 });
  };

  const handlePostcodeKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addPostcodeTag(postcodeInput);
    } else if (e.key === 'Backspace' && !postcodeInput && postcodeTags.length > 0) {
      removePostcodeTag(postcodeTags[postcodeTags.length - 1]);
    }
  };

  useEffect(() => {
    fetch('/api/scrapers')
      .then(r => r.json())
      .then(d => setSources(d))
      .catch(() => {});
  }, []);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        {/* Multi-postcode chip input */}
        <div
          className="relative flex items-center flex-wrap gap-1.5 flex-1 min-w-[200px] bg-slate-800 border border-slate-700 rounded-xl px-2.5 py-1.5 cursor-text focus-within:border-emerald-500"
          onClick={() => postcodeInputRef.current?.focus()}
        >
          <Search size={14} className="text-slate-500 shrink-0" />
          {postcodeTags.map(tag => (
            <span key={tag} className="flex items-center gap-1 bg-emerald-500/20 text-emerald-300 text-xs font-medium px-2 py-0.5 rounded-lg">
              {tag}
              <button type="button" onClick={e => { e.stopPropagation(); removePostcodeTag(tag); }} className="hover:text-white">
                <X size={11} />
              </button>
            </span>
          ))}
          <input
            ref={postcodeInputRef}
            type="text"
            placeholder={postcodeTags.length === 0 ? 'Postcode, e.g. WD18, LU4' : ''}
            value={postcodeInput}
            onChange={e => setPostcodeInput(e.target.value.toUpperCase())}
            onKeyDown={handlePostcodeKeyDown}
            onBlur={() => addPostcodeTag(postcodeInput)}
            className="flex-1 min-w-[80px] bg-transparent text-sm text-slate-200 placeholder-slate-500 focus:outline-none py-0.5"
          />
        </div>

        {/* Source */}
        <select
          value={filters.source || ''}
          onChange={e => handleChange('source', e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
        >
          <option value="">All Sources</option>
          {sources.map(s => (
            <option key={s.id} value={s.name}>{s.name}</option>
          ))}
        </select>

        {/* Property type */}
        <select
          value={filters.property_type || ''}
          onChange={e => handleChange('property_type', e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
        >
          <option value="">All Types</option>
          {TYPES.filter(Boolean).map(t => (
            <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
          ))}
        </select>

        {/* Sort */}
        <select
          value={filters.sort_by || 'investment_score'}
          onChange={e => handleChange('sort_by', e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
        >
          {SORTS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>

        <button
          onClick={onReset}
          className="p-2.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-colors"
          title="Reset filters"
        >
          <X size={16} />
        </button>
      </div>

      {/* Range filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-slate-500 text-xs whitespace-nowrap">Min Score</span>
          <input
            type="number" min="0" max="100" placeholder="0"
            value={filters.min_score || ''}
            onChange={e => handleChange('min_score', e.target.value ? Number(e.target.value) : undefined)}
            className="w-20 bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-500 text-xs whitespace-nowrap">Min Yield %</span>
          <input
            type="number" min="0" max="20" step="0.5" placeholder="0"
            value={filters.min_yield || ''}
            onChange={e => handleChange('min_yield', e.target.value ? Number(e.target.value) : undefined)}
            className="w-20 bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-500 text-xs whitespace-nowrap">Beds</span>
          <input
            type="number" min="1" max="10" placeholder="Min"
            value={filters.min_beds || ''}
            onChange={e => handleChange('min_beds', e.target.value ? Number(e.target.value) : undefined)}
            className="w-16 bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
          />
          <span className="text-slate-600 text-xs">—</span>
          <input
            type="number" min="1" max="10" placeholder="Max"
            value={filters.max_beds || ''}
            onChange={e => handleChange('max_beds', e.target.value ? Number(e.target.value) : undefined)}
            className="w-16 bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
          />
        </div>
      </div>
    </div>
  );
}
