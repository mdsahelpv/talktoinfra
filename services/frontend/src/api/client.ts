import type { User } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

interface RequestConfig extends RequestInit {
  skipAuth?: boolean;
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;
  private onAuthError: (() => void) | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.token = token;
  }

  setOnAuthError(callback: () => void) {
    this.onAuthError = callback;
  }

  private async request<T>(endpoint: string, config: RequestConfig = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((config.headers as Record<string, string>) || {}),
    };

    if (this.token && !config.skipAuth) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...config,
      headers,
    });

    if (!response.ok) {
      // Handle authentication errors
      if (response.status === 401 || response.status === 403) {
        if (this.onAuthError) {
          this.onAuthError();
        }
      }
      const error = await response.json().catch(() => ({ message: 'An error occurred' }));
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    if (response.status === 204) {
      return null as T;
    }

    return response.json();
  }

  get<T>(endpoint: string, config?: RequestConfig) {
    return this.request<T>(endpoint, { ...config, method: 'GET' });
  }

  post<T>(endpoint: string, data?: unknown, config?: RequestConfig) {
    return this.request<T>(endpoint, {
      ...config,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  put<T>(endpoint: string, data?: unknown, config?: RequestConfig) {
    return this.request<T>(endpoint, {
      ...config,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  delete<T>(endpoint: string, config?: RequestConfig) {
    return this.request<T>(endpoint, { ...config, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient(API_BASE_URL);

export const authApi = {
  login: (credentials: { username: string; password: string }) =>
    apiClient.post<{ access_token: string; token_type: string }>('/api/auth/login', credentials),
  
  getProfile: () => apiClient.get<User>('/api/auth/me'),
};

export const chatApi = {
  getSessions: () => apiClient.get<Array<{ id: string; title: string; created_at: string; updated_at: string }>>('/api/chat/sessions'),
  
  getMessages: (sessionId: string) =>
    apiClient.get<Array<{ id: string; role: string; content: string; timestamp: string }>>(`/api/chat/sessions/${sessionId}/messages`),
  
  sendMessage: (sessionId: string, content: string) =>
    apiClient.post<{ message_id: string }>('/api/chat/message', { session_id: sessionId, content }),
  
  streamMessage: (sessionId: string, content: string) => {
    const url = `${API_BASE_URL}/api/chat/stream`;
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiClient['token']}`,
      },
      body: JSON.stringify({ session_id: sessionId, content }),
    });
  },
};

export const dashboardApi = {
  getStats: () =>
    apiClient.get<{
      total_conversations: number;
      total_messages: number;
      pending_approvals: number;
      completed_actions: number;
      failed_actions: number;
    }>('/api/dashboard/stats'),
  
  getRecentActivity: () =>
    apiClient.get<Array<{ id: string; type: string; description: string; timestamp: string; user?: string }>>(
      '/api/dashboard/activity'
    ),
};

export const actionsApi = {
  getActions: (status?: string) =>
    apiClient.get<Array<{
      id: string;
      type: string;
      name: string;
      description: string;
      status: string;
      requires_approval: boolean;
      created_at: string;
    }>>(`/api/actions${status ? `?status=${status}` : ''}`),
  
  getAction: (id: string) => apiClient.get(`/api/actions/${id}`),
  
  approveAction: (id: string) => apiClient.post(`/api/actions/${id}/approve`, {}),
  
  rejectAction: (id: string) => apiClient.post(`/api/actions/${id}/reject`, {}),
  
  executeAction: (id: string, dryRun: boolean = false) =>
    apiClient.post(`/api/actions/${id}/execute`, { dry_run: dryRun }),
};

export const scanApi = {
  getPresets: () =>
    apiClient.get<string[]>('/api/v1/scan/presets'),

  startScan: (request: {
    ip_range: string;
    ports: number[];
    timeout?: number;
    concurrent_limit?: number;
    service_detection?: boolean;
  }) =>
    apiClient.post<{ job_id: string; status: string; message: string }>('/api/v1/scan/start', request),

  getScanStatus: (jobId: string) =>
    apiClient.get<{
      job_id: string;
      status: string;
      progress: number;
      total_hosts: number;
      scanned_hosts: number;
      found_hosts: number;
      current_ip?: string;
      estimated_time_remaining?: number;
    }>(`/api/v1/scan/${jobId}/status`),

  getScanResults: (jobId: string, aliveOnly: boolean = true) =>
    apiClient.get<Array<{
      id: string;
      ip_address: string;
      hostname?: string;
      ports: Array<{
        port: number;
        status: string;
        service?: string;
        banner?: string;
      }>;
      status: string;
      response_time_ms?: number;
      discovered_at: string;
      added_to_hosts: boolean;
    }>>(`/api/v1/scan/${jobId}/results?alive_only=${aliveOnly}`),

  stopScan: (jobId: string) =>
    apiClient.post(`/api/v1/scan/${jobId}/stop`, {}),
};

export const hostApi = {
  listHosts: () =>
    apiClient.get<Array<{
      id: string;
      name: string;
      ip_address: string;
      ports: number[];
      services: string[];
      status: string;
      last_checked_at?: string;
      added_at: string;
      added_by: string;
    }>>('/api/v1/hosts'),

  addHost: (host: {
    name: string;
    ip_address: string;
    ports: number[];
    services?: string[];
  }) =>
    apiClient.post<{
      id: string;
      name: string;
      ip_address: string;
      ports: number[];
      services: string[];
      status: string;
      added_at: string;
      added_by: string;
    }>('/api/v1/hosts', host),

  deleteHost: (hostId: string) =>
    apiClient.delete(`/api/v1/hosts/${hostId}`),
};

export const discoveryApi = {
  getScanners: () =>
    apiClient.get<{
      scanners: Array<{
        name: string;
        description: string;
        available: boolean;
        requires_root: boolean;
        recommended_for: string;
        average_speed: string;
      }>;
      recommended: string;
    }>('/api/v1/discovery/scanners'),

  getPortPresets: () =>
    apiClient.get<{
      presets: Array<{
        name: string;
        description: string;
        ports: number[];
      }>;
    }>('/api/v1/discovery/port-presets'),

  startScan: (request: {
    ip_range: string;
    ports: number[];
    scan_type?: 'python' | 'fast' | 'detailed' | 'hybrid';
    timeout?: number;
    concurrent_limit?: number;
    service_detection?: boolean;
    require_approval?: boolean;
  }) =>
    apiClient.post<{
      job_id: string;
      status: string;
      message: string;
    }>('/api/v1/discovery/scans', request),

  getScans: (status?: string, limit?: number, offset?: number) => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (limit !== undefined) params.append('limit', limit.toString());
    if (offset !== undefined) params.append('offset', offset.toString());
    const query = params.toString();
    return apiClient.get<{
      items: Array<{
        id: string;
        status: string;
        scan_type: string;
        progress: number;
        ip_range: string;
        ports: number[];
        total_hosts?: number;
        scanned_hosts: number;
        found_hosts: number;
        created_by: string;
        started_at: string;
        completed_at?: string;
        error_message?: string;
        config: Record<string, unknown>;
        created_at: string;
      }>;
      total: number;
      page: number;
      page_size: number;
      pages: number;
    }>(`/api/v1/discovery/scans${query ? `?${query}` : ''}`);
  },

  getScan: (jobId: string) =>
    apiClient.get<{
      id: string;
      status: string;
      scan_type: string;
      progress: number;
      ip_range: string;
      ports: number[];
      total_hosts?: number;
      scanned_hosts: number;
      found_hosts: number;
      created_by: string;
      started_at: string;
      completed_at?: string;
      error_message?: string;
      config: Record<string, unknown>;
      created_at: string;
    }>(`/api/v1/discovery/scans/${jobId}`),

  getScanStatus: (jobId: string) =>
    apiClient.get<{
      job_id: string;
      status: string;
      progress: number;
      total_hosts?: number;
      scanned_hosts: number;
      found_hosts: number;
      current_phase?: string;
      estimated_time_remaining?: number;
      message?: string;
    }>(`/api/v1/discovery/scans/${jobId}/status`),

  getScanResults: (jobId: string, aliveOnly: boolean = true) =>
    apiClient.get<{
      job_id: string;
      status: string;
      total_hosts: number;
      found_hosts: number;
      hosts: Array<{
        id: string;
        ip_address: string;
        hostname?: string;
        status: string;
        response_time_ms?: number;
        ports: Array<{
          port: number;
          status: string;
          service?: string;
          service_version?: string;
          banner?: string;
          protocol: string;
        }>;
        discovered_at: string;
      }>;
    }>(`/api/v1/discovery/scans/${jobId}/results?alive_only=${aliveOnly}`),

  stopScan: (jobId: string) =>
    apiClient.post<{ message: string }>(`/api/v1/discovery/scans/${jobId}/stop`, {}),

  deleteScan: (jobId: string) =>
    apiClient.delete<{ message: string }>(`/api/v1/discovery/scans/${jobId}`),

  getDiscoveryStatus: () =>
    apiClient.get<{
      total_scans: number;
      active_scans: number;
      completed_scans_24h: number;
      total_managed_hosts: number;
      online_hosts: number;
      offline_hosts: number;
      health_check_enabled: boolean;
      last_health_check?: string;
    }>('/api/v1/discovery/status'),
};
