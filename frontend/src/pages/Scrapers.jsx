import React, { useEffect, useState } from 'react';
import {
  Plus, Play, Trash2, ToggleLeft, ToggleRight, Globe, RefreshCw,
  CheckCircle, XCircle, Clock, AlertCircle, Search, ChevronDown, ChevronUp,
  Layers, Link2, ArrowRight, Zap
} from 'lucide-react';
import { scrapersApi } from '../services/api';
import toast from 'react-hot-toast';
import clsx from 'clsx';

const TYPE_LABELS = { auction: 'Auction', estate_agent: 'Estate Agent', rental: 'Rental' };
const TYPE_COLOURS = {
  auction: 'text-amber-400 bg-amber-400/10',
  estate_agent: 'text-blue-400 bg-blue-400/10',
  rental: 'text-purple-400 bg-purple-400/10',
};

function StatusBadge({ status }) {
  if (!status) return <span className="text-slate-600 text-xs">Never run</span>;
  const map = {
    success: { icon: CheckCircle, colour: 'text-emerald-400', label: 'Success' },
    error:   { icon: XCircle,    colour: 'text-red-400',     label: 'Error'   },
    running: { icon: RefreshCw,  colour: 'text-blue-400 animate-spin', label: 'Running' },
    pending: { icon: Clock,      colour: 'text-slate-400',   label: 'Pending' },
  };
  const { icon: Icon, colour, label } = map[status] || map.pending;
  return (
    <span className={clsx('flex items-center gap-1 text-xs font-medium', colour)}>
      <Icon size={13} /> {label}
    </span>
  );
}

function InvestigationBadge({ status }) {
  if (!status) return null;
  const map = {
    done:    { icon: Search,    colour: 'text-teal-400',   label: 'Analysed' },
    running: { icon: RefreshCw, colour: 'text-blue-400 animate-spin', label: 'Analysing…' },
    pending: { icon: Clock,     colour: 'text-slate-500',  label: 'Analysis queued' },
    error:   { icon: XCircle,   colour: 'text-red-400',    label: 'Analysis failed' },
  };
  const { icon: Icon, colour, label } = map[status] || {};
  if (!Icon) return null;
  return (
    <span className={clsx('flex items-center gap-1 text-xs', colour)}>
      <Icon size={12} /> {label}
    </span>
  );
}

function PaginationTypeBadge({ type }) {
  const map = {
    standard_next: { colour: 'text-emerald-400 bg-emerald-400/10', label: 'Next-page nav' },
    numbered:      { colour: 'text-emerald-400 bg-emerald-400/10', label: 'Numbered pages' },
    query_param:   { colour: 'text-emerald-400 bg-emerald-400/10', label: '?page=N' },
    ajax_load_more:{ colour: 'text-amber-400 bg-amber-400/10',     label: 'AJAX / Load More' },
    single_page:   { colour: 'text-slate-400 bg-slate-800',        label: 'Single page' },
    unknown:       { colour: 'text-slate-400 bg-slate-800',        label: 'Unknown' },
  };
  const { colour, label } = map[type] || map.unknown;
  return <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-lg', colour)}>{label}</span>;
}

