import React, { useEffect, useState } from 'react';

const AD_CONFIG_URL = '/api/ads/config';

export default function AdBar() {
  const [ad, setAd] = useState(null);

  useEffect(() => {
    fetch(AD_CONFIG_URL)
      .then(r => r.json())
      .then(data => {
        if (data && data.enabled) setAd(data);
      })
      .catch(() => {/* silently hide bar on fetch failure */});
  }, []);

  if (!ad) return null;

  const bgStyle = {
    backgroundColor: ad.background_colour_fallback || '#1a1a2e',
    color: ad.text_colour || '#ffffff',
  };

  return (
    <div
      style={{ height: '50px', zIndex: 9999, ...bgStyle }}
      className="fixed bottom-0 left-0 right-0 flex items-center overflow-hidden"
    >
      {/* Background image via picture element */}
      {(ad.background_image_mobile || ad.background_image_desktop) && (
        <picture className="absolute inset-0 w-full h-full pointer-events-none">
          {ad.background_image_desktop && (
            <source media="(min-width: 1024px)" srcSet={ad.background_image_desktop} />
          )}
          {ad.background_image_mobile && (
            <img
              src={ad.background_image_mobile}
              alt=""
              className="w-full h-full object-cover"
              aria-hidden="true"
            />
          )}
        </picture>
      )}

      {/* Content — relative so it sits above picture */}
      <div className="relative flex items-center w-full px-4 lg:pl-64 gap-3">
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
        {ad.cta_url && ad.cta_label && (
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
    </div>
  );
}
