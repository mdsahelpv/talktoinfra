import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '@/api/client';

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApi.getStats,
    refetchInterval: 30000,
  });
}

export function useRecentActivity() {
  return useQuery({
    queryKey: ['recent-activity'],
    queryFn: dashboardApi.getRecentActivity,
    refetchInterval: 10000,
  });
}
