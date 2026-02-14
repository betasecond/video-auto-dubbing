/**
 * API 客户端 - 与后端 FastAPI 交互
 */

import axios, { AxiosError } from 'axios';

// API 基础配置
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

// 创建 axios 实例
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 秒超时
});

// 响应拦截器 - 统一错误处理
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      // 服务器返回错误响应
      const errorData = error.response.data as any;
      const errorMessage = errorData?.detail || errorData?.error || '请求失败';
      console.error('API Error:', errorMessage);
      throw new Error(errorMessage);
    } else if (error.request) {
      // 请求已发送但没有收到响应
      console.error('Network Error:', error.message);
      throw new Error('网络连接失败，请检查后端服务是否运行');
    } else {
      // 其他错误
      console.error('Error:', error.message);
      throw error;
    }
  }
);

// ==================== 类型定义 ====================

export type TaskStatus =
  | 'pending'
  | 'extracting'
  | 'transcribing'
  | 'translating'
  | 'synthesizing'
  | 'muxing'
  | 'completed'
  | 'failed';

// 后端返回大写，前端发送小写（后端会转换）
export type SubtitleMode = 'none' | 'external' | 'burn';
export type SubtitleModeResponse = 'NONE' | 'EXTERNAL' | 'BURN';

export interface Task {
  id: string;
  title: string | null;
  source_language: string;
  target_language: string;
  status: TaskStatus;
  subtitle_mode: SubtitleModeResponse;
  progress: number;
  current_step: string | null;
  error_message: string | null;
  segment_count: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface Segment {
  id: string;
  task_id: string;
  segment_index: number;
  start_time_ms: number;
  end_time_ms: number;
  original_text: string | null;
  translated_text: string | null;
  speaker_id: string | null;
  emotion: string | null;
  confidence: number | null;
  voice_id: string | null;
  audio_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskDetail extends Task {
  video_duration_ms: number | null;
  input_video_path: string | null;
  extracted_audio_path: string | null;
  output_video_path: string | null;
  subtitle_file_path: string | null;
  celery_task_id: string | null;
  segments: Segment[];
}

export interface TaskListResponse {
  items: Task[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DownloadUrlResponse {
  download_url: string;
  subtitle_url?: string;
  expires_in: number;
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy';
  services: {
    database: boolean;
    redis: boolean;
    ffmpeg: boolean;
  };
  version: string;
}

export interface SystemStats {
  tasks: {
    total: number;
    pending?: number;
    extracting?: number;
    transcribing?: number;
    translating?: number;
    synthesizing?: number;
    muxing?: number;
    completed?: number;
    failed?: number;
  };
  workers: {
    active: number;
    registered: string[];
  };
}

// ==================== API 方法 ====================

/**
 * PostObject 签名响应类型
 */
interface PostSignatureResponse {
  host: string;
  key: string;
  policy: string;
  x_oss_signature_version: string;
  x_oss_credential: string;
  x_oss_date: string;
  signature: string;
  video_key: string;
}

/**
 * 获取 PostObject 签名（前端直传 OSS）
 */
export async function getPostSignature(filename: string): Promise<PostSignatureResponse> {
  const response = await apiClient.post('/upload/presign', { filename });
  return response.data;
}

/**
 * 用 PostObject 表单直传文件到 OSS
 */
export async function uploadToOSS(
  signData: PostSignatureResponse,
  file: File,
  onProgress?: (percent: number) => void
): Promise<void> {
  const formData = new FormData();
  formData.append('key', signData.key);
  formData.append('policy', signData.policy);
  formData.append('x-oss-signature-version', signData.x_oss_signature_version);
  formData.append('x-oss-credential', signData.x_oss_credential);
  formData.append('x-oss-date', signData.x_oss_date);
  formData.append('x-oss-signature', signData.signature);
  formData.append('success_action_status', '200');
  // file 必须是最后一个表单域
  formData.append('file', file);

  await axios.post(signData.host, formData, {
    timeout: 600000,
    onUploadProgress: (event) => {
      if (event.total && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    },
  });
}

/**
 * 创建配音任务（前端直传模式）
 */
export async function createTask(
  video: File,
  sourceLanguage: string,
  targetLanguage: string,
  title?: string,
  subtitleMode: SubtitleMode = 'external',
  onUploadProgress?: (percent: number) => void
): Promise<Task> {
  // 1. 获取 PostObject 签名
  const signData = await getPostSignature(video.name);

  // 2. FormData POST 直传到 OSS
  await uploadToOSS(signData, video, onUploadProgress);

  // 3. 用 video_key 创建任务
  const formData = new FormData();
  formData.append('video_key', signData.video_key);
  formData.append('source_language', sourceLanguage);
  formData.append('target_language', targetLanguage);
  formData.append('subtitle_mode', subtitleMode);
  if (title) {
    formData.append('title', title);
  }

  const response = await apiClient.post<Task>('/tasks', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

/**
 * 获取任务列表
 */
export async function getTasks(
  page: number = 1,
  pageSize: number = 20,
  status?: TaskStatus
): Promise<TaskListResponse> {
  const params: any = { page, page_size: pageSize };
  if (status) {
    params.status = status;
  }

  const response = await apiClient.get<TaskListResponse>('/tasks', { params });
  return response.data;
}

/**
 * 获取任务详情
 */
export async function getTask(taskId: string): Promise<TaskDetail> {
  const response = await apiClient.get<TaskDetail>(`/tasks/${taskId}`);
  return response.data;
}

/**
 * 删除任务
 */
export async function deleteTask(taskId: string): Promise<void> {
  await apiClient.delete(`/tasks/${taskId}`);
}

/**
 * 获取任务结果下载链接
 */
export async function getDownloadUrl(taskId: string): Promise<DownloadUrlResponse> {
  const response = await apiClient.get<DownloadUrlResponse>(`/tasks/${taskId}/result`);
  return response.data;
}

/**
 * 健康检查
 */
export async function checkHealth(): Promise<HealthStatus> {
  const response = await apiClient.get<HealthStatus>('/monitoring/health');
  return response.data;
}

/**
 * 获取系统统计信息
 */
export async function getStats(): Promise<SystemStats> {
  const response = await apiClient.get<SystemStats>('/monitoring/stats');
  return response.data;
}

// ==================== 辅助函数 ====================

/**
 * 格式化任务状态显示
 */
export function getStatusLabel(status: TaskStatus): string {
  const labels: Record<TaskStatus, string> = {
    pending: '等待中',
    extracting: '提取音频',
    transcribing: '语音识别',
    translating: '翻译中',
    synthesizing: '语音合成',
    muxing: '视频合成',
    completed: '已完成',
    failed: '失败',
  };
  return labels[status] || status;
}

/**
 * 获取状态颜色
 */
export function getStatusColor(status: TaskStatus): string {
  const colors: Record<TaskStatus, string> = {
    pending: 'bg-gray-100 text-gray-800',
    extracting: 'bg-blue-100 text-blue-800',
    transcribing: 'bg-purple-100 text-purple-800',
    translating: 'bg-yellow-100 text-yellow-800',
    synthesizing: 'bg-pink-100 text-pink-800',
    muxing: 'bg-indigo-100 text-indigo-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
}

/**
 * 格式化时长（毫秒 -> 可读格式）
 */
export function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}:${String(minutes % 60).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
  }
  return `${minutes}:${String(seconds % 60).padStart(2, '0')}`;
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

/**
 * 格式化时间
 */
export function formatDateTime(dateString: string): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date);
}

/**
 * 支持的语言列表
 */
export const SUPPORTED_LANGUAGES = [
  { code: 'zh', name: '中文' },
  { code: 'en', name: '英语' },
  { code: 'ja', name: '日语' },
  { code: 'ko', name: '韩语' },
  { code: 'es', name: '西班牙语' },
  { code: 'fr', name: '法语' },
  { code: 'de', name: '德语' },
  { code: 'ru', name: '俄语' },
];

/**
 * 获取语言名称
 */
export function getLanguageName(code: string): string {
  const lang = SUPPORTED_LANGUAGES.find((l) => l.code === code);
  return lang?.name || code;
}

// ==================== Task API 对象 ====================

export const taskApi = {
  create: async (payload: { video: File; source_language: string; target_language: string; title?: string; subtitle_mode?: SubtitleMode; onUploadProgress?: (percent: number) => void }): Promise<Task> => {
    return createTask(
      payload.video,
      payload.source_language,
      payload.target_language,
      payload.title,
      payload.subtitle_mode,
      payload.onUploadProgress
    );
  },

  list: async (page: number = 1, pageSize: number = 20, status?: TaskStatus): Promise<TaskListResponse> => {
    return getTasks(page, pageSize, status);
  },

  get: async (taskId: string): Promise<TaskDetail> => {
    return getTask(taskId);
  },

  delete: async (taskId: string): Promise<void> => {
    return deleteTask(taskId);
  },

  getResult: async (taskId: string): Promise<DownloadUrlResponse> => {
    return getDownloadUrl(taskId);
  },
};
