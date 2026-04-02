import { useState } from 'react';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';

export default function ImageGallery({ imageUrl, imageUrls, alt }) {
  const [lightboxIdx, setLightboxIdx] = useState(null);

  let images = [];
  if (imageUrls) {
    try {
      images = JSON.parse(imageUrls);
    } catch {
      images = [];
    }
  }
  if (!images.length && imageUrl) {
    images = [imageUrl];
  }
  if (!images.length) return null;

  const openLightbox = (idx) => setLightboxIdx(idx);
  const closeLightbox = () => setLightboxIdx(null);
  const prev = () => setLightboxIdx((i) => (i > 0 ? i - 1 : images.length - 1));
  const next = () => setLightboxIdx((i) => (i < images.length - 1 ? i + 1 : 0));

  return (
    <>
      {/* Hero image */}
      <div
        className="h-64 w-full overflow-hidden bg-slate-900 rounded-b-2xl cursor-pointer"
        onClick={() => openLightbox(0)}
      >
        <img
          src={images[0]}
          alt={alt}
          className="w-full h-full object-cover"
          onError={(e) => { e.target.parentElement.style.display = 'none'; }}
        />
      </div>

      {/* Thumbnail strip (if more than 1 image) */}
      {images.length > 1 && (
        <div className="flex gap-2 px-6 overflow-x-auto py-1">
          {images.slice(0, 10).map((src, idx) => (
            <button
              key={idx}
              onClick={() => openLightbox(idx)}
              className={`flex-shrink-0 w-16 h-12 rounded-lg overflow-hidden border-2 transition-colors ${
                lightboxIdx === idx ? 'border-emerald-500' : 'border-transparent hover:border-slate-600'
              }`}
            >
              <img src={src} alt={`${alt} ${idx + 1}`} className="w-full h-full object-cover" />
            </button>
          ))}
          {images.length > 10 && (
            <span className="flex items-center text-xs text-slate-500 px-2">
              +{images.length - 10} more
            </span>
          )}
        </div>
      )}

      {/* Lightbox overlay */}
      {lightboxIdx !== null && (
        <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center" onClick={closeLightbox}>
          <button
            onClick={(e) => { e.stopPropagation(); closeLightbox(); }}
            className="absolute top-4 right-4 text-white/70 hover:text-white p-2"
          >
            <X size={24} />
          </button>
          {images.length > 1 && (
            <>
              <button
                onClick={(e) => { e.stopPropagation(); prev(); }}
                className="absolute left-4 text-white/70 hover:text-white p-2"
              >
                <ChevronLeft size={32} />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); next(); }}
                className="absolute right-4 text-white/70 hover:text-white p-2"
              >
                <ChevronRight size={32} />
              </button>
            </>
          )}
          <img
            src={images[lightboxIdx]}
            alt={`${alt} ${lightboxIdx + 1}`}
            className="max-h-[85vh] max-w-[90vw] object-contain"
            onClick={(e) => e.stopPropagation()}
          />
          <div className="absolute bottom-4 text-white/60 text-sm">
            {lightboxIdx + 1} / {images.length}
          </div>
        </div>
      )}
    </>
  );
}
