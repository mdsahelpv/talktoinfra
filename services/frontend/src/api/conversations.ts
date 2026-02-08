import { apiClient } from './client';
import type {
    Conversation,
    ConversationListItem,
    QueryRequest,
    QueryResponse,
    ConversationCreateRequest,
    ActionApproval,
    ApprovalActionRequest,
    CreateAlertRequest,
    Alert,
    WorkflowExecution,
    WorkflowExecutionRequest,
    WorkflowControlRequest,
    WorkflowProgressUpdate,
    ClusterInfo,
    NamespaceInfo,
    UserPreferences,
    ClusterContext,
    OutputFormat,
} from '@/types/conversation';

const AI_ROUTER_URL = import.meta.env.VITE_AI_ROUTER_URL || '';
const MONITORING_URL = import.meta.env.VITE_MONITORING_URL || AI_ROUTER_URL;

export const conversationsApi = {
    // Conversation CRUD
    createConversation: (data: ConversationCreateRequest) =>
        apiClient.post<Conversation>('/api/v1/conversations', data),

    getConversation: (conversationId: string) =>
        apiClient.get<Conversation>(`/api/v1/conversations/${conversationId}`),

    listConversations: (userId: string, limit = 20, offset = 0) =>
        apiClient.get<{
            items: ConversationListItem[];
            total: number;
        }>(`/api/v1/conversations?user_id=${userId}&limit=${limit}&offset=${offset}`),

    deleteConversation: (conversationId: string) =>
        apiClient.delete(`/api/v1/conversations/${conversationId}`),

    // Messages
    getMessages: (conversationId: string) =>
        apiClient.get<Conversation['messages']>(`/api/v1/conversations/${conversationId}/messages`),

    // Query processing
    sendQuery: (request: QueryRequest) =>
        apiClient.post<QueryResponse>(`${AI_ROUTER_URL}/query`, request),

    streamQuery: (request: QueryRequest) => {
        const url = `${AI_ROUTER_URL}/query/stream`;
        return fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(request),
        });
    },

    // Approval workflow
    createApproval: (data: {
        conversation_id: string;
        user_id: string;
        action_type: string;
        target_resources: string[];
        description: string;
        risk_level: string;
        impact_summary: string;
        rollback_plan?: string;
    }) =>
        apiClient.post<ActionApproval>(`${AI_ROUTER_URL}/approvals`, data),

    getApproval: (approvalId: string) =>
        apiClient.get<ActionApproval>(`${AI_ROUTER_URL}/approvals/${approvalId}`),

    getConversationApprovals: (conversationId: string) =>
        apiClient.get<ActionApproval[]>(`${AI_ROUTER_URL}/conversations/${conversationId}/approvals`),

    approveAction: (request: ApprovalActionRequest) =>
        apiClient.post<ActionApproval>(`${AI_ROUTER_URL}/approvals/${request.approval_id}/approve`, {
            action: request.action,
            reason: request.reason,
        }),

    rejectAction: (request: ApprovalActionRequest) =>
        apiClient.post<ActionApproval>(`${AI_ROUTER_URL}/approvals/${request.approval_id}/reject`, {
            action: request.action,
            reason: request.reason,
        }),

    cancelApproval: (approvalId: string, userId: string) =>
        apiClient.post<{ success: boolean }>(`${AI_ROUTER_URL}/approvals/${approvalId}/cancel`, {
            user_id: userId,
        }),

    listPendingApprovals: (limit = 50) =>
        apiClient.get<ActionApproval[]>(`${AI_ROUTER_URL}/approvals/pending?limit=${limit}`),

    // Intent classification (for preview)
    classifyIntent: (query: string) =>
        apiClient.post<{
            intent: string;
            confidence: number;
            entities: Array<{ type: string; value: string }>;
        }>(`${AI_ROUTER_URL}/classify`, { query }),

    // Alert management
    createAlert: (request: CreateAlertRequest) =>
        apiClient.post<Alert>(`${MONITORING_URL}/alerts`, request),

    listAlerts: (params?: {
        status?: string;
        severity?: string;
        limit?: number;
        offset?: number;
    }) => {
        const queryParams = new URLSearchParams();
        if (params?.status) queryParams.set('status', params.status);
        if (params?.severity) queryParams.set('severity', params.severity);
        if (params?.limit) queryParams.set('limit', String(params.limit));
        if (params?.offset) queryParams.set('offset', String(params.offset));

        return apiClient.get<Alert[]>(`${MONITORING_URL}/alerts?${queryParams.toString()}`);
    },

    getAlert: (alertId: string) =>
        apiClient.get<Alert>(`${MONITORING_URL}/alerts/${alertId}`),

    updateAlert: (alertId: string, data: Partial<CreateAlertRequest>) =>
        apiClient.post<Alert>(`${MONITORING_URL}/alerts/${alertId}`, data),

    deleteAlert: (alertId: string) =>
        apiClient.delete(`${MONITORING_URL}/alerts/${alertId}`),

    enableAlert: (alertId: string) =>
        apiClient.post<Alert>(`${MONITORING_URL}/alerts/${alertId}/enable`),

    disableAlert: (alertId: string) =>
        apiClient.post<Alert>(`${MONITORING_URL}/alerts/${alertId}/disable`),

    testAlert: (alertId: string) =>
        apiClient.post<{ success: boolean }>(`${MONITORING_URL}/alerts/${alertId}/test`),

    // Workflow execution API
    startWorkflow: (request: WorkflowExecutionRequest) =>
        apiClient.post<WorkflowExecution>(`${AI_ROUTER_URL}/workflows/execute`, request),

    getWorkflowExecution: (workflowExecutionId: string) =>
        apiClient.get<WorkflowExecution>(`${AI_ROUTER_URL}/workflows/${workflowExecutionId}`),

    getWorkflowsByConversation: (conversationId: string) =>
        apiClient.get<WorkflowExecution[]>(`${AI_ROUTER_URL}/workflows?conversation_id=${conversationId}`),

    controlWorkflow: (request: WorkflowControlRequest) =>
        apiClient.post<WorkflowExecution>(`${AI_ROUTER_URL}/workflows/${request.workflow_execution_id}/control`, {
            action: request.action,
            step_id: request.step_id,
            reason: request.reason,
        }),

    getWorkflowProgress: (workflowExecutionId: string) =>
        apiClient.get<WorkflowProgressUpdate>(`${AI_ROUTER_URL}/workflows/${workflowExecutionId}/progress`),

    retryWorkflowStep: (workflowExecutionId: string, stepId: string, userId: string) =>
        apiClient.post<WorkflowExecution>(`${AI_ROUTER_URL}/workflows/${workflowExecutionId}/steps/${stepId}/retry`, {
            user_id: userId,
        }),

    skipWorkflowStep: (workflowExecutionId: string, stepId: string, userId: string, reason?: string) =>
        apiClient.post<WorkflowExecution>(`${AI_ROUTER_URL}/workflows/${workflowExecutionId}/steps/${stepId}/skip`, {
            user_id: userId,
            reason,
        }),

    cancelWorkflow: (workflowExecutionId: string, userId: string, reason?: string) =>
        apiClient.post<WorkflowExecution>(`${AI_ROUTER_URL}/workflows/${workflowExecutionId}/cancel`, {
            user_id: userId,
            reason,
        }),

    // Cluster Context API
    listClusters: () =>
        apiClient.get<ClusterInfo[]>('/api/v1/clusters'),

    getCluster: (clusterId: string) =>
        apiClient.get<ClusterInfo>(`/api/v1/clusters/${clusterId}`),

    getClusterNamespaces: (clusterId: string) =>
        apiClient.get<NamespaceInfo[]>(`/api/v1/clusters/${clusterId}/namespaces`),

    testClusterConnection: (clusterId: string) =>
        apiClient.post<{ success: boolean; message: string }>(`/api/v1/clusters/${clusterId}/test-connection`),

    // User Preferences API
    getUserPreferences: (userId: string) =>
        apiClient.get<UserPreferences>(`/api/v1/users/${userId}/preferences`),

    updateUserPreferences: (userId: string, preferences: Partial<UserPreferences>) =>
        apiClient.post<UserPreferences>(`/api/v1/users/${userId}/preferences`, preferences),

    updatePreferredCluster: (userId: string, clusterId: string | null) =>
        apiClient.post<UserPreferences>(`/api/v1/users/${userId}/preferences/preferred-cluster`, { cluster_id: clusterId }),

    updatePreferredOutputFormat: (userId: string, format: OutputFormat) =>
        apiClient.post<UserPreferences>(`/api/v1/users/${userId}/preferences/output-format`, { format }),

    addQueryToHistory: (userId: string, query: { query: string; cluster_id?: string; namespace?: string; result_count?: number }) =>
        apiClient.post<UserPreferences>(`/api/v1/users/${userId}/preferences/query-history`, query),

    clearQueryHistory: (userId: string) =>
        apiClient.delete(`/api/v1/users/${userId}/preferences/query-history`),

    getQuerySuggestions: (userId: string, context?: { cluster_id?: string; namespace?: string }) => {
        const queryParams = new URLSearchParams();
        if (context?.cluster_id) queryParams.set('cluster_id', context.cluster_id);
        if (context?.namespace) queryParams.set('namespace', context.namespace);
        return apiClient.get<string[]>(`/api/v1/users/${userId}/preferences/query-suggestions?${queryParams.toString()}`);
    },

    // Remember namespace per cluster
    rememberNamespace: (userId: string, clusterId: string, namespace: string) =>
        apiClient.post<UserPreferences>(`/api/v1/users/${userId}/preferences/remember-namespace`, { cluster_id: clusterId, namespace }),

    forgetNamespace: (userId: string, clusterId: string, namespace: string) => {
        const queryParams = new URLSearchParams();
        queryParams.set('cluster_id', clusterId);
        queryParams.set('namespace', namespace);
        return apiClient.delete(`/api/v1/users/${userId}/preferences/remember-namespace?${queryParams.toString()}`);
    },
    // Cluster Context Persistence
    saveClusterContext: (userId: string, context: ClusterContext) =>
        apiClient.post<UserPreferences>(`/api/v1/users/${userId}/preferences/cluster-context`, context),

    loadClusterContext: (userId: string) =>
        apiClient.get<ClusterContext>(`/api/v1/users/${userId}/preferences/cluster-context`),
};
