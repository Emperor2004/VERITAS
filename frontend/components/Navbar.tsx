'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ShieldCheck, FileSpreadsheet, Moon, Sun, ArrowDownToLine, Sparkles } from 'lucide-react';

export default function Navbar() {
  const pathname = usePathname();
  const [isLight, setIsLight] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('veritas_theme');
    if (saved === 'light') {
      setIsLight(true);
      document.documentElement.classList.add('light');
    } else {
      setIsLight(false);
      document.documentElement.classList.remove('light');
    }
  }, []);

  const toggleTheme = () => {
    const next = !isLight;
    setIsLight(next);
    if (next) {
      document.documentElement.classList.add('light');
      localStorage.setItem('veritas_theme', 'light');
    } else {
      document.documentElement.classList.remove('light');
      localStorage.setItem('veritas_theme', 'dark');
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-rule glass-panel">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo & Title */}
        <div className="flex items-center space-x-6">
          <Link href="/" className="flex items-center space-x-3 group">
            <div className="relative w-9 h-9 rounded-lg bg-gradient-to-tr from-emerald-500 via-teal-400 to-cyan-400 flex items-center justify-center text-slate-950 shadow-[0_0_20px_rgba(16,185,129,0.35)] transition-transform group-hover:scale-105">
              <ShieldCheck className="w-5 h-5 stroke-[2.2]" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                  VERITAS
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold tracking-wide">
                  v2.0
                </span>
              </div>
              <span className="text-[10px] tracking-wider uppercase text-ink-soft font-mono">
                Enterprise AI Risk & Governance
              </span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1 pl-4 border-l border-rule">
            <Link
              href="/"
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                pathname === '/'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm'
                  : 'text-ink-soft hover:text-ink hover:bg-white/[0.04]'
              }`}
            >
              Audit Pipeline
            </Link>
            <Link
              href="/runs"
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                pathname.startsWith('/runs') && pathname === '/runs'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm'
                  : 'text-ink-soft hover:text-ink hover:bg-white/[0.04]'
              }`}
            >
              Case Files
            </Link>
            <Link
              href="/method"
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                pathname === '/method'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm'
                  : 'text-ink-soft hover:text-ink hover:bg-white/[0.04]'
              }`}
            >
              Methodology
            </Link>
          </nav>
        </div>

        {/* Right Controls & Profile */}
        <div className="flex items-center space-x-3.5">
          {/* Sample Dataset Button */}
          <a
            href="/api/sample.csv"
            download="veritas_sample_benchmark.csv"
            className="hidden sm:inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-ink bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 hover:border-emerald-500/40 rounded-md transition-all group"
            title="Download verified 500-row deterministic test CSV"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400 group-hover:scale-110 transition-transform" />
            <span>Sample Dataset</span>
            <ArrowDownToLine className="w-3 h-3 text-ink-soft" />
          </a>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle theme"
            className="p-2 rounded-md text-ink-soft hover:text-ink bg-white/[0.03] hover:bg-white/[0.08] border border-rule transition-colors"
          >
            {isLight ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4 text-amber" />}
          </button>

          {/* Auditor Badge */}
          <div className="hidden sm:flex items-center space-x-2 pl-3 border-l border-rule text-xs text-ink-soft font-mono">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="text-slate-300 font-medium">om@optywise.audit</span>
          </div>
        </div>
      </div>
    </header>
  );
}
