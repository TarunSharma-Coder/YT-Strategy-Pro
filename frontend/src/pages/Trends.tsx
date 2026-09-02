import React from 'react';
import { TrendingUp, Flame, Activity, Sparkles, Hash } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { AnalysisResponse } from '../types';

interface TrendsProps {
  data: AnalysisResponse;
}

export const Trends: React.FC<TrendsProps> = ({ data }) => {
  const { top_keywords, monthly_trend } = data;

  const keywordChartData = top_keywords.slice(0, 10).map((k) => ({
    name: k.keyword,
    viewsPerDay: k.avg_views_per_day,
    uses: k.uses,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-r from-emerald-950/40 via-slate-900 to-slate-950 p-6 sm:p-8 border border-emerald-500/20 shadow-xl">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-600/20 text-emerald-400 border border-emerald-500/30">
            <TrendingUp className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
              Topic Trends & Growth Heatmap
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              Identify rising search keywords, growing topics, and market velocity shifts
            </p>
          </div>
        </div>
      </div>

      {/* Top Rising Keywords Chart */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <h3 className="font-outfit text-base font-bold text-white">Top 10 High-Velocity Keywords</h3>
          <span className="text-xs text-emerald-400 font-semibold">Ranked by Views/Day</span>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={keywordChartData} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis type="number" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis dataKey="name" type="category" stroke="#64748b" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '12px' }}
              />
              <Bar dataKey="viewsPerDay" name="Avg Views / Day" fill="#10b981" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Keywords Table */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <h3 className="font-outfit text-base font-bold text-white">Comprehensive Keyword Performance</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="pb-3 font-medium">Keyword</th>
                <th className="pb-3 font-medium">Uses</th>
                <th className="pb-3 font-medium">Channels Using</th>
                <th className="pb-3 font-medium text-right">Avg Views</th>
                <th className="pb-3 font-medium text-right">Daily Velocity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {top_keywords.map((k) => (
                <tr key={k.keyword} className="hover:bg-slate-800/30">
                  <td className="py-3 font-bold text-slate-200">{k.keyword}</td>
                  <td className="py-3 text-slate-400">{k.uses} videos</td>
                  <td className="py-3 text-slate-400">{k.channels} channels</td>
                  <td className="py-3 text-slate-300 text-right">{k.avg_views.toLocaleString()}</td>
                  <td className="py-3 font-bold text-emerald-400 text-right">+{k.avg_views_per_day.toLocaleString()}/d</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
