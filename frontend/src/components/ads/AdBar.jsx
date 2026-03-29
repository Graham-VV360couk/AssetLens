import React, { useEffect, useState } from 'react';

const AD_CONFIG_URL = '/api/ads/config';

export default function AdBar() {
  const [ad, setAd] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(AD_CONFIG_URL, { signal: controller.signal })
      .then(r => r.json())
      .then(data => { if (data?.enabled) setAd(data); })
      .catch(() => {/* silently hide bar on fetch failure */});
    return () => controller.abort();
  }, []);

  if (!ad) return null;

  const bgStyle = {
    background: `linear-gradient(to right, ${ad.colour_1 || '#1a1a2e'}, ${ad.colour_2 || '#1a1a2e'})`,
    color: ad.text_colour || '#ffffff',
  };

  return (
    <aside
      aria-label="Advertisement"
      style={{ height: '50px', zIndex: 9999, ...bgStyle }}
      className="fixed bottom-0 left-0 right-0 flex items-center overflow-hidden"
    >
      {/* Content */}
      <div className="flex items-center w-full px-4 lg:pl-64 gap-3">
        {/* Logo */}
        {ad.logo_url && (
          <img
            src={ad.logo_url}
            alt={ad.advertiser_name || 'Advertiser'}
            className="h-7 w-auto object-contain flex-shrink-0"
          />
        )}

        {/* Strapline */}
        <p
          className="flex-1 text-center font-medium leading-tight line-clamp-2 lg:line-clamp-1 text-[10px] lg:text-sm"
          style={{ color: ad.text_colour || '#ffffff' }}
        >
          {ad.strapline}
        </p>

        {/* CTA */}
        {ad.cta_url?.startsWith('http') && ad.cta_label && (
          <a
            href={ad.cta_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0 bg-emerald-500 hover:bg-emerald-400 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap"
          >
            {ad.cta_label} →
          </a>
        )}
      </div>
    </aside>
  );
}
