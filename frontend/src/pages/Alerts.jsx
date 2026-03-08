import React, { useEffect, useState } from 'react';
import { Bell, TrendingUp, Star } from 'lucide-react';
import PropertyCard from '../components/ui/PropertyCard';
import LoadingSpinner from '../components/ui/LoadingSpinner';

export default function Alerts() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/properties/high-value?page_size=30')
      .then(r => r.json())
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
          <Bell size={20} className="text-amber-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">High-Value Alerts</h1>
          <p className="text-slate-400 text-sm">Properties with investment score ≥ 70</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <LoadingSpinner size={36} className="text-emerald-500" />
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 rounded-xl px-4 py-2.5">
            <Star size={14} className="text-amber-400" />
            <span className="text-amber-300 text-sm font-medium">
              {data?.total ?? 0} high-value opportunities identified
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {data?.items?.map(prop => (
              <PropertyCard key={prop.id} property={prop} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
