import React, { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix default marker icons (Leaflet + webpack issue)
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom coloured markers
function createIcon(color, size = 12) {
  return L.divIcon({
    className: '',
    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.4)"></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

const ICONS = {
  home: createIcon('#3b82f6', 18),         // blue — center point
  school_primary: createIcon('#10b981', 10),  // green
  school_secondary: createIcon('#f59e0b', 10), // amber
  school_other: createIcon('#8b5cf6', 10),    // purple
  station: createIcon('#ef4444', 12),          // red
  bus: createIcon('#22c55e', 6),               // small green
  property: createIcon('#60a5fa', 10),         // light blue
  planning: createIcon('#f97316', 8),          // orange
};

function schoolIcon(phase) {
  if (!phase) return ICONS.school_other;
  const p = phase.toLowerCase();
  if (p.includes('primary') || p.includes('infant') || p.includes('junior')) return ICONS.school_primary;
  if (p.includes('secondary')) return ICONS.school_secondary;
  return ICONS.school_other;
}

// Heat map layer for crime data
function HeatLayer({ points, options = {} }) {
  const map = useMap();
  const layerRef = useRef(null);

  useEffect(() => {
    if (!points || points.length === 0) return;

    import('leaflet.heat').then(() => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
      }
      layerRef.current = L.heatLayer(points, {
        radius: 20,
        blur: 15,
        maxZoom: 17,
        max: 1.0,
        gradient: { 0.2: '#22c55e', 0.4: '#f59e0b', 0.6: '#f97316', 0.8: '#ef4444', 1.0: '#991b1b' },
        ...options,
      }).addTo(map);
    });

    return () => {
      if (layerRef.current) {
        map.removeLayer(layerRef.current);
      }
    };
  }, [map, points, options]);

  return null;
}

// Auto-fit bounds to markers
function FitBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds && bounds.length > 0) {
      map.fitBounds(bounds, { padding: [30, 30], maxZoom: 15 });
    }
  }, [map, bounds]);
  return null;
}

export default function NeighbourhoodMap({
  center,           // { lat, lng }
  schools = [],     // [{ name, phase, distance_mi, latitude?, longitude? }]  — lat/lng from postcode lookup
  transport = [],   // [{ name, stop_type, distance_mi, latitude, longitude }]
  planning = [],    // [{ dataset, name, distance_mi, latitude?, longitude? }]
  crimePoints = [], // [[lat, lng, intensity], ...]
  nearbyProperties = [], // [{ id, address, asking_price, latitude, longitude, distance_mi }]
  height = '500px',
  showLegend = true,
}) {
  if (!center || !center.lat || !center.lng) {
    return (
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-8 text-center text-slate-500">
        No coordinates available for map
      </div>
    );
  }

  // Collect all points for bounds
  const allPoints = [[center.lat, center.lng]];
  transport.forEach(t => { if (t.latitude) allPoints.push([t.latitude, t.longitude]); });
  nearbyProperties.forEach(p => { if (p.latitude) allPoints.push([p.latitude, p.longitude]); });

  return (
    <div className="relative rounded-xl overflow-hidden border border-slate-700/50">
      <MapContainer
        center={[center.lat, center.lng]}
        zoom={14}
        style={{ height, width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        <FitBounds bounds={allPoints.length > 1 ? allPoints : null} />

        {/* Crime heat map */}
        {crimePoints.length > 0 && <HeatLayer points={crimePoints} />}

        {/* Center marker */}
        <Marker position={[center.lat, center.lng]} icon={ICONS.home}>
          <Popup><strong>Search location</strong></Popup>
        </Marker>

        {/* Schools */}
        {schools.map((s, i) => {
          // Schools don't have lat/lng directly — we'd need to resolve via postcode
          // For now, skip schools without coordinates
          if (!s.latitude || !s.longitude) return null;
          return (
            <Marker key={`school-${i}`} position={[s.latitude, s.longitude]} icon={schoolIcon(s.phase)}>
              <Popup>
                <div className="text-xs">
                  <strong>{s.name}</strong><br />
                  {s.phase} &middot; {s.distance_mi}mi
                  {s.is_selective && <><br />Selective</>}
                  {s.number_of_pupils && <><br />{s.number_of_pupils} pupils</>}
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Transport */}
        {transport.map((t, i) => {
          if (!t.latitude || !t.longitude) return null;
          const icon = t.stop_type === 'BCT' ? ICONS.bus : ICONS.station;
          return (
            <Marker key={`transport-${i}`} position={[t.latitude, t.longitude]} icon={icon}>
              <Popup>
                <div className="text-xs">
                  <strong>{t.name}</strong><br />
                  {t.stop_type === 'BCT' ? 'Bus Stop' : 'Station'} &middot; {t.distance_mi}mi
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Nearby properties */}
        {nearbyProperties.map((p, i) => {
          if (!p.latitude || !p.longitude) return null;
          return (
            <Marker key={`prop-${i}`} position={[p.latitude, p.longitude]} icon={ICONS.property}>
              <Popup>
                <div className="text-xs">
                  <strong>{p.address?.substring(0, 40)}</strong><br />
                  {p.asking_price ? `£${p.asking_price.toLocaleString()}` : ''} &middot; {p.distance_mi}mi
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Planning — show as circles */}
        {planning.map((p, i) => {
          if (!p.latitude || !p.longitude) return null;
          const colors = {
            'flood-risk-zone': '#ef4444',
            'conservation-area': '#f59e0b',
            'green-belt': '#22c55e',
            'article-4-direction-area': '#8b5cf6',
            'listed-building': '#3b82f6',
          };
          return (
            <Circle
              key={`plan-${i}`}
              center={[p.latitude, p.longitude]}
              radius={50}
              pathOptions={{
                color: colors[p.dataset] || '#f97316',
                fillOpacity: 0.3,
                weight: 1,
              }}
            >
              <Popup>
                <div className="text-xs">
                  <strong>{p.dataset.replace(/-/g, ' ')}</strong><br />
                  {p.name && <>{p.name}<br /></>}
                  {p.flood_risk_level && <>Level {p.flood_risk_level}<br /></>}
                  {p.listed_building_grade && <>Grade {p.listed_building_grade}<br /></>}
                  {p.distance_mi}mi
                </div>
              </Popup>
            </Circle>
          );
        })}
      </MapContainer>

      {/* Legend */}
      {showLegend && (
        <div className="absolute bottom-3 right-3 z-[1000] bg-slate-900/90 border border-slate-700 rounded-lg px-3 py-2 text-xs space-y-1">
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-blue-500 inline-block" /> Search point</div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-emerald-500 inline-block" /> Primary school</div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-amber-500 inline-block" /> Secondary school</div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-red-500 inline-block" /> Station</div>
          <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-green-500 inline-block" /> Bus stop</div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-blue-400 inline-block" /> For sale</div>
          {crimePoints.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 inline-block rounded" style={{ background: 'linear-gradient(to right, #22c55e, #f59e0b, #ef4444)' }} />
              Crime heat
            </div>
          )}
        </div>
      )}
    </div>
  );
}
