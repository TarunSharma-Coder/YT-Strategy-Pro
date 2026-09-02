import React from 'react';
import { History, Download, Calendar } from 'lucide-react';
import { AnalysisResponse } from '../types';

interface HistoricalDataProps {
  data: AnalysisResponse;
}

export const HistoricalData: React.FC<HistoricalDataProps> = ({ data }) => {
  const { all_videos, monthly_trend } = data;

  const handleExportCSV = () => {
    const headers = ['Video ID', 'Channel', 'Title', 'Type', 'Upload Date', 'Views', 'Views/Day', 'Likes', 'Comments', 'URL'];
    const rows = all_videos.map((v) => [
      v.video_id,
      `"${v.channel.replace(/"/g, '""')}"`,
      `"${v.title.replace(/"/g, '""')}"`,
      v.video_type,
      v.upload_date,
      v.views,
      v.views_per_day,
      v.likes,
      v.comments,
      v.url,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `youtube_strategy_export_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 p-6 sm:p-8 border border-slate-800 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
              <History className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
                Historical Records & Data Exports
              </h1>
              <p className="text-xs sm:text-sm text-slate-400">
                Complete audit logs of {all_videos.length} videos across all channels
              </p>
            </div>
          </div>

          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 hover:scale-[1.02] active:scale-95 transition-all"
          >
            <Download className="h-4 w-4" />
            <span>Export CSV Dataset</span>
          </button>
        </div>
      </div>

      {/* Full Videos Table */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <h3 className="font-outfit text-base font-bold text-white">Full Video Archive</h3>
        <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-slate-900 border-b border-slate-800 text-slate-400">
              <tr>
                <th className="pb-3 pt-2 font-medium">Channel</th>
                <th className="pb-3 pt-2 font-medium">Title</th>
                <th className="pb-3 pt-2 font-medium">Type</th>
                <th className="pb-3 pt-2 font-medium">Upload Date</th>
                <th className="pb-3 pt-2 font-medium text-right">Views</th>
                <th className="pb-3 pt-2 font-medium text-right">Velocity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {all_videos.map((v) => (
                <tr key={v.video_id} className="hover:bg-slate-800/30">
                  <td className="py-2.5 font-semibold text-indigo-400">{v.channel}</td>
                  <td className="py-2.5 text-slate-200 truncate max-w-sm">
                    <a href={v.url} target="_blank" rel="noopener noreferrer" className="hover:text-indigo-300">
                      {v.title}
                    </a>
                  </td>
                  <td className="py-2.5 text-slate-400">{v.video_type}</td>
                  <td className="py-2.5 text-slate-400">{v.upload_date}</td>
                  <td className="py-2.5 font-bold text-slate-100 text-right">{v.views.toLocaleString()}</td>
                  <td className="py-2.5 font-bold text-emerald-400 text-right">+{v.views_per_day.toLocaleString()}/d</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
