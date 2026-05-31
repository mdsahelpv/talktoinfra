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

  discover: {
    scan: () => request<{ scan: Record<string, any>; total_agents: number; scan_timestamp: string | null }>('/discover/scan'),
    summary: () => request<{ total_categories: number; total_resources: number; categories: any[] }>('/discover/summary'),
  },

  networkScan: {
    start: (cidr: string, ports?: number[]) =>
      request<{ job_id: string; cidr: string; status: string; total_hosts: number }>('/network-scan', {
        method: 'POST',
        body: JSON.stringify({ cidr, ports }),
      }),
    status: (jobId: string) =>
      request<{
        job_id: string; cidr: string; status: string; progress: number;
        total_hosts: number; scanned_hosts: number; hosts_found: number;
        hosts: Array<{ ip: string; hostname: string; status: string; ports: Array<{ port: number; service: string; state: string }> }>;
        created_at: number; completed_at: number | null; error: string;
      }>(`/network-scan/${jobId}`),
    ports: () =>
      request<{ ports: Array<{ port: number; service: string }>; groups: Record<string, number[]>; quick_ports: number[] }>('/network-scan/ports/common'),
    deployAgent: (jobId: string, hostIps: string[]) =>
      request<any>(`/network-scan/${jobId}/deploy-agent`, {
        method: 'POST',
        body: JSON.stringify({ job_id: jobId, host_ips: hostIps }),
      }),
    connectAgentless: (jobId: string, hostIps: string[]) =>
      request<any>(`/network-scan/${jobId}/connect-agentless`, {
        method: 'POST',
        body: JSON.stringify({ job_id: jobId, host_ips: hostIps }),
      }),
  },
}
