import React, { useState } from 'react';
import { X, Plus, Trash2, Calendar, FileText, Sparkles, AlertCircle, Loader2 } from 'lucide-react';
import { YoutubeIcon } from './YoutubeIcon';
import confetti from 'canvas-confetti';

interface SetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRunAnalysis: (payload: {
    own_channel_url: string;
    competitor_urls: string[];
    start_date?: string;
    end_date?: string;
    max_videos_per_channel: number;
    video_description: string;
    api_key?: string;
  }) => Promise<boolean>;
  isLoading: boolean;
  error?: string | null;
}

export const SetupModal: React.FC<SetupModalProps> = ({
  isOpen,
  onClose,
  onRunAnalysis,
  isLoading,
  error,
}) => {
  const [ownChannel, setOwnChannel] = useState('');
  const [competitors, setCompetitors] = useState<string[]>(['']);
  const [datePreset, setDatePreset] = useState('All latest 100');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [maxVideos, setMaxVideos] = useState(50);
  const [description, setDescription] = useState('');
  const [apiKey, setApiKey] = useState('');

  if (!isOpen) return null;

  const handleAddCompetitor = () => {
    if (competitors.length < 5) {
      setCompetitors([...competitors, '']);
    }
  };

  const handleRemoveCompetitor = (index: number) => {
    setCompetitors(competitors.filter((_, i) => i !== index));
  };

  const handleCompetitorChange = (index: number, value: string) => {
    const updated = [...competitors];
    updated[index] = value;
    setCompetitors(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ownChannel.trim()) return;

    let sDate = startDate;
    let eDate = endDate;

    if (datePreset === 'Last month') {
      const now = new Date();
      const past = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      sDate = past.toISOString().split('T')[0];
      eDate = now.toISOString().split('T')[0];
    } else if (datePreset === 'Last 3 months') {
      const now = new Date();
      const past = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
      sDate = past.toISOString().split('T')[0];
      eDate = now.toISOString().split('T')[0];
    } else if (datePreset === 'Last week') {
      const now = new Date();
      const past = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      sDate = past.toISOString().split('T')[0];
      eDate = now.toISOString().split('T')[0];
    }

    const success = await onRunAnalysis({
      own_channel_url: ownChannel.trim(),
      competitor_urls: competitors.filter((c) => c.trim().length > 0),
      start_date: sDate || undefined,
      end_date: eDate || undefined,
      max_videos_per_channel: maxVideos,
      video_description: description.trim(),
      api_key: apiKey.trim() || undefined,
    });

    if (success) {
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 },
      });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md overflow-y-auto">
      <div className="relative w-full max-w-2xl rounded-2xl border border-slate-800 bg-[#0c1220] p-6 shadow-2xl shadow-indigo-950/50 my-8">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
              <YoutubeIcon className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold font-outfit text-white">Channel Setup & Intelligence Engine</h2>
              <p className="text-xs text-slate-400">Configure your target channels and date scope</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Error alert */}
        {error && (
          <div className="mt-4 flex items-center gap-3 rounded-xl bg-rose-500/10 border border-rose-500/20 p-3 text-xs text-rose-400">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4 text-xs">
          {/* Own Channel URL */}
          <div>
            <label className="block font-semibold text-slate-200 mb-1">
              Your Channel Link or Handle <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              id="own-channel-input"
              required
              placeholder="e.g. @MrBeast or https://www.youtube.com/@iQuanta"
              value={ownChannel}
              onChange={(e) => setOwnChannel(e.target.value)}
              className="w-full rounded-xl bg-slate-900 border border-slate-800 px-3.5 py-2.5 text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
            />
          </div>

          {/* Competitor URLs */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="font-semibold text-slate-200">
                Competitor Channels (Up to 5)
              </label>
              {competitors.length < 5 && (
                <button
                  type="button"
                  onClick={handleAddCompetitor}
                  className="flex items-center gap-1 text-[11px] font-semibold text-indigo-400 hover:text-indigo-300"
                >
                  <Plus className="h-3 w-3" /> Add Competitor
                </button>
              )}
            </div>

            <div className="space-y-2">
              {competitors.map((comp, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <input
                    type="text"
                    id={`competitor-input-${idx}`}
                    placeholder={`Competitor #${idx + 1} (e.g. @UnacademyCAT)`}
                    value={comp}
                    onChange={(e) => handleCompetitorChange(idx, e.target.value)}
                    className="flex-1 rounded-xl bg-slate-900 border border-slate-800 px-3.5 py-2 text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500"
                  />
                  {competitors.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveCompetitor(idx)}
                      className="rounded-lg p-2 text-slate-500 hover:bg-rose-500/10 hover:text-rose-400 transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Date Scope & Fetch Limit */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
            <div>
              <label className="block font-semibold text-slate-200 mb-1">Date Scope</label>
              <select
                value={datePreset}
                onChange={(e) => setDatePreset(e.target.value)}
                className="w-full rounded-xl bg-slate-900 border border-slate-800 px-3 py-2 text-slate-100 outline-none focus:border-indigo-500"
              >
                <option value="All latest 100">All latest videos</option>
                <option value="Last week">Last 7 days</option>
                <option value="Last month">Last 30 days</option>
                <option value="Last 3 months">Last 90 days</option>
                <option value="Custom">Custom Date Range</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-200 mb-1">Max Videos Per Channel</label>
              <select
                value={maxVideos}
                onChange={(e) => setMaxVideos(Number(e.target.value))}
                className="w-full rounded-xl bg-slate-900 border border-slate-800 px-3 py-2 text-slate-100 outline-none focus:border-indigo-500"
              >
                <option value={20}>20 videos (Fastest)</option>
                <option value={50}>50 videos (Recommended)</option>
                <option value={100}>100 videos (Deep historical)</option>
              </select>
            </div>
          </div>

          {datePreset === 'Custom' && (
            <div className="grid grid-cols-2 gap-3 p-3 rounded-xl bg-slate-900/50 border border-slate-800">
              <div>
                <label className="block text-slate-400 mb-1">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full rounded-lg bg-slate-800 border border-slate-700 px-2.5 py-1.5 text-slate-200"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full rounded-lg bg-slate-800 border border-slate-700 px-2.5 py-1.5 text-slate-200"
                />
              </div>
            </div>
          )}

          {/* Next Video Description */}
          <div>
            <label className="block font-semibold text-slate-200 mb-1">
              Your Next Video Idea / Description (Optional)
            </label>
            <textarea
              rows={2}
              placeholder="e.g. CAT 2027 complete roadmap for working professionals, syllabus, mock timetable..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded-xl bg-slate-900 border border-slate-800 px-3.5 py-2 text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500 resize-none"
            />
            <p className="text-[10px] text-slate-500 mt-0.5">Used to generate AI title options and market fit score</p>
          </div>

          {/* Optional Custom API Key */}
          <div>
            <label className="block font-semibold text-slate-200 mb-1">
              YouTube Data API Key (Optional override)
            </label>
            <input
              type="password"
              placeholder="Defaults to backend .env key if empty"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full rounded-xl bg-slate-900 border border-slate-800 px-3.5 py-2 text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500 font-mono text-xs"
            />
          </div>

          {/* Submit */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl px-4 py-2.5 text-xs font-semibold text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={isLoading}
              id="start-analysis-submit-btn"
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-violet-600 px-6 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 transition-all hover:scale-[1.02] disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Analyzing Channels...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 text-amber-300" />
                  <span>Run Analysis Engine</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
