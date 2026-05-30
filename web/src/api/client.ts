const BASE_URL = '/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  chat: (message: string, sessionId = '') =>
    request<{ session_id: string; message: string; tool_calls?: any[]; requires_approval: boolean; approval_id: string | null }>(
      '/chat',
      { method: 'POST', body: JSON.stringify({ session_id: sessionId, message }) }
    ),

  approve: (approvalId: string, approved: boolean, note = '') =>
    request<{ success: boolean }>(
      `/chat/approve?approval_id=${approvalId}&approved=${approved}&note=${note}`,
      { method: 'POST' }
    ),

  sessions: {
    list: (limit = 20) =>
      request<{ sessions: any[]; total: number }>(`/sessions?limit=${limit}`),
    create: (description = '') =>
      request<{ session_id: string }>('/sessions', { method: 'POST', body: JSON.stringify({ description }) }),
  },

  tools: {
    list: () => request<{ tools: any[]; total: number }>('/tools'),
  },

  agents: {
    list: () => request<{ agents: any[] }>('/agents'),
  },

  audit: {
    list: (sessionId = '', limit = 50) =>
      request<{ entries: any[]; total: number }>(`/audit?session_id=${sessionId}&limit=${limit}`),
  },

  health: () => request<{ service: string; version: string; healthy: boolean }>('/health'),
}
