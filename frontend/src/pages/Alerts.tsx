import React from 'react';
import { Bell, Flame, TrendingUp, AlertTriangle, ArrowRight } from 'lucide-react';
import { AnalysisResponse } from '../types';

interface AlertsProps {
  data: AnalysisResponse;
}

export const Alerts: React.FC<AlertsProps> = ({ data }) => {
  const { outliers, competitor_videos, own_channel } = data;

  const viralAlerts = outliers
    .filter((o) => (o.outlier_multiplier || 0) >= 3.0)
    .map((o) => ({
      id: o.video_id,
      type: 'viral_spike',
      title: `Competitor Viral Breakout: "${o.title}"`,
      channel: o.channel,
      multiplier: `${o.outlier_multiplier}x`,
      views: o.views,
      vpd: o.views_per_day,
      url: o.url,
      action: 'Model this topic hook & thumbnail packaging angle',
    }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-r from-red-950/40 via-slate-900 to-slate-950 p-6 sm:p-8 border border-red-500/20 shadow-xl">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-red-600/20 text-red-400 border border-red-500/30">
            <Bell className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
              Viral Surge & Intelligence Alerts
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              Active detection of competitor viral spikes and market surges
            </p>
          </div>
        </div>
      </div>

      {/* Alerts Feed */}
      <div className="space-y-3">
        {viralAlerts.length > 0 ? (
          viralAlerts.map((alert, idx) => (
            <div
              key={idx}
              className="glass-panel rounded-2xl p-5 border border-amber-500/30 bg-amber-950/10 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="flex items-start gap-3.5">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/20 text-amber-300 border border-amber-500/30 flex-shrink-0">
                  <Flame className="h-5 w-5 fill-current" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold text-amber-300 border border-amber-500/30">
                      {alert.multiplier} Velocity Spike
                    </span>
                    <span className="text-xs font-semibold text-indigo-400">{alert.channel}</span>
                  </div>
                  <h3 className="font-outfit text-sm font-bold text-white mt-1">{alert.title}</h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Gaining +{alert.vpd.toLocaleString()} views/day • {alert.action}
                  </p>
                </div>
              </div>

              <a
                href={alert.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 px-4 py-2 text-xs font-bold text-slate-200 transition-all flex-shrink-0"
              >
                <span>Inspect Video</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </a>
            </div>
          ))
        ) : (
          <div className="glass-panel rounded-3xl p-12 text-center border border-slate-800">
            <Bell className="h-10 w-10 text-slate-700 mx-auto mb-3" />
            <h3 className="font-outfit text-base font-bold text-slate-300">No Extreme Spikes Detected</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
              All monitored competitors are currently performing within their standard view distribution ranges.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
