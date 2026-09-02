export interface ChannelInfo {
  id: string;
  title: string;
  description: string;
  published_at?: string;
  thumbnail?: string;
  subscriber_count: number;
  view_count: number;
  video_count: number;
  uploads_playlist?: string;
}

export interface ChannelStats {
  total_videos: number;
  total_views: number;
  avg_views: number;
  median_views: number;
  avg_views_per_day: number;
  shorts_count: number;
  long_count: number;
  avg_title_length: number;
  avg_duration_minutes: number;
}

export interface CompetitorItem {
  channel: string;
  id: string;
  thumbnail?: string;
  subscriber_count: number;
  stats: ChannelStats;
}

export interface VideoItem {
  video_id: string;
  title: string;
  channel: string;
  channel_id?: string;
  source_channel?: string;
  upload_date: string;
  published_at: string;
  views: number;
  likes: number;
  comments: number;
  video_age_days: number;
  duration_seconds: number;
  duration_minutes: number;
  title_length: number;
  word_count: number;
  has_number: string;
  has_question: string;
  has_year: string;
  title_length_bucket: string;
  video_length_bucket: string;
  video_type: string;
  content_category: string;
  views_per_day: number;
  keywords: string;
  hook_keywords: string;
  opening_pattern: string;
  youtube_tags: string;
  url: string;
  thumbnail: string;
  ctr?: number | null;
  outlier_multiplier?: number;
  views_multiplier?: number;
  is_outlier?: boolean;
  outlier_tier?: string;
}

export interface KeywordRecord {
  keyword: string;
  uses: number;
  channels: number;
  avg_views: number;
  avg_views_per_day: number;
  best_title: string;
  best_url: string;
}

export interface HookRecord {
  hook: string;
  uses: number;
  channels: number;
  avg_views: number;
  avg_views_per_day: number;
  best_title: string;
  best_url: string;
}

export interface MonthlyRecord {
  month: string;
  channel: string;
  total_videos: number;
  total_views: number;
  avg_views: number;
  avg_views_per_day: number;
  shorts: number;
  long_videos: number;
  top_video_title: string;
  top_video_views: number;
  top_video_url: string;
}

export interface TitleSuggestion {
  rank: number;
  title: string;
  hook_type: string;
  clarity_score: number;
  curiosity_score: number;
  urgency_score: number;
  specificity_score: number;
  orientation: string;
}

export interface AnalysisResponse {
  status: string;
  own_channel: ChannelInfo;
  own_videos: VideoItem[];
  own_stats: ChannelStats;
  competitor_channels: ChannelInfo[];
  competitor_videos: VideoItem[];
  competitors_stats: CompetitorItem[];
  all_videos: VideoItem[];
  outliers: VideoItem[];
  top_keywords: KeywordRecord[];
  top_hooks: HookRecord[];
  monthly_trend: MonthlyRecord[];
  content_gap: {
    category_pivot: any[];
    opportunities: any[];
    summary: any[];
  };
  title_suggestions: TitleSuggestion[];
  summary: {
    total_channels: number;
    total_videos_analyzed: number;
    total_outliers_found: number;
  };
}

export interface ThumbnailEvaluation {
  thumbnail_text?: string;
  face_present?: string;
  face_count?: number;
  dominant_emotion?: string;
  main_subject?: string;
  thumbnail_style?: string;
  readability_score: number;
  visual_hierarchy_score: number;
  clutter_score?: number;
  curiosity_score: number;
  urgency_score: number;
  mobile_readability_score: number;
  title_thumbnail_alignment_score: number;
  complementarity_score: number;
  redundancy_score: number;
  curiosity_gap_score: number;
  packaging_score: number;
  strengths: string[];
  problems: string[];
  recommendations: string[];
}
