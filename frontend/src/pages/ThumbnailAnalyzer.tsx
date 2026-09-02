import React, { useState } from 'react';
import { Image as ImageIcon, Upload, Sparkles, AlertCircle, CheckCircle2, RefreshCw, Layers, Eye, Gauge } from 'lucide-react';
import { analyzeUploadedThumbnail } from '../services/api';
import { ThumbnailEvaluation } from '../types';

export const ThumbnailAnalyzer: React.FC = () => {
  const [title, setTitle] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [evaluation, setEvaluation] = useState<ThumbnailEvaluation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setError(null);
    }
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !selectedFile) {
      setError('Please provide both video title and upload a thumbnail image.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const result = await analyzeUploadedThumbnail(title, selectedFile);
      setEvaluation(result.analysis);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to analyze thumbnail package.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-r from-violet-950/40 via-slate-900 to-slate-950 p-6 sm:p-8 border border-violet-500/20 shadow-xl">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600/20 text-violet-400 border border-violet-500/30">
            <ImageIcon className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
              Thumbnail & Packaging Vision AI
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              Evaluate title-thumbnail synergy, visual hierarchy, readability, and curiosity gap with AI vision
            </p>
          </div>
        </div>
      </div>

      {/* Upload and Title Form */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-5 glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
          <h3 className="font-outfit text-base font-bold text-white">Upload Packaging For Test</h3>

          {error && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleAnalyze} className="space-y-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-200 mb-1">Video Title</label>
              <input
                type="text"
                id="thumbnail-title-input"
                required
                placeholder="e.g. CAT 2027 Complete Roadmap (Do NOT Make These Mistakes)"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full rounded-xl bg-slate-900 border border-slate-800 px-3.5 py-2.5 text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-200 mb-1">Thumbnail Image (16:9)</label>
              <div className="relative border-2 border-dashed border-slate-700 hover:border-indigo-500/60 rounded-2xl p-4 text-center cursor-pointer transition-colors bg-slate-900/40">
                <input
                  type="file"
                  id="thumbnail-file-upload"
                  accept="image/png, image/jpeg, image/webp"
                  onChange={handleFileChange}
                  className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
                />
                {previewUrl ? (
                  <div className="space-y-2">
                    <img
                      src={previewUrl}
                      alt="Preview"
                      className="mx-auto aspect-video max-h-44 rounded-xl object-cover ring-1 ring-slate-700 shadow-lg"
                    />
                    <p className="text-[11px] text-slate-400">Click or drag to replace image</p>
                  </div>
                ) : (
                  <div className="py-6 space-y-2">
                    <Upload className="h-8 w-8 text-indigo-400 mx-auto" />
                    <p className="font-semibold text-slate-300">Drag & drop thumbnail or browse</p>
                    <p className="text-[10px] text-slate-500">Supports JPG, PNG (Max 10MB)</p>
                  </div>
                )}
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading || !selectedFile}
              id="analyze-thumbnail-btn"
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 py-3 font-bold text-white shadow-lg shadow-indigo-600/30 hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 transition-all"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>Evaluating Packaging Vision...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 text-amber-300" />
                  <span>Run Packaging Intelligence Score</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Evaluation Output */}
        <div className="lg:col-span-7 space-y-4">
          {evaluation ? (
            <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-6">
              {/* Score Header */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-2xl bg-gradient-to-r from-indigo-950/60 to-violet-950/60 border border-indigo-500/30">
                <div className="flex items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600 text-white font-outfit text-2xl font-black shadow-xl shadow-indigo-600/40">
                    {evaluation.packaging_score}
                  </div>
                  <div>
                    <h3 className="font-outfit text-lg font-bold text-white">Overall Packaging Score</h3>
                    <p className="text-xs text-indigo-300">
                      {evaluation.packaging_score >= 80
                        ? '🔥 Elite High CTR Packaging'
                        : evaluation.packaging_score >= 60
                        ? '⚡ Solid Packaging with Optimization Opportunities'
                        : '⚠️ Needs Rework Before Publishing'}
                    </p>
                  </div>
                </div>

                <div className="text-right text-xs text-slate-300">
                  <span className="rounded-full bg-slate-800 px-3 py-1 font-semibold text-slate-200">
                    Style: {evaluation.thumbnail_style || 'Minimal'}
                  </span>
                </div>
              </div>

              {/* Sub-Scores Matrix */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                {[
                  { label: 'Readability', score: evaluation.readability_score },
                  { label: 'Visual Hierarchy', score: evaluation.visual_hierarchy_score },
                  { label: 'Curiosity Gap', score: evaluation.curiosity_gap_score },
                  { label: 'Title Alignment', score: evaluation.title_thumbnail_alignment_score },
                  { label: 'Complementarity', score: evaluation.complementarity_score },
                  { label: 'Mobile Clarity', score: evaluation.mobile_readability_score },
                ].map((item) => (
                  <div key={item.label} className="rounded-xl bg-slate-900/80 p-3 border border-slate-800">
                    <span className="text-[11px] text-slate-400 block">{item.label}</span>
                    <div className="flex items-center justify-between mt-1">
                      <span className="font-outfit text-lg font-bold text-white">{item.score}/10</span>
                      <div className="w-12 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                        <div
                          className="h-full bg-indigo-500 rounded-full"
                          style={{ width: `${item.score * 10}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Strengths and Recommendations */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div className="rounded-xl bg-emerald-950/20 border border-emerald-500/20 p-4 space-y-2">
                  <h4 className="font-bold text-xs text-emerald-400 flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4" /> Packaging Strengths
                  </h4>
                  <ul className="space-y-1 text-[11px] text-slate-300">
                    {evaluation.strengths.map((s, idx) => (
                      <li key={idx} className="flex items-start gap-1.5">
                        <span className="text-emerald-400 font-bold">•</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="rounded-xl bg-indigo-950/20 border border-indigo-500/20 p-4 space-y-2">
                  <h4 className="font-bold text-xs text-indigo-400 flex items-center gap-1.5">
                    <Sparkles className="h-4 w-4 text-amber-300" /> Actionable Recommendations
                  </h4>
                  <ul className="space-y-1 text-[11px] text-slate-300">
                    {evaluation.recommendations.map((r, idx) => (
                      <li key={idx} className="flex items-start gap-1.5">
                        <span className="text-indigo-400 font-bold">•</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <div className="glass-panel rounded-2xl p-12 text-center border border-slate-800 h-full flex flex-col items-center justify-center">
              <Eye className="h-12 w-12 text-slate-700 mb-3" />
              <h3 className="font-outfit text-base font-bold text-slate-300">No Packaging Evaluated Yet</h3>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                Enter your prospective video title and upload your thumbnail to get instant multi-modal CTR intelligence.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
