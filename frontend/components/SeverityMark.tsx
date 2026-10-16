import React from 'react';
import { Square, Circle, Minus, AlertTriangle, ShieldCheck } from 'lucide-react';

interface SeverityMarkProps {
  severity: 'violation' | 'informational' | 'threshold' | string;
  label?: string;
}

export default function SeverityMark({ severity, label }: SeverityMarkProps) {
  if (severity === 'violation') {
    return (
      <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/25 text-xs font-semibold shadow-[0_0_12px_rgba(244,63,94,0.15)]">
        <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shadow-[0_0_6px_rgba(244,63,94,0.8)]" />
        <span>{label || 'Violation'}</span>
      </span>
    );
  }

  if (severity === 'informational') {
    return (
      <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/25 text-xs font-semibold shadow-[0_0_12px_rgba(99,102,241,0.15)]">
        <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_6px_rgba(99,102,241,0.8)]" />
        <span>{label || 'Informational'}</span>
      </span>
    );
  }

  return (
    <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 text-xs font-semibold shadow-[0_0_12px_rgba(16,185,129,0.15)]">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.8)]" />
      <span>{label || 'Within Threshold'}</span>
    </span>
  );
}
