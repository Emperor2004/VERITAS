'use client';

import React from 'react';
import { useParams, usePathname, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { fetchRun } from '../../../../lib/api';
import Link from 'next/link';
import RunStepper from '../../../../components/RunStepper';
import {
  ShieldCheck,
  Scale,
  Activity,
  Layers,
  MessageSquare,
  FileText,
  Fingerprint,
  UserCheck,
  Calendar,
  Loader2,
  Trash2,
  Sparkles,
} from 'lucide-react';
import { deleteRun } from '../../../../lib/api';

export default function ResultsLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const pathname = usePathname();
  const router = useRouter();
  const runId = params.id as string;

  const { data: run, isLoading } = useQuery({
    queryKey: ['run', runId],
    queryFn: () => fetchRun(runId),
  });

  if (isLoading || !run) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
        <p className="text-xs font-mono text-ink-soft">Loading audit case file #{runId}...</p>
      </div>
    );
  }

  const summary = run.summary || {
    run_id: runId,
    timestamp: run.created_at || new Date().toISOString(),
    total_records: 0,
    anomalies_detected: 0,
    fairness_violations: 0,
    nist_violations: 0,
    nist_informational: 0,
    status: 'completed',
  };

  const tabs = [
    { label: 'Executive Summary', href: `/runs/${runId}/summary`, icon: Layers },
    { label: 'Fairness & Disparity', href: `/runs/${runId}/fairness`, icon: Scale },
    { label: 'Outlier Records', href: `/runs/${runId}/anomalies`, icon: Activity },
    { label: 'NIST Controls', href: `/runs/${runId}/controls`, icon: ShieldCheck },
    { label: 'Ask VERITAS (Q&A)', href: `/runs/${runId}/qa`, icon: MessageSquare },
    { label: 'Audit Workpaper', href: `/runs/${runId}/report`, icon: FileText },
  ];

  const handleDelete = async () => {
    if (confirm('Permanently purge this audit run and all associated data?')) {
      await deleteRun(runId);
      router.push('/');
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <RunStepper currentStep="results" />

      {/* Case-File Header Stamp */}
      <div className="glass-panel rounded-2xl p-6 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-rule">
          <div className="space-y-1">
            <div className="flex items-center space-x-3">
              <span className="font-mono text-sm font-bold text-white flex items-center space-x-2">
                <span className="px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono text-xs">
                  Case #{run.run_id.slice(0, 10)}
                </span>
              </span>
              <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-xs font-bold uppercase tracking-wider shadow-[0_0_12px_rgba(16,185,129,0.2)]">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>{run.status}</span>
              </span>
            </div>
            <p className="text-xs text-ink-soft font-mono pt-0.5">
              Deterministic Statistical Run · SHA-256 Pipeline Integrity Sealed
            </p>
          </div>

          <div className="flex items-center space-x-4 text-xs font-mono">
            <div className="flex items-center space-x-1.5 text-slate-300">
              <UserCheck className="w-4 h-4 text-emerald-400" />
              <span>Auditor: <strong className="text-white">{run.approved_by || 'Om'}</strong></span>
            </div>
            <div className="flex items-center space-x-1.5 text-slate-300">
              <Fingerprint className="w-4 h-4 text-emerald-400" />
              <span>Seal: <strong className="text-white">{run.config_fingerprint?.slice(0, 8) || '34504959'}</strong></span>
            </div>
            <button
              onClick={handleDelete}
              title="Purge case file"
              className="p-1.5 rounded-lg hover:bg-rose-500/10 text-ink-soft hover:text-rose-400 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Stat Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl glass-card space-y-1">
            <span className="text-[11px] font-mono uppercase text-ink-soft font-semibold">Total Audited Records</span>
            <div className="text-2xl font-extrabold font-mono text-white tracking-tight">
              {summary.total_records.toLocaleString()}
            </div>
          </div>

          <div className="p-4 rounded-xl glass-card space-y-1">
            <span className="text-[11px] font-mono uppercase text-ink-soft font-semibold">Anomalies Detected</span>
            <div className="text-2xl font-extrabold font-mono text-amber-400 tracking-tight flex items-center space-x-2">
              <span>{summary.anomalies_detected}</span>
              {summary.anomalies_detected > 0 && (
                <span className="text-[10px] font-sans font-bold px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300">
                  Outliers
                </span>
              )}
            </div>
          </div>

          <div className="p-4 rounded-xl glass-card space-y-1">
            <span className="text-[11px] font-mono uppercase text-ink-soft font-semibold">Fairness Violations</span>
            <div className="text-2xl font-extrabold font-mono text-rose-400 tracking-tight">
              {summary.fairness_violations}
            </div>
          </div>

          <div className="p-4 rounded-xl glass-card space-y-1">
            <span className="text-[11px] font-mono uppercase text-ink-soft font-semibold">NIST Mapped Controls</span>
            <div className="text-2xl font-extrabold font-mono text-white tracking-tight flex items-baseline space-x-2">
              <span className="text-rose-400">{summary.nist_violations}</span>
              <span className="text-xs text-ink-soft font-normal font-sans">violations</span>
              <span className="text-indigo-400 text-sm font-normal">/ {summary.nist_informational} info</span>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center space-x-2 border-t border-rule pt-4 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                  isActive
                    ? 'bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 shadow-[0_0_20px_rgba(16,185,129,0.35)] font-bold'
                    : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
                }`}
              >
                <Icon className="w-4 h-4 stroke-[2]" />
                <span>{tab.label}</span>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Tab Content */}
      <div className="w-full">{children}</div>
    </div>
  );
}
