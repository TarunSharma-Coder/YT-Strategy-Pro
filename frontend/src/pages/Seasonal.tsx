import React from 'react';
import { Calendar, Clock, BarChart2, Flame } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { AnalysisResponse } from '../types';

interface SeasonalProps {
  data: AnalysisResponse;
}

export const Seasonal: React.FC<SeasonalProps> = ({ data }) => {
  const { monthly_trend } = data;

  // Aggregate by month
  const monthMap: Record<string, { month: string; totalViews: number; totalVideos: number }> = {};
  monthly_trend.forEach((m) => {
    if (!monthMap[m.month]) {
      monthMap[m.month] = { month: m.month, totalViews: 0, totalVideos: 0 };
    }
    monthMap[m.month].totalViews += m.total_views;
    monthMap[m.month].totalVideos += m.total_videos;
  });

  const monthChartData = Object.values(monthMap).sort((a, b) => a.month.localeCompare(b.month));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-r from-indigo-950/40 via-slate-900 to-slate-950 p-6 sm:p-8 border border-indigo-500/20 shadow-xl">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <Calendar className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
              Seasonal & Publishing Cadence Intelligence
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              Discover monthly demand surges and competitor upload patterns
            </p>
          </div>
        </div>
      </div>

      {/* Monthly Views Surge Chart */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <h3 className="font-outfit text-base font-bold text-white">Monthly Aggregate Market Views</h3>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={monthChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="month" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '12px' }}
              />
              <Bar dataKey="totalViews" name="Total Views" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Monthly Detail Table */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <h3 className="font-outfit text-base font-bold text-white">Monthly Breakdown by Channel</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="pb-3 font-medium">Month</th>
                <th className="pb-3 font-medium">Channel</th>
                <th className="pb-3 font-medium">Uploads (L / S)</th>
                <th className="pb-3 font-medium text-right">Total Views</th>
                <th className="pb-3 font-medium text-right">Top Performer</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {monthly_trend.map((m, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30">
                  <td className="py-3 font-bold text-indigo-400">{m.month}</td>
                  <td className="py-3 font-semibold text-slate-200">{m.channel}</td>
                  <td className="py-3 text-slate-400">
                    {m.total_videos} ({m.long_videos}L / {m.shorts}S)
                  </td>
                  <td className="py-3 font-bold text-slate-100 text-right">{m.total_views.toLocaleString()}</td>
                  <td className="py-3 text-slate-300 text-right truncate max-w-[200px]">{m.top_video_title || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
