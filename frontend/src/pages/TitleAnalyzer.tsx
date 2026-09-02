import React, { useState } from 'react';
import { Type, Sparkles, Copy, Check, Star, RefreshCw } from 'lucide-react';
import { TitleSuggestion } from '../types';
import { evaluateTitleOnly } from '../services/api';

interface TitleAnalyzerProps {
  suggestions?: TitleSuggestion[];
}

export const TitleAnalyzer: React.FC<TitleAnalyzerProps> = ({ suggestions = [] }) => {
  const [customTitle, setCustomTitle] = useState('');
  const [customAnalysis, setCustomAnalysis] = useState<any | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleEvaluateCustom = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customTitle.trim()) return;
    setIsEvaluating(true);
    try {
      const res = await evaluateTitleOnly(customTitle.trim());
      setCustomAnalysis(res.analysis);
    } catch (e) {
      console.error(e);
    } finally {
      setIsEvaluating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-r from-indigo-950/40 via-slate-900 to-slate-950 p-6 sm:p-8 border border-indigo-500/20 shadow-xl">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <Type className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
              Title Recommendation & Click Intelligence
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              High-converting title variations engineered from your channel description & competitor viral hooks
            </p>
          </div>
        </div>
      </div>

      {/* Suggested Titles */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/60">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-amber-300" />
            <h3 className="font-outfit text-base font-bold text-white">Recommended Title Angles</h3>
          </div>
          <span className="text-xs text-indigo-400 font-semibold">Engineered For High CTR</span>
        </div>

        {suggestions && suggestions.length > 0 ? (
          <div className="space-y-3">
            {suggestions.map((s, idx) => (
              <div
                key={idx}
                className="glass-card rounded-xl p-4 bg-slate-900/70 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4 group"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-500/20 text-[10px] font-bold text-indigo-400 border border-indigo-500/30">
                      {s.rank}
                    </span>
                    <span className="rounded-md bg-violet-500/10 px-2 py-0.5 text-[10px] font-semibold text-violet-300 border border-violet-500/20">
                      {s.hook_type} Angle
                    </span>
                    <span className="rounded-md bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-400">
                      {s.orientation}
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-white group-hover:text-indigo-300 transition-colors">
                    {s.title}
                  </h4>
                </div>

                {/* Score Badges & Copy */}
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-slate-400">Clarity: <strong className="text-slate-200">{s.clarity_score}/10</strong></span>
                    <span className="text-slate-400">Curiosity: <strong className="text-amber-400">{s.curiosity_score}/10</strong></span>
                  </div>

                  <button
                    onClick={() => handleCopy(s.title, idx)}
                    className="flex items-center gap-1 rounded-xl bg-slate-800 hover:bg-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-200 transition-all active:scale-95 cursor-pointer"
                  >
                    {copiedIndex === idx ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5 text-slate-400" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 text-center text-xs text-slate-400 space-y-1">
            <p className="font-semibold text-slate-300">No channel title suggestions generated yet.</p>
            <p>Run a channel analysis to get personalized title variations, or test any custom title in the live scorer below!</p>
          </div>
        )}
      </div>

      {/* Live Custom Title Tester */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <h3 className="font-outfit text-base font-bold text-white">Live Custom Title Scorer</h3>
        <form onSubmit={handleEvaluateCustom} className="flex gap-2">
          <input
            type="text"
            placeholder="Type any video title to test curiosity, clarity, specificity & urgency scores..."
            value={customTitle}
            onChange={(e) => setCustomTitle(e.target.value)}
            className="flex-1 rounded-xl bg-slate-900 border border-slate-800 px-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={isEvaluating || !customTitle.trim()}
            className="rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 hover:scale-[1.02] active:scale-98 disabled:opacity-50"
          >
            {isEvaluating ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Score Title'}
          </button>
        </form>

        {customAnalysis && (
          <div className="mt-4 p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3 text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-center">
              <div className="p-2.5 rounded-lg bg-slate-800/60">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Clarity</span>
                <p className="text-lg font-bold font-outfit text-white mt-0.5">{customAnalysis.clarity_score}/10</p>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-800/60">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Curiosity</span>
                <p className="text-lg font-bold font-outfit text-amber-400 mt-0.5">{customAnalysis.curiosity_score}/10</p>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-800/60">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Specificity</span>
                <p className="text-lg font-bold font-outfit text-indigo-400 mt-0.5">{customAnalysis.specificity_score}/10</p>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-800/60">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Urgency</span>
                <p className="text-lg font-bold font-outfit text-rose-400 mt-0.5">{customAnalysis.urgency_score}/10</p>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-800/60 col-span-2 sm:col-span-1">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Hook Type</span>
                <p className="text-xs font-bold text-slate-200 mt-1">{customAnalysis.hook_type}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
