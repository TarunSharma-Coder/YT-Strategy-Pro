import React from 'react';
import {
  LayoutDashboard,
  User,
  Users,
  Film,
  Zap,
  TrendingUp,
  Calendar,
  Search,
  MessageSquare,
  Split,
  Image,
  Type,
  Lightbulb,
  History,
  Bell,
  Settings as SettingsIcon,
} from 'lucide-react';

export type PageId =
  | 'overview'
  | 'your-channel'
  | 'competitors'
  | 'video-analyzer'
  | 'outliers'
  | 'trends'
  | 'seasonal'
  | 'search-demand'
  | 'audience-intelligence'
  | 'content-gap'
  | 'thumbnail-analyzer'
  | 'title-analyzer'
  | 'content-ideas'
  | 'historical-data'
  | 'alerts'
  | 'settings';

interface NavItem {
  id: PageId;
  label: string;
  icon: React.FC<{ className?: string }>;
  badge?: string;
}

interface NavGroup {
  group: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    group: 'Overview',
    items: [
      { id: 'overview', label: 'Overview', icon: LayoutDashboard },
      { id: 'your-channel', label: 'Your Channel', icon: User },
    ],
  },
  {
    group: 'Research',
    items: [
      { id: 'competitors', label: 'Competitors', icon: Users },
      { id: 'video-analyzer', label: 'Video Analyzer', icon: Film },
      { id: 'outliers', label: 'Outliers & Viral', icon: Zap, badge: 'HOT' },
      { id: 'trends', label: 'Trends & Heatmap', icon: TrendingUp },
      { id: 'seasonal', label: 'Seasonal Rhythm', icon: Calendar },
      { id: 'search-demand', label: 'Search Demand', icon: Search },
      { id: 'audience-intelligence', label: 'Audience Comments', icon: MessageSquare, badge: 'AI' },
      { id: 'content-gap', label: 'Content Gap', icon: Split },
    ],
  },
  {
    group: 'Create',
    items: [
      { id: 'thumbnail-analyzer', label: 'Thumbnail Vision', icon: Image, badge: 'Vision' },
      { id: 'title-analyzer', label: 'Title Formulas', icon: Type },
      { id: 'content-ideas', label: 'What To Post Next', icon: Lightbulb },
    ],
  },
  {
    group: 'Track & Configure',
    items: [
      { id: 'historical-data', label: 'Monthly History', icon: History },
      { id: 'alerts', label: 'Viral Alerts', icon: Bell },
      { id: 'settings', label: 'API Settings', icon: SettingsIcon },
    ],
  },
];

interface SidebarProps {
  currentPage: PageId;
  onSelectPage: (page: PageId) => void;
  outlierCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onSelectPage,
  outlierCount = 0,
}) => {
  return (
    <aside className="w-64 flex-shrink-0 border-r border-slate-800/80 bg-[#090d16] flex flex-col h-[calc(100vh-4rem)] sticky top-16 overflow-y-auto">
      <div className="flex-1 py-4 px-3 space-y-6">
        {NAV_GROUPS.map((group) => (
          <div key={group.group}>
            <h3 className="px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 font-outfit">
              {group.group}
            </h3>
            <div className="mt-2 space-y-1">
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = currentPage === item.id;
                return (
                  <button
                    key={item.id}
                    id={`nav-${item.id}`}
                    onClick={() => onSelectPage(item.id)}
                    className={`group flex w-full items-center justify-between rounded-xl px-3 py-2 text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-gradient-to-r from-indigo-600/90 to-violet-600/90 text-white font-semibold shadow-md shadow-indigo-600/20'
                        : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon
                        className={`h-4 w-4 transition-colors ${
                          isActive ? 'text-white' : 'text-slate-400 group-hover:text-indigo-400'
                        }`}
                      />
                      <span>{item.label}</span>
                    </div>

                    {item.id === 'outliers' && outlierCount > 0 ? (
                      <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold text-amber-300 border border-amber-500/30 animate-pulse">
                        {outlierCount}
                      </span>
                    ) : item.badge ? (
                      <span
                        className={`rounded-full px-1.5 py-0.2 text-[9px] font-semibold uppercase tracking-wider ${
                          item.badge === 'HOT'
                            ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                            : item.badge === 'AI' || item.badge === 'Vision'
                            ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {item.badge}
                      </span>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-slate-800/60">
        <div className="rounded-xl bg-slate-900/60 p-3 border border-slate-800/50">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping"></span>
            <span className="text-xs font-medium text-slate-300">FastAPI Online</span>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Port 8000 • Sub-10ms UI sync</p>
        </div>
      </div>
    </aside>
  );
};
