import React, { useState } from 'react';
import { MessageSquare, ThumbsUp, Sparkles, Filter, RefreshCw, Send, AlertCircle, Bot } from 'lucide-react';
import { analyzeComments, generateGlmReport } from '../services/api';
import { VideoItem } from '../types';

interface AudienceIntelligenceProps {
  videos: VideoItem[];
  ownChannelTitle: string;
}

export const AudienceIntelligence: React.FC<AudienceIntelligenceProps> = ({
  videos,
  ownChannelTitle,
}) => {
  const [customVideoInput, setCustomVideoInput] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [isLoading, setIsLoading] = useState(false);
  const [isGlmLoading, setIsGlmLoading] = useState(false);
  const [commentsData, setCommentsData] = useState<any | null>(null);
  const [glmReport, setGlmReport] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFetchComments = async (overrideVideoId?: string) => {
    let videoIds: string[] = [];
    if (overrideVideoId) {
      let vid = overrideVideoId.trim();
      if (vid.includes('v=')) {
        vid = vid.split('v=')[1].split('&')[0];
      } else if (vid.includes('youtu.be/')) {
        vid = vid.split('youtu.be/')[1].split('?')[0];
      }
      videoIds = [vid];
    } else if (videos.length > 0) {
      videoIds = videos.slice(0, 5).map((v) => v.video_id);
    }

    if (!videoIds.length) {
      setError('Please provide a video URL or ID to analyze comments.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const res = await analyzeComments(videoIds, 40);
      setCommentsData(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to analyze audience comments.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customVideoInput.trim()) return;
    handleFetchComments(customVideoInput.trim());
  };

  const handleGenerateGlmReport = async () => {
    if (!commentsData) return;
    setIsGlmLoading(true);
    setError(null);
    try {
      const res = await generateGlmReport({
        comments_summary: commentsData.category_summary,
        sample_comments: commentsData.comments,
        channel_title: ownChannelTitle || 'Analyzed Video',
      });
      setGlmReport(res.report);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to generate GLM AI report.');
    } finally {
      setIsGlmLoading(false);
    }
  };

  const filteredComments = commentsData?.comments
    ? commentsData.comments.filter((c: any) => selectedCategory === 'All' || c.primary_type === selectedCategory)
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-r from-indigo-950/40 via-slate-900 to-slate-950 p-6 sm:p-8 border border-indigo-500/20 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
              <MessageSquare className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
                Audience Intelligence & Comment Mining
              </h1>
              <p className="text-xs sm:text-sm text-slate-400">
                Categorize viewer intents (Content Requests, Purchase Intent, Confusion, Complaints) & AI reports
              </p>
            </div>
          </div>

          {videos.length > 0 && (
            <button
              onClick={() => handleFetchComments()}
              disabled={isLoading}
              id="fetch-comments-btn"
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 hover:scale-[1.02] disabled:opacity-50 transition-all cursor-pointer"
            >
              {isLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4 text-amber-300" />}
              <span>{commentsData ? 'Refresh Channel Comments' : 'Analyze Channel Video Comments'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Standalone Video Comment Search Box */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-3">
        <h3 className="font-outfit text-sm font-bold text-white">Analyze Any Video Comments</h3>
        <form onSubmit={handleCustomSubmit} className="flex gap-2">
          <input
            type="text"
            placeholder="Paste YouTube Video URL or Video ID (e.g. https://www.youtube.com/watch?v=F5_G0AHfYhI)..."
            value={customVideoInput}
            onChange={(e) => setCustomVideoInput(e.target.value)}
            className="flex-1 rounded-xl bg-slate-900 border border-slate-800 px-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={isLoading || !customVideoInput.trim()}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 hover:scale-[1.02] active:scale-98 disabled:opacity-50 transition-all cursor-pointer"
          >
            {isLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            <span>Analyze</span>
          </button>
        </form>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {commentsData ? (
        <div className="space-y-6">
          {/* Summary Pills */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {commentsData.category_summary.map((cat: any) => (
              <div
                key={cat.primary_type}
                onClick={() => setSelectedCategory(cat.primary_type)}
                className={`glass-card cursor-pointer rounded-xl p-3 border transition-all ${
                  selectedCategory === cat.primary_type
                    ? 'border-indigo-500 bg-indigo-950/40 shadow-lg shadow-indigo-500/20'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-200">{cat.primary_type}</span>
                  <span className="rounded-full bg-indigo-500/20 px-2 py-0.5 text-[10px] font-bold text-indigo-400">
                    {cat.total_comments}
                  </span>
                </div>
                <p className="mt-1 text-[10px] text-slate-400">Avg {cat.avg_likes} likes per comment</p>
              </div>
            ))}
          </div>

          {/* GLM Executive Intelligence Action */}
          <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 bg-gradient-to-r from-violet-950/30 to-slate-900">
            <div className="flex items-center gap-3">
              <Bot className="h-6 w-6 text-violet-400" />
              <div>
                <h4 className="text-xs font-bold text-white">Generate Executive Audience Report with GLM / Z.AI</h4>
                <p className="text-[11px] text-slate-400">Synthesizes viewer friction points, questions, and demand signals</p>
              </div>
            </div>
            <button
              onClick={handleGenerateGlmReport}
              disabled={isGlmLoading}
              className="flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-violet-600/30 hover:scale-[1.02] disabled:opacity-50"
            >
              {isGlmLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-3.5 w-3.5 text-amber-300" />}
              <span>Generate GLM Report</span>
            </button>
          </div>

          {/* GLM Report Display */}
          {glmReport && (
            <div className="glass-panel rounded-2xl p-6 border border-violet-500/30 bg-violet-950/20 space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold text-violet-300">
                <Bot className="h-4 w-4" />
                <span>Executive AI Intelligence Report</span>
              </div>
              <div className="prose prose-invert max-w-none text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
                {glmReport}
              </div>
            </div>
          )}

          {/* Comments Feed */}
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="font-outfit text-base font-bold text-white">
                Filtered Comments ({filteredComments.length})
              </h3>
              <button
                onClick={() => setSelectedCategory('All')}
                className={`text-xs font-semibold ${selectedCategory === 'All' ? 'text-indigo-400' : 'text-slate-400 hover:text-slate-200'}`}
              >
                Show All
              </button>
            </div>

            <div className="space-y-3">
              {filteredComments.map((c: any, idx: number) => (
                <div key={idx} className="rounded-xl bg-slate-900/60 p-3.5 border border-slate-800/80 space-y-2">
                  <div className="flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-300">{c.author || 'Viewer'}</span>
                      <span className="rounded-md bg-indigo-500/10 px-1.5 py-0.5 text-[9px] font-semibold text-indigo-400 border border-indigo-500/20">
                        {c.primary_type}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 text-slate-400">
                      <ThumbsUp className="h-3 w-3" />
                      <span>{c.comment_likes}</span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-200 leading-relaxed">{c.comment_text}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="glass-panel rounded-3xl p-12 text-center border border-slate-800">
          <MessageSquare className="h-10 w-10 text-slate-700 mx-auto mb-3" />
          <h3 className="font-outfit text-base font-bold text-slate-300">No Comments Analyzed Yet</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
            Click 'Analyze Top Video Comments' above to scrape, categorize, and extract content opportunities.
          </p>
        </div>
      )}
    </div>
  );
};
