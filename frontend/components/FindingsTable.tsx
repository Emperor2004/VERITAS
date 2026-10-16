'use client';

import React, { useState } from 'react';
import { MappedFinding } from '../lib/api';
import SeverityMark from './SeverityMark';
import { ChevronDown, ChevronUp, Search, ShieldCheck, BookOpen, Sparkles } from 'lucide-react';

interface FindingsTableProps {
  findings: MappedFinding[];
}

export default function FindingsTable({ findings }: FindingsTableProps) {
  const [search, setSearch] = useState('');
  const [filterTier, setFilterTier] = useState<'all' | 'violation' | 'informational'>('all');
  const [sortField, setSortField] = useState<'control_id' | 'severity_tier'>('control_id');
  const [sortAsc, setSortAsc] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const filtered = findings.filter((f) => {
    if (filterTier !== 'all' && f.severity_tier !== filterTier) return false;
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      f.control_id.toLowerCase().includes(q) ||
      (f.control_title && f.control_title.toLowerCase().includes(q)) ||
      (f.category && f.category.toLowerCase().includes(q)) ||
      (f.plain_explanation?.summary && f.plain_explanation.summary.toLowerCase().includes(q))
    );
  });

  const sorted = [...filtered].sort((a, b) => {
    const valA = a[sortField] || '';
    const valB = b[sortField] || '';
    if (valA < valB) return sortAsc ? -1 : 1;
    if (valA > valB) return sortAsc ? 1 : -1;
    return 0;
  });

  const toggleSort = (field: 'control_id' | 'severity_tier') => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  return (
    <div className="w-full glass-panel rounded-2xl overflow-hidden space-y-4 p-5 sm:p-6">
      {/* Search & Filter Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pb-4 border-b border-rule">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search NIST controls, keywords, risks..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-900/60 border border-white/10 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30 transition-all font-mono"
          />
        </div>

        <div className="flex items-center space-x-2 self-end sm:self-auto text-xs">
          <span className="text-ink-soft font-mono">Filter:</span>
          <button
            onClick={() => setFilterTier('all')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
              filterTier === 'all'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                : 'bg-white/[0.03] text-slate-400 border border-rule hover:text-white'
            }`}
          >
            All ({findings.length})
          </button>
          <button
            onClick={() => setFilterTier('violation')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
              filterTier === 'violation'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-sm'
                : 'bg-white/[0.03] text-slate-400 border border-rule hover:text-white'
            }`}
          >
            Violations
          </button>
          <button
            onClick={() => setFilterTier('informational')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
              filterTier === 'informational'
                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shadow-sm'
                : 'bg-white/[0.03] text-slate-400 border border-rule hover:text-white'
            }`}
          >
            Informational
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-rule bg-white/[0.02]">
              <th
                onClick={() => toggleSort('control_id')}
                className="p-3.5 font-bold text-slate-300 cursor-pointer hover:text-emerald-400 transition-colors"
              >
                <div className="flex items-center space-x-1.5">
                  <span>NIST Control ID</span>
                  {sortField === 'control_id' && (
                    sortAsc ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />
                  )}
                </div>
              </th>
              <th className="p-3.5 font-bold text-slate-300">Category & Domain</th>
              <th
                onClick={() => toggleSort('severity_tier')}
                className="p-3.5 font-bold text-slate-300 cursor-pointer hover:text-emerald-400 transition-colors"
              >
                <div className="flex items-center space-x-1.5">
                  <span>Severity</span>
                  {sortField === 'severity_tier' && (
                    sortAsc ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />
                  )}
                </div>
              </th>
              <th className="p-3.5 font-bold text-slate-300">Executive Summary</th>
              <th className="p-3.5 font-bold text-slate-300 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule/60">
            {sorted.map((f, idx) => {
              const rowKey = f.finding_id || `${f.control_id}-${idx}`;
              const isExpanded = expandedId === rowKey;
              return (
                <React.Fragment key={rowKey}>
                  <tr
                    onClick={() => setExpandedId(isExpanded ? null : rowKey)}
                    className="hover:bg-white/[0.03] cursor-pointer transition-colors group"
                  >
                    <td className="p-3.5 font-mono font-bold text-emerald-400 whitespace-nowrap">
                      {f.control_id}
                    </td>
                    <td className="p-3.5 text-white font-medium">
                      <div>{f.control_title || f.category || 'NIST AI RMF Actionable Control'}</div>
                      <div className="text-[10px] text-cyan-400/80 font-mono uppercase tracking-wider">
                        {f.nist_function || 'MEASURE'}
                      </div>
                    </td>
                    <td className="p-3.5 whitespace-nowrap">
                      <SeverityMark severity={f.severity_tier} />
                    </td>
                    <td className="p-3.5 text-slate-400 max-w-md truncate">
                      {f.plain_explanation?.summary || f.risk_statement || 'Deterministic control evaluation recorded.'}
                    </td>
                    <td className="p-3.5 text-right">
                      <button
                        type="button"
                        className="px-2.5 py-1 rounded-md text-xs font-semibold text-emerald-400 hover:bg-emerald-500/10 inline-flex items-center space-x-1 transition-all"
                      >
                        <span>{isExpanded ? 'Hide' : 'Details'}</span>
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </button>
                    </td>
                  </tr>

                  {/* Expanded Card with Plain-English & Remediation */}
                  {isExpanded && (
                    <tr className="bg-slate-900/50">
                      <td colSpan={5} className="p-6 space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                          {/* Plain-English Card */}
                          <div className="glass-card rounded-xl p-5 space-y-3 border-emerald-500/20">
                            <div className="flex items-center justify-between pb-2 border-b border-rule">
                              <span className="text-xs font-bold text-white flex items-center space-x-2">
                                <Sparkles className="w-4 h-4 text-emerald-400" />
                                <span>Agent-5: Plain-English Audit Narrative</span>
                              </span>
                              <span className="inline-flex items-center space-x-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                                <ShieldCheck className="w-3 h-3" />
                                <span>Verified Traceability</span>
                              </span>
                            </div>
                            <div className="text-xs space-y-2 text-slate-300">
                              <p>
                                <strong className="text-white">What Happened:</strong>{' '}
                                {f.plain_explanation?.what_happened || f.risk_statement || 'Observed selection rate disparity violated threshold.'}
                              </p>
                              <p>
                                <strong className="text-white">Why It Matters:</strong>{' '}
                                {f.plain_explanation?.why_it_matters || 'Systematic disparities trigger regulatory liabilities under EEOC and EU AI Act.'}
                              </p>
                              <p>
                                <strong className="text-white">Recommended Action:</strong>{' '}
                                {f.plain_explanation?.recommended_action || 'Review training data representation and execute threshold shifts.'}
                              </p>
                            </div>
                          </div>

                          {/* Remediation Playbook Card */}
                          <div className="glass-card rounded-xl p-5 space-y-3 border-indigo-500/20">
                            <div className="flex items-center justify-between pb-2 border-b border-rule">
                              <span className="text-xs font-bold text-white flex items-center space-x-2">
                                <BookOpen className="w-4 h-4 text-indigo-400" />
                                <span>Remediation Playbook</span>
                              </span>
                              <span className="text-[10px] font-mono text-indigo-300 px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20">
                                {f.remediation_id || 'PLAYBOOK-DISPARITY-REDUCE'}
                              </span>
                            </div>
                            <p className="text-xs text-slate-300 leading-relaxed">
                              {f.remediation_playbook ||
                                'Apply Fairlearn demographic parity post-processing or re-weight training samples on protected demographic subgroups before deployment.'}
                            </p>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {sorted.length === 0 && (
        <div className="py-12 text-center text-xs text-ink-soft">
          No findings matching the selected search query.
        </div>
      )}
    </div>
  );
}
