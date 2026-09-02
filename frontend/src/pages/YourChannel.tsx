import React from 'react';
import { User, Eye, Flame, PlaySquare, Calendar, Hash, Tag, Clock } from 'lucide-react';
import { AnalysisResponse, VideoItem } from '../types';
import { MetricCard } from '../components/MetricCard';
import { VideoCard } from '../components/VideoCard';

interface YourChannelProps {
  data: AnalysisResponse;
}

export const YourChannel: React.FC<YourChannelProps> = ({ data }) => {
  const { own_channel, own_stats, own_videos, top_keywords, top_hooks } = data;

  return (
    <div className="space-y-6">
      {/* Channel Header Banner */}
      <div className="glass-panel rounded-3xl p-6 sm:p-8 border border-slate-800 bg-gradient-to-r from-slate-900 via-indigo-950/30 to-slate-900">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="flex items-center gap-5">
            <img
              src={own_channel.thumbnail || ''}
              alt={own_channel.title}
              className="h-20 w-20 rounded-2xl object-cover ring-4 ring-indigo-500/30 shadow-xl"
            />
            <div>
              <div className="inline-flex items-center gap-1.5 rounded-full bg-indigo-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-indigo-400 border border-indigo-500/20 mb-1.5">
                <User className="h-3 w-3" />
                <span>Primary Analyzed Channel</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
                {own_channel.title}
              </h1>
              <p className="mt-1 text-xs text-slate-400 max-w-xl line-clamp-2">
                {own_channel.description || 'No description available'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="rounded-2xl bg-slate-800/80 p-4 border border-slate-700/80 text-center min-w-[100px]">
              <span className="text-xl font-black font-outfit text-white">
                {own_channel.subscriber_count ? `${(own_channel.subscriber_count / 1000).toFixed(1)}k` : 'Hidden'}
              </span>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Subscribers</p>
            </div>
            <div className="rounded-2xl bg-slate-800/80 p-4 border border-slate-700/80 text-center min-w-[100px]">
              <span className="text-xl font-black font-outfit text-white">
                {own_stats.total_videos}
              </span>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Tracked Videos</p>
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Channel Views"
          value={own_stats.total_views}
          subtitle={`Across ${own_stats.total_videos} videos`}
          icon={Eye}
          color="indigo"
        />
        <MetricCard
          title="Median Video Views"
          value={own_stats.median_views}
          subtitle="Baseline benchmark"
          icon={Flame}
          color="emerald"
        />
        <MetricCard
          title="Avg Views / Day"
          value={`+${own_stats.avg_views_per_day.toLocaleString()}`}
          subtitle="Current pace"
          icon={PlaySquare}
          color="amber"
        />
        <MetricCard
          title="Avg Video Length"
          value={`${own_stats.avg_duration_minutes} min`}
          subtitle={`${own_stats.shorts_count} Shorts • ${own_stats.long_count} Long`}
          icon={Clock}
          color="violet"
        />
      </div>

      {/* Keywords & Hooks Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Keywords */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/60 mb-3">
            <div className="flex items-center gap-2">
              <Hash className="h-4 w-4 text-indigo-400" />
              <h3 className="font-outfit text-base font-bold text-white">Top Title Keywords</h3>
            </div>
            <span className="text-xs text-slate-400">By frequency & velocity</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="pb-2 font-medium">Keyword</th>
                  <th className="pb-2 font-medium">Uses</th>
                  <th className="pb-2 font-medium text-right">Avg Views / Day</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {top_keywords.slice(0, 8).map((k) => (
                  <tr key={k.keyword} className="hover:bg-slate-800/30">
                    <td className="py-2.5 font-semibold text-slate-200">{k.keyword}</td>
                    <td className="py-2.5 text-slate-400">{k.uses}</td>
                    <td className="py-2.5 font-bold text-emerald-400 text-right">
                      +{k.avg_views_per_day.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top Hooks */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/60 mb-3">
            <div className="flex items-center gap-2">
              <Tag className="h-4 w-4 text-violet-400" />
              <h3 className="font-outfit text-base font-bold text-white">Top Hook Words</h3>
            </div>
            <span className="text-xs text-slate-400">High-converting trigger words</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="pb-2 font-medium">Hook Trigger</th>
                  <th className="pb-2 font-medium">Uses</th>
                  <th className="pb-2 font-medium text-right">Avg Views</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {top_hooks.slice(0, 8).map((h) => (
                  <tr key={h.hook} className="hover:bg-slate-800/30">
                    <td className="py-2.5 font-semibold text-violet-300">#{h.hook}</td>
                    <td className="py-2.5 text-slate-400">{h.uses}</td>
                    <td className="py-2.5 font-bold text-slate-200 text-right">
                      {h.avg_views.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Your Channel Videos Grid */}
      <div className="space-y-3">
        <h3 className="font-outfit text-base font-bold text-white">All Channel Uploads</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {own_videos.map((video) => (
            <VideoCard key={video.video_id} video={video} />
          ))}
        </div>
      </div>
    </div>
  );
};
