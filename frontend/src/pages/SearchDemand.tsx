import React from 'react';
import { Search, Sparkles, TrendingUp, Target, ArrowRight } from 'lucide-react';
import { AnalysisResponse } from '../types';

interface SearchDemandProps {
  data: AnalysisResponse;
}

export const SearchDemand: React.FC<SearchDemandProps> = ({ data }) => {
  const { top_keywords, content_gap, all_videos } = data;

  // Derive high-opportunity search terms
  const searchOpportunities = top_keywords
    .filter((k) => k.channels >= 2)
    .map((k) => ({
      term: k.keyword,
      demandScore: Math.min(100, Math.round(k.avg_views_per_day / 50 + k.uses * 5)),
      competition: k.channels > 3 ? 'High' : 'Moderate',
      avgViewsDay: k.avg_views_per_day,
      suggestedAngle: `How to Master ${k.keyword.toUpperCase()} (The Secret Step-by-Step Method)`,
    }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-r from-indigo-950/40 via-slate-900 to-slate-950 p-6 sm:p-8 border border-indigo-500/20 shadow-xl">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <Search className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
              Search Demand & Opportunity Finder
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              Pinpoint high-search intent terms with validated viewer demand across competitors
            </p>
          </div>
        </div>
      </div>

      {/* Opportunity Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {searchOpportunities.map((opp, idx) => (
          <div key={idx} className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-bold font-outfit text-base text-white capitalize">{opp.term}</span>
              <span className="rounded-md bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-300 border border-emerald-500/30">
                Score: {opp.demandScore}/100
              </span>
            </div>

            <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
              <span>Velocity: <strong className="text-emerald-400">+{opp.avgViewsDay.toLocaleString()}/d</strong></span>
              <span>Competition: <strong className="text-indigo-400">{opp.competition}</strong></span>
            </div>

            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-[11px] space-y-1">
              <span className="text-slate-500 font-semibold uppercase text-[9px]">Suggested Title Angle:</span>
              <p className="text-slate-200 font-semibold">{opp.suggestedAngle}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
