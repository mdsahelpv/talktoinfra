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

export type MessageRole = 'user' | 'assistant' | 'system';

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
}

export interface ConversationTimelineProps {
    messages: ConversationMessage[];
    currentMessageId?: string;
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
