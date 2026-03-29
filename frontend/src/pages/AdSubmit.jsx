import React, { useState } from 'react';
import toast from 'react-hot-toast';

export default function AdSubmit() {
  const [form, setForm] = useState({
    advertiser_name: '',
    strapline: '',
    cta_label: '',
    cta_url: '',
    colour_1: '#1a1a2e',
    colour_2: '#1a1a2e',
    submit_token: '',
  });
  const [logo, setLogo] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  function handleChange(e) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!logo) {
      toast.error('Please upload your logo');
      return;
    }

    setSubmitting(true);
    try {
      const data = new FormData();
      data.append('advertiser_name', form.advertiser_name);
      data.append('strapline', form.strapline);
      data.append('cta_label', form.cta_label);
      data.append('cta_url', form.cta_url);
      data.append('colour_1', form.colour_1);
      data.append('colour_2', form.colour_2);
      data.append('logo', logo);

      const res = await fetch('/api/ads/submit', {
        method: 'POST',
        headers: { 'X-Submit-Token': form.submit_token },
        body: data,
      });

      if (res.status === 409) {
        toast.error('A submission is already awaiting approval. Please try again later.');
        return;
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || 'Submission failed');
        return;
      }

      setSubmitted(true);
    } catch {
      toast.error('Network error — please try again');
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 max-w-md w-full text-center">
          <div className="w-12 h-12 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-emerald-400 text-2xl">✓</span>
          </div>
          <h1 className="text-white text-xl font-bold mb-2">Submission received</h1>
          <p className="text-slate-400 text-sm">
            Your advertisement has been submitted and is awaiting approval. You will be notified once it goes live.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 max-w-lg w-full">
        <h1 className="text-white text-xl font-bold mb-1">Advertise on AssetLens</h1>
        <p className="text-slate-400 text-sm mb-6">
          Property-sector advertising for professionals — conveyancing, finance, auctions, and more.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Advertiser name" name="advertiser_name" value={form.advertiser_name} onChange={handleChange} required />
          <Field label="Strapline (max 80 chars)" name="strapline" value={form.strapline} onChange={handleChange} maxLength={80} required />
          <Field label="CTA button label (max 20 chars)" name="cta_label" value={form.cta_label} onChange={handleChange} maxLength={20} required />
          <Field label="CTA URL" name="cta_url" type="url" value={form.cta_url} onChange={handleChange} required />

          <div>
            <label className="block text-slate-400 text-xs font-medium mb-1">
              Logo <span className="text-slate-500">(PNG or SVG recommended, transparent background)</span>
            </label>
            <input
              type="file"
              accept="image/png,image/svg+xml,image/jpeg"
              onChange={e => setLogo(e.target.files[0] || null)}
              className="block w-full text-slate-400 text-sm file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:bg-slate-700 file:text-slate-200 file:text-xs hover:file:bg-slate-600"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-400 text-xs font-medium mb-1">
                Background colour 1 <span className="text-slate-500">(optional)</span>
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  name="colour_1"
                  value={form.colour_1}
                  onChange={handleChange}
                  className="w-10 h-8 rounded cursor-pointer bg-transparent border-0"
                />
                <input
                  type="text"
                  name="colour_1"
                  value={form.colour_1}
                  onChange={handleChange}
                  maxLength={7}
                  className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>
            </div>
            <div>
              <label className="block text-slate-400 text-xs font-medium mb-1">
                Background colour 2 <span className="text-slate-500">(for gradient)</span>
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  name="colour_2"
                  value={form.colour_2}
                  onChange={handleChange}
                  className="w-10 h-8 rounded cursor-pointer bg-transparent border-0"
                />
                <input
                  type="text"
                  name="colour_2"
                  value={form.colour_2}
                  onChange={handleChange}
                  maxLength={7}
                  className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-emerald-500 font-mono"
                />
              </div>
            </div>
          </div>
          <p className="text-slate-500 text-xs -mt-1">Set both colours the same for a solid background. Leave as default for dark navy.</p>

          <Field label="Submission token" name="submit_token" type="password" value={form.submit_token} onChange={handleChange} required />

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-white font-semibold py-2.5 rounded-xl transition-colors"
          >
            {submitting ? 'Submitting…' : 'Submit advertisement'}
          </button>
        </form>
      </div>
    </div>
  );
}

function Field({ label, name, value, onChange, type = 'text', required, maxLength }) {
  return (
    <div>
      <label className="block text-slate-400 text-xs font-medium mb-1">{label}</label>
      <input
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        required={required}
        maxLength={maxLength}
        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 text-sm focus:outline-none focus:border-emerald-500"
      />
    </div>
  );
}
