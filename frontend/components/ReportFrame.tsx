'use client';

import React, { useState } from 'react';
import { ShieldCheck, Download, ExternalLink, Loader2 } from 'lucide-react';

interface ReportFrameProps {
  runId: string;
}

export default function ReportFrame({ runId }: ReportFrameProps) {
  const [isLoading, setIsLoading] = useState(true);
  const reportUrl = `/api/runs/${runId}/report.html`;
  const pdfUrl = `/api/runs/${runId}/report.pdf`;

  return (
    <div className="w-full bg-sheet border border-rule rounded overflow-hidden flex flex-col h-[800px]">
      {/* Report Header Bar */}
      <div className="px-5 py-3 border-b border-rule bg-paper/60 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-verdigris" />
          <span className="text-xs font-bold text-ink">
            Executive Audit Workpaper & Regulatory Compliance Report
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sheet border border-rule text-ink-soft">
            Sandboxed
          </span>
        </div>

        <div className="flex items-center space-x-3">
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            download={`veritas_audit_${runId.slice(0, 8)}.pdf`}
            className="px-3 py-1.5 rounded bg-verdigris hover:bg-verdigris-hover text-white text-xs font-semibold flex items-center space-x-1.5 transition-colors shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Official PDF</span>
          </a>
        </div>
      </div>

      {/* Sandboxed iframe */}
      <div className="relative flex-1 w-full bg-white">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
            <div className="flex items-center space-x-2 text-xs font-mono text-ink-soft">
              <Loader2 className="w-4 h-4 animate-spin text-verdigris" />
              <span>Rendering sandboxed HTML report...</span>
            </div>
          </div>
        )}
        <iframe
          src={reportUrl}
          title="Audit Workpaper Report"
          sandbox="allow-scripts"
          onLoad={() => setIsLoading(false)}
          className="w-full h-full border-none"
        />
      </div>
    </div>
  );
}
