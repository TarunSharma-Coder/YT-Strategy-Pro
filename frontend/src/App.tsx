import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Sidebar, PageId } from './components/Sidebar';
import { SetupModal } from './components/SetupModal';
import { Overview } from './pages/Overview';
import { YourChannel } from './pages/YourChannel';
import { Competitors } from './pages/Competitors';
import { Outliers } from './pages/Outliers';
import { Trends } from './pages/Trends';
import { Seasonal } from './pages/Seasonal';
import { SearchDemand } from './pages/SearchDemand';
import { AudienceIntelligence } from './pages/AudienceIntelligence';
import { ContentGap } from './pages/ContentGap';
import { ThumbnailAnalyzer } from './pages/ThumbnailAnalyzer';
import { TitleAnalyzer } from './pages/TitleAnalyzer';
import { ContentIdeas } from './pages/ContentIdeas';
import { HistoricalData } from './pages/HistoricalData';
import { Alerts } from './pages/Alerts';
import { VideoAnalyzer } from './pages/VideoAnalyzer';
import { Settings } from './pages/Settings';
import { runAnalysis } from './services/api';
import { AnalysisResponse } from './types';
import { Sparkles, SlidersHorizontal, Layers, PlaySquare } from 'lucide-react';
import { YoutubeIcon } from './components/YoutubeIcon';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageId>('overview');
  const [isSetupOpen, setIsSetupOpen] = useState(false);
  const [analysisData, setAnalysisData] = useState<AnalysisResponse | null>(null);
  const [selectedChannelFilter, setSelectedChannelFilter] = useState('All');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunAnalysis = async (payload: {
    own_channel_url: string;
    competitor_urls: string[];
    start_date?: string;
    end_date?: string;
    max_videos_per_channel: number;
    video_description: string;
    api_key?: string;
  }): Promise<boolean> => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await runAnalysis(payload);
      setAnalysisData(data);
      setSelectedChannelFilter('All');
      setIsSetupOpen(false);
      return true;
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to complete channel analysis.');
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  // Filtered videos based on selected channel filter
  const filteredVideos = analysisData
    ? selectedChannelFilter === 'All'
      ? analysisData.all_videos
      : analysisData.all_videos.filter((v) => v.channel === selectedChannelFilter)
    : [];

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <Navbar
        analysisData={analysisData}
        onOpenSetup={() => setIsSetupOpen(true)}
        selectedChannelFilter={selectedChannelFilter}
        onSelectChannelFilter={setSelectedChannelFilter}
      />

      <div className="flex flex-1">
        {/* Left Sidebar */}
        <Sidebar
          currentPage={currentPage}
          onSelectPage={setCurrentPage}
          outlierCount={analysisData?.summary.total_outliers_found || 0}
        />

        {/* Main Workspace View */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full overflow-y-auto">
          {/* Always Available Standalone Pages */}
          {currentPage === 'settings' && <Settings />}
          {currentPage === 'thumbnail-analyzer' && <ThumbnailAnalyzer />}
          {currentPage === 'title-analyzer' && (
            <TitleAnalyzer suggestions={analysisData?.title_suggestions || []} />
          )}
          {currentPage === 'video-analyzer' && (
            <VideoAnalyzer initialVideos={analysisData?.all_videos || []} />
          )}
          {currentPage === 'audience-intelligence' && (
            <AudienceIntelligence
              videos={filteredVideos}
              ownChannelTitle={analysisData?.own_channel.title || ''}
            />
          )}

          {/* Analysis Data Dependent Pages */}
          {analysisData ? (
            <>
              {currentPage === 'overview' && (
                <Overview
                  data={analysisData}
                  filteredVideos={filteredVideos}
                  onOpenSetup={() => setIsSetupOpen(true)}
                  onNavigateToOutliers={() => setCurrentPage('outliers')}
                />
              )}
              {currentPage === 'your-channel' && <YourChannel data={analysisData} />}
              {currentPage === 'competitors' && <Competitors data={analysisData} onOpenSetup={() => setIsSetupOpen(true)} />}
              {currentPage === 'outliers' && <Outliers outliers={analysisData.outliers} />}
              {currentPage === 'trends' && <Trends data={analysisData} />}
              {currentPage === 'seasonal' && <Seasonal data={analysisData} />}
              {currentPage === 'search-demand' && <SearchDemand data={analysisData} />}
              {currentPage === 'content-gap' && <ContentGap data={analysisData} />}
              {currentPage === 'content-ideas' && <ContentIdeas data={analysisData} />}
              {currentPage === 'historical-data' && <HistoricalData data={analysisData} />}
              {currentPage === 'alerts' && <Alerts data={analysisData} />}
            </>
          ) : (
            /* Empty State / Analysis Required Prompt */
            currentPage === 'overview' ? (
              <div className="my-8 flex flex-col items-center justify-center text-center py-16 px-4">
                <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-violet-600 shadow-2xl shadow-indigo-600/40 mb-6">
                  <YoutubeIcon className="h-10 w-10 text-white" />
                </div>

                <h1 className="text-3xl sm:text-4xl font-extrabold font-outfit text-white tracking-tight">
                  YouTube Strategy & Packaging <span className="bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">Pro</span>
                </h1>
                <p className="mt-3 text-sm text-slate-400 max-w-lg leading-relaxed">
                  Connect your YouTube channel and up to 5 competitors to unlock viral outlier detection, topic gap heatmaps, AI thumbnail packaging intelligence, and audience comment mining.
                </p>

                <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
                  <button
                    id="empty-state-start-btn"
                    onClick={() => setIsSetupOpen(true)}
                    className="flex items-center gap-2.5 rounded-2xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-violet-600 px-6 py-3.5 text-sm font-bold text-white shadow-xl shadow-indigo-600/30 hover:scale-105 active:scale-95 transition-all cursor-pointer"
                  >
                    <SlidersHorizontal className="h-4 w-4" />
                    <span>Start Channel Analysis</span>
                    <Sparkles className="h-4 w-4 text-amber-300" />
                  </button>

                  <button
                    onClick={() => setCurrentPage('thumbnail-analyzer')}
                    className="rounded-2xl bg-slate-900 border border-slate-800 px-6 py-3.5 text-sm font-bold text-slate-300 hover:bg-slate-800 hover:text-white transition-all cursor-pointer"
                  >
                    Test Thumbnail AI
                  </button>
                </div>

                {/* Quick Feature Pills */}
                <div className="mt-12 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl text-left">
                  <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-1.5">
                    <h4 className="text-xs font-bold text-indigo-400 font-outfit">🔥 10x Viral Outlier Radar</h4>
                    <p className="text-[11px] text-slate-400">Identifies breakthrough competitor videos beating average view velocity by 2x to 10x.</p>
                  </div>
                  <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-1.5">
                    <h4 className="text-xs font-bold text-violet-400 font-outfit">⚡ Vision Packaging AI</h4>
                    <p className="text-[11px] text-slate-400">Multi-modal score for curiosity gap, visual hierarchy, and title-thumbnail complementarity.</p>
                  </div>
                  <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-1.5">
                    <h4 className="text-xs font-bold text-emerald-400 font-outfit">💬 Audience Intent Mining</h4>
                    <p className="text-[11px] text-slate-400">Classifies comments into purchase intent, course requests, confusion, and complaint topics.</p>
                  </div>
                </div>
              </div>
            ) : (
              !['settings', 'thumbnail-analyzer', 'title-analyzer', 'video-analyzer', 'audience-intelligence'].includes(currentPage) && (
                <div className="my-12 flex flex-col items-center justify-center text-center py-12 px-4 glass-panel rounded-3xl border border-slate-800 max-w-2xl mx-auto">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 mb-4">
                    <SlidersHorizontal className="h-8 w-8" />
                  </div>
                  <h2 className="text-xl sm:text-2xl font-bold font-outfit text-white">Channel Analysis Required</h2>
                  <p className="mt-2 text-xs sm:text-sm text-slate-400 max-w-md">
                    This section requires data from your channel and competitors. Configure and run a scan to unlock full intelligence.
                  </p>
                  <button
                    onClick={() => setIsSetupOpen(true)}
                    className="mt-6 flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-6 py-3 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 hover:scale-105 active:scale-95 transition-all cursor-pointer"
                  >
                    <Sparkles className="h-4 w-4 text-amber-300" />
                    <span>Configure & Run Analysis</span>
                  </button>
                </div>
              )
            )
          )}
        </main>
      </div>

      {/* Setup & Configuration Modal */}
      <SetupModal
        isOpen={isSetupOpen}
        onClose={() => setIsSetupOpen(false)}
        onRunAnalysis={handleRunAnalysis}
        isLoading={isLoading}
        error={error}
      />
    </div>
  );
};

export default App;
