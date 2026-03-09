import React, { useEffect, useState } from 'react';
import {
  Plus, Play, Trash2, ToggleLeft, ToggleRight, Globe, RefreshCw,
  CheckCircle, XCircle, Clock, AlertCircle, Search, ChevronDown, ChevronUp,
  Layers, Link2, ArrowRight, Zap, Pencil, Save, X, FileText, HelpCircle,
  Lightbulb, BookOpen, Terminal
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
    standard_next:  { colour: 'text-emerald-400 bg-emerald-400/10', label: 'Next-page nav' },
    numbered:       { colour: 'text-emerald-400 bg-emerald-400/10', label: 'Numbered pages' },
    query_param:    { colour: 'text-emerald-400 bg-emerald-400/10', label: '?page=N' },
    ajax_load_more: { colour: 'text-amber-400 bg-amber-400/10',     label: 'AJAX / Load More' },
    single_page:    { colour: 'text-slate-400 bg-slate-800',        label: 'Single page' },
    unknown:        { colour: 'text-slate-400 bg-slate-800',        label: 'Unknown' },
  };
  const { colour, label } = map[type] || map.unknown;
  return <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-lg', colour)}>{label}</span>;
}

function EditPanel({ source, onSave, onCancel }) {
  const [form, setForm] = useState({
    name: source.name,
    url: source.url,
    source_type: source.source_type,
    max_pages: source.max_pages,
    notes: source.notes || '',
    scrape_detail_pages: source.scrape_detail_pages || false,
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!form.name.trim() || !form.url.trim()) return toast.error('Name and URL required');
    setSaving(true);
    try {
      await onSave(form);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="border-t border-slate-800 bg-slate-800/30 px-5 py-4 space-y-3">
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
        <Pencil size={12} className="text-emerald-400" /> Edit Source
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-slate-500 block mb-1">Name</label>
          <input
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
          />
        </div>
        <div>
          <label className="text-xs text-slate-500 block mb-1">Source Type</label>
          <select
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
            value={form.source_type}
            onChange={e => setForm(f => ({ ...f, source_type: e.target.value }))}
          >
            <option value="auction">Auction</option>
            <option value="estate_agent">Estate Agent</option>
            <option value="rental">Rental</option>
          </select>
        </div>
        <div className="md:col-span-2">
          <label className="text-xs text-slate-500 block mb-1">URL</label>
          <input
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            value={form.url}
            onChange={e => setForm(f => ({ ...f, url: e.target.value }))}
          />
        </div>
        <div>
          <label className="text-xs text-slate-500 block mb-1">Max pages per scrape run</label>
          <input
            type="number" min={1} max={50}
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
            value={form.max_pages}
            onChange={e => setForm(f => ({ ...f, max_pages: parseInt(e.target.value) || 1 }))}
          />
          <p className="text-xs text-slate-600 mt-1">For AJAX/Load More sites, each "page" = one Load More click (~9 properties).</p>
        </div>
        <div>
          <label className="text-xs text-slate-500 block mb-1">Notes</label>
          <input
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            value={form.notes}
            onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
          />
        </div>
      </div>

      {/* Detail pages toggle */}
      <div className="flex items-start gap-3 bg-slate-800 rounded-xl p-3">
        <button
          type="button"
          onClick={() => setForm(f => ({ ...f, scrape_detail_pages: !f.scrape_detail_pages }))}
          className="mt-0.5 shrink-0"
        >
          {form.scrape_detail_pages
            ? <ToggleRight size={22} className="text-emerald-400" />
            : <ToggleLeft size={22} className="text-slate-500" />
          }
        </button>
        <div>
          <p className="text-sm text-white font-medium">Fetch detail pages</p>
          <p className="text-xs text-slate-500 mt-0.5">
            Follow each property link to scrape extra fields: description, tenure, legal pack URL, lot reference.
            Adds ~2s per property — 100 properties ≈ 3 extra minutes per run.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-white text-sm font-semibold rounded-xl px-4 py-2 transition-colors"
        >
          {saving ? <RefreshCw size={13} className="animate-spin" /> : <Save size={13} />}
          Save
        </button>
        <button
          onClick={onCancel}
          className="flex items-center gap-2 text-slate-400 hover:text-slate-200 text-sm rounded-xl px-4 py-2 hover:bg-slate-800 transition-colors"
        >
          <X size={13} /> Cancel
        </button>
      </div>
    </div>
  );
}

function StrategyBadge({ strategy }) {
  if (!strategy) return null;
  const type = strategy.type;
  if (type === 'all_results_url') return (
    <span className="flex items-center gap-1 text-xs text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-lg font-medium">
      <CheckCircle size={11} /> All-results URL saved
    </span>
  );
  if (type === 'pagination_template') {
    const tmpl = strategy.pagination_template || {};
    return (
      <span className="flex items-center gap-1 text-xs text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-lg font-medium" title={tmpl.template}>
        <CheckCircle size={11} /> Pagination template saved
      </span>
    );
  }
  return null;
}

function HintPanel({ sourceId, onSaved }) {
  const [mode, setMode] = useState(null); // 'all' | 'pages'
  const [allUrl, setAllUrl] = useState('');
  const [pageUrls, setPageUrls] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const submit = async () => {
    setError('');
    setSaving(true);
    try {
      const payload = mode === 'all'
        ? { all_results_url: allUrl.trim() }
        : { page_urls: pageUrls.split('\n').map(u => u.trim()).filter(Boolean) };
      const updated = await scrapersApi.hint(sourceId, payload);
      onSaved(updated);
      setMode(null);
    } catch (e) {
      setError(e.message || 'Failed to save hint');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="border border-dashed border-slate-700 rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Lightbulb size={13} className="text-amber-400 shrink-0" />
        <p className="text-xs text-slate-400 font-medium">Help configure scraping for this site</p>
      </div>
      <p className="text-xs text-slate-500">
        If automatic detection isn't finding all properties, you can give us a hint — either a URL that shows everything at once, or a few page URLs so we can learn the pattern.
      </p>

      {!mode && (
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setMode('all')}
            className="flex items-center gap-1.5 text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 px-3 py-1.5 rounded-lg transition-colors"
          >
            <Globe size={11} /> I have a "show all" URL
          </button>
          <button
            onClick={() => setMode('pages')}
            className="flex items-center gap-1.5 text-xs bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 px-3 py-1.5 rounded-lg transition-colors"
          >
            <BookOpen size={11} /> I have 2–3 page URLs
          </button>
        </div>
      )}

      {mode === 'all' && (
        <div className="space-y-2">
          <label className="text-xs text-slate-500 block">
            URL that returns all results on one page (e.g. <code className="text-slate-400">?size=500</code>, <code className="text-slate-400">?per_page=all</code>)
          </label>
          <input
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            placeholder="https://example.com/properties?size=500"
            value={allUrl}
            onChange={e => setAllUrl(e.target.value)}
          />
          <div className="flex gap-2">
            <button onClick={submit} disabled={!allUrl.trim() || saving}
              className="flex items-center gap-1.5 text-xs bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-white px-3 py-1.5 rounded-lg transition-colors font-medium">
              {saving ? <RefreshCw size={11} className="animate-spin" /> : <Save size={11} />} Save
            </button>
            <button onClick={() => setMode(null)} className="text-xs text-slate-500 hover:text-slate-300 px-2 py-1.5">Cancel</button>
          </div>
        </div>
      )}

      {mode === 'pages' && (
        <div className="space-y-2">
          <label className="text-xs text-slate-500 block">
            Paste 2–3 page URLs, one per line — we'll work out the pattern automatically
          </label>
          <textarea
            rows={3}
            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
            placeholder={`https://example.com/property-search/3/?submit=1\nhttps://example.com/property-search/4/?submit=1\nhttps://example.com/property-search/5/?submit=1`}
            value={pageUrls}
            onChange={e => setPageUrls(e.target.value)}
          />
          <div className="flex gap-2">
            <button onClick={submit} disabled={pageUrls.split('\n').filter(u => u.trim()).length < 2 || saving}
              className="flex items-center gap-1.5 text-xs bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-white px-3 py-1.5 rounded-lg transition-colors font-medium">
              {saving ? <RefreshCw size={11} className="animate-spin" /> : <Save size={11} />} Derive pattern
            </button>
            <button onClick={() => setMode(null)} className="text-xs text-slate-500 hover:text-slate-300 px-2 py-1.5">Cancel</button>
          </div>
        </div>
      )}

      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}

function InvestigationPanel({ source, onInvestigate, onSourceUpdated }) {
  const data = source.investigation_data ? (() => {
    try { return JSON.parse(source.investigation_data); } catch { return null; }
  })() : null;

  const [showHint, setShowHint] = useState(false);

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
      <div className="px-5 py-4 bg-slate-800/30 border-t border-slate-800 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-slate-500 text-sm">No investigation data yet.</span>
          <button onClick={onInvestigate}
            className="flex items-center gap-1.5 text-xs text-teal-400 hover:text-teal-300 bg-teal-400/10 hover:bg-teal-400/20 px-3 py-1.5 rounded-lg transition-colors">
            <Search size={12} /> Analyse Site
          </button>
        </div>
        <HintPanel sourceId={source.id} onSaved={updated => { onSourceUpdated(updated); setShowHint(false); }} />
      </div>
    );
  }

  const pagination = data.pagination || {};
  const cards = data.property_cards || {};
  const detail = data.detail_page || {};
  const ajax = data.ajax_indicators || [];
  const recs = data.recommendations || [];
  const strategy = data.strategy || null;

  // Show hint panel when: no cards found, or explicitly opened
  const needsHelp = (cards.count === 0 || cards.count == null) && !strategy;

  return (
    <div className="border-t border-slate-800 bg-slate-800/20 px-5 py-4 space-y-4">
      {/* Strategy confirmed banner */}
      {strategy && (
        <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-3 py-2.5">
          <CheckCircle size={14} className="text-emerald-400 shrink-0" />
          <div className="flex-1 min-w-0">
            {strategy.type === 'all_results_url' && (
              <p className="text-xs text-emerald-300 font-medium">
                Using all-results URL: <span className="font-mono text-emerald-400/80 truncate">{strategy.all_results_url}</span>
              </p>
            )}
            {strategy.type === 'pagination_template' && (
              <>
                <p className="text-xs text-emerald-300 font-medium">
                  Using pagination template: <span className="font-mono text-emerald-400/80">{strategy.pagination_template?.template}</span>
                </p>
                <p className="text-xs text-emerald-400/60 mt-0.5">
                  Start page {strategy.pagination_template?.start_page} · derived from pages {strategy.pagination_template?.sample_pages?.join(', ')}
                </p>
              </>
            )}
          </div>
          <button onClick={() => setShowHint(h => !h)}
            className="text-xs text-slate-500 hover:text-slate-300 shrink-0 transition-colors">
            {showHint ? 'Cancel' : 'Change'}
          </button>
        </div>
      )}

      <div className="flex flex-wrap gap-4 text-xs">
        <div className="flex items-center gap-2">
          <Layers size={13} className="text-slate-500" />
          <span className="text-slate-400">Cards found:</span>
          <span className={clsx('font-semibold', (cards.count ?? 0) > 0 ? 'text-white' : 'text-amber-400')}>
            {cards.count ?? '?'}
          </span>
          {cards.selector && <span className="text-slate-600">({cards.selector})</span>}
        </div>
        <div className="flex items-center gap-2">
          <Globe size={13} className="text-slate-500" />
          <span className="text-slate-400">Pagination:</span>
          <PaginationTypeBadge type={pagination.type} />
          {pagination.max_page_found > 1 && (
            <span className="text-slate-600">{pagination.max_page_found} pages detected</span>
          )}
        </div>
        {detail.has_detail_page !== undefined && (
          <div className="flex items-center gap-2">
            <Link2 size={13} className="text-slate-500" />
            <span className="text-slate-400">Detail pages:</span>
            {detail.has_detail_page
              ? <span className="text-emerald-400 font-medium">Extra data available</span>
              : <span className="text-slate-500">No extra data</span>
            }
          </div>
        )}
      </div>

      {detail.extra_fields_available && detail.extra_fields_available.length > 0 && (
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-xs text-slate-500">Fields on detail pages:</span>
          {detail.extra_fields_available.map(f => (
            <span key={f} className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded-md">{f}</span>
          ))}
          {!source.scrape_detail_pages && (
            <span className="text-xs text-amber-400/70 ml-1">(enable "Fetch detail pages" in settings)</span>
          )}
        </div>
      )}

      {ajax.length > 0 && (
        <div className="flex items-start gap-2">
          <Zap size={13} className="text-amber-400 mt-0.5 shrink-0" />
          <div className="text-xs text-amber-400/80 space-y-0.5">
            {ajax.map((a, i) => <p key={i}>{a}</p>)}
          </div>
        </div>
      )}

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

      {/* Hint panel — shown when no cards found OR user clicks help */}
      {(needsHelp || showHint) && !strategy && (
        <HintPanel sourceId={source.id} onSaved={updated => { onSourceUpdated(updated); setShowHint(false); }} />
      )}
      {showHint && strategy && (
        <HintPanel sourceId={source.id} onSaved={updated => { onSourceUpdated(updated); setShowHint(false); }} />
      )}

      <div className="flex items-center justify-between pt-1">
        {data.analysed_at && (
          <span className="text-xs text-slate-600">
            Analysed {new Date(data.analysed_at).toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'short' })}
          </span>
        )}
        <div className="flex items-center gap-3">
          {!needsHelp && !strategy && (
            <button onClick={() => setShowHint(h => !h)}
              className="flex items-center gap-1 text-xs text-slate-600 hover:text-amber-400 transition-colors">
              <HelpCircle size={11} /> Help configure
            </button>
          )}
          <button onClick={onInvestigate}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-teal-400 transition-colors">
            <RefreshCw size={11} /> Re-analyse
          </button>
        </div>
      </div>
    </div>
  );
}

