'use client';

import React, { useState, useRef } from 'react';
import { UploadCloud, FileSpreadsheet, Loader2, Sparkles, CheckCircle2 } from 'lucide-react';
import { validateDataset, ColumnInspection } from '../lib/api';

interface DropzoneProps {
  onValidated: (file: File, inspection: ColumnInspection) => void;
  onError: (errorMsg: string) => void;
  isProcessing: boolean;
}

export default function Dropzone({ onValidated, onError, isProcessing }: DropzoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'csv' && ext !== 'xlsx') {
      onError('Unsupported file format. Please upload a .csv or .xlsx dataset.');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      onError('File size exceeds the 10 MB limit.');
      return;
    }

    setSelectedFile(file);
    setIsValidating(true);
    try {
      const inspection = await validateDataset(file);
      onValidated(file, inspection);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to validate uploaded file';
      onError(msg);
    } finally {
      setIsValidating(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
      className={`group relative w-full border-2 border-dashed p-10 rounded-2xl transition-all cursor-pointer flex flex-col items-center justify-center text-center overflow-hidden ${
        isDragOver
          ? 'border-emerald-400 bg-emerald-500/[0.08] shadow-[0_0_35px_rgba(16,185,129,0.25)] scale-[1.01]'
          : selectedFile
          ? 'border-emerald-500/50 bg-slate-900/60 shadow-[0_0_25px_rgba(16,185,129,0.15)]'
          : 'border-white/15 hover:border-emerald-400/50 bg-slate-900/40 hover:bg-slate-900/60 shadow-lg'
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.xlsx"
        className="hidden"
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            handleFile(e.target.files[0]);
          }
        }}
      />

      {/* Decorative ambient radial glow */}
      <div className="absolute -top-12 -left-12 w-40 h-40 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none group-hover:bg-emerald-500/20 transition-all" />
      <div className="absolute -bottom-12 -right-12 w-40 h-40 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none group-hover:bg-cyan-500/20 transition-all" />

      {/* Central Icon */}
      <div className="relative mb-5">
        <div
          className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-all ${
            isValidating || isProcessing
              ? 'bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 shadow-[0_0_25px_rgba(16,185,129,0.3)]'
              : selectedFile
              ? 'bg-gradient-to-tr from-emerald-500 to-teal-400 text-slate-950 shadow-[0_0_20px_rgba(16,185,129,0.35)] scale-105'
              : 'bg-white/[0.05] border border-white/10 text-slate-300 group-hover:border-emerald-500/30 group-hover:text-emerald-400 group-hover:scale-110 shadow-md'
          }`}
        >
          {isValidating || isProcessing ? (
            <Loader2 className="w-8 h-8 animate-spin" />
          ) : selectedFile ? (
            <FileSpreadsheet className="w-8 h-8 stroke-[2.2]" />
          ) : (
            <UploadCloud className="w-8 h-8 stroke-[1.8]" />
          )}
        </div>
      </div>

      <div className="space-y-1.5 max-w-sm">
        <p className="text-sm font-bold text-white tracking-tight flex items-center justify-center space-x-2">
          <span>{selectedFile ? selectedFile.name : 'Upload AI Model Decision Dataset'}</span>
          {selectedFile && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
        </p>
        <p className="text-xs text-ink-soft">
          {selectedFile
            ? `${(selectedFile.size / 1024).toFixed(1)} KB · Click or drag another file to replace`
            : 'Drop a CSV or XLSX here (up to 10 MB). Instant schema discovery.'}
        </p>
      </div>

      {isValidating && (
        <div className="mt-4 flex items-center space-x-2 text-xs text-emerald-400 font-mono bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20 animate-pulse">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>Agent-1 analyzing column roles & privacy boundary...</span>
        </div>
      )}
    </div>
  );
}
