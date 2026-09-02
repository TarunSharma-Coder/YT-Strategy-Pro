import React from 'react';
import { Eye, Zap, TrendingUp, Sparkles, Trophy, Users, PlaySquare } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';
import { AnalysisResponse, VideoItem } from '../types';
import { MetricCard } from '../components/MetricCard';
import { VideoCard } from '../components/VideoCard';

interface OverviewProps {
  data: AnalysisResponse;
  filteredVideos: VideoItem[];
  onOpenSetup: () => void;
  onNavigateToOutliers: () => void;
}

export const Overview: React.FC<OverviewProps> = ({
  data,
  filteredVideos,
  onOpenSetup,
  onNavigateToOutliers,
}) => {
  const { own_channel, own_stats, competitors_stats, outliers, top_hooks } = data;
  const topOutliers = outliers.filter((v) => v.is_outlier).slice(0, 4);

  // Velocity comparison chart data
  const velocityData = [
    {
      name: own_channel.title.length > 15 ? own_channel.title.substring(0, 15) + '...' : own_channel.title,
      viewsPerDay: own_stats.avg_views_per_day,
      avgViews: own_stats.avg_views,
      isOwn: true,
    },
    ...competitors_stats.map((c) => ({
      name: c.channel.length > 15 ? c.channel.substring(0, 15) + '...' : c.channel,
      viewsPerDay: c.stats.avg_views_per_day,
      avgViews: c.stats.avg_views,
      isOwn: false,
    })),
  ];

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-indigo-950 via-slate-900 to-slate-950 p-6 sm:p-8 border border-indigo-500/20 shadow-2xl">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-xl">
            <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-400 border border-indigo-500/20 mb-3">
              <Sparkles className="h-3.5 w-3.5 text-amber-300" />
              Intelligence Dashboard Active
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white tracking-tight">
              Benchmarking <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">{own_channel.title}</span>
            </h1>
            <p className="mt-2 text-xs sm:text-sm text-slate-400 leading-relaxed">
              Analyzed {filteredVideos.length} videos across {data.summary.total_channels} channels. Found {data.summary.total_outliers_found} high-velocity outliers you can model for your next upload.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={onNavigateToOutliers}
              className="flex items-center gap-2 rounded-xl bg-amber-500/10 px-4 py-2.5 text-xs font-bold text-amber-300 border border-amber-500/30 hover:bg-amber-500/20 transition-all"
            >
              <Zap className="h-4 w-4 fill-current" />
              View {data.summary.total_outliers_found} Viral Outliers
            </button>
            <button
              onClick={onOpenSetup}
              className="rounded-xl bg-slate-800 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-700 hover:text-white transition-all border border-slate-700"
            >
              Update Scope
            </button>
          </div>
        </div>

        {/* Decorative background glow */}
        <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-indigo-600/15 blur-3xl" />
        <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-violet-600/15 blur-3xl" />
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Views Tracked"
          value={data.all_videos.reduce((acc, v) => acc + (v.views || 0), 0)}
          subtitle={`Across ${data.summary.total_videos_analyzed} uploads`}
          icon={Eye}
          color="indigo"
          trend="+ Live YouTube Data"
        />

        <MetricCard
          title="Avg Views / Day Velocity"
          value={`+${own_stats.avg_views_per_day.toLocaleString()}/d`}
          subtitle={`Channel median: ${own_stats.median_views.toLocaleString()} views`}
          icon={TrendingUp}
          color="emerald"
        />

        <MetricCard
          title="Viral Outliers Found"
          value={data.summary.total_outliers_found}
          subtitle="Beating median velocity by >2x"
          icon={Zap}
          color="amber"
          trend="High Potential Formulas"
        />

        <MetricCard
          title="Top Performing Hook"
          value={top_hooks[0] ? `#${top_hooks[0].hook}` : 'Complete'}
          subtitle={top_hooks[0] ? `Avg +${top_hooks[0].avg_views_per_day.toLocaleString()}/day` : 'Standard'}
          icon={Trophy}
          color="violet"
        />
      </div>

      {/* Chart & Benchmark Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Channel Velocity Benchmark */}
        <div className="glass-panel rounded-2xl p-5 lg:col-span-2 border border-slate-800">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800/60 mb-4">
            <div>
              <h3 className="font-outfit text-base font-bold text-white">Daily Views Velocity Benchmark</h3>
              <p className="text-xs text-slate-400">Average views gained per day per channel</p>
            </div>
            <span className="rounded-lg bg-indigo-500/10 px-2.5 py-1 text-xs font-semibold text-indigo-400">
              Views / Day (VPD)
            </span>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={velocityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '12px' }}
                />
                <Bar dataKey="viewsPerDay" name="Views / Day" fill="#6366f1" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Channels Benchmarking List */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800/60 mb-3">
              <h3 className="font-outfit text-base font-bold text-white">Monitored Channels</h3>
              <Users className="h-4 w-4 text-indigo-400" />
            </div>

            <div className="space-y-3">
              {/* Own Channel */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-indigo-950/40 border border-indigo-500/30">
                <div className="flex items-center gap-3">
                  <img
                    src={own_channel.thumbnail || ''}
                    alt={own_channel.title}
                    className="h-9 w-9 rounded-full object-cover ring-2 ring-indigo-500/50"
                  />
                  <div>
                    <h4 className="text-xs font-bold text-white truncate max-w-[130px]">{own_channel.title}</h4>
                    <span className="text-[10px] text-indigo-300 font-semibold">Your Channel</span>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs font-bold text-indigo-400">+{own_stats.avg_views_per_day.toLocaleString()}/d</p>
                  <p className="text-[10px] text-slate-400">{own_stats.total_videos} videos</p>
                </div>
              </div>

              {/* Competitors */}
              {competitors_stats.map((c) => (
                <div key={c.id} className="flex items-center justify-between p-2.5 rounded-xl bg-slate-900/40 border border-slate-800/60 hover:border-slate-700 transition-colors">
                  <div className="flex items-center gap-2.5">
                    <img
                      src={c.thumbnail || ''}
                      alt={c.channel}
                      className="h-8 w-8 rounded-full object-cover ring-1 ring-slate-700"
                    />
                    <div className="truncate max-w-[130px]">
                      <h4 className="text-xs font-semibold text-slate-200 truncate">{c.channel}</h4>
                      <span className="text-[10px] text-slate-500">{c.subscriber_count ? `${(c.subscriber_count / 1000).toFixed(0)}k subs` : 'Competitor'}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-bold text-slate-200">+{c.stats.avg_views_per_day.toLocaleString()}/d</p>
                    <p className="text-[10px] text-slate-400">{c.stats.total_videos} videos</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Top 4 Outliers Showcase */}
      {topOutliers.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-amber-400 fill-current" />
              <h3 className="font-outfit text-base font-bold text-white">Top Viral Outliers</h3>
              <span className="text-xs text-slate-400">• Videos beating channel median view velocity</span>
            </div>

            <button
              onClick={onNavigateToOutliers}
              className="text-xs font-semibold text-indigo-400 hover:text-indigo-300"
            >
              See all {data.summary.total_outliers_found} outliers →
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {topOutliers.map((video) => (
              <VideoCard key={video.video_id} video={video} />
            ))}
          </div>
        </div>
      )}

      {/* Recent Videos Grid */}
      <div className="space-y-3 pt-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <PlaySquare className="h-4 w-4 text-indigo-400" />
            <h3 className="font-outfit text-base font-bold text-white">Latest Tracked Videos</h3>
            <span className="text-xs text-slate-400">({filteredVideos.length} videos)</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filteredVideos.slice(0, 8).map((video) => (
            <VideoCard key={video.video_id} video={video} />
          ))}
        </div>
      </div>
    </div>
  );
};
