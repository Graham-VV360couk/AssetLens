import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import Properties from './pages/Properties';
import PropertyDetail from './pages/PropertyDetail';
import Alerts from './pages/Alerts';
import Scrapers from './pages/Scrapers';
import AdSubmit from './pages/AdSubmit';
import AdminAds from './pages/AdminAds';

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: { background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155' },
        }}
      />
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="properties" element={<Properties />} />
          <Route path="properties/:id" element={<PropertyDetail />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="scrapers" element={
            (process.env.REACT_APP_ADMIN_EMAILS || '').split(',').includes(localStorage.getItem('assetlens_user_email'))
              ? <Scrapers />
              : <Navigate to="/dashboard" replace />
          } />
        </Route>
        <Route path="/advertise" element={<AdSubmit />} />
        <Route path="/admin/ads" element={<AdminAds />} />
      </Routes>
    </BrowserRouter>
  );
}
