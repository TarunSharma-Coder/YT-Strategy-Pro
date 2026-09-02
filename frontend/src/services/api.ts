import axios from 'axios';
import { AnalysisResponse, ThumbnailEvaluation } from '../types';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const runAnalysis = async (data: {
  own_channel_url: string;
  competitor_urls: string[];
  start_date?: string;
  end_date?: string;
  max_videos_per_channel: number;
  video_description?: string;
  api_key?: string;
}): Promise<AnalysisResponse> => {
  const response = await api.post<AnalysisResponse>('/analysis/run', data);
  return response.data;
};

export const fetchVideoDetails = async (videoId: string, apiKey?: string) => {
  const response = await api.get('/analysis/video-details', {
    params: { video_id: videoId, api_key: apiKey },
  });
  return response.data;
};

export const evaluateTitleOnly = async (title: string) => {
  const response = await api.post('/thumbnail/evaluate-title', { title });
  return response.data;
};

export const analyzeUploadedThumbnail = async (
  title: string,
  file: File,
  openaiKey?: string
): Promise<{ status: string; analysis: ThumbnailEvaluation }> => {
  const formData = new FormData();
  formData.append('title', title);
  formData.append('file', file);
  if (openaiKey) {
    formData.append('openai_key', openaiKey);
  }
  const response = await api.post('/thumbnail/analyze-upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const analyzeComments = async (
  videoIds: string[],
  maxComments = 50,
  apiKey?: string
) => {
  const response = await api.post('/comments/analyze', {
    video_ids: videoIds,
    max_comments_per_video: maxComments,
    api_key: apiKey,
  });
  return response.data;
};

export const generateGlmReport = async (payload: {
  comments_summary: any[];
  sample_comments: any[];
  channel_title: string;
  glm_key?: string;
  glm_model?: string;
}) => {
  const response = await api.post('/comments/glm-report', payload);
  return response.data;
};

export const getSettingsStatus = async () => {
  const response = await api.get('/settings/status');
  return response.data;
};

export const verifyApiKeys = async (keys: {
  youtube_key?: string;
  openai_key?: string;
  glm_key?: string;
}) => {
  const response = await api.post('/settings/verify-keys', keys);
  return response.data;
};

export default api;
