'use client';

import { useState } from 'react';
import Link from 'next/link';
import useSWR from 'swr';
import { Plus, RefreshCw, Filter, ChevronLeft, ChevronRight } from 'lucide-react';
import {
  getTasks,
  getStatusLabel,
  getStatusColor,
  formatDateTime,
  getLanguageName,
  type TaskStatus,
  type Task,
} from '@/lib/api';

export default function TasksPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all');
  const pageSize = 10;

  // 使用 SWR 自动刷新任务列表
  const { data, error, isLoading, mutate } = useSWR(
    ['tasks', page, statusFilter],
    () => getTasks(page, pageSize, statusFilter === 'all' ? undefined : statusFilter),
    {
      refreshInterval: 3000, // 每 3 秒自动刷新
      revalidateOnFocus: true,
    }
  );

  const handleRefresh = () => {
    mutate();
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= (data?.total_pages || 1)) {
      setPage(newPage);
    }
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">我的任务</h1>
          <p className="text-slate-600 mt-2">
            {data ? `共 ${data.total} 个任务` : '加载中...'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            刷新
          </button>

          <Link
            href="/tasks/new"
            className="flex items-center gap-2 bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            新建任务
          </Link>
        </div>
      </div>

      {/* 过滤器 */}
      <div className="mb-6 flex items-center gap-3">
        <Filter className="w-4 h-4 text-slate-500" />
        <div className="flex flex-wrap gap-2">
          {[
            { value: 'all', label: '全部' },
            { value: 'pending', label: '等待中' },
            { value: 'extracting', label: '提取音频' },
            { value: 'transcribing', label: '语音识别' },
            { value: 'translating', label: '翻译中' },
            { value: 'synthesizing', label: '语音合成' },
            { value: 'muxing', label: '视频合成' },
            { value: 'completed', label: '已完成' },
            { value: 'failed', label: '失败' },
          ].map((status) => (
            <button
              key={status.value}
              onClick={() => {
                setStatusFilter(status.value as TaskStatus | 'all');
                setPage(1);
              }}
              className={`
                px-3 py-1.5 text-sm font-medium rounded-lg transition-colors
                ${
                  statusFilter === status.value
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }
              `}
            >
              {status.label}
            </button>
          ))}
        </div>
      </div>

      {/* 任务列表 */}
      {error ? (
        <div className="text-center py-12">
          <p className="text-red-600 mb-4">加载失败：{error.message}</p>
          <button
            onClick={handleRefresh}
            className="text-blue-600 hover:text-blue-700 underline"
          >
            重试
          </button>
        </div>
      ) : isLoading && !data ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent" />
          <p className="text-slate-600 mt-4">加载中...</p>
        </div>
      ) : !data?.items.length ? (
        <div className="text-center py-12 bg-slate-50 rounded-lg border-2 border-dashed border-slate-300">
          <p className="text-slate-600 mb-4">
            {statusFilter === 'all' ? '还没有任务' : '没有符合条件的任务'}
          </p>
          <Link
            href="/tasks/new"
            className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium"
          >
            <Plus className="w-4 h-4" />
            创建第一个任务
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {data.items.map((task) => (
            <TaskCard key={task.id} task={task} />
          ))}
        </div>
      )}

      {/* 分页 */}
      {data && data.total_pages > 1 && (
        <div className="mt-8 flex items-center justify-between">
          <p className="text-sm text-slate-600">
            第 {page} 页，共 {data.total_pages} 页
          </p>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePageChange(page - 1)}
              disabled={page === 1}
              className="flex items-center gap-1 px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              上一页
            </button>

            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(5, data.total_pages) }, (_, i) => {
                let pageNum: number;
                if (data.total_pages <= 5) {
                  pageNum = i + 1;
                } else if (page <= 3) {
                  pageNum = i + 1;
                } else if (page >= data.total_pages - 2) {
                  pageNum = data.total_pages - 4 + i;
                } else {
                  pageNum = page - 2 + i;
                }

                return (
                  <button
                    key={pageNum}
                    onClick={() => handlePageChange(pageNum)}
                    className={`
                      w-10 h-10 rounded-lg font-medium transition-colors
                      ${
                        page === pageNum
                          ? 'bg-blue-600 text-white'
                          : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
                      }
                    `}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>

            <button
              onClick={() => handlePageChange(page + 1)}
              disabled={page === data.total_pages}
              className="flex items-center gap-1 px-4 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              下一页
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// 任务卡片组件
function TaskCard({ task }: { task: Task }) {
  return (
    <Link href={`/tasks/${task.id}`}>
      <div className="p-6 bg-white border border-slate-200 rounded-lg hover:shadow-lg hover:border-blue-300 transition-all cursor-pointer">
        <div className="flex items-start justify-between gap-4">
          {/* 左侧信息 */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-lg font-semibold text-slate-900 truncate">
                {task.title || '未命名任务'}
              </h3>
              <span
                className={`px-2.5 py-0.5 text-xs font-medium rounded-full whitespace-nowrap ${getStatusColor(
                  task.status
                )}`}
              >
                {getStatusLabel(task.status)}
              </span>
            </div>

            <div className="flex items-center gap-4 text-sm text-slate-600">
              <span>
                {getLanguageName(task.source_language)} → {getLanguageName(task.target_language)}
              </span>
              <span>•</span>
              <span>{task.segment_count} 个分段</span>
              {task.current_step && (
                <>
                  <span>•</span>
                  <span>{task.current_step}</span>
                </>
              )}
            </div>

            {task.error_message && (
              <p className="mt-2 text-sm text-red-600">{task.error_message}</p>
            )}

            <p className="mt-2 text-xs text-slate-500">
              创建于 {formatDateTime(task.created_at)}
              {task.completed_at && ` • 完成于 ${formatDateTime(task.completed_at)}`}
            </p>
          </div>

          {/* 右侧进度 */}
          <div className="flex flex-col items-end gap-2">
            <div className="text-right">
              <p className="text-2xl font-bold text-slate-900">{task.progress}%</p>
            </div>

            <div className="w-32 h-2 bg-slate-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  task.status === 'completed'
                    ? 'bg-green-500'
                    : task.status === 'failed'
                    ? 'bg-red-500'
                    : 'bg-blue-500'
                }`}
                style={{ width: `${task.progress}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
