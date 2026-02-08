// Conversation and workflow types for chat interface

export type IntentType =
    | 'QUERY'
    | 'ACTION'
    | 'DISCOVERY'
    | 'ONBOARDING'
    | 'MANAGEMENT'
    | 'ANALYSIS'
    | 'HELP'
    | 'UNKNOWN';

export type ConversationState =
    | 'NEW'
    | 'ACKNOWLEDGED'
    | 'PROCESSING'
    | 'PENDING_APPROVAL'
    | 'EXECUTING'
    | 'COMPLETED'
    | 'FAILED'
    | 'CANCELLED';

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';

export type ApprovalLevel = 'USER' | 'MANAGER' | 'ADMIN';

export type MessageRole = 'user' | 'assistant' | 'system';

// Pagination types
export interface PaginationState {
    currentPage: number;
    pageSize: number;
    totalItems: number;
    totalPages: number;
}

export interface PaginationConfig {
    pageSizeOptions: number[];
    defaultPageSize: number;
}

// Filter types
export type FilterOperator = 'eq' | 'ne' | 'gt' | 'lt' | 'gte' | 'lte' | 'contains' | 'in' | 'not_in';

export interface FilterCondition {
    field: string;
    operator: FilterOperator;
    value: unknown;
}

export type FilterPreset =
    | 'all'
    | 'failing'
    | 'pending'
    | 'errors'
    | 'warnings'
    | 'healthy';

export interface FilterState {
    preset: FilterPreset;
    customConditions: FilterCondition[];
    searchQuery: string;
}

// Sort types
export type SortDirection = 'asc' | 'desc';

export interface SortState {
    field: string;
    direction: SortDirection;
}

// Query result metadata
export interface QueryResultMetadata {
    totalItems?: number;
    displayedItems?: number;
    executionTimeMs?: number;
    resultType?: string;
    resourceKind?: string;
    namespaces?: string[];
    clusterId?: string;
}

// Alert types
export type AlertSeverity = 'critical' | 'warning' | 'info' | 'low';

export type AlertConditionType = 'threshold' | 'time_based' | 'resource_based' | 'custom';

export type AlertStatus = 'active' | 'firing' | 'pending' | 'resolved' | 'disabled';

export interface AlertThreshold {
    metric: string;
    operator: 'gt' | 'lt' | 'gte' | 'lte' | 'eq';
    value: number;
    duration?: number; // in seconds
}

export interface AlertNotificationChannel {
    type: 'email' | 'slack' | 'webhook' | 'pagerduty';
    destination: string;
    enabled: boolean;
}

export interface AlertConfig {
    name: string;
    description?: string;
    condition: {
        type: AlertConditionType;
        query?: string;
        threshold?: AlertThreshold;
        timeRange?: number; // in seconds
        expression?: string;
    };
    severity: AlertSeverity;
    channels: AlertNotificationChannel[];
    enabled: boolean;
    labels?: Record<string, string>;
    annotations?: Record<string, string>;
}

export interface Alert {
    id: string;
    name: string;
    description?: string;
    condition: AlertConfig['condition'];
    severity: AlertSeverity;
    status: AlertStatus;
    current_value?: number;
    starts_at?: string;
    ends_at?: string;
    labels?: Record<string, string>;
    annotations?: Record<string, string>;
    created_at: string;
    updated_at: string;
    created_by?: string;
}

export interface CreateAlertRequest {
    name: string;
    description?: string;
    condition: AlertConfig['condition'];
    severity: AlertSeverity;
    channels: AlertNotificationChannel[];
    enabled: boolean;
    labels?: Record<string, string>;
    annotations?: Record<string, string>;
    query_context?: {
        original_query: string;
        result_type: string;
        filters?: FilterState;
    };
}

export interface ApprovalRule {
    id: string;
    level: ApprovalLevel;
    condition: string;
    description: string;
}

export interface ApproverHistoryEntry {
    level: ApprovalLevel;
    approver_id: string;
    action: 'approved' | 'rejected';
    reason?: string;
    timestamp: string;
}

