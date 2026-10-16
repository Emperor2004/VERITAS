'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import ReportFrame from '../../../../../components/ReportFrame';

export default function ReportPage() {
  const params = useParams();
  const runId = params.id as string;

  return (
    <div className="space-y-4">
      <ReportFrame runId={runId} />
    </div>
  );
}
