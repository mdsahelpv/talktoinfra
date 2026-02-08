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
};
