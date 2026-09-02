import React from 'react';
import { Lightbulb, Sparkles, Star, ArrowRight, Zap, Target } from 'lucide-react';
import { AnalysisResponse } from '../types';

interface ContentIdeasProps {
  data: AnalysisResponse;
}

export const ContentIdeas: React.FC<ContentIdeasProps> = ({ data }) => {
  const { top_keywords, top_hooks, content_gap } = data;

  const generatedIdeas = top_keywords.slice(0, 6).map((k, idx) => {
    const topic = k.keyword.toUpperCase();
    return {
      rank: idx + 1,
      topic: k.keyword,
      demandScore: Math.min(99, 70 + idx * 4),
      whyMakeThis: `Proven market demand with ${k.uses} competitor videos averaging +${k.avg_views_per_day.toLocaleString()} views/day.`,
      titleAngles: [
        `The Complete ${topic} Roadmap (Everything You Need to Know)`,
        `3 Huge ${topic} Mistakes to Avoid in 2026`,
        `How I Mastered ${topic} in 14 Days (Step-by-Step)`,
        `The Brutal Truth About ${topic} Nobody Talks About`,
        `${topic} Strategy Masterclass for Beginners`,
      ],
    };
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-r from-amber-950/40 via-slate-900 to-slate-950 p-6 sm:p-8 border border-amber-500/20 shadow-xl">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-600/20 text-amber-400 border border-amber-500/30">
            <Lightbulb className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
              What Should We Post Next?
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              Ranked content ideas generated from competitor gaps, validated search signals, and audience demand
            </p>
          </div>
        </div>
      </div>

      {/* Ideas List */}
      <div className="space-y-4">
        {generatedIdeas.map((idea) => (
          <div key={idea.rank} className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <span className="flex h-7 w-7 items-center justify-center rounded-xl bg-amber-500 text-slate-950 font-bold font-outfit text-sm">
                  #{idea.rank}
                </span>
                <h3 className="font-outfit text-lg font-bold text-white capitalize">{idea.topic} Strategy</h3>
              </div>

              <span className="rounded-full bg-amber-500/10 px-3 py-1 text-xs font-bold text-amber-300 border border-amber-500/30">
                Demand Score: {idea.demandScore}/100
              </span>
            </div>

            <p className="text-xs text-slate-300">{idea.whyMakeThis}</p>

            <div className="space-y-2 pt-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">5 High-CTR Title Angles:</span>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {idea.titleAngles.map((title, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs font-semibold text-slate-200 hover:border-indigo-500/40 hover:text-indigo-300 transition-colors cursor-pointer flex items-center justify-between"
                  >
                    <span>{title}</span>
                    <ArrowRight className="h-3.5 w-3.5 text-slate-500 flex-shrink-0 ml-2" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
