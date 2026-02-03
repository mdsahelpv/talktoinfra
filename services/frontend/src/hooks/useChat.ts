import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { chatApi } from '@/api/client';
import { useChatStore } from '@/stores';
import type { Message } from '@/types';

export function useChatSessions() {
  return useQuery({
    queryKey: ['chat-sessions'],
    queryFn: chatApi.getSessions,
  });
}

export function useChatMessages(sessionId: string) {
  return useQuery({
    queryKey: ['chat-messages', sessionId],
    queryFn: () => chatApi.getMessages(sessionId),
    enabled: !!sessionId,
  });
}

export function useSendMessage() {
  const queryClient = useQueryClient();
  const { addMessage } = useChatStore();

  return useMutation({
    mutationFn: async ({ sessionId, content }: { sessionId: string; content: string }) => {
      const userMessage: Message = {
        id: Math.random().toString(36).substring(2, 15),
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };
      addMessage(sessionId, userMessage);

      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, content }),
      });

      return { response, sessionId };
    },
    onSuccess: async ({ sessionId }) => {
      queryClient.invalidateQueries({ queryKey: ['chat-messages', sessionId] });
    },
  });
}
