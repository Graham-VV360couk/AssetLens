import React, { useState } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Building2, Bell, Globe, Menu, X, Activity
} from 'lucide-react';
import clsx from 'clsx';
import AdBar from '../ads/AdBar';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/properties', icon: Building2, label: 'Properties' },
  { to: '/alerts', icon: Bell, label: 'Alerts' },
  { to: '/scrapers', icon: Globe, label: 'Data Sources' },
];

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden">
      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 border-r border-slate-800 transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0 flex flex-col',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-800">
          <div className="w-9 h-9 rounded-xl bg-emerald-500 flex items-center justify-center">
            <Activity size={20} className="text-white" />
          </div>
          <div>
            <span className="text-white font-bold text-lg tracking-tight">AssetLens</span>
            <p className="text-slate-500 text-xs">Property Intelligence</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-150',
                  isActive
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                )
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-800">
          <p className="text-slate-600 text-xs">
            Data: Land Registry © Crown copyright
          </p>
          <p className="text-slate-600 text-xs mt-0.5">AssetLens v1.0</p>
        </div>
      </aside>

      {/* Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 bg-slate-900 border-b border-slate-800 lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-slate-800"
          >
            <Menu size={20} />
          </button>
          <span className="text-white font-bold">AssetLens</span>
          <div className="w-9" />
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto pb-[50px]">
          <Outlet />
        </main>
      </div>
      <AdBar />
    </div>
  );
}
