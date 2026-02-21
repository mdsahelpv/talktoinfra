// Source Citation Types (duplicated from citations.ts to avoid circular imports)
export interface SourceCitation {
  id: string;
  type: string;
  name: string;
  description: string;
  retrieved_at: string;
  confidence: number;
  score: number;
  source: string;
  source_id: string;
  // Additional properties for UI display
  title?: string;
  content?: string;
  relevance?: number;
  url?: string;
  raw_data?: Record<string, unknown>;
  metadata?: {
    discovered_at?: string;
    last_seen_at?: string;
    scan_job_id?: string;
  };
}

export {
  toUICitationCard,
  getConfidenceLabel,
  getConfidenceColor,
  CONFIDENCE_THRESHOLDS,
  RESOURCE_TYPE_ICONS,
  SOURCE_LABELS,
} from './citations';

// Workflow Types
export type {
  WorkflowStatus,
  ExecutionStatus,
  StepType,
  WorkflowStep,
  Workflow,
  WorkflowExecution,
  WorkflowStepExecution,
  WorkflowTemplate,
  WorkflowListResponse,
  ExecutionListResponse,
} from './workflow';

export interface User {
  id: string;
  username: string;
  email?: string;
  roles: string[];
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  sources?: SourceCitation[];
  actions?: Action[];
  isStreaming?: boolean;
}

export interface Source {
  id: string;
  title: string;
  url?: string;
  content: string;
  relevance: number;
}

export interface Action {
  id: string;
  type: 'kubernetes' | 'terraform' | 'ansible' | 'script';
  name: string;
  description: string;
  status: 'pending' | 'approved' | 'rejected' | 'executing' | 'completed' | 'failed';
  requiresApproval: boolean;
  dryRun?: boolean;
  parameters: Record<string, unknown>;
  result?: ActionResult;
  createdAt: string;
  executedAt?: string;
  approvedBy?: string;
}

export interface ActionResult {
  success: boolean;
  output: string;
  error?: string;
  logs: string[];
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
}

export interface DashboardStats {
  totalConversations: number;
  totalMessages: number;
  pendingApprovals: number;
  completedActions: number;
  failedActions: number;
  recentActivity: ActivityItem[];
}

export interface ActivityItem {
  id: string;
  type: 'message' | 'action' | 'approval';
  description: string;
  timestamp: string;
  user?: string;
}

export interface WebSocketMessage {
  type: 'message' | 'action_update' | 'notification' | 'stream_chunk';
  payload: unknown;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// Infrastructure Discovery Types

export type ScanType = 'python' | 'fast' | 'detailed' | 'hybrid';

export interface DiscoveredPort {
  port: number;
  status: 'open' | 'closed' | 'filtered';
  service?: string;
  service_version?: string;
  banner?: string;
  protocol: 'tcp' | 'udp';
}

export interface DiscoveredHost {
  id: string;
  ip_address: string;
  hostname?: string;
  ports: DiscoveredPort[];
  status: 'alive' | 'unreachable' | 'filtered';
  response_time_ms?: number;
  discovered_at: string;
  added_to_hosts: boolean;
}

export interface PortPreset {
  name: string;
  description: string;
  ports: number[];
}

export interface ScannerInfo {
  name: string;
  description: string;
  available: boolean;
  requires_root: boolean;
  recommended_for: string;
  average_speed: string;
}

export interface DiscoveryStatus {
  total_scans: number;
  active_scans: number;
  completed_scans_24h: number;
  total_managed_hosts: number;
  online_hosts: number;
  offline_hosts: number;
  health_check_enabled: boolean;
  last_health_check?: string;
}

export interface ManagedHost {
  id: string;
  name: string;
  ip_address: string;
  ports: number[];
  services: string[];
  status: 'online' | 'offline' | 'unknown';
  last_checked_at?: string;
  added_at: string;
  added_by: string;
}

export interface ScanRequest {
  ip_range: string;
  ports: number[];
  timeout: number;
  concurrent_limit: number;
  service_detection: boolean;
}

export interface ScanJob {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  scan_type: ScanType;
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
}

export interface ScanJobList {
  items: ScanJob[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ScanJobResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface ScanStatus {
  job_id: string;
  status: string;
  progress: number;
  total_hosts?: number;
  scanned_hosts: number;
  found_hosts: number;
  current_phase?: string;
  estimated_time_remaining?: number;
  message?: string;
}

export interface ScanResults {
  job_id: string;
  status: string;
  total_hosts: number;
  found_hosts: number;
  hosts: DiscoveredHost[];
}
