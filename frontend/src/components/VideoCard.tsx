import React from 'react';
import { Play, ExternalLink, Flame, Eye, Clock, Calendar } from 'lucide-react';
import { VideoItem } from '../types';

interface VideoCardProps {
  video: VideoItem;
  onAnalyzeVideo?: (videoId: string) => void;
}

export const VideoCard: React.FC<VideoCardProps> = ({ video, onAnalyzeVideo }) => {
  const isHighOutlier = (video.outlier_multiplier || 0) >= 5;
  const isOutlier = (video.outlier_multiplier || 0) >= 1.8;

  return (
    <div className="glass-card group relative flex flex-col overflow-hidden rounded-2xl bg-slate-900/60 border border-slate-800/80 transition-all hover:border-indigo-500/40 hover:shadow-xl hover:shadow-indigo-500/10">
      {/* Thumbnail Container */}
      <div className="relative aspect-video w-full overflow-hidden bg-slate-950">
        <img
          src={video.thumbnail || 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=60'}
          alt={video.title}
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        />

        {/* Overlay gradient */}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-transparent opacity-60 group-hover:opacity-40 transition-opacity" />

        {/* Duration Badge */}
        <div className="absolute bottom-2 right-2 flex items-center gap-1 rounded-md bg-slate-950/80 px-1.5 py-0.5 text-[10px] font-semibold text-slate-200 backdrop-blur-md">
          <Clock className="h-3 w-3 text-slate-400" />
          <span>{video.duration_minutes ? `${video.duration_minutes}m` : video.video_length_bucket}</span>
        </div>

        {/* Video Type Pill */}
        <div className="absolute top-2 left-2 flex items-center gap-1.5">
          <span
            className={`rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
              video.video_type === 'Shorts'
                ? 'bg-red-500 text-white shadow-lg shadow-red-500/30'
                : 'bg-slate-900/90 text-slate-300 border border-slate-700/50'
            }`}
          >
            {video.video_type}
          </span>

          {video.outlier_tier && video.outlier_tier !== 'Standard' && (
            <span
              className={`flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider ${
                isHighOutlier
                  ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 shadow-lg shadow-amber-500/30 animate-pulse'
                  : 'bg-indigo-500 text-white'
              }`}
            >
              <Flame className="h-3 w-3" />
              {video.outlier_multiplier}x Viral
            </span>
          )}
        </div>

        {/* Action Button */}
        <a
          href={video.url}
          target="_blank"
          rel="noopener noreferrer"
          className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-slate-950/40 backdrop-blur-xs"
        >
          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-indigo-600 text-white shadow-lg shadow-indigo-600/40 transition-transform group-hover:scale-110">
            <Play className="h-5 w-5 fill-current ml-0.5" />
          </div>
        </a>
      </div>

      {/* Content */}
      <div className="flex flex-1 flex-col justify-between p-4">
        <div>
          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <span className="font-semibold text-indigo-400 truncate max-w-[160px]">{video.channel}</span>
            <div className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              <span>{video.upload_date}</span>
            </div>
          </div>

          <h4 className="mt-1.5 line-clamp-2 text-xs font-semibold text-slate-100 leading-snug group-hover:text-indigo-300 transition-colors">
            {video.title}
          </h4>
        </div>

        {/* Metrics Footer */}
        <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs">
          <div className="flex items-center gap-1 font-semibold text-slate-200">
            <Eye className="h-3.5 w-3.5 text-slate-400" />
            <span>{video.views.toLocaleString()}</span>
          </div>

          <div className="flex items-center gap-1 rounded-full bg-slate-800/80 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
            <span>+{video.views_per_day.toLocaleString()}/day</span>
          </div>
        </div>

        {/* Tags / Hook pills */}
        {video.hook_keywords && (
          <div className="mt-2 flex flex-wrap gap-1">
            {video.hook_keywords
              .split(',')
              .slice(0, 2)
              .map((hook, idx) => (
                <span
                  key={idx}
                  className="rounded-md bg-violet-500/10 px-1.5 py-0.5 text-[9px] font-medium text-violet-300 border border-violet-500/20"
                >
                  #{hook.trim()}
                </span>
              ))}
          </div>
        )}
      </div>
    </div>
  );
};
