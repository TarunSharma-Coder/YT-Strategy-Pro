import React from 'react';
import { Users, Eye, TrendingUp, BarChart2, Video, Trophy } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';
import { AnalysisResponse } from '../types';
import { VideoCard } from '../components/VideoCard';

interface CompetitorsProps {
  data: AnalysisResponse;
  onOpenSetup?: () => void;
}

export const Competitors: React.FC<CompetitorsProps> = ({ data, onOpenSetup }) => {
  const { own_channel, own_stats, competitor_channels, competitor_videos, competitors_stats } = data;

  const comparisonData = [
    {
      name: own_channel.title,
      viewsPerDay: own_stats.avg_views_per_day,
      avgViews: own_stats.avg_views,
      totalVideos: own_stats.total_videos,
      shorts: own_stats.shorts_count,
      long: own_stats.long_count,
    },
    ...competitors_stats.map((c) => ({
      name: c.channel,
      viewsPerDay: c.stats.avg_views_per_day,
      avgViews: c.stats.avg_views,
      totalVideos: c.stats.total_videos,
      shorts: c.stats.shorts_count,
      long: c.stats.long_count,
    })),
  ];

  if (competitor_channels.length === 0) {
    return (
      <div className="space-y-6">
        <div className="rounded-3xl bg-gradient-to-r from-violet-950/40 via-slate-900 to-slate-950 p-6 sm:p-8 border border-violet-500/20 shadow-xl">
          <div className="flex items-center gap-3 mb-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600/20 text-violet-400 border border-violet-500/30">
              <Users className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
                Competitor Benchmark Matrix
              </h1>
              <p className="text-xs sm:text-sm text-slate-400">
                Compare your metrics directly against up to 5 competitor channels
              </p>
            </div>
          </div>
        </div>

        <div className="glass-panel rounded-3xl p-12 text-center border border-slate-800 max-w-xl mx-auto space-y-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-violet-600/20 text-violet-400 border border-violet-500/30 mx-auto">
            <Users className="h-8 w-8" />
          </div>
          <h3 className="font-outfit text-xl font-bold text-white">No Competitors Added Yet</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            You currently analyzed only your own channel. Add competitor URLs or handles to unlock side-by-side velocity benchmarks, outlier detection, and content gap heatmaps.
          </p>
          {onOpenSetup && (
            <button
              onClick={onOpenSetup}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-2.5 text-xs font-bold text-white shadow-lg shadow-violet-600/30 hover:scale-105 active:scale-95 transition-all cursor-pointer"
            >
              <Users className="h-4 w-4" />
              <span>Add Competitors</span>
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-r from-violet-950/40 via-slate-900 to-slate-950 p-6 sm:p-8 border border-violet-500/20 shadow-xl">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600/20 text-violet-400 border border-violet-500/30">
            <Users className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
              Competitor Benchmark Matrix
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              Side-by-side performance analysis across {competitor_channels.length} rival channels
            </p>
          </div>
        </div>
      </div>

      {/* Competitors Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {competitors_stats.map((c) => (
          <div key={c.id} className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
            <div className="flex items-center gap-3">
              <img
                src={c.thumbnail || ''}
                alt={c.channel}
                className="h-12 w-12 rounded-xl object-cover ring-2 ring-slate-700"
              />
              <div className="truncate">
                <h3 className="font-outfit font-bold text-base text-white truncate">{c.channel}</h3>
                <p className="text-xs text-slate-400">
                  {c.subscriber_count ? `${(c.subscriber_count / 1000).toFixed(0)}k subscribers` : 'Competitor'}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/60 text-xs">
              <div className="rounded-xl bg-slate-900/60 p-2.5">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Avg Views/Day</span>
                <p className="text-base font-bold text-emerald-400 font-outfit mt-0.5">
                  +{c.stats.avg_views_per_day.toLocaleString()}
                </p>
              </div>

              <div className="rounded-xl bg-slate-900/60 p-2.5">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Avg Views</span>
                <p className="text-base font-bold text-slate-100 font-outfit mt-0.5">
                  {c.stats.avg_views.toLocaleString()}
                </p>
              </div>

              <div className="rounded-xl bg-slate-900/60 p-2.5">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Format Ratio</span>
                <p className="text-xs font-semibold text-slate-200 mt-0.5">
                  {c.stats.long_count}L / {c.stats.shorts_count}S
                </p>
              </div>

              <div className="rounded-xl bg-slate-900/60 p-2.5">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Avg Title Length</span>
                <p className="text-xs font-semibold text-slate-200 mt-0.5">
                  {c.stats.avg_title_length} chars
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Comparison Chart */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800">
        <h3 className="font-outfit text-base font-bold text-white mb-4">Competitor Volume & Views Comparison</h3>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={comparisonData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '12px' }}
              />
              <Legend />
              <Bar dataKey="avgViews" name="Average Views" fill="#818cf8" radius={[4, 4, 0, 0]} />
              <Bar dataKey="viewsPerDay" name="Views / Day Velocity" fill="#34d399" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Competitor Videos */}
      <div className="space-y-3">
        <h3 className="font-outfit text-base font-bold text-white">Top Competitor Uploads</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {competitor_videos.slice(0, 8).map((video) => (
            <VideoCard key={video.video_id} video={video} />
          ))}
        </div>
      </div>
    </div>
  );
};
