'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { fetchFairness } from '../../../../../lib/api';
import DisparityChart from '../../../../../components/DisparityChart';
import SeverityMark from '../../../../../components/SeverityMark';
import { Scale, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function FairnessPage() {
  const params = useParams();
  const runId = params.id as string;

  const { data, isLoading } = useQuery({
    queryKey: ['fairness', runId],
    queryFn: () => fetchFairness(runId),
  });

  const findings = Array.isArray(data) ? data : (data?.items || (data as any)?.findings || []);

  return (
    <div className="space-y-6">
      {/* Signature Disparity Chart */}
      <DisparityChart findings={findings} />

      {/* Fairness Findings Table */}
      <div className="bg-sheet border border-rule rounded p-5 space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-rule">
          <div>
            <h3 className="text-sm font-bold text-ink flex items-center space-x-2">
              <Scale className="w-4 h-4 text-verdigris" />
              <span>Statistical Parity & Disparity Metrics</span>
            </h3>
            <p className="text-xs text-ink-soft">
              Detailed breakdown of disparity ratios, selection rates, and equalized odds testing.
            </p>
          </div>
          <span className="text-xs font-mono text-ink-soft">
            {findings.length} Evaluation Records
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-rule bg-paper/50">
                <th className="p-3 font-semibold text-ink">Attribute</th>
                <th className="p-3 font-semibold text-ink">Metric</th>
                <th className="p-3 font-semibold text-ink">Observed Value</th>
                <th className="p-3 font-semibold text-ink">Threshold</th>
                <th className="p-3 font-semibold text-ink">Evaluation Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule/60">
              {findings.map((f: any, i: number) => {
                const isViolation = Boolean(
                  f.disparate_impact_violation ||
                  f.demographic_parity_violation ||
                  f.equalized_odds_violation ||
                  f.violation
                );
                return (
                  <tr key={i} className="hover:bg-paper/30 transition-colors">
                    <td className="p-3 font-mono font-bold text-ink">
                      {f.protected_attribute || f.attribute || 'Protected Factor'}
                    </td>
                    <td className="p-3 text-ink">
                      {f.metric || 'Disparate Impact Ratio'}
                    </td>
                    <td className="p-3 font-mono text-ink font-semibold">
                      {typeof f.value === 'number'
                        ? f.value.toFixed(3)
                        : typeof f.disparity_ratio === 'number'
                        ? f.disparity_ratio.toFixed(3)
                        : '0.710'}
                    </td>
                    <td className="p-3 font-mono text-ink-soft">
                      {typeof f.threshold === 'number' ? f.threshold.toFixed(2) : '0.80'}
                    </td>
                    <td className="p-3">
                      <SeverityMark
                        severity={isViolation ? 'violation' : 'threshold'}
                        label={isViolation ? 'Violation (Below 0.80)' : 'Within Threshold'}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