function InvestigationPanel({ source, onInvestigate }) {
  const data = source.investigation_data ? (() => {
    try { return JSON.parse(source.investigation_data); } catch { return null; }
  })() : null;

  if (source.investigation_status === 'pending' || source.investigation_status === 'running') {
    return (
      <div className="px-5 py-4 bg-slate-800/30 border-t border-slate-800 flex items-center gap-2 text-slate-500 text-sm">
        <RefreshCw size={14} className="animate-spin" />
        Investigating site structure — this usually takes 10–30 seconds…
      </div>
    );
  }

  if (!data) {
    return (
      <div className="px-5 py-4 bg-slate-800/30 border-t border-slate-800 flex items-center justify-between">
        <span className="text-slate-500 text-sm">No investigation data yet.</span>
        <button
          onClick={onInvestigate}
          className="flex items-center gap-1.5 text-xs text-teal-400 hover:text-teal-300 bg-teal-400/10 hover:bg-teal-400/20 px-3 py-1.5 rounded-lg transition-colors"
        >
          <Search size={12} /> Analyse Site
        </button>
      </div>
    );
  }

  const pagination = data.pagination || {};
  const cards = data.property_cards || {};
  const detail = data.detail_page || {};
  const ajax = data.ajax_indicators || [];
  const recs = data.recommendations || [];

  return (
    <div className="border-t border-slate-800 bg-slate-800/20 px-5 py-4 space-y-4">
      {/* Summary row */}
      <div className="flex flex-wrap gap-4 text-xs">
        <div className="flex items-center gap-2">
          <Layers size={13} className="text-slate-500" />
          <span className="text-slate-400">Cards found:</span>
          <span className="text-white font-semibold">{cards.count ?? '?'}</span>
          {cards.selector && <span className="text-slate-600">({cards.selector})</span>}
        </div>
        <div className="flex items-center gap-2">
          <Globe size={13} className="text-slate-500" />
          <span className="text-slate-400">Pagination:</span>
          <PaginationTypeBadge type={pagination.type} />
          {pagination.max_pages_recommended && (
            <span className="text-slate-600">rec. max {pagination.max_pages_recommended} pages</span>
          )}
        </div>
        {detail.has_detail_page !== undefined && (
          <div className="flex items-center gap-2">
            <Link2 size={13} className="text-slate-500" />
            <span className="text-slate-400">Detail pages:</span>
            {detail.has_detail_page
              ? <span className="text-emerald-400 font-medium">Yes — extra data available</span>
              : <span className="text-slate-500">No extra data</span>
            }
          </div>
        )}
      </div>

      {/* Extra detail fields */}
      {detail.extra_fields_available && detail.extra_fields_available.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-slate-500">Fields on detail pages:</span>
          {detail.extra_fields_available.map(f => (
            <span key={f} className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-md">{f}</span>
          ))}
        </div>
      )}

      {/* AJAX indicators */}
      {ajax.length > 0 && (
        <div className="flex items-start gap-2">
          <Zap size={13} className="text-amber-400 mt-0.5 shrink-0" />
          <div className="text-xs text-amber-400/80 space-y-0.5">
            {ajax.map((a, i) => <p key={i}>{a}</p>)}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recs.length > 0 && (
        <div className="space-y-1.5">
          {recs.map((r, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-slate-400">
              <ArrowRight size={12} className="text-teal-400 mt-0.5 shrink-0" />
              {r}
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between pt-1">
        {data.analysed_at && (
          <span className="text-xs text-slate-600">
            Analysed {new Date(data.analysed_at).toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'short' })}
          </span>
        )}
        <button
          onClick={onInvestigate}
          className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-teal-400 transition-colors"
        >
          <RefreshCw size={11} /> Re-analyse
        </button>
      </div>
    </div>
  );
}

const EMPTY_FORM = { name: '', url: '', source_type: 'auction', max_pages: 5, notes: '' };

export default function Scrapers() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(EMPTY_FORM);
  const [adding, setAdding] = useState(false);
  const [running, setRunning] = useState({});
  const [expanded, setExpanded] = useState({});

  const load = async () => {
    try {
      const data = await scrapersApi.getAll();
      setSources(data);
    } catch {
      toast.error('Failed to load scraper sources');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  // Auto-refresh while any investigation/scrape is running
  useEffect(() => {
    const active = sources.some(s =>
      s.last_run_status === 'running' ||
      s.investigation_status === 'running' ||
      s.investigation_status === 'pending'
    );
    if (!active) return;
    const timer = setTimeout(load, 4000);
    return () => clearTimeout(timer);
  }, [sources]);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.url.trim()) return toast.error('Name and URL are required');
    try {
      setAdding(true);
      const created = await scrapersApi.add(form);
      setSources(prev => [created, ...prev]);
      setForm(EMPTY_FORM);
      // Auto-expand to show investigation progress
      setExpanded(prev => ({ ...prev, [created.id]: true }));
      toast.success(`Added ${created.name} — analysing site…`);
    } catch {
      toast.error('Failed to add source');
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Delete "${name}"?`)) return;
    try {
      await scrapersApi.delete(id);
      setSources(prev => prev.filter(s => s.id !== id));
      toast.success('Deleted');
    } catch {
      toast.error('Failed to delete');
    }
  };

  const handleToggle = async (id) => {
    try {
      const updated = await scrapersApi.toggle(id);
      setSources(prev => prev.map(s => s.id === id ? updated : s));
    } catch {
      toast.error('Failed to toggle');
    }
  };

  const handleRun = async (id, name) => {
    try {
      setRunning(prev => ({ ...prev, [id]: true }));
      await scrapersApi.run(id);
      toast.success(`Scraper started for ${name}`);
      setTimeout(async () => {
        const updated = await scrapersApi.getAll();
        setSources(updated);
        setRunning(prev => ({ ...prev, [id]: false }));
      }, 3000);
    } catch (err) {
      toast.error(err.message || 'Failed to start scraper');
      setRunning(prev => ({ ...prev, [id]: false }));
    }
  };

  const handleInvestigate = async (id, name) => {
    try {
      await scrapersApi.investigate(id);
      setSources(prev => prev.map(s => s.id === id ? { ...s, investigation_status: 'pending' } : s));
      setExpanded(prev => ({ ...prev, [id]: true }));
      toast.success(`Analysing ${name}…`);
    } catch (err) {
      toast.error(err.message || 'Failed to start investigation');
    }
  };

  const toggleExpand = (id) => setExpanded(prev => ({ ...prev, [id]: !prev[id] }));

  const fmtDate = (d) => d ? new Date(d).toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'short' }) : '—';

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Data Sources</h1>
        <p className="text-slate-400 text-sm mt-1">
          Add auction houses and estate agent sites to scrape for property listings.
        </p>
      </div>

      {/* Add form */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">
        <h2 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
          <Plus size={16} className="text-emerald-400" /> Add New Source
        </h2>
        <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          <input
            className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 col-span-1"
            placeholder="Name (e.g. Allsop Auctions)"
            value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
          />
          <input
            className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 lg:col-span-2"
            placeholder="URL (e.g. https://www.allsop.co.uk/residential-auctions)"
            value={form.url}
            onChange={e => setForm(f => ({ ...f, url: e.target.value }))}
          />
          <div className="flex gap-2">
            <select
              className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
              value={form.source_type}
              onChange={e => setForm(f => ({ ...f, source_type: e.target.value }))}
            >
              <option value="auction">Auction</option>
              <option value="estate_agent">Estate Agent</option>
              <option value="rental">Rental</option>
            </select>
            <input
              type="number"
              min={1} max={20}
              className="w-16 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
              title="Max pages to scrape"
              value={form.max_pages}
              onChange={e => setForm(f => ({ ...f, max_pages: parseInt(e.target.value) || 5 }))}
            />
          </div>
          <input
            className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 md:col-span-2 lg:col-span-3"
            placeholder="Notes (optional)"
            value={form.notes}
            onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
          />
          <button
            type="submit"
            disabled={adding}
            className="flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-white text-sm font-semibold rounded-xl px-4 py-2 transition-colors"
          >
            {adding ? <RefreshCw size={15} className="animate-spin" /> : <Plus size={15} />}
            Add Source
          </button>
        </form>
      </div>

      {/* Sources list */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-300">
            Configured Sources <span className="text-slate-500 font-normal ml-1">({sources.length})</span>
          </h2>
          <button onClick={load} className="text-slate-500 hover:text-slate-300 p-1 rounded-lg hover:bg-slate-800 transition-colors">
            <RefreshCw size={14} />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-slate-600">
            <RefreshCw size={20} className="animate-spin mr-2" /> Loading…
          </div>
        ) : sources.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-600 gap-2">
            <Globe size={32} className="text-slate-700" />
            <p className="text-sm">No sources configured yet.</p>
            <p className="text-xs">Add an auction house URL above to get started.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/50">
            {sources.map(source => (
              <div key={source.id} className={clsx('transition-colors', source.is_active ? '' : 'opacity-50')}>
                {/* Main row */}
                <div className="flex items-center gap-3 px-5 py-3 hover:bg-slate-800/20">
                  {/* Expand toggle */}
                  <button
                    onClick={() => toggleExpand(source.id)}
                    className="text-slate-600 hover:text-slate-400 p-0.5 shrink-0"
                  >
                    {expanded[source.id] ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                  </button>

                  {/* Name + URL */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-white font-medium text-sm">{source.name}</span>
                      <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-lg shrink-0', TYPE_COLOURS[source.source_type] || 'text-slate-400 bg-slate-800')}>
                        {TYPE_LABELS[source.source_type] || source.source_type}
                      </span>
                      <InvestigationBadge status={source.investigation_status} />
                    </div>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-slate-500 hover:text-emerald-400 text-xs transition-colors truncate block mt-0.5"
                      title={source.url}
                    >
                      {source.url.replace(/^https?:\/\//, '').slice(0, 70)}{source.url.length > 78 ? '…' : ''}
                    </a>
                    {source.notes && <p className="text-slate-600 text-xs mt-0.5">{source.notes}</p>}
                  </div>

                  {/* Status + stats */}
                  <div className="hidden md:flex flex-col items-end gap-0.5 shrink-0 min-w-[100px] text-right">
                    <StatusBadge status={source.last_run_status} />
                    <span className="text-slate-600 text-xs">{fmtDate(source.last_run_at)}</span>
                  </div>
                  <div className="hidden sm:block shrink-0 text-right min-w-[70px]">
                    <span className="text-emerald-400 font-semibold text-sm">{source.last_run_properties ?? 0}</span>
                    <span className="text-slate-600 text-xs"> new</span>
                    <p className="text-slate-600 text-xs">{source.total_properties_found ?? 0} total</p>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => handleRun(source.id, source.name)}
                      disabled={running[source.id] || source.last_run_status === 'running'}
                      title="Run scraper now"
                      className="p-1.5 rounded-lg text-slate-500 hover:text-emerald-400 hover:bg-slate-800 disabled:opacity-40 transition-colors"
                    >
                      <Play size={14} className={running[source.id] ? 'animate-pulse' : ''} />
                    </button>
                    <button
                      onClick={() => handleInvestigate(source.id, source.name)}
                      disabled={source.investigation_status === 'running' || source.investigation_status === 'pending'}
                      title="Analyse site structure"
                      className="p-1.5 rounded-lg text-slate-500 hover:text-teal-400 hover:bg-slate-800 disabled:opacity-40 transition-colors"
                    >
                      <Search size={14} />
                    </button>
                    <button
                      onClick={() => handleToggle(source.id)}
                      title={source.is_active ? 'Disable' : 'Enable'}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                    >
                      {source.is_active
                        ? <ToggleRight size={16} className="text-emerald-400" />
                        : <ToggleLeft size={16} />
                      }
                    </button>
                    <button
                      onClick={() => handleDelete(source.id, source.name)}
                      title="Delete"
                      className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-slate-800 transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {/* Error banner */}
                {source.last_run_status === 'error' && source.last_error && (
                  <div className="px-12 pb-2">
                    <p className="text-red-500 text-xs bg-red-500/10 rounded-lg px-3 py-1.5" title={source.last_error}>
                      {source.last_error.slice(0, 200)}
                    </p>
                  </div>
                )}

                {/* Investigation panel */}
                {expanded[source.id] && (
                  <InvestigationPanel
                    source={source}
                    onInvestigate={() => handleInvestigate(source.id, source.name)}
                  />
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Info box */}
      <div className="flex items-start gap-3 bg-slate-900/50 border border-slate-800 rounded-xl p-4">
        <AlertCircle size={16} className="text-amber-400 mt-0.5 shrink-0" />
        <div className="text-xs text-slate-500 space-y-1">
          <p><span className="text-slate-300 font-medium">Site analysis:</span> When you add a source, AssetLens automatically analyses its structure — detecting how many properties are listed, what pagination strategy the site uses, and whether individual property pages contain extra data.</p>
          <p><span className="text-slate-300 font-medium">AJAX / Load More sites:</span> Sites like agentspropertyauction.com load listings via JavaScript. Standard scraping captures only the initial page. Full extraction requires Playwright (headless browser mode).</p>
          <p><span className="text-slate-300 font-medium">robots.txt:</span> Sources that block scraping will be skipped automatically. The 2s rate limit applies between all requests.</p>
        </div>
      </div>
    </div>
  );
}