export interface ActionApprovalChain {
    id: string;
    current_level: ApprovalLevel;
    target_level: ApprovalLevel;
    rules: ApprovalRule[];
    history: ApproverHistoryEntry[];
    status: ApprovalStatus;
    created_at: string;
    updated_at: string;
}

export interface ActionApproval {
    id: string;
    conversation_id: string;
    user_id: string;
    action_type: string;
    target_resources: string[];
    description: string;
    risk_level: RiskLevel;
    impact_summary: string;
    rollback_plan?: string;
    status: ApprovalStatus;
    approver_id?: string;
    approved_at?: string;
    rejected_at?: string;
    rejection_reason?: string;
    created_at: string;
    expires_at: string;
    // Rich approval fields
    affected_resources?: Array<{
        type: string;
        name: string;
        change_type: 'create' | 'update' | 'delete' | 'read';
        before_state?: Record<string, unknown>;
        after_state?: Record<string, unknown>;
    }>;
    risk_analysis?: {
        what_could_go_wrong: string[];
        dependencies: string[];
        estimated_downtime: string;
        rollback_time_estimate: string;
    };
    approval_chain?: ActionApprovalChain;
}

export interface IntentClassification {
    intent: IntentType;
    confidence: number;
    entities: Array<{
        type: string;
        value: string;
        confidence?: number;
    }>;
    action_type?: string;
    target_resource?: string;
    requires_approval?: boolean;
    risk_level?: RiskLevel;
}

export interface ConversationMessage {
    id: string;
    role: MessageRole;
    content: string;
    timestamp: string;
    metadata?: Record<string, unknown>;
    intent?: IntentClassification;
    sources?: QuerySource[];
}

export interface Conversation {
    id: string;
    user_id: string;
    title?: string;
    messages: ConversationMessage[];
    state: ConversationState;
    created_at: string;
    updated_at: string;
    metadata?: Record<string, unknown>;
}

export interface ConversationListItem {
    id: string;
    user_id: string;
    title?: string;
    message_count: number;
    state: ConversationState;
    created_at: string;
    updated_at: string;
    metadata?: Record<string, unknown>;
}

export interface QuerySource {
    type: string;
    resource_id?: string;
    resource_type?: string;
    confidence: number;
    metadata?: Record<string, unknown>;
}

export interface QueryResponse {
    response: string;
    conversation_id: string;
    intent: IntentClassification;
    sources: QuerySource[];
    workflow_state?: string;
    metadata?: Record<string, unknown>;
    timestamp: string;
}

export interface ActionApproval {
    id: string;
    conversation_id: string;
    user_id: string;
    action_type: string;
    target_resources: string[];
    description: string;
    risk_level: RiskLevel;
    impact_summary: string;
    rollback_plan?: string;
    status: ApprovalStatus;
    approver_id?: string;
    approved_at?: string;
    rejected_at?: string;
    rejection_reason?: string;
    created_at: string;
    expires_at: string;
}

export interface ConversationCreateRequest {
    user_id: string;
    title?: string;
    metadata?: Record<string, unknown>;
}

export interface QueryRequest {
    query: string;
    conversation_id?: string;
    user_id: string;
    context?: Record<string, unknown>;
}

export interface ApprovalActionRequest {
    approval_id: string;
    action: 'approve' | 'reject';
    reason?: string;
}

export interface ChatInputState {
    isLoading: boolean;
    isStreaming: boolean;
    error?: string;
}

export interface ApprovalModalProps {
    isOpen: boolean;
    approval: ActionApproval | null;
    onApprove: (reason?: string) => void;
    onReject: (reason: string) => void;
    onClose: () => void;
}

export interface IntentIndicatorProps {
    intent: IntentClassification;
    showDetails?: boolean;
}

export interface QueryResultProps {
    response: string;
    sources: QuerySource[];
    intent: IntentClassification;
    showSources?: boolean;
    metadata?: QueryResultMetadata;
}

