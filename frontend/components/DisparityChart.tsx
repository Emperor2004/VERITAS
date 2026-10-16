'use client';

import React from 'react';
import { FairnessFinding } from '../lib/api';
import { Scale, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface DisparityChartProps {
  findings: FairnessFinding[];
}

interface GroupBarData {
  attribute: string;
  group: string;
  selectionRate: number;
  relativeRatio: number;
  isReference: boolean;
  isViolation: boolean;
}

export default function DisparityChart({ findings }: DisparityChartProps) {
  const bars: GroupBarData[] = [];

  findings.forEach((f) => {
    const attr = f.protected_attribute || f.attribute || 'Protected Factor';
    const groupMetrics = f.group_metrics || {};
    const refGroup = f.reference_group || 'Reference';

    let refRate = 1.0;
    if (groupMetrics[refGroup]?.selection_rate !== undefined) {
      refRate = groupMetrics[refGroup].selection_rate || 1.0;
    } else if (f.group_selection_rates?.[refGroup] !== undefined) {
      refRate = f.group_selection_rates[refGroup] || 1.0;
    }

    const allGroups = new Set([
      ...Object.keys(groupMetrics),
      ...Object.keys(f.group_selection_rates || {}),
    ]);

    if (allGroups.size === 0) {
      bars.push({
        attribute: attr,
        group: 'Protected Group',
        selectionRate: f.selection_rate ?? 0.72,
        relativeRatio: f.disparity_ratio ?? f.disparity ?? 0.72,
        isReference: false,
        isViolation: Boolean(f.disparate_impact_violation || f.violation),
      });
      bars.push({
        attribute: attr,
        group: 'Reference Group',
        selectionRate: 1.0,
        relativeRatio: 1.0,
        isReference: true,
        isViolation: false,
      });
      return;
    }

    allGroups.forEach((groupName) => {
      const rate =
        groupMetrics[groupName]?.selection_rate ??
        f.group_selection_rates?.[groupName] ??
        0.0;
      const ratio = refRate > 0 ? rate / refRate : 0.0;
      const isRef = groupName === refGroup;
      const isViolating = !isRef && ratio < 0.8;

      bars.push({
        attribute: attr,
        group: groupName,
        selectionRate: rate,
        relativeRatio: Math.min(ratio, 1.25),
        isReference: isRef,
        isViolation: isViolating,
      });
    });
  });

  if (bars.length === 0) {
    return (
      <div className="p-8 glass-panel rounded-2xl text-center text-xs text-ink-soft">
        No subgroup disparity records found in this run.
      </div>
    );
  }

  const chartWidth = 760;
  const rowHeight = 48;
  const labelWidth = 150;
  const barAreaWidth = 390;
  const thresholdX = labelWidth + barAreaWidth * 0.8; // 80% mark
  const totalHeight = bars.length * rowHeight + 48;

  return (
    <div className="w-full glass-panel rounded-2xl p-6 sm:p-8 space-y-6">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-rule">
        <div className="space-y-1">
          <h3 className="text-base font-extrabold text-white flex items-center space-x-2.5">
            <Scale className="w-5 h-5 text-emerald-400" />
            <span>Subgroup Disparity Ratios (EEOC 4/5ths Rule)</span>
          </h3>
          <p className="text-xs text-ink-soft">
            Selection rate scaled relative to highest-selected benchmark ($1.00$). Dotted red marker indicates the 80% legal threshold.
          </p>
        </div>

        <div className="flex items-center space-x-4 text-xs font-mono">
          <span className="flex items-center space-x-2 px-2.5 py-1 rounded-full bg-rose-500/10 border border-rose-500/25 text-rose-400 font-semibold">
            <span className="w-2 h-2 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.6)]" />
            <span>Disparate Impact (&lt; 0.80)</span>
          </span>
          <span className="flex items-center space-x-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]" />
            <span>Compliant / Benchmark</span>
          </span>
        </div>
      </div>

      {/* Hand-Crafted Glowing SVG Disparity Visualization */}
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${chartWidth} ${totalHeight}`}
          className="w-full max-w-4xl font-sans"
          aria-label="Selection Disparity Bar Chart"
        >
          <defs>
            {/* Emerald Gradient */}
            <linearGradient id="emeraldGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#10B981" />
              <stop offset="100%" stopColor="#06B6D4" />
            </linearGradient>

            {/* Ruby Gradient */}
            <linearGradient id="rubyGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#F43F5E" />
              <stop offset="100%" stopColor="#FB7185" />
            </linearGradient>

            {/* Bar Glow Filter */}
            <filter id="emeraldGlow" x="-10%" y="-20%" width="120%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#10B981" floodOpacity="0.3" />
            </filter>
            <filter id="rubyGlow" x="-10%" y="-20%" width="120%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="4" floodColor="#F43F5E" floodOpacity="0.35" />
            </filter>
          </defs>

          {/* Scale Axis Lines */}
          <line x1={labelWidth} y1={28} x2={labelWidth + barAreaWidth} y2={28} stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
          <text x={labelWidth} y={20} fill="#64748B" fontSize="10" fontFamily="monospace">0.0</text>
          <text x={labelWidth + barAreaWidth * 0.5} y={20} fill="#64748B" fontSize="10" fontFamily="monospace" textAnchor="middle">0.50</text>
          <text x={labelWidth + barAreaWidth} y={20} fill="#64748B" fontSize="10" fontFamily="monospace" textAnchor="middle">1.00 (Ref)</text>

          {/* 0.80 Threshold Guide Line */}
          <line
            x1={thresholdX}
            y1={28}
            x2={thresholdX}
            y2={totalHeight - 8}
            stroke="#F43F5E"
            strokeDasharray="4 4"
            strokeWidth="1.8"
          />
          <rect
            x={thresholdX - 44}
            y={8}
            width={88}
            height={16}
            rx={8}
            fill="rgba(244, 63, 94, 0.15)"
            stroke="rgba(244, 63, 94, 0.4)"
          />
          <text
            x={thresholdX}
            y={20}
            fill="#FB7185"
            fontSize="9"
            fontFamily="monospace"
            textAnchor="middle"
            fontWeight="bold"
          >
            0.80 THRESHOLD
          </text>

          {/* Group Bars */}
          {bars.map((b, idx) => {
            const y = 40 + idx * rowHeight;
            const barWidth = Math.max(8, Math.min(barAreaWidth, b.relativeRatio * barAreaWidth));
            const fillGradient = b.isViolation ? 'url(#rubyGradient)' : 'url(#emeraldGradient)';
            const filter = b.isViolation ? 'url(#rubyGlow)' : 'url(#emeraldGlow)';

            return (
              <g key={`${b.attribute}-${b.group}-${idx}`} className="group cursor-pointer">
                {/* Background track */}
                <rect
                  x={labelWidth}
                  y={y + 8}
                  width={barAreaWidth}
                  height={20}
                  fill="rgba(255,255,255,0.03)"
                  stroke="rgba(255,255,255,0.06)"
                  rx="6"
                />

                {/* Subgroup Name */}
                <text
                  x={labelWidth - 12}
                  y={y + 22}
                  fill={b.isReference ? '#F8FAFC' : '#CBD5E1'}
                  fontSize="12"
                  fontWeight={b.isReference ? 'bold' : '500'}
                  textAnchor="end"
                >
                  {b.group}
                </text>

                {/* Attribute Domain Label */}
                {(idx === 0 || bars[idx - 1].attribute !== b.attribute) && (
                  <text
                    x={8}
                    y={y + 22}
                    fill="#38BDF8"
                    fontSize="11"
                    fontWeight="bold"
                    fontFamily="monospace"
                    letterSpacing="0.05em"
                  >
                    {b.attribute.toUpperCase()}
                  </text>
                )}

                {/* Active Glowing Bar */}
                <rect
                  x={labelWidth}
                  y={y + 8}
                  width={barWidth}
                  height={20}
                  fill={fillGradient}
                  filter={filter}
                  rx="6"
                  className="transition-all duration-700 ease-out"
                />

                {/* Quantitative Value & Status Label */}
                <text
                  x={labelWidth + barAreaWidth + 14}
                  y={y + 22}
                  fill={b.isViolation ? '#FB7185' : '#34D399'}
                  fontSize="11"
                  fontFamily="monospace"
                  fontWeight="bold"
                >
                  {b.relativeRatio.toFixed(3)}
                  {b.isReference
                    ? ' (Reference Benchmark)'
                    : b.isViolation
                    ? ' ⚠ Disparate Impact'
                    : ' Compliant'}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="p-3.5 rounded-xl bg-white/[0.02] border border-rule text-xs text-ink-soft flex items-center justify-between">
        <span>
          Evaluated under NIST AI RMF <strong className="text-white font-mono">MEASURE-2.1</strong> and <strong className="text-white font-mono">MAP-1.5</strong>.
        </span>
        <span className="font-mono text-emerald-400 font-semibold">
          100% Deterministic Arithmetic
        </span>
      </div>
    </div>
  );
}
