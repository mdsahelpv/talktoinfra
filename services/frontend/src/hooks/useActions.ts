import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { actionsApi } from '@/api/client';

export function useActions(status?: string) {
  return useQuery({
    queryKey: ['actions', status],
    queryFn: () => actionsApi.getActions(status),
    refetchInterval: status === 'pending' ? 5000 : 30000,
  });
}

export function useAction(id: string) {
  return useQuery({
    queryKey: ['action', id],
    queryFn: () => actionsApi.getAction(id),
    enabled: !!id,
  });
}

export function useApproveAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: actionsApi.approveAction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] });
    },
  });
}

export function useRejectAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: actionsApi.rejectAction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] });
    },
  });
}

export function useExecuteAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, dryRun }: { id: string; dryRun?: boolean }) =>
      actionsApi.executeAction(id, dryRun),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] });
    },
  });
}