export interface QueryResultPaginationProps {
    pagination: PaginationState;
    onPageChange: (page: number) => void;
    onPageSizeChange: (pageSize: number) => void;
    loading?: boolean;
}

export interface QueryResultFiltersProps {
    filters: FilterState;
    onFiltersChange: (filters: FilterState) => void;
    availableFields: string[];
    resultType?: string;
}

export interface ExportDropdownProps {
    data: Record<string, unknown>[];
    filename?: string;
    disabled?: boolean;
}

export interface CreateAlertModalProps {
    isOpen: boolean;
    onClose: () => void;
    onCreate: (alert: CreateAlertRequest) => void;
    queryContext?: {
        originalQuery: string;
        resultType: string;
        filters?: FilterState;
        sampleData?: Record<string, unknown>[];
    };
    loading?: boolean;
}

export interface ConversationTimelineProps {
    messages: ConversationMessage[];
    currentMessageId?: string;
    showTimestamps?: boolean;
    maxMessages?: number;
}

export const INTENT_COLORS: Record<IntentType, string> = {
    QUERY: 'bg-blue-100 text-blue-800',
    ACTION: 'bg-red-100 text-red-800',
    DISCOVERY: 'bg-purple-100 text-purple-800',
    ONBOARDING: 'bg-green-100 text-green-800',
    MANAGEMENT: 'bg-yellow-100 text-yellow-800',
    ANALYSIS: 'bg-indigo-100 text-indigo-800',
    HELP: 'bg-gray-100 text-gray-800',
    UNKNOWN: 'bg-gray-100 text-gray-800',
};

export const RISK_COLORS: Record<RiskLevel, string> = {
    LOW: 'text-green-600',
    MEDIUM: 'text-yellow-600',
    HIGH: 'text-orange-600',
    CRITICAL: 'text-red-600',
};

export const STATE_ICONS: Record<ConversationState, string> = {
    NEW: '🆕',
    ACKNOWLEDGED: '✅',
    PROCESSING: '⚙️',
    PENDING_APPROVAL: '⏳',
    EXECUTING: '🚀',
    COMPLETED: '🎉',
    FAILED: '❌',
    CANCELLED: '🚫',
};

export const ALERT_SEVERITY_COLORS: Record<AlertSeverity, string> = {
    critical: 'bg-red-100 text-red-800',
    warning: 'bg-yellow-100 text-yellow-800',
    info: 'bg-blue-100 text-blue-800',
    low: 'bg-gray-100 text-gray-800',
};

export const ALERT_STATUS_COLORS: Record<AlertStatus, string> = {
    active: 'bg-red-100 text-red-800',
    firing: 'bg-red-100 text-red-800',
    pending: 'bg-yellow-100 text-yellow-800',
    resolved: 'bg-green-100 text-green-800',
    disabled: 'bg-gray-100 text-gray-800',
};

export interface NotificationPreferences {
    email_enabled: boolean;
    slack_enabled: boolean;
    in_app_enabled: boolean;
    sound_enabled: boolean;
}

export interface ApprovalNotification {
    id: string;
    approval_id: string;
    conversation_id: string;
    message: string;
    action_type: string;
    risk_level: RiskLevel;
    created_at: string;
    read: boolean;
}

export interface ApprovalNotificationProps {
    notifications: ApprovalNotification[];
    pendingCount: number;
    onMarkAsRead: (notificationId: string) => void;
    onApproveAll: () => void;
    onViewApproval: (approvalId: string) => void;
    onTogglePreferences: () => void;
    preferences: NotificationPreferences;
}

export interface ApprovalChainIndicatorProps {
    chain: ActionApprovalChain;
    onEscalate?: () => void;
    showActions?: boolean;
}

export const APPROVAL_LEVEL_ORDER: ApprovalLevel[] = ['USER', 'MANAGER', 'ADMIN'];

