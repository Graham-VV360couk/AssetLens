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
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/auth/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import Account from './pages/Account';
import Neighbourhood from './pages/Neighbourhood';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster
          position="top-right"
          toastOptions={{
            style: { background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155' },
          }}
        />
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="properties" element={<Properties />} />
            <Route path="properties/:id" element={<PropertyDetail />} />
            <Route path="neighbourhood" element={<Neighbourhood />} />
            <Route path="neighbourhood/:postcode" element={<Neighbourhood />} />
            <Route path="alerts" element={<ProtectedRoute><Alerts /></ProtectedRoute>} />
            <Route path="account" element={<ProtectedRoute><Account /></ProtectedRoute>} />
            <Route path="scrapers" element={
              (process.env.REACT_APP_ADMIN_EMAILS || '').split(',').includes(localStorage.getItem('assetlens_user_email'))
                ? <Scrapers />
                : <Navigate to="/dashboard" replace />
            } />
          </Route>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/advertise" element={<AdSubmit />} />
          <Route path="/admin/ads" element={<AdminAds />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
