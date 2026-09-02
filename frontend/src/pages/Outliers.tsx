import React, { useState } from 'react';
import { Zap, Flame, Filter, Trophy, Sparkles } from 'lucide-react';
import { VideoItem } from '../types';
import { VideoCard } from '../components/VideoCard';

interface OutliersProps {
  outliers: VideoItem[];
}

export const Outliers: React.FC<OutliersProps> = ({ outliers }) => {
  const [filterTier, setFilterTier] = useState<string>('All');
  const [filterType, setFilterType] = useState<string>('All');

  const filteredOutliers = outliers.filter((video) => {
    if (!video.is_outlier) return false;
    if (filterTier === '10x' && video.outlier_tier !== '10x Mega Viral') return false;
    if (filterTier === '5x' && video.outlier_tier !== '5x Super Outlier' && video.outlier_tier !== '10x Mega Viral') return false;
    if (filterTier === '2x' && (video.outlier_multiplier || 0) < 2.0) return false;
    if (filterType !== 'All' && video.video_type !== filterType) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="rounded-3xl bg-gradient-to-r from-amber-950/40 via-slate-900 to-slate-950 p-6 sm:p-8 border border-amber-500/20 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-amber-500/10 px-3 py-1 text-xs font-semibold text-amber-300 border border-amber-500/20 mb-2">
              <Flame className="h-3.5 w-3.5 fill-current" />
              Viral Multiplier Detection Engine
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
              Viral Outlier Radar
            </h1>
            <p className="mt-1 text-xs sm:text-sm text-slate-400">
              Videos outperforming their channel average view velocity by 2x to 10x+. Analyze what made them win.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="rounded-2xl bg-amber-500/10 border border-amber-500/30 p-4 text-center">
              <span className="text-2xl font-black font-outfit text-amber-300">{outliers.filter(o => o.is_outlier).length}</span>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-400">Outliers Found</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 glass-panel p-3 rounded-2xl border border-slate-800">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {['All', '10x', '5x', '2x'].map((tier) => (
            <button
              key={tier}
              id={`outlier-tier-${tier}`}
              onClick={() => setFilterTier(tier)}
              className={`rounded-xl px-3.5 py-1.5 text-xs font-semibold transition-all ${
                filterTier === tier
                  ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              {tier === 'All' ? 'All Outliers' : `${tier}+ Multiplier`}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-3.5 w-3.5 text-slate-400" />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="rounded-xl bg-slate-900 border border-slate-700 px-3 py-1.5 text-xs text-slate-200 outline-none"
          >
            <option value="All">All Formats</option>
            <option value="Long video">Long Form Only</option>
            <option value="Shorts">Shorts Only</option>
          </select>
        </div>
      </div>

      {/* Grid of Outliers */}
      {filteredOutliers.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredOutliers.map((video) => (
            <VideoCard key={video.video_id} video={video} />
          ))}
        </div>
      ) : (
        <div className="glass-panel rounded-3xl p-12 text-center border border-slate-800">
          <Zap className="h-10 w-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-300">No outliers match this filter</h3>
          <p className="text-xs text-slate-500 mt-1">Try selecting a broader multiplier tier or format filter.</p>
        </div>
      )}
    </div>
  );
};