export const APPROVAL_LEVEL_CONFIG: Record<ApprovalLevel, { label: string; color: string; icon: string }> = {
    USER: { label: 'User', color: 'bg-blue-100 text-blue-800', icon: '👤' },
    MANAGER: { label: 'Manager', color: 'bg-purple-100 text-purple-800', icon: '👔' },
    ADMIN: { label: 'Admin', color: 'bg-red-100 text-red-800', icon: '🛡️' },
};

// Workflow execution types for multi-step task progress tracking

export type WorkflowStepStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'SKIPPED' | 'PAUSED';

export type WorkflowExecutionStatus = 'PENDING' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export type WorkflowControlAction = 'PAUSE' | 'RESUME' | 'CANCEL' | 'RETRY' | 'SKIP';

export type WorkflowStepType =
    | 'QUERY'
    | 'APPROVAL'
    | 'KUBERNETES'
    | 'TERRAFORM'
    | 'SHELL'
    | 'API_CALL'
    | 'TRANSFORM'
    | 'VALIDATION'
    | 'NOTIFICATION'
    | 'WAIT'
    | 'CONDITIONAL'
    | 'PARALLEL'
    | 'LOOP'
    | 'CUSTOM';

export interface WorkflowStepInput {
    type: string;
    data: Record<string, unknown>;
    source?: string;
}

export interface WorkflowStepOutput {
    type: string;
    data: Record<string, unknown>;
    error?: string;
}

export interface WorkflowStepLog {
    timestamp: string;
    level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';
    message: string;
    details?: Record<string, unknown>;
}

export interface WorkflowStep {
    id: string;
    name: string;
    description?: string;
    type: WorkflowStepType;
    status: WorkflowStepStatus;
    order: number;
    input?: WorkflowStepInput;
    output?: WorkflowStepOutput;
    logs: WorkflowStepLog[];
    started_at?: string;
    completed_at?: string;
    duration_ms?: number;
    error?: string;
    retry_count: number;
    max_retries: number;
    dependencies: string[];
    parallel_with?: string[];
    skip_if?: Record<string, unknown>;
    metadata?: Record<string, unknown>;
}

export interface WorkflowExecution {
    id: string;
    conversation_id: string;
    name: string;
    description?: string;
    status: WorkflowExecutionStatus;
    steps: WorkflowStep[];
    current_step_id: string | null;
    progress_percentage: number;
    started_at: string;
    completed_at?: string;
    total_duration_ms?: number;
    created_by: string;
    metadata?: Record<string, unknown>;
    error?: string;
    result_summary?: Record<string, unknown>;
}

export interface WorkflowExecutionRequest {
    conversation_id: string;
    user_id: string;
    workflow_definition: {
        name: string;
        description?: string;
        steps: Omit<WorkflowStep, 'id' | 'status' | 'logs' | 'started_at' | 'completed_at' | 'retry_count'>[];
    };
    context?: Record<string, unknown>;
}

export interface WorkflowControlRequest {
    workflow_execution_id: string;
    user_id: string;
    action: WorkflowControlAction;
    step_id?: string;
    reason?: string;
}

export interface WorkflowProgressUpdate {
    workflow_execution_id: string;
    current_step_id: string;
    status: WorkflowExecutionStatus;
    progress_percentage: number;
    step_updates: Array<{
        step_id: string;
        status: WorkflowStepStatus;
        output?: WorkflowStepOutput;
        error?: string;
        logs?: WorkflowStepLog[];
    }>;
    timestamp: string;
}

// Cross-Cluster Context Types

export type ClusterContextMode = 'single' | 'all';

export interface ClusterInfo {
    id: string;
    name: string;
    provider?: 'aws' | 'gcp' | 'azure' | 'onprem' | 'other';
    region?: string;
    status: 'connected' | 'disconnected' | 'error';
    last_connected_at?: string;
}

export interface NamespaceInfo {
    id: string;
    name: string;
    cluster_id: string;
    status: 'active' | 'terminating' | 'unknown';
    resource_count?: number;
}

export interface ClusterContext {
    mode: ClusterContextMode;
    selected_cluster_id: string | null;
    selected_namespace: string | null;
    available_clusters: ClusterInfo[];
    available_namespaces: NamespaceInfo[];
}

