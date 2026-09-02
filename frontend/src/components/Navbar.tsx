import React from 'react';
import { Sparkles, SlidersHorizontal, Activity, Layers } from 'lucide-react';
import { YoutubeIcon } from './YoutubeIcon';
import { AnalysisResponse } from '../types';

interface NavbarProps {
  analysisData: AnalysisResponse | null;
  onOpenSetup: () => void;
  selectedChannelFilter: string;
  onSelectChannelFilter: (channel: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  analysisData,
  onOpenSetup,
  selectedChannelFilter,
  onSelectChannelFilter,
}) => {
  const channelNames = analysisData
    ? [analysisData.own_channel.title, ...analysisData.competitor_channels.map((c) => c.title)]
    : [];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-[#090d16]/90 backdrop-blur-xl">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-red-600 via-rose-500 to-indigo-600 shadow-lg shadow-red-500/20">
            <YoutubeIcon className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-outfit text-lg font-bold tracking-tight text-white">
                YT Strategy <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">Pro</span>
              </span>
              <span className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-[10px] font-semibold text-indigo-400 border border-indigo-500/20">
                v2.0 Fullstack
              </span>
            </div>
            <p className="text-xs text-slate-400">Viral Outliers & Packaging Intelligence</p>
          </div>
        </div>

        {/* Channel Filter & Actions */}
        <div className="flex items-center gap-3">
          {analysisData && (
            <div className="hidden md:flex items-center gap-2 bg-slate-900/90 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300">
              <Layers className="h-3.5 w-3.5 text-indigo-400" />
              <span className="text-slate-500">Filter:</span>
              <select
                id="channel-filter-select"
                value={selectedChannelFilter}
                onChange={(e) => onSelectChannelFilter(e.target.value)}
                className="bg-transparent font-medium text-slate-200 outline-none cursor-pointer"
              >
                <option value="All" className="bg-slate-900 text-slate-200">
                  All Channels ({analysisData.summary.total_channels})
                </option>
                {channelNames.map((name) => (
                  <option key={name} value={name} className="bg-slate-900 text-slate-200">
                    {name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {analysisData && (
            <div className="hidden lg:flex items-center gap-2 rounded-full bg-emerald-500/10 px-3 py-1 border border-emerald-500/20 text-xs font-medium text-emerald-400">
              <Activity className="h-3.5 w-3.5 animate-pulse" />
              <span>{analysisData.summary.total_videos_analyzed} Videos Analyzed</span>
            </div>
          )}

          <button
            id="open-setup-btn"
            onClick={onOpenSetup}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-violet-600 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-500/20 transition-all hover:scale-[1.02] hover:shadow-indigo-500/30 active:scale-[0.98]"
          >
            <SlidersHorizontal className="h-4 w-4" />
            <span>{analysisData ? 'Change Channels' : 'Setup & Analyze'}</span>
            <Sparkles className="h-3.5 w-3.5 text-amber-300" />
          </button>
        </div>
      </div>
    </header>
  );
};
