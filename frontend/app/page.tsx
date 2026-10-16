'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import RunStepper from '../components/RunStepper';
import Dropzone from '../components/Dropzone';
import ColumnCheck from '../components/ColumnCheck';
import { ColumnInspection, createRun } from '../lib/api';
import { ArrowRight, Table, AlertCircle, Sparkles, ShieldCheck, Scale, Activity, Lock } from 'lucide-react';

export default function UploadPage() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [inspection, setInspection] = useState<ColumnInspection | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleValidated = (file: File, res: ColumnInspection) => {
    setSelectedFile(file);
    setInspection(res);
    setErrorMsg(null);
  };

  const handleError = (msg: string) => {
    setErrorMsg(msg);
    setInspection(null);
  };

  const handleCreateRun = async () => {
    if (!selectedFile) return;
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const { run_id } = await createRun(selectedFile, 'om@optywise.audit', 'Om Lead Auditor');
      router.push(`/runs/${run_id}/review`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to initialize audit run';
      setErrorMsg(msg);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8 pb-12">
      {/* Run Stepper */}
      <RunStepper currentStep="upload" />

      {/* Hero & Context Header */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left column: Context, Value Proposition & Standards */}
        <div className="lg:col-span-5 space-y-6">
          <div className="space-y-3">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-[11px] font-mono text-emerald-400 font-semibold tracking-wide shadow-sm">
              <Sparkles className="w-3.5 h-3.5" />
              <span>NIST AI RMF 1.0 & EEOC COMPLIANCE</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white leading-tight">
              Algorithmic Bias & Risk Audit Platform
            </h1>
            <p className="text-sm text-ink-soft leading-relaxed">
              Evaluate machine learning decision systems for demographic disparate impact, multivariate
              feature drift, and NIST AI RMF regulatory alignment with cryptographic verification.
            </p>
          </div>

          {/* 3 Core Pillars Cards */}
          <div className="grid grid-cols-1 gap-3">
            <div className="p-4 rounded-xl glass-card flex items-start space-x-3.5">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0 mt-0.5">
                <Scale className="w-4 h-4" />
              </div>
              <div className="space-y-0.5">
                <h4 className="text-xs font-bold text-white">EEOC 4/5ths Rule & Disparity</h4>
                <p className="text-[11px] text-ink-soft">
                  Rigorous statistical testing of demographic parity difference, disparate impact ratio, and equalized odds.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl glass-card flex items-start space-x-3.5">
              <div className="w-8 h-8 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0 mt-0.5">
                <Activity className="w-4 h-4" />
              </div>
              <div className="space-y-0.5">
                <h4 className="text-xs font-bold text-white">Multivariate Outlier Clustering</h4>
                <p className="text-[11px] text-ink-soft">
                  Isolation Forest anomaly detection grouped by dominant feature z-scores (Agent-2).
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl glass-card flex items-start space-x-3.5">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 mt-0.5">
                <Lock className="w-4 h-4" />
              </div>
              <div className="space-y-0.5">
                <h4 className="text-xs font-bold text-white">Cryptographic Human Sign-Off</h4>
                <p className="text-[11px] text-ink-soft">
                  Every run requires human auditor sign-off sealed with a canonical SHA-256 fingerprint.
                </p>
              </div>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-white/[0.02] border border-rule text-xs text-ink-soft flex items-center space-x-2.5 font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Deterministic Statistical Engine · Zero Hallucinated Numbers</span>
          </div>
        </div>

        {/* Right column: Dropzone + ColumnCheck + Live Preview */}
        <div className="lg:col-span-7 space-y-6">
          <Dropzone
            onValidated={handleValidated}
            onError={handleError}
            isProcessing={isSubmitting}
          />

          {errorMsg && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start space-x-3 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">Validation Alert</p>
                <p className="mt-0.5">{errorMsg}</p>
              </div>
            </div>
          )}

          {inspection && (
            <div className="space-y-6">
              <ColumnCheck inspection={inspection} />

              {/* Data Preview Table */}
              {inspection.preview_rows && inspection.preview_rows.length > 0 && (
                <div className="glass-panel rounded-2xl overflow-hidden">
                  <div className="px-5 py-3.5 border-b border-rule flex items-center justify-between">
                    <span className="text-xs font-bold text-white flex items-center space-x-2">
                      <Table className="w-4 h-4 text-emerald-400" />
                      <span>Ingestion Preview (First {inspection.preview_rows.length} Records)</span>
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/[0.05] border border-white/10 text-ink-soft">
                      Dry-Run Memory Profile
                    </span>
                  </div>
                  <div className="overflow-x-auto max-h-60">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-slate-900/80 border-b border-rule">
                          {Object.keys(inspection.preview_rows[0]).map((col) => (
                            <th key={col} className="p-3 font-mono text-[11px] font-semibold text-slate-300 whitespace-nowrap">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-rule/40 font-mono text-[11px]">
                        {inspection.preview_rows.map((row, idx) => (
                          <tr key={idx} className="hover:bg-white/[0.03] transition-colors">
                            {Object.values(row).map((val, cidx) => (
                              <td key={cidx} className="p-3 whitespace-nowrap text-slate-300">
                                {String(val ?? '—')}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Action Button */}
              <div className="p-4 rounded-2xl glass-card flex flex-col sm:flex-row items-center justify-between gap-4">
                <button
                  onClick={handleCreateRun}
                  disabled={isSubmitting || (inspection.errors && inspection.errors.length > 0)}
                  className={`w-full sm:w-auto px-8 py-3 rounded-xl font-bold text-xs tracking-wide uppercase flex items-center justify-center space-x-2.5 transition-all shadow-lg ${
                    isSubmitting || (inspection.errors && inspection.errors.length > 0)
                      ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-white/10'
                      : 'bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-400 hover:from-emerald-400 hover:to-cyan-300 text-slate-950 shadow-[0_0_25px_rgba(16,185,129,0.35)] hover:scale-[1.02] active:scale-[0.98]'
                  }`}
                >
                  <span>{isSubmitting ? 'Initializing Audit Case...' : 'Create Audit Case File'}</span>
                  <ArrowRight className="w-4 h-4 stroke-[2.5]" />
                </button>
                <p className="text-xs text-ink-soft text-center sm:text-right">
                  Nothing is analyzed until you sign off on parameters.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