export interface ClusterContextState {
    current: ClusterContext;
    last_updated: string;
}

// User Preferences Types

export type OutputFormat = 'table' | 'json' | 'yaml' | 'summary';

export interface UserQueryHistory {
    query: string;
    timestamp: string;
    cluster_id?: string;
    namespace?: string;
    result_count?: number;
}

export interface UserPreferenceClusterUsage {
    cluster_id: string;
    usage_count: number;
    last_used_at: string;
}

export interface UserPreferences {
    user_id: string;
    preferred_output_format: OutputFormat;
    preferred_cluster_id: string | null;
    cluster_usage: UserPreferenceClusterUsage[];
    query_history: UserQueryHistory[];
    common_queries: string[];
    remembered_namespaces: Record<string, string[]>; // cluster_id -> namespaces
    show_cluster_badges: boolean;
    auto_include_all_clusters: boolean;
    query_suggestions_enabled: boolean;
    last_active_at: string;
    created_at: string;
}

// Cross-Cluster Query Result Types

export interface ClusterQueryResult {
    cluster_id: string;
    cluster_name: string;
    namespace?: string;
    items: Record<string, unknown>[];
    total_count: number;
    execution_time_ms: number;
    status: 'success' | 'error' | 'partial';
    error_message?: string;
}

export interface CrossClusterQueryMetadata {
    query: string;
    mode: ClusterContextMode;
    target_clusters: string[];
    results: ClusterQueryResult[];
    total_items: number;
    aggregated_count: number;
    execution_time_ms: number;
    namespaces_scoped: boolean;
}

// Query Request with Context
export interface QueryRequestWithContext extends QueryRequest {
    context?: {
        cluster_context?: ClusterContext;
        namespace?: string;
        output_format?: OutputFormat;
        include_all_clusters?: boolean;
    };
}

// Component prop types for context selectors

export interface ClusterContextSelectorProps {
    clusters: ClusterInfo[];
    selectedClusterId: string | null;
    mode: ClusterContextMode;
    onClusterChange: (clusterId: string | null) => void;
    onModeChange: (mode: ClusterContextMode) => void;
    loading?: boolean;
    disabled?: boolean;
}

export interface NamespaceSelectorProps {
    namespaces: NamespaceInfo[];
    selectedNamespace: string | null;
    clusterId: string | null;
    onNamespaceChange: (namespace: string | null) => void;
    loading?: boolean;
    disabled?: boolean;
    showAllOption?: boolean;
}

export interface UserPreferencesProps {
    preferences: UserPreferences;
    onPreferencesChange: (preferences: Partial<UserPreferences>) => void;
    onClearHistory: () => void;
    onExportPreferences: () => void;
    loading?: boolean;
}

// Helper functions and constants

export interface WorkflowProgressProps {
    workflowExecution: WorkflowExecution;
    expandedStepId?: string | null;
    onStepClick?: (stepId: string) => void;
    showControls?: boolean;
    onControlAction?: (action: WorkflowControlAction, stepId?: string) => void;
    autoScroll?: boolean;
}

export interface StepDetailsProps {
    step: WorkflowStep;
    isExpanded: boolean;
    onToggleExpand: () => void;
    showLogs?: boolean;
    maxLogs?: number;
}

export interface WorkflowControlsProps {
    workflowExecution: WorkflowExecution;
    onControlAction: (action: WorkflowControlAction, stepId?: string) => void;
    loading?: boolean;
    disabled?: boolean;
}

// Helper functions and constants

export const WORKFLOW_STEP_STATUS_CONFIG: Record<WorkflowStepStatus, { icon: string; color: string; label: string }> = {
    PENDING: { icon: '○', color: 'text-gray-400', label: 'Pending' },
    RUNNING: { icon: '◐', color: 'text-blue-500 animate-spin', label: 'Running' },
    COMPLETED: { icon: '✓', color: 'text-green-500', label: 'Completed' },
    FAILED: { icon: '✗', color: 'text-red-500', label: 'Failed' },
    SKIPPED: { icon: '⊘', color: 'text-gray-400', label: 'Skipped' },
    PAUSED: { icon: '⏸', color: 'text-yellow-500', label: 'Paused' },
};

