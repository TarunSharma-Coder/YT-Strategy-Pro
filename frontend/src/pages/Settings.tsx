import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Key, CheckCircle2, XCircle, RefreshCw, Sparkles, ShieldCheck } from 'lucide-react';
import { getSettingsStatus, verifyApiKeys } from '../services/api';

export const Settings: React.FC = () => {
  const [status, setStatus] = useState<any | null>(null);
  const [youtubeKey, setYoutubeKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [glmKey, setGlmKey] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyResults, setVerifyResults] = useState<any | null>(null);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const data = await getSettingsStatus();
      setStatus(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsVerifying(true);
    try {
      const results = await verifyApiKeys({
        youtube_key: youtubeKey.trim() || undefined,
        openai_key: openaiKey.trim() || undefined,
        glm_key: glmKey.trim() || undefined,
      });
      setVerifyResults(results);
    } catch (e) {
      console.error(e);
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 p-6 sm:p-8 border border-slate-800 shadow-xl">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <SettingsIcon className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold font-outfit text-white">
              API Keys & Engine Configuration
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              Manage connection credentials for YouTube Data API v3, OpenAI Vision, and GLM AI
            </p>
          </div>
        </div>
      </div>

      {/* Status Overview */}
      {status && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300">YouTube Data API</span>
              {status.youtube_configured ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : (
                <XCircle className="h-4 w-4 text-rose-400" />
              )}
            </div>
            <p className="text-xs font-mono text-slate-400">{status.youtube_key_preview}</p>
          </div>

          <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300">OpenAI Vision AI</span>
              {status.openai_configured ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : (
                <XCircle className="h-4 w-4 text-amber-400" />
              )}
            </div>
            <p className="text-xs font-mono text-slate-400">{status.openai_key_preview}</p>
          </div>

          <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300">GLM / Z.AI AI</span>
              {status.glm_configured ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : (
                <XCircle className="h-4 w-4 text-amber-400" />
              )}
            </div>
            <p className="text-xs font-mono text-slate-400">{status.glm_key_preview}</p>
          </div>
        </div>
      )}

      {/* Key Input & Test Form */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <h3 className="font-outfit text-base font-bold text-white">Override & Test API Keys</h3>

        <form onSubmit={handleVerify} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-200 mb-1">YouTube Data API Key</label>
            <input
              type="password"
              placeholder="Paste custom YouTube Data API v3 key..."
              value={youtubeKey}
              onChange={(e) => setYoutubeKey(e.target.value)}
              className="w-full rounded-xl bg-slate-900 border border-slate-800 px-3.5 py-2.5 text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500 font-mono"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-200 mb-1">OpenAI API Key (Vision Packaging)</label>
            <input
              type="password"
              placeholder="Paste OpenAI key (sk-...)..."
              value={openaiKey}
              onChange={(e) => setOpenaiKey(e.target.value)}
              className="w-full rounded-xl bg-slate-900 border border-slate-800 px-3.5 py-2.5 text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500 font-mono"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-200 mb-1">GLM / Z.AI API Key (Comment Intelligence)</label>
            <input
              type="password"
              placeholder="Paste GLM key..."
              value={glmKey}
              onChange={(e) => setGlmKey(e.target.value)}
              className="w-full rounded-xl bg-slate-900 border border-slate-800 px-3.5 py-2.5 text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500 font-mono"
            />
          </div>

          <button
            type="submit"
            disabled={isVerifying}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 hover:scale-[1.02] active:scale-95 disabled:opacity-50 transition-all"
          >
            {isVerifying ? <RefreshCw className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
            <span>Test API Keys Connection</span>
          </button>
        </form>

        {verifyResults && (
          <div className="mt-4 space-y-2 pt-4 border-t border-slate-800 text-xs">
            {Object.entries(verifyResults).map(([key, val]: [string, any]) => (
              <div
                key={key}
                className={`p-3 rounded-xl border flex items-center justify-between ${
                  val.valid ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-300' : 'bg-rose-950/20 border-rose-500/30 text-rose-300'
                }`}
              >
                <span className="font-bold capitalize">{key}</span>
                <span>{val.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
