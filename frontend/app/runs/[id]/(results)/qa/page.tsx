'use client';

import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import { askQuestion, QAResponse } from '../../../../../lib/api';
import { MessageSquare, Send, ShieldAlert, Sparkles, BookOpen, Loader2, Bot, User } from 'lucide-react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: string[];
  tokens?: number;
}

export default function QAPage() {
  const params = useParams();
  const runId = params.id as string;

  const [input, setInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        'Hello. I am the VERITAS Conversational Audit Assistant (Agent-6). I have direct read-only access to this case file\'s fairness tests, outlier clusters, and NIST AI RMF mappings. What would you like to examine?',
      citations: ['NIST-MEASURE-2.1', 'NIST-MAP-1.5'],
    },
  ]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSubmitting) return;

    const question = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setIsSubmitting(true);

    try {
      const res: QAResponse = await askQuestion(runId, question);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.answer,
          citations: res.citations,
          tokens: res.tokens_used,
        },
      ]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error executing audit query';
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Audit Query Error: ${msg}. Notice: This assistant operates in strict read-only mode and refuses mutation tools.`,
        },
      ]);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl overflow-hidden flex flex-col h-[700px]">
      {/* Header Bar */}
      <div className="p-4 sm:p-5 border-b border-rule bg-slate-900/60 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-white shadow-[0_0_15px_rgba(99,102,241,0.4)]">
            <Bot className="w-4 h-4 stroke-[2.2]" />
          </div>
          <div>
            <span className="text-xs font-bold text-white flex items-center space-x-2">
              <span>Ask VERITAS Conversational Auditor (Agent-6)</span>
              <span className="text-[10px] font-mono px-2 py-0.2 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                Active
              </span>
            </span>
            <p className="text-[11px] text-ink-soft">Direct interrogation of disparity ratios, outlier drivers, and playbooks</p>
          </div>
        </div>

        <div className="flex items-center space-x-1.5 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>Immutable Read-Only Mode</span>
        </div>
      </div>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex items-start space-x-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {m.role === 'assistant' && (
              <div className="w-7 h-7 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 mt-0.5">
                <Bot className="w-4 h-4" />
              </div>
            )}

            <div
              className={`max-w-xl rounded-2xl p-4 text-xs leading-relaxed space-y-2.5 ${
                m.role === 'user'
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 font-semibold shadow-[0_0_20px_rgba(16,185,129,0.25)]'
                  : 'glass-card border-white/10 text-slate-200 shadow-md'
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>

              {m.citations && m.citations.length > 0 && (
                <div className="pt-2.5 border-t border-white/10 flex flex-wrap items-center gap-1.5">
                  <span className="text-[10px] font-mono font-bold uppercase opacity-75">
                    Verified Citations:
                  </span>
                  {m.citations.map((c, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 rounded-md bg-white/[0.08] border border-white/10 font-mono text-[10px] text-emerald-300 font-semibold"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {m.role === 'user' && (
              <div className="w-7 h-7 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 shrink-0 mt-0.5">
                <User className="w-4 h-4" />
              </div>
            )}
          </div>
        ))}

        {isSubmitting && (
          <div className="flex items-center space-x-2 text-xs font-mono text-emerald-400 p-3 bg-emerald-500/5 rounded-xl border border-emerald-500/15 max-w-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Consulting case findings & NIST controls...</span>
          </div>
        )}
      </div>

      {/* Suggested Quick Prompts */}
      <div className="px-5 py-2.5 bg-slate-900/60 border-t border-rule flex items-center space-x-2 overflow-x-auto text-xs text-ink-soft">
        <span className="text-[10px] uppercase font-mono font-bold text-slate-400 shrink-0">Prompts:</span>
        <button
          onClick={() => setInput('Which protected attribute has the lowest disparate impact ratio?')}
          className="px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-slate-300 hover:text-white whitespace-nowrap text-xs transition-colors"
        >
          Lowest disparate impact?
        </button>
        <button
          onClick={() => setInput('Explain the remediation playbook for NIST-MEASURE-2.1.')}
          className="px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-slate-300 hover:text-white whitespace-nowrap text-xs transition-colors"
        >
          Remediation for MEASURE-2.1?
        </button>
        <button
          onClick={() => setInput('Summarize the top outlier clusters detected by Agent-2.')}
          className="px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 text-slate-300 hover:text-white whitespace-nowrap text-xs transition-colors"
        >
          Top outlier clusters?
        </button>
      </div>

      {/* Input Bar */}
      <form onSubmit={handleSend} className="p-3 sm:p-4 border-t border-rule bg-slate-900/80 flex items-center space-x-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about disparities, anomalies, or compliance actions..."
          disabled={isSubmitting}
          className="flex-1 px-4 py-2.5 bg-slate-950/80 border border-white/10 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30 transition-all font-sans"
        />
        <button
          type="submit"
          disabled={!input.trim() || isSubmitting}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-400 hover:from-emerald-400 hover:to-teal-300 disabled:opacity-40 text-slate-950 text-xs font-bold uppercase tracking-wide flex items-center space-x-2 transition-all shadow-[0_0_20px_rgba(16,185,129,0.3)]"
        >
          <span>Ask</span>
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
}
