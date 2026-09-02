import React, { useState } from 'react';
import { Film, Search, Play, Eye, ThumbsUp, MessageSquare, Clock, Calendar, RefreshCw, AlertCircle } from 'lucide-react';
import { fetchVideoDetails } from '../services/api';
import { VideoItem } from '../types';

interface VideoAnalyzerProps {
  initialVideos: VideoItem[];
}

export const VideoAnalyzer: React.FC<VideoAnalyzerProps> = ({ initialVideos }) => {
  const [videoIdInput, setVideoIdInput] = useState('');
  const [selectedVideo, setSelectedVideo] = useState<any | null>(initialVideos[0] || null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleInspect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!videoIdInput.trim()) return;

    let vid = videoIdInput.trim();
    if (vid.includes('v=')) {
      vid = vid.split('v=')[1].split('&')[0];
    } else if (vid.includes('youtu.be/')) {
      vid = vid.split('youtu.be/')[1].split('?')[0];
    }

    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchVideoDetails(vid);
      setSelectedVideo(res.video);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to fetch video details.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-r from-indigo-950/40 via-slate-900 to-slate-950 p-6 sm:p-8 border border-indigo-500/20 shadow-xl">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <Film className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
              Single Video Deep-Dive Analyzer
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              Inspect any video URL or ID to analyze view velocity, tag structure, title clarity, and engagement
            </p>
          </div>
        </div>
      </div>

      {/* URL Input Form */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <h3 className="font-outfit text-base font-bold text-white">Enter Video URL or Video ID</h3>
        <form onSubmit={handleInspect} className="flex gap-2">
          <input
            type="text"
            placeholder="e.g. https://www.youtube.com/watch?v=dQw4w9WgXcQ or dQw4w9WgXcQ"
            value={videoIdInput}
            onChange={(e) => setVideoIdInput(e.target.value)}
            className="flex-1 rounded-xl bg-slate-900 border border-slate-800 px-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={isLoading || !videoIdInput.trim()}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 hover:scale-[1.02] disabled:opacity-50"
          >
            {isLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            <span>Analyze Video</span>
          </button>
        </form>

        {error && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400 flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Selected Video Display */}
      {selectedVideo && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-6 glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
            <div className="aspect-video w-full rounded-xl overflow-hidden bg-slate-950">
              <img
                src={selectedVideo.thumbnail || ''}
                alt={selectedVideo.title}
                className="w-full h-full object-cover"
              />
            </div>
            <div>
              <span className="text-xs font-semibold text-indigo-400">{selectedVideo.channel || selectedVideo.source_channel}</span>
              <h2 className="text-base font-bold text-white mt-1">{selectedVideo.title}</h2>
            </div>
            <a
              href={selectedVideo.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-xs font-semibold text-indigo-400 hover:text-indigo-300"
            >
              <Play className="h-4 w-4 fill-current" /> Open in YouTube
            </a>
          </div>

          <div className="lg:col-span-6 space-y-4">
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400 block mb-1">Total Views</span>
                <p className="text-xl font-bold font-outfit text-white">{(selectedVideo.views || 0).toLocaleString()}</p>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400 block mb-1">Daily Velocity</span>
                <p className="text-xl font-bold font-outfit text-emerald-400">+{selectedVideo.views_per_day || 0}/day</p>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400 block mb-1">Likes</span>
                <p className="text-xl font-bold font-outfit text-slate-200">{(selectedVideo.likes || 0).toLocaleString()}</p>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400 block mb-1">Comments</span>
                <p className="text-xl font-bold font-outfit text-slate-200">{(selectedVideo.comments || 0).toLocaleString()}</p>
              </div>
            </div>

            {selectedVideo.youtube_tags && (
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                <span className="text-xs font-bold text-slate-300">YouTube Search Tags</span>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {selectedVideo.youtube_tags.split(',').map((t: string, i: number) => (
                    <span key={i} className="rounded-lg bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300">
                      {t.trim()}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
