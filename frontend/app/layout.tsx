import React from 'react';
import type { Metadata } from 'next';
import '../styles/tokens.css';
import Providers from './providers';
import Navbar from '../components/Navbar';
import { ShieldCheck } from 'lucide-react';

export const metadata: Metadata = {
  title: 'VERITAS | Enterprise AI Governance & NIST AI RMF Audit Platform',
  description: 'Auditing machine learning models for demographic bias, multivariate drift, and NIST AI RMF compliance with human-in-the-loop approvals.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-paper text-ink flex flex-col font-sans selection:bg-emerald-500/25 selection:text-emerald-200">
        <Providers>
          <div className="fixed inset-0 bg-tech-grid pointer-events-none opacity-60 z-0" />
          <Navbar />
          <main className="relative z-10 flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </main>
          <footer className="relative z-10 w-full border-t border-rule bg-sheet-glass backdrop-blur-md py-4 text-center text-xs text-ink-soft font-mono flex items-center justify-center space-x-3">
            <span className="flex items-center space-x-1.5 text-emerald-400 font-semibold">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>VERITAS ENGINE</span>
            </span>
            <span>·</span>
            <span>Deterministic Statistical Boundary</span>
            <span>·</span>
            <span>NIST AI RMF 1.0 (NIST AI 100-1)</span>
            <span>·</span>
            <span className="text-slate-400">SHA-256 Verified</span>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