function StrategyLibraryPanel() {
  const [open, setOpen] = useState(false);
  const [library, setLibrary] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await scrapersApi.getLibrary();
      setLibrary(data);
    } catch { /* silent */ }
    finally { setLoading(false); }
  };

  const toggle = () => {
    setOpen(o => !o);
    if (!open && !library) load();
  };

  const typeColour = (type) => type === 'all_results_url'
    ? 'text-blue-400 bg-blue-400/10'
    : 'text-purple-400 bg-purple-400/10';
  const typeLabel = (type) => type === 'all_results_url' ? 'Single page' : 'Pagination';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
      <button
        onClick={toggle}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-800/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <BookOpen size={16} className="text-teal-400" />
          <span className="text-sm font-semibold text-slate-300">Strategy Library</span>
          {library && (
            <span className="text-xs text-slate-500 font-normal ml-1">
              — {library.filter(p => p.success_count > 0).length} proven patterns
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-600">Patterns tried automatically when scraping a new site</span>
          {open ? <ChevronUp size={14} className="text-slate-500" /> : <ChevronDown size={14} className="text-slate-500" />}
        </div>
      </button>

      {open && (
        <div className="border-t border-slate-800 px-5 py-4">
          {loading && (
            <div className="flex items-center gap-2 text-slate-500 text-sm py-4 justify-center">
              <RefreshCw size={14} className="animate-spin" /> Loading…
            </div>
          )}
          {library && (
            <div className="space-y-2">
              <p className="text-xs text-slate-500 mb-3">
                When a new site is added and auto-detection finds fewer than 5 properties, these probes are tried automatically in order of past success. Confirmed hints and successful scrapes add to the counts.
              </p>
              <div className="grid gap-2">
                {library.map(probe => (
                  <div key={probe.probe_id}
                    className={clsx(
                      'flex items-center gap-3 rounded-xl px-3 py-2.5 border',
                      probe.success_count > 0
                        ? 'border-slate-700 bg-slate-800/50'
                        : 'border-slate-800 bg-slate-900/50 opacity-60'
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-white text-xs font-medium">{probe.name}</span>
                        <span className={clsx('text-xs px-1.5 py-0.5 rounded font-medium', typeColour(probe.type))}>
                          {typeLabel(probe.type)}
                        </span>
                        {probe.domains.length > 0 && (
                          <span className="text-slate-600 text-xs" title={probe.domains.join(', ')}>
                            {probe.domains[0]}{probe.domains.length > 1 ? ` +${probe.domains.length - 1}` : ''}
                          </span>
                        )}
                      </div>
                      <p className="text-slate-600 text-xs mt-0.5">{probe.description}</p>
                    </div>
                    <div className="text-right shrink-0 min-w-[70px]">
                      {probe.success_count > 0 ? (
                        <>
                          <div className="text-emerald-400 text-sm font-semibold">{probe.success_count} ✓</div>
                          {probe.fail_count > 0 && <div className="text-slate-600 text-xs">{probe.fail_count} ✗</div>}
                        </>
                      ) : (
                        <span className="text-slate-700 text-xs">untried</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RunLogPane({ sourceId, isRunning }) {
  const [logs, setLogs] = useState([]);
  const [open, setOpen] = useState(true);
  const bottomRef = React.useRef(null);

  useEffect(() => {
    if (!sourceId) return;
    let cancelled = false;
    const poll = async () => {
      try {
        const data = await scrapersApi.getLogs(sourceId);
        if (!cancelled) setLogs(data);
      } catch { /* ignore */ }
    };
    poll();
    if (!isRunning) return;
    const timer = setInterval(poll, 2000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [sourceId, isRunning]);

  useEffect(() => {
    if (open && bottomRef.current) bottomRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [logs, open]);

  const levelColour = (level) => ({
    error:   'text-red-400',
    warning: 'text-amber-400',
    info:    'text-slate-300',
    debug:   'text-slate-600',
  }[level] || 'text-slate-400');

  if (logs.length === 0 && !isRunning) return null;

  return (
    <div className="mx-4 mb-2 rounded-xl border border-slate-800 bg-slate-950 overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-500 hover:text-slate-300 transition-colors"
      >
        <Terminal size={11} className={isRunning ? 'text-blue-400 animate-pulse' : 'text-slate-600'} />
        <span className="font-medium">Run log</span>
        {isRunning && <span className="text-blue-400 animate-pulse ml-1">● live</span>}
        <span className="ml-auto text-slate-700">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 max-h-52 overflow-y-auto font-mono text-xs space-y-0.5">
          {logs.map((log, i) => (
            <div key={i} className="flex gap-2 leading-relaxed">
              <span className="text-slate-700 shrink-0 select-none">
                {new Date(log.created_at).toLocaleTimeString('en-GB')}
              </span>
              <span className={clsx('shrink-0 uppercase w-12', levelColour(log.level))}>{log.level}</span>
              <span className={levelColour(log.level)}>{log.message}</span>
            </div>
          ))}
          {logs.length === 0 && (
            <p className="text-slate-700 py-2">Waiting for logs…</p>
          )}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}

const EMPTY_FORM = { name: '', url: '', source_type: 'auction', max_pages: 5, notes: '', scrape_detail_pages: false };

export default function Scrapers() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(EMPTY_FORM);
  const [adding, setAdding] = useState(false);
  const [running, setRunning] = useState({});
  const [expanded, setExpanded] = useState({});  // which rows show investigation panel
  const [editing, setEditing] = useState({});     // which rows show edit panel

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

  const handleSave = async (id, payload) => {
    try {
      const updated = await scrapersApi.update(id, payload);
      setSources(prev => prev.map(s => s.id === id ? updated : s));
      setEditing(prev => ({ ...prev, [id]: false }));
      toast.success('Settings saved');
    } catch {
      toast.error('Failed to save');
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
      setEditing(prev => ({ ...prev, [id]: false }));
      toast.success(`Analysing ${name}…`);
    } catch (err) {
      toast.error(err.message || 'Failed to start investigation');
    }
  };

  const toggleExpand = (id) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
    if (editing[id]) setEditing(prev => ({ ...prev, [id]: false }));
  };

  const toggleEdit = (id) => {
    setEditing(prev => ({ ...prev, [id]: !prev[id] }));
    if (expanded[id]) setExpanded(prev => ({ ...prev, [id]: false }));
  };

  const fmtDate = (d) => d
    ? new Date(d).toLocaleString('en-GB', { dateStyle: 'short', timeStyle: 'short' })
    : '—';

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
            className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
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
              type="number" min={1} max={50}
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
                    title="Show analysis"
                  >
                    {expanded[source.id] ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                  </button>

                  {/* Name + URL + badges */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-white font-medium text-sm">{source.name}</span>
                      <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-lg shrink-0', TYPE_COLOURS[source.source_type] || 'text-slate-400 bg-slate-800')}>
                        {TYPE_LABELS[source.source_type] || source.source_type}
                      </span>
                      {/* max_pages badge */}
                      <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded-lg shrink-0" title="Max pages per scrape run">
                        {source.max_pages}p
                      </span>
                      {/* detail pages indicator */}
                      {source.scrape_detail_pages && (
                        <span className="flex items-center gap-1 text-xs text-purple-400 bg-purple-400/10 px-2 py-0.5 rounded-lg shrink-0" title="Fetching detail pages">
                          <FileText size={10} /> details
                        </span>
                      )}
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
                      onClick={() => toggleEdit(source.id)}
                      title="Edit settings"
                      className={clsx(
                        'p-1.5 rounded-lg hover:bg-slate-800 transition-colors',
                        editing[source.id] ? 'text-emerald-400' : 'text-slate-500 hover:text-slate-200'
                      )}
                    >
                      <Pencil size={14} />
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
                {/* Save error (success run but some listings failed) */}
                {source.last_run_status === 'success' && source.last_error && (
                  <div className="px-12 pb-2">
                    <p className="text-amber-500 text-xs bg-amber-500/10 rounded-lg px-3 py-1.5" title={source.last_error}>
                      Some listings had save errors: {source.last_error.slice(0, 150)}
                    </p>
                  </div>
                )}

                {/* Edit panel */}
                {editing[source.id] && (
                  <EditPanel
                    source={source}
                    onSave={(payload) => handleSave(source.id, payload)}
                    onCancel={() => setEditing(prev => ({ ...prev, [source.id]: false }))}
                  />
                )}

                {/* Investigation panel */}
                {expanded[source.id] && !editing[source.id] && (
                  <InvestigationPanel
                    source={source}
                    onInvestigate={() => handleInvestigate(source.id, source.name)}
                    onSourceUpdated={updated => setSources(prev => prev.map(s => s.id === updated.id ? updated : s))}
                  />
                )}

                {/* Live run log */}
                <RunLogPane
                  sourceId={source.id}
                  isRunning={running[source.id] || source.last_run_status === 'running'}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Strategy Library */}
      <StrategyLibraryPanel />

      {/* Info box */}
      <div className="flex items-start gap-3 bg-slate-900/50 border border-slate-800 rounded-xl p-4">
        <AlertCircle size={16} className="text-amber-400 mt-0.5 shrink-0" />
        <div className="text-xs text-slate-500 space-y-1">
          <p><span className="text-slate-300 font-medium">Site analysis:</span> When you add a source, AssetLens automatically analyses its structure — detecting pagination, card selectors, and whether property detail pages contain extra data.</p>
          <p><span className="text-slate-300 font-medium">Can't find all properties?</span> Open the analysis panel (▾) and use "Help configure scraping". Either paste a URL that shows all results at once (e.g. <code className="text-slate-400">?size=500</code>), or paste 2–3 page URLs and the system will derive the pagination pattern automatically.</p>
          <p><span className="text-slate-300 font-medium">Detail pages:</span> Enable "Fetch detail pages" in settings to collect description, tenure, and legal pack URLs from individual property pages. Adds ~2s per property per run.</p>
        </div>
      </div>
    </div>
  );
}
