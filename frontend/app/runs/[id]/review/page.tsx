'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { fetchRun, fetchConfigBounds, approveRun, rejectRun, RunReviewPayload } from '../../../../lib/api';
import RunStepper from '../../../../components/RunStepper';
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Fingerprint,
  UserCheck,
  Calendar,
  Sparkles,
  ArrowRight,
  Loader2,
  Lock,
} from 'lucide-react';

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const runId = params.id as string;

  const { data: run, isLoading: isRunLoading } = useQuery({
    queryKey: ['run', runId],
    queryFn: () => fetchRun(runId),
  });

  const { data: bounds } = useQuery({
    queryKey: ['config-bounds'],
    queryFn: fetchConfigBounds,
  });

  const [protectedAttrs, setProtectedAttrs] = useState<string[]>([]);
  const [significance, setSignificance] = useState<number>(0.05);
  const [minGroupSize, setMinGroupSize] = useState<number>(30);
  const [permutations, setPermutations] = useState<number>(1000);
  const [reviewerName, setReviewerName] = useState('Om (Lead AI Compliance Auditor)');
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (run?.review?.proposed_config) {
      const p = run.review.proposed_config;
      if (p.protected_attributes && p.protected_attributes.length > 0) {
        setProtectedAttrs(p.protected_attributes);
      } else if (run.review.detected_protected_candidates?.length > 0) {
        setProtectedAttrs(run.review.detected_protected_candidates);
      }
      if (typeof p.significance_level === 'number') setSignificance(p.significance_level);
      if (typeof p.min_group_size === 'number') setMinGroupSize(p.min_group_size);
      if (typeof p.permutations === 'number') setPermutations(p.permutations);
    }
  }, [run]);

  if (isRunLoading || !run) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
        <p className="text-xs font-mono text-ink-soft">Retrieving audit envelope for case {runId}...</p>
      </div>
    );
  }

  if (run.status === 'completed') {
    router.replace(`/runs/${runId}/summary`);
    return null;
  }

  const review: RunReviewPayload = run.review || {
    run_id: runId,
    row_count: 0,
    column_names: [],
    detected_protected_candidates: [],
    proposed_config: {},
  };

  const handleToggleAttr = (attr: string) => {
    if (protectedAttrs.includes(attr)) {
      if (protectedAttrs.length > 1) {
        setProtectedAttrs(protectedAttrs.filter((a) => a !== attr));
      }
    } else {
      setProtectedAttrs([...protectedAttrs, attr]);
    }
  };

  const handleApprove = async () => {
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await approveRun(
        runId,
        {
          protected_attributes: protectedAttrs,
          significance_level: Number(significance),
          min_group_size: Number(minGroupSize),
          permutations: Number(permutations),
        },
        { email: 'om@optywise.audit', name: reviewerName }
      );
      router.push(`/runs/${runId}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Approval failed';
      setErrorMsg(msg);
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      setErrorMsg('Please specify a formal justification for rejecting this audit run.');
      return;
    }
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await rejectRun(runId, rejectReason);
      setShowRejectModal(false);
      router.push(`/runs/${runId}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Rejection failed';
      setErrorMsg(msg);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8 pb-12">
      <RunStepper currentStep="review" />

      {/* Case Header Strip */}
      <div className="glass-panel rounded-2xl p-4 sm:p-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3.5">
          <span className="font-mono text-xs px-2.5 py-1 rounded-md bg-white/[0.05] border border-white/10 font-bold text-emerald-400">
            Case #{run.run_id.slice(0, 12)}
          </span>
          <span className="text-white text-xs font-semibold">
            {review.row_count.toLocaleString()} Decision Records Validated
          </span>
        </div>
        <div className="flex items-center space-x-4 text-xs font-mono text-ink-soft">
          <span className="flex items-center space-x-1.5 text-slate-300">
            <Fingerprint className="w-4 h-4 text-emerald-400" />
            <span>Fingerprint: <strong className="text-white">{run.config_fingerprint || 'Pending Sign-Off'}</strong></span>
          </span>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center space-x-3 text-xs text-rose-300">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Review Form & Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Form: Proposed Configuration */}
        <div className="lg:col-span-8 glass-panel rounded-2xl p-6 sm:p-8 space-y-7">
          <div className="border-b border-rule pb-4">
            <h2 className="text-lg font-bold text-white flex items-center space-x-2.5">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <span>Statistical Audit Parameters & Human Sign-off</span>
            </h2>
            <p className="text-xs text-ink-soft mt-1">
              Verify statistical significance thresholds, demographic factors under evaluation, and Monte Carlo permutation bounds.
            </p>
          </div>

          {/* Protected Attributes Selection */}
          <div className="space-y-3">
            <label className="text-xs font-bold text-white uppercase tracking-wider flex items-center justify-between">
              <span>Scrutinized Demographic Attributes</span>
              <span className="text-[11px] font-normal text-slate-400">At least one required</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {(review.detected_protected_candidates?.length > 0
                ? review.detected_protected_candidates
                : ['sex', 'race', 'age_group']
              ).map((attr) => {
                const isSelected = protectedAttrs.includes(attr);
                return (
                  <button
                    key={attr}
                    type="button"
                    onClick={() => handleToggleAttr(attr)}
                    className={`px-4 py-3 rounded-xl text-xs font-mono flex items-center justify-between border transition-all ${
                      isSelected
                        ? 'border-emerald-500/50 bg-emerald-500/10 text-white font-bold shadow-[0_0_15px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500/30'
                        : 'border-white/10 bg-slate-900/40 text-slate-400 hover:border-white/20 hover:text-white'
                    }`}
                  >
                    <span>{attr}</span>
                    <span
                      className={`w-4 h-4 rounded flex items-center justify-center transition-colors ${
                        isSelected ? 'bg-emerald-500 text-slate-950' : 'border border-white/20'
                      }`}
                    >
                      {isSelected && <CheckCircle2 className="w-3.5 h-3.5 stroke-[3]" />}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Quantitative Thresholds */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
            {/* Significance Level */}
            <div className="p-4 rounded-xl glass-card space-y-2">
              <label className="text-xs font-bold text-white flex items-center justify-between">
                <span>Significance (α)</span>
                <span className="text-[10px] text-emerald-400 font-mono">
                  [{bounds?.significance_level.min ?? 0.001}–{bounds?.significance_level.max ?? 0.999}]
                </span>
              </label>
              <input
                type="number"
                step="0.005"
                min={bounds?.significance_level.min ?? 0.001}
                max={bounds?.significance_level.max ?? 0.999}
                value={significance}
                onChange={(e) => setSignificance(parseFloat(e.target.value))}
                className="w-full px-3 py-2 bg-slate-900/80 border border-white/10 focus-ring rounded-lg text-xs font-mono text-white"
              />
              <p className="text-[10px] text-ink-soft">Standard false positive rate boundary.</p>
            </div>

            {/* Minimum Group Size */}
            <div className="p-4 rounded-xl glass-card space-y-2">
              <label className="text-xs font-bold text-white flex items-center justify-between">
                <span>Min Group Size</span>
                <span className="text-[10px] text-emerald-400 font-mono">
                  [{bounds?.min_group_size.min ?? 1}–1M]
                </span>
              </label>
              <input
                type="number"
                step="1"
                min={bounds?.min_group_size.min ?? 1}
                max={bounds?.min_group_size.max ?? 1000000}
                value={minGroupSize}
                onChange={(e) => setMinGroupSize(parseInt(e.target.value, 10))}
                className="w-full px-3 py-2 bg-slate-900/80 border border-white/10 focus-ring rounded-lg text-xs font-mono text-white"
              />
              <p className="text-[10px] text-ink-soft">Subgroups below this trigger small-sample warnings.</p>
            </div>

            {/* Permutation Count */}
            <div className="p-4 rounded-xl glass-card space-y-2">
              <label className="text-xs font-bold text-white flex items-center justify-between">
                <span>Permutations</span>
                <span className="text-[10px] text-emerald-400 font-mono">
                  [100–100k]
                </span>
              </label>
              <input
                type="number"
                step="100"
                min={bounds?.permutations.min ?? 1}
                max={bounds?.permutations.max ?? 100000}
                value={permutations}
                onChange={(e) => setPermutations(parseInt(e.target.value, 10))}
                className="w-full px-3 py-2 bg-slate-900/80 border border-white/10 focus-ring rounded-lg text-xs font-mono text-white"
              />
              <p className="text-[10px] text-ink-soft">Monte Carlo exact permutation rounds.</p>
            </div>
          </div>

          {/* Agent-3 AI Stability Rationale Card */}
          {review.rationale && (
            <div className="p-5 rounded-xl bg-gradient-to-br from-indigo-500/[0.08] to-purple-500/[0.04] border border-indigo-500/25 space-y-2.5 text-xs">
              <div className="flex items-center space-x-2 font-bold text-indigo-300 font-mono text-xs">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <span>Agent-3: AI Parameter Stability Rationale & Proxy Screening</span>
              </div>
              {review.rationale.significance_justification && (
                <p className="text-slate-300">
                  <strong className="text-white">Significance Justification:</strong>{' '}
                  {review.rationale.significance_justification}
                </p>
              )}
              {review.rationale.sample_size_stability && (
                <p className="text-slate-300">
                  <strong className="text-white">Sample Stability:</strong>{' '}
                  {review.rationale.sample_size_stability}
                </p>
              )}
              {review.rationale.proxy_features_detected && review.rationale.proxy_features_detected.length > 0 && (
                <div className="flex items-center space-x-2 text-amber-300 pt-1">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
                  <span>
                    Potential proxy correlation detected in feature(s):{' '}
                    <strong>{review.rationale.proxy_features_detected.join(', ')}</strong>
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Auditor Sign-off Seal */}
          <div className="pt-5 border-t border-rule space-y-5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono flex items-center space-x-2">
              <Lock className="w-4 h-4 text-emerald-400" />
              <span>Auditor Sign-off Seal & Identity Stamp</span>
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="space-y-1.5">
                <span className="text-ink-soft font-semibold flex items-center space-x-1.5">
                  <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Reviewer Identity (Stamped to Audit Trail)</span>
                </span>
                <input
                  type="text"
                  value={reviewerName}
                  onChange={(e) => setReviewerName(e.target.value)}
                  className="w-full px-3.5 py-2 bg-slate-900/80 border border-white/10 rounded-lg font-mono text-xs text-white focus-ring"
                />
              </div>
              <div className="space-y-1.5">
                <span className="text-ink-soft font-semibold flex items-center space-x-1.5">
                  <Calendar className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Certified Timestamp (UTC)</span>
                </span>
                <div className="px-3.5 py-2 bg-slate-900/50 border border-white/10 rounded-lg font-mono text-xs text-slate-400">
                  {new Date().toUTCString()}
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <button
                type="button"
                onClick={handleApprove}
                disabled={isSubmitting || protectedAttrs.length === 0}
                className="px-8 py-3 rounded-xl bg-gradient-to-r from-emerald-500 via-teal-400 to-cyan-400 hover:from-emerald-400 hover:to-cyan-300 text-slate-950 font-bold text-xs uppercase tracking-wide flex items-center space-x-2.5 transition-all shadow-[0_0_25px_rgba(16,185,129,0.35)] hover:scale-[1.02] active:scale-[0.98]"
              >
                {isSubmitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ShieldCheck className="w-4 h-4 stroke-[2.5]" />
                )}
                <span>Approve & Execute Audit</span>
              </button>

              <button
                type="button"
                onClick={() => setShowRejectModal(true)}
                disabled={isSubmitting}
                className="px-5 py-3 rounded-xl border border-rose-500/30 text-rose-300 hover:bg-rose-500/10 text-xs font-bold transition-all"
              >
                Reject Configuration
              </button>
            </div>
          </div>
        </div>

        {/* Right Sidebar: Execution Scope */}
        <div className="lg:col-span-4 glass-panel rounded-2xl p-6 space-y-5 text-xs">
          <h3 className="font-bold text-white text-sm pb-3 border-b border-rule">
            Autonomous Pipeline Scope
          </h3>
          <ul className="space-y-4 text-ink-soft">
            <li className="flex items-start space-x-3">
              <span className="w-2 h-2 rounded-full bg-emerald-400 mt-1.5 shrink-0 shadow-[0_0_8px_rgba(16,185,129,0.6)]" />
              <div>
                <strong className="text-white text-xs">Multivariate Anomaly Detection:</strong>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Robust Scaler IQR transformation + Isolation Forest outlier signatures.
                </p>
              </div>
            </li>
            <li className="flex items-start space-x-3">
              <span className="w-2 h-2 rounded-full bg-emerald-400 mt-1.5 shrink-0 shadow-[0_0_8px_rgba(16,185,129,0.6)]" />
              <div>
                <strong className="text-white text-xs">Demographic Disparity Scan:</strong>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  EEOC 4/5ths Rule ($0.80$ threshold), Demographic Parity, and Equalized Odds.
                </p>
              </div>
            </li>
            <li className="flex items-start space-x-3">
              <span className="w-2 h-2 rounded-full bg-emerald-400 mt-1.5 shrink-0 shadow-[0_0_8px_rgba(16,185,129,0.6)]" />
              <div>
                <strong className="text-white text-xs">NIST AI RMF 1.0 Mapping:</strong>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Deterministic binding to Govern, Map, Measure, and Manage risk controls.
                </p>
              </div>
            </li>
            <li className="flex items-start space-x-3">
              <span className="w-2 h-2 rounded-full bg-emerald-400 mt-1.5 shrink-0 shadow-[0_0_8px_rgba(16,185,129,0.6)]" />
              <div>
                <strong className="text-white text-xs">Cryptographic Workpaper & PDF:</strong>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Board-ready regulatory compliance document sealed with SHA-256 fingerprint.
                </p>
              </div>
            </li>
          </ul>

          <div className="p-4 rounded-xl bg-white/[0.02] border border-rule text-[11px] text-slate-400 space-y-1">
            <span className="font-bold text-white">Immutable Checkpointing:</span>
            <p>
              Backed by durable LangGraph checkpoints. State is preserved across server restarts.
            </p>
          </div>
        </div>
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="glass-panel border-rose-500/30 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center space-x-2.5 text-rose-400 font-bold text-sm">
              <XCircle className="w-5 h-5" />
              <span>Reject Audit Configuration</span>
            </div>
            <p className="text-xs text-ink-soft">
              Document reason for rejecting this configuration. This rationale will be permanently recorded in the audit trail.
            </p>
            <textarea
              rows={3}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g. Inappropriate significance threshold, missing primary protected column..."
              className="w-full p-3 bg-slate-900 border border-white/10 rounded-xl text-xs font-mono text-white focus-ring"
            />
            <div className="flex justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={() => setShowRejectModal(false)}
                className="px-4 py-2 text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleReject}
                disabled={isSubmitting}
                className="px-5 py-2 bg-rose-600 text-white text-xs font-bold rounded-lg hover:bg-rose-500 shadow-md"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
