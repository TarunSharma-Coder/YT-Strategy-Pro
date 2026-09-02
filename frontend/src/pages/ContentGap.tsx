import React from 'react';
import { Split, Sparkles, TrendingUp, CheckCircle2, ArrowRight } from 'lucide-react';
import { AnalysisResponse } from '../types';

interface ContentGapProps {
  data: AnalysisResponse;
}

export const ContentGap: React.FC<ContentGapProps> = ({ data }) => {
  const { content_gap, own_channel } = data;
  const { category_pivot, opportunities } = content_gap;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-r from-indigo-950/40 via-slate-900 to-slate-950 p-6 sm:p-8 border border-indigo-500/20 shadow-xl">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <Split className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
              Content Gap Matrix
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              Discover topic niches competitors are publishing and getting views on that your channel has not covered
            </p>
          </div>
        </div>
      </div>

      {/* Category Pivot Breakdown */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <h3 className="font-outfit text-base font-bold text-white">Category Distribution by Channel</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="pb-3 font-medium">Channel</th>
                <th className="pb-3 font-medium">Academic / Conceptual</th>
                <th className="pb-3 font-medium">Strategy / Career</th>
                <th className="pb-3 font-medium">Other / Mixed</th>
                <th className="pb-3 font-medium text-right">Total Uploads</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {category_pivot.map((p) => {
                const isOwn = p.channel === own_channel.title;
                return (
                  <tr key={p.channel} className={isOwn ? 'bg-indigo-950/30' : 'hover:bg-slate-800/20'}>
                    <td className="py-3 font-bold text-slate-100 flex items-center gap-2">
                      <span>{p.channel}</span>
                      {isOwn && (
                        <span className="rounded-md bg-indigo-500/20 px-1.5 py-0.5 text-[9px] font-bold text-indigo-300">
                          YOU
                        </span>
                      )}
                    </td>
                    <td className="py-3 text-slate-300 font-semibold">{p.Academic || 0}</td>
                    <td className="py-3 text-slate-300 font-semibold">{p['Non-academic / Strategy'] || 0}</td>
                    <td className="py-3 text-slate-400">{p['Other / mixed'] || 0}</td>
                    <td className="py-3 font-bold text-slate-200 text-right">{p.total_videos}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Untapped Topic Opportunities */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-amber-300" />
            <h3 className="font-outfit text-base font-bold text-white">
              Untapped Topic Opportunities ({opportunities.length})
            </h3>
          </div>
          <span className="text-xs text-slate-400">Topics competitors covered but you haven't</span>
        </div>

        {opportunities.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {opportunities.map((opp, idx) => (
              <div
                key={idx}
                className="rounded-xl bg-slate-900/60 p-4 border border-slate-800/80 hover:border-indigo-500/40 transition-colors space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-indigo-300 capitalize text-sm">{opp.topic}</span>
                  <span className="rounded-md bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-400 border border-emerald-500/20">
                    {opp.competitor_views.toLocaleString()} Total Competitor Views
                  </span>
                </div>

                <p className="text-[11px] text-slate-400">
                  Covered by {opp.competitor_channels} competitor channel(s) across {opp.competitor_videos} video(s).
                </p>

                {opp.best_video && (
                  <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px]">
                    <span className="text-slate-300 truncate max-w-[280px]">Top: "{opp.best_video}"</span>
                    <a
                      href={opp.best_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-0.5"
                    >
                      Inspect <ArrowRight className="h-3 w-3" />
                    </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-slate-500 text-xs">
            No clear keyword gaps detected in this date scope.
          </div>
        )}
      </div>
    </div>
  );
};
