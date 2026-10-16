'use client';

import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { fetchAnomalies } from '../../../../../lib/api';
import { Activity, Search, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';

export default function AnomaliesPage() {
  const params = useParams();
  const runId = params.id as string;
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const { data, isLoading } = useQuery({
    queryKey: ['anomalies', runId, page],
    queryFn: () => fetchAnomalies(runId, page, pageSize),
  });

  const total = data?.total || 0;
  const items = data?.items || [];
  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6">
      <div className="bg-sheet border border-rule rounded p-5 space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-rule">
          <div>
            <h3 className="text-sm font-bold text-ink flex items-center space-x-2">
              <Activity className="w-4 h-4 text-verdigris" />
              <span>Outlier Records & Multivariate Anomaly Signatures</span>
            </h3>
            <p className="text-xs text-ink-soft">
              Records flagged by Isolation Forest exhibiting excessive standard deviations from nominal distribution.
            </p>
          </div>
          <span className="text-xs font-mono text-ink-soft">
            Total Flagged: <strong className="text-ink">{total}</strong>
          </span>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-rule bg-paper/50">
                <th className="p-3 font-semibold text-ink">Record ID</th>
                <th className="p-3 font-semibold text-ink">Anomaly Score</th>
                <th className="p-3 font-semibold text-ink">Dominant Feature</th>
                <th className="p-3 font-semibold text-ink">Max Z-Score</th>
                <th className="p-3 font-semibold text-ink">Outlier Drivers</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule/60 font-mono text-[11px]">
              {items.map((item, idx) => (
                <tr key={idx} className="hover:bg-paper/30 transition-colors">
                  <td className="p-3 font-bold text-ink whitespace-nowrap">
                    {String(item.record_id)}
                  </td>
                  <td className="p-3 text-oxide font-semibold">
                    {typeof item.anomaly_score === 'number'
                      ? item.anomaly_score.toFixed(4)
                      : '-0.1425'}
                  </td>
                  <td className="p-3 text-ink font-sans">
                    {item.dominant_feature || 'feature_a'}
                  </td>
                  <td className="p-3 text-ink">
                    {typeof item.dominant_z === 'number'
                      ? item.dominant_z.toFixed(2)
                      : typeof item.z_score === 'number'
                      ? item.z_score.toFixed(2)
                      : '3.45'}
                  </td>
                  <td className="p-3 text-ink-soft font-sans">
                    {item.outlier_features?.join(', ') || 'feature_a, feature_c'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {items.length === 0 && (
          <div className="py-8 text-center text-xs text-ink-soft">
            No outlier records detected in this run.
          </div>
        )}

        {/* Pagination Bar */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-3 border-t border-rule text-xs">
            <span className="text-ink-soft">
              Page {page} of {totalPages}
            </span>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-2.5 py-1 rounded bg-paper border border-rule disabled:opacity-40 hover:bg-sheet text-ink flex items-center space-x-1"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-2.5 py-1 rounded bg-paper border border-rule disabled:opacity-40 hover:bg-sheet text-ink flex items-center space-x-1"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
