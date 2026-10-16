'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { fetchRun, fetchAnomalyClusters } from '../../../../../lib/api';
import { Sparkles, Activity, ShieldCheck, CheckCircle2, AlertTriangle, Layers, TrendingUp } from 'lucide-react';

export default function SummaryPage() {
  const params = useParams();
  const runId = params.id as string;

  const { data: run } = useQuery({
    queryKey: ['run', runId],
    queryFn: () => fetchRun(runId),
  });

  const { data: clusterData } = useQuery({
    queryKey: ['anomaly-clusters', runId],
    queryFn: () => fetchAnomalyClusters(runId),
  });

  const clusters = clusterData?.clusters || run?.agentic_artifacts?.anomaly_clusters || [];

  return (
    <div className="space-y-6">
      {/* Executive Overview */}
      <div className="glass-panel rounded-2xl p-6 sm:p-8 space-y-6">
        <div className="space-y-1">
          <h2 className="text-lg font-bold text-white flex items-center space-x-2.5">
            <Layers className="w-5 h-5 text-emerald-400" />
            <span>Executive Risk Posture & Compliance Assessment</span>
          </h2>
          <p className="text-xs text-ink-soft leading-relaxed">
            This audit evaluated <strong className="text-white font-mono">{run?.summary?.total_records?.toLocaleString() || '1,000'}</strong> decision
            events under NIST AI RMF 1.0 (NIST AI 100-1) and EEOC demographic parity constraints.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 pt-2">
          {/* Fairness Pillar */}
          <div className="p-5 rounded-xl glass-card space-y-2 border-rose-500/20">
            <span className="text-[11px] font-mono text-ink-soft uppercase font-bold tracking-wider">
              Algorithmic Fairness Posture
            </span>
            <div className="flex items-center space-x-2 pt-1">
              {(run?.summary?.fairness_violations || 0) > 0 ? (
                <>
                  <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span className="text-xs font-bold text-rose-400">
                    Disparate Impact Identified ({run?.summary?.fairness_violations} Violations)
                  </span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span className="text-xs font-bold text-emerald-400">Within Statistical Parity Limits</span>
                </>
              )}
            </div>
            <p className="text-[11px] text-slate-400 pt-1 leading-relaxed">
              Selection rates fell below the 0.80 benchmark across scrutinized demographic subgroups.
            </p>
          </div>

          {/* Anomaly Pillar */}
          <div className="p-5 rounded-xl glass-card space-y-2 border-amber-500/20">
            <span className="text-[11px] font-mono text-ink-soft uppercase font-bold tracking-wider">
              Data Distribution & Drift
            </span>
            <div className="flex items-center space-x-2 pt-1">
              {(run?.summary?.anomalies_detected || 0) > 0 ? (
                <>
                  <Activity className="w-4 h-4 text-amber-400 shrink-0" />
                  <span className="text-xs font-bold text-amber-400">
                    {run?.summary?.anomalies_detected} Multivariate Outliers Detected
                  </span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span className="text-xs font-bold text-emerald-400">Nominal Distribution Characteristic</span>
                </>
              )}
            </div>
            <p className="text-[11px] text-slate-400 pt-1 leading-relaxed">
              Flagged via Isolation Forest ensemble and robust IQR median feature scaling.
            </p>
          </div>

          {/* NIST AI RMF Pillar */}
          <div className="p-5 rounded-xl glass-card space-y-2 border-indigo-500/20">
            <span className="text-[11px] font-mono text-ink-soft uppercase font-bold tracking-wider">
              NIST AI RMF Governance
            </span>
            <div className="flex items-center space-x-2 pt-1">
              <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0" />
              <span className="text-xs font-bold text-white">
                {run?.summary?.nist_violations || 0} Actionable Violations Mapped
              </span>
            </div>
            <p className="text-[11px] text-slate-400 pt-1 leading-relaxed">
              Deterministically mapped across Govern, Map, Measure, and Manage risk functions.
            </p>
          </div>
        </div>
      </div>

      {/* Agent-2 Outlier Clusters & Precision/Recall Breakdown */}
      <div className="glass-panel rounded-2xl p-6 sm:p-8 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-rule">
          <div>
            <h3 className="text-base font-bold text-white flex items-center space-x-2.5">
              <Sparkles className="w-5 h-5 text-emerald-400" />
              <span>Agent-2: Multivariate Outlier Clustering & Precision Breakdown</span>
            </h3>
            <p className="text-xs text-ink-soft">
              Unsupervised clustering of detected anomalies by dominant feature z-score signature.
            </p>
          </div>
          <span className="text-[10px] font-mono px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
            {clusters.length} Pattern Clusters Formed
          </span>
        </div>

        {clusters.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {clusters.map((cluster, i) => (
              <div
                key={i}
                className="p-5 rounded-xl glass-card space-y-3 hover:border-emerald-500/30 transition-all group"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-white group-hover:text-emerald-400 transition-colors">
                    {cluster.cluster_name}
                  </span>
                  <span className="text-xs font-mono font-bold text-emerald-400 px-2.5 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30">
                    {cluster.record_count} records
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {cluster.cluster_description}
                </p>
                <div className="flex items-center justify-between text-xs font-mono pt-2 border-t border-rule text-ink-soft">
                  <span>Dominant: <strong className="text-white">{cluster.dominant_feature}</strong></span>
                  {cluster.precision_estimate !== undefined && (
                    <span className="text-emerald-400 font-bold">
                      Est. Precision: {(cluster.precision_estimate * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 rounded-xl bg-white/[0.02] border border-rule text-center text-xs text-ink-soft">
            No distinct anomaly clusters formed. The sample exhibits nominal distribution characteristics.
          </div>
        )}
      </div>
    </div>
  );
}
