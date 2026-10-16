'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { fetchFindings } from '../../../../../lib/api';
import FindingsTable from '../../../../../components/FindingsTable';
import { ShieldCheck } from 'lucide-react';

export default function ControlsPage() {
  const params = useParams();
  const runId = params.id as string;

  const { data } = useQuery({
    queryKey: ['findings', runId],
    queryFn: () => fetchFindings(runId),
  });

  const findings = data?.items || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-ink flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-verdigris" />
            <span>NIST AI RMF Actionable Findings & Verification</span>
          </h2>
          <p className="text-xs text-ink-soft">
            Controls matched deterministically to NIST AI 100-1 taxonomy with number-verified explanations.
          </p>
        </div>
      </div>

      <FindingsTable findings={findings} />
    </div>
  );
}
