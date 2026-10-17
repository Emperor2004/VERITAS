'use client';

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { fetchRuns } from '../../lib/api';
import { FolderArchive, ArrowRight, ShieldCheck, Clock, Fingerprint, Loader2 } from 'lucide-react';

export default function RunsHistoryPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['runs'],
    queryFn: () => fetchRuns(50, 0),
  });

  const runs = data?.runs || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-rule">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink flex items-center space-x-2">
            <FolderArchive className="w-6 h-6 text-verdigris" />
            <span>Audit Case Files</span>
          </h1>
          <p className="text-xs text-ink-soft mt-1">
            Historical audit records and signed compliance envelopes preserved in SQLite storage.
          </p>
        </div>
        <Link
          href="/"
          className="px-4 py-2 rounded bg-verdigris hover:bg-verdigris-hover text-white text-xs font-semibold shadow-sm transition-colors"
        >
          New Audit Run
        </Link>
      </div>

      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-3">
          <Loader2 className="w-7 h-7 animate-spin text-verdigris" />
          <p className="text-xs font-mono text-ink-soft">Loading audit records...</p>
        </div>
      ) : runs.length === 0 ? (
        <div className="p-12 bg-sheet border border-rule rounded text-center space-y-3">
          <FolderArchive className="w-10 h-10 text-ink-soft/40 mx-auto" />
          <h3 className="text-sm font-semibold text-ink">No Audit Records Yet</h3>
          <p className="text-xs text-ink-soft max-w-sm mx-auto">
            Upload a model decision dataset on the home page to initialize your first audited case file.
          </p>
          <Link
            href="/"
            className="inline-block mt-2 px-4 py-2 bg-verdigris text-white text-xs font-semibold rounded"
          >
            Start First Audit
          </Link>
        </div>
      ) : (
        <div className="bg-sheet border border-rule rounded divide-y divide-rule/60 overflow-hidden">
          {runs.map((r) => (
            <Link
              key={r.run_id}
              href={`/runs/${r.run_id}`}
              className="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 hover:bg-paper/40 transition-colors group"
            >
              <div className="space-y-1">
                <div className="flex items-center space-x-3">
                  <span className="font-mono text-xs font-bold text-ink group-hover:text-verdigris transition-colors">
                    #{r.run_id.slice(0, 12)}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-semibold ${
                      r.status === 'completed'
                        ? 'bg-moss/10 text-moss border border-moss/20'
                        : r.status === 'awaiting_approval'
                        ? 'bg-amber/10 text-amber border border-amber/20'
                        : r.status === 'rejected'
                        ? 'bg-oxide/10 text-oxide border border-oxide/20'
                        : 'bg-verdigris/10 text-verdigris border border-verdigris/20'
                    }`}
                  >
                    {r.status.replace('_', ' ')}
                  </span>
                </div>
                <div className="flex items-center space-x-4 text-[11px] text-ink-soft">
                  <span className="flex items-center space-x-1">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{new Date(r.created_at || '').toLocaleDateString()}</span>
                  </span>
                  {r.config_fingerprint && (
                    <span className="flex items-center space-x-1 font-mono">
                      <Fingerprint className="w-3.5 h-3.5 text-verdigris" />
                      <span>{r.config_fingerprint.slice(0, 8)}</span>
                    </span>
                  )}
                  {r.approved_by && (
                    <span>Approved by: {r.approved_by}</span>
                  )}
                </div>
              </div>

              <div className="flex items-center space-x-4 self-end sm:self-auto">
                {r.summary && (
                  <div className="text-right text-xs">
                    <span className="font-mono font-bold text-ink">
                      {((r.summary.total_records ?? r.row_count ?? 0) as number).toLocaleString()} rows
                    </span>
                    <div className="text-[11px] text-ink-soft">
                      {r.summary.fairness_violations ?? 0} violations · {r.summary.anomalies_detected ?? (r.summary as any).anomaly_total ?? 0} outliers
                    </div>
                  </div>
                )}
                <ArrowRight className="w-4 h-4 text-ink-soft group-hover:text-verdigris group-hover:translate-x-0.5 transition-all" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