export const WORKFLOW_EXECUTION_STATUS_CONFIG: Record<WorkflowExecutionStatus, { icon: string; color: string; label: string }> = {
    PENDING: { icon: '○', color: 'text-gray-400', label: 'Pending' },
    RUNNING: { icon: '⚙️', color: 'text-blue-500 animate-pulse', label: 'Running' },
    PAUSED: { icon: '⏸', color: 'text-yellow-500', label: 'Paused' },
    COMPLETED: { icon: '✓', color: 'text-green-500', label: 'Completed' },
    FAILED: { icon: '✗', color: 'text-red-500', label: 'Failed' },
    CANCELLED: { icon: '⊘', color: 'text-gray-400', label: 'Cancelled' },
};

export const WORKFLOW_STEP_TYPE_ICONS: Record<WorkflowStepType, string> = {
    QUERY: '🔍',
    APPROVAL: '✅',
    KUBERNETES: '☸️',
    TERRAFORM: '🏗️',
    SHELL: '💻',
    API_CALL: '🌐',
    TRANSFORM: '🔄',
    VALIDATION: '✓',
    NOTIFICATION: '🔔',
    WAIT: '⏱️',
    CONDITIONAL: '?',
    PARALLEL: '∥',
    LOOP: '↻',
    CUSTOM: '⚙️',
};

export function calculateProgressPercentage(completedSteps: number, totalSteps: number): number {
    if (totalSteps === 0) return 0;
    return Math.round((completedSteps / totalSteps) * 100);
}

export function formatDuration(ms: number): string {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
}

export function getStepDuration(step: WorkflowStep): string | null {
    if (!step.started_at) return null;
    const start = new Date(step.started_at).getTime();
    const end = step.completed_at ? new Date(step.completed_at).getTime() : Date.now();
    return formatDuration(end - start);
}

export function isWorkflowActive(status: WorkflowExecutionStatus): boolean {
    return status === 'RUNNING' || status === 'PAUSED';
}

export function canStepExecute(step: WorkflowStep, allSteps: WorkflowStep[]): boolean {
    if (step.status !== 'PENDING') return false;
    const dependencies = step.dependencies || [];
    return dependencies.every(depId => {
        const depStep = allSteps.find(s => s.id === depId);
        return depStep?.status === 'COMPLETED';
    });
}

export function findNextRunnableStep(steps: WorkflowStep[]): WorkflowStep | null {
    return steps.find(s => canStepExecute(s, steps)) || null;
}

export function getFailedSteps(steps: WorkflowStep[]): WorkflowStep[] {
    return steps.filter(s => s.status === 'FAILED');
}

export function getCompletedSteps(steps: WorkflowStep[]): WorkflowStep[] {
    return steps.filter(s => s.status === 'COMPLETED');
}

export function getPendingSteps(steps: WorkflowStep[]): WorkflowStep[] {
    return steps.filter(s => s.status === 'PENDING');
}

export function getRunningSteps(steps: WorkflowStep[]): WorkflowStep[] {
    return steps.filter(s => s.status === 'RUNNING');
}

export const FILTER_PRESETS: Record<FilterPreset, { label: string; icon: string; description: string }> = {
    all: { label: 'All Results', icon: '📋', description: 'Show all results' },
    failing: { label: 'Failing', icon: '❌', description: 'Only show failing resources' },
    pending: { label: 'Pending', icon: '⏳', description: 'Only show pending resources' },
    errors: { label: 'Errors', icon: '🚨', description: 'Only show errors' },
    warnings: { label: 'Warnings', icon: '⚠️', description: 'Only show warnings' },
    healthy: { label: 'Healthy', icon: '✅', description: 'Only show healthy resources' },
};
