import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { taskApi } from '@/lib/api';
import { Task, TaskCreatePayload, TaskListResponse } from '@/lib/types';

// ==================== Hooks ====================

/**
 * 获取任务列表 Hook
 * 支持分页和状态过滤
 */
export function useTasks(page: number = 1, status?: string) {
  return useQuery({
    queryKey: ['tasks', page, status],
    queryFn: () => taskApi.list(page, 20, status),
    // 保持数据新鲜度，避免频繁刷新（Rule 4.3）
    staleTime: 1000 * 60, // 1分钟
  });
}

/**
 * 获取单个任务详情 Hook
 * 包含所有分段信息
 */
export function useTask(id: string) {
  return useQuery({
    queryKey: ['task', id],
    queryFn: () => taskApi.get(id),
    // 如果任务未完成，缩短轮询间隔
    refetchInterval: (query) => {
      const task = query.state.data;
      if (task && task.status !== 'completed' && task.status !== 'failed') {
        return 2000; // 2秒轮询一次
      }
      return false;
    },
  });
}

/**
 * 创建任务 Mutation
 */
export function useCreateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: TaskCreatePayload) => taskApi.create(payload),
    onSuccess: () => {
      // 创建成功后刷新列表
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

/**
 * 删除任务 Mutation
 */
export function useDeleteTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => taskApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
}

/**
 * 获取结果下载链接 Hook
 */
export function useTaskResult(id: string, isCompleted: boolean) {
  return useQuery({
    queryKey: ['task-result', id],
    queryFn: () => taskApi.getResult(id),
    enabled: isCompleted, // 只有完成时才获取
    staleTime: 1000 * 60 * 60, // 1小时（链接有效期）
  });
}
