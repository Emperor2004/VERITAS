import React from 'react';
import { CheckCircle2, AlertTriangle, ShieldCheck, Tag } from 'lucide-react';
import { ColumnInspection } from '../lib/api';

interface ColumnCheckProps {
  inspection: ColumnInspection;
}

export default function ColumnCheck({ inspection }: ColumnCheckProps) {
  const { detected_roles, row_count, column_count, errors } = inspection;

  const roleRows = [
    {
      label: 'Model Decision',
      role: 'Prediction',
      desc: 'Predicted outcome or classification decision',
      value: detected_roles.prediction,
      count: detected_roles.prediction ? 1 : 0,
      required: true,
      pillColor: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    },
    {
      label: 'Ground Truth',
      role: 'Actual',
      desc: 'Observed target label / repayment / hire outcome',
      value: detected_roles.actual,
      count: detected_roles.actual ? 1 : 0,
      required: true,
      pillColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    },
    {
      label: 'Protected Demographic Factors',
      role: 'Protected',
      desc: 'Sensitive attributes scrutinized for disparate impact',
      value: (detected_roles.protected || detected_roles.protected_attributes)?.join(', '),
      count: (detected_roles.protected || detected_roles.protected_attributes)?.length || 0,
      required: true,
      pillColor: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    },
    {
      label: 'Numeric Continuous Features',
      role: 'Features',
      desc: 'Input variables tested for multivariate drift & outliers',
      value: (detected_roles.features || detected_roles.feature_columns)?.join(', '),
      count: (detected_roles.features || detected_roles.feature_columns)?.length || 0,
      required: true,
      pillColor: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    },
    {
      label: 'Excluded Identifiers',
      role: 'Ignored',
      desc: 'Unique IDs, transaction keys, or raw timestamps',
      value: [detected_roles.record_id, detected_roles.timestamp].filter(Boolean).join(', ') || detected_roles.ignored?.join(', '),
      count: [detected_roles.record_id, detected_roles.timestamp].filter(Boolean).length || detected_roles.ignored?.length || 0,
      required: false,
      pillColor: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
    },
  ];

  return (
    <div className="w-full glass-panel rounded-2xl p-6 space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-rule">
        <div className="space-y-0.5">
          <h3 className="text-sm font-bold text-white flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Agent-1 Inferred Column Schema</span>
          </h3>
          <p className="text-xs text-ink-soft">
            <strong className="text-slate-300 font-mono">{row_count.toLocaleString()}</strong> rows ·{' '}
            <strong className="text-slate-300 font-mono">{column_count}</strong> columns mapped under privacy boundaries
          </p>
        </div>

        {errors && errors.length > 0 ? (
          <span className="inline-flex items-center space-x-1.5 text-xs text-rose-400 font-semibold px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/25">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Missing required fields</span>
          </span>
        ) : (
          <span className="inline-flex items-center space-x-1.5 text-xs text-emerald-400 font-semibold px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 shadow-[0_0_15px_rgba(16,185,129,0.15)]">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>All required roles verified</span>
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-2.5">
        {roleRows.map((row) => {
          const isMissing = row.required && row.count === 0;
          return (
            <div
              key={row.role}
              className={`p-3.5 rounded-xl border transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${
                isMissing
                  ? 'bg-rose-500/[0.05] border-rose-500/30'
                  : 'bg-white/[0.02] border-rule hover:border-white/15'
              }`}
            >
              <div className="space-y-0.5">
                <div className="flex items-center space-x-2">
                  <span className="font-semibold text-xs text-white">{row.label}</span>
                  <span className={`text-[10px] font-mono px-2 py-0.2 rounded border font-bold ${row.pillColor}`}>
                    {row.role}
                  </span>
                </div>
                <p className="text-[11px] text-ink-soft">{row.desc}</p>
              </div>

              <div className="text-left sm:text-right flex items-center space-x-2.5 self-stretch sm:self-auto justify-between sm:justify-end border-t sm:border-t-0 border-rule/40 pt-2 sm:pt-0">
                <span
                  className={`font-mono text-xs max-w-xs truncate ${
                    isMissing ? 'text-rose-400 font-bold' : 'text-slate-300'
                  }`}
                  title={row.value}
                >
                  {row.value || (isMissing ? 'Missing required field' : 'None')}
                </span>
                {row.count > 0 ? (
                  <span className="px-2 py-0.5 rounded-full bg-white/[0.05] border border-white/10 font-mono text-[10px] text-emerald-400 font-bold shrink-0">
                    {row.count} detected
                  </span>
                ) : isMissing ? (
                  <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                ) : (
                  <span className="text-ink-soft text-xs">—</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {errors && errors.length > 0 && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 space-y-1.5">
          {errors.map((err, i) => (
            <p key={i} className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
              <span>{err}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
