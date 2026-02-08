import React, { useState, useRef, useEffect, useCallback } from 'react';
import type {
    Conversation,
    ConversationMessage,
    ActionApproval,
    ApprovalNotification as ApprovalNotificationType,
    NotificationPreferences,
    WorkflowExecution,
    WorkflowControlAction,
} from '@/types/conversation';
import { conversationsApi } from '@/api/conversations';
import { ConversationTimeline } from './ConversationTimeline';
import { IntentIndicator } from './IntentIndicator';
import { ApprovalModal } from './ApprovalModal';
import ApprovalNotification from './ApprovalNotification';
import WorkflowProgress from './WorkflowProgress';
import { ClusterContextSelector } from './ClusterContextSelector';
import { NamespaceSelector } from './NamespaceSelector';
import UserPreferences from './UserPreferences';
import { useClusterContext } from '@/hooks/useClusterContext';
import { useUserPreferences } from '@/hooks/useUserPreferences';

interface ChatInterfaceProps {
    userId: string;
    initialConversationId?: string;
    onConversationChange?: (conversation: Conversation) => void;
}

const DEFAULT_TITLE = 'New Conversation';

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
    userId,
    initialConversationId,
    onConversationChange,
}) => {
    // State
    const [conversation, setConversation] = useState<Conversation | null>(null);
    const [messages, setMessages] = useState<ConversationMessage[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    // isStreaming state kept for future streaming support
    const [isStreaming] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [approvalModal, setApprovalModal] = useState<{
        isOpen: boolean;
        approval: ActionApproval | null;
    }>({ isOpen: false, approval: null });

    // Notification state
    const [notifications, setNotifications] = useState<ApprovalNotificationType[]>([]);
    const [notificationPreferences, setNotificationPreferences] = useState<NotificationPreferences>({
        email_enabled: true,
        slack_enabled: true,
        in_app_enabled: true,
        sound_enabled: false,
    });

    // Workflow execution state
    const [workflowExecution, setWorkflowExecution] = useState<WorkflowExecution | null>(null);
    const [expandedStepId, setExpandedStepId] = useState<string | null>(null);
    const [workflowLoading, setWorkflowLoading] = useState(false);

    // Cluster context state
    const {
        clusters,
        namespaces,
        context: clusterContext,
        loading: clusterLoading,
        error: clusterError,
        setSelectedCluster,
        selectCluster,
        refreshClusters,
        setMode,
        setSelectedNamespace,
        refreshNamespaces,
        connectedClusters,
        isAllClustersMode,
        clusterCounts,
    } = useClusterContext({ userId });

    // User preferences state
    const {
        preferences: userPreferences,
        loading: preferencesLoading,
        hasChanges: preferencesHasChanges,
        updatePreferences,
        savePreferences,
        resetPreferences,
        setOutputFormat,
        addQueryToHistory,
        clearQueryHistory,
        exportPreferences,
        importPreferences,
        rememberNamespace,
        forgetNamespace,
        getRememberedNamespaces,
    } = useUserPreferences({ userId });

    // Refs
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);
    const workflowPollingRef = useRef<NodeJS.Timeout | null>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Poll for pending approvals
    useEffect(() => {
        const fetchPendingApprovals = async () => {
            try {
                const pendingApprovals = await conversationsApi.listPendingApprovals();
                const newNotifications: ApprovalNotificationType[] = pendingApprovals.map((approval) => ({
                    id: `notif_${approval.id}`,
                    approval_id: approval.id,
                    conversation_id: approval.conversation_id,
                    message: `New approval request for ${approval.action_type}`,
                    action_type: approval.action_type,
                    risk_level: approval.risk_level,
                    created_at: approval.created_at,
                    read: false,
                }));
                setNotifications(newNotifications);

                if (newNotifications.length > 0 && notificationPreferences.sound_enabled) {
                    // Sound notification would be played here
                }
            } catch (err) {
                console.error('Failed to fetch pending approvals:', err);
            }
        };

        fetchPendingApprovals();
        const interval = setInterval(fetchPendingApprovals, 30000);

        return () => clearInterval(interval);
    }, [notificationPreferences.sound_enabled]);

    // Poll for workflow progress
    const startWorkflowPolling = useCallback((workflowId: string) => {
        const pollWorkflow = async () => {
            try {
                // eslint-disable-next-line @typescript-eslint/no-unused-vars
                const _progress = await conversationsApi.getWorkflowProgress(workflowId);

                // Fetch full workflow execution for detailed updates
                const workflow = await conversationsApi.getWorkflowExecution(workflowId);
                setWorkflowExecution(workflow);

                // Stop polling if workflow is completed, failed, or cancelled
                if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(workflow.status)) {
                    if (workflowPollingRef.current) {
                        clearInterval(workflowPollingRef.current);
                        workflowPollingRef.current = null;
                    }

                    // Add system message about completion
                    const systemMessage: ConversationMessage = {
                        id: `msg_${Date.now()}`,
                        role: 'system',
                        content: workflow.status === 'COMPLETED'
                            ? `✅ Workflow "${workflow.name}" completed successfully.`
                            : `❌ Workflow "${workflow.name}" ${workflow.status.toLowerCase()}.`,
                        timestamp: new Date().toISOString(),
                    };
                    setMessages(prev => [...prev, systemMessage]);
                }
            } catch (err) {
                console.error('Failed to fetch workflow progress:', err);
            }
        };

        pollWorkflow();
        workflowPollingRef.current = setInterval(pollWorkflow, 3000); // Poll every 3 seconds
    }, []);

    // Cleanup polling on unmount
    useEffect(() => {
        return () => {
            if (workflowPollingRef.current) {
                clearInterval(workflowPollingRef.current);
            }
        };
    }, []);

    // Initialize conversation
    // eslint-disable-next-line react-hooks/exhaustive-deps
    useEffect(() => {
        if (initialConversationId) {
            loadConversation(initialConversationId);
        } else {
            createNewConversation();
        }
    }, [initialConversationId]);

    const createNewConversation = async () => {
        try {
            const conv = await conversationsApi.createConversation({
                user_id: userId,
                title: DEFAULT_TITLE,
            });
            setConversation(conv);
            setMessages([]);
            onConversationChange?.(conv);
        } catch (err) {
            setError('Failed to create conversation');
            console.error(err);
        }
    };

    const loadConversation = async (conversationId: string) => {
        try {
            const conv = await conversationsApi.getConversation(conversationId);
            setConversation(conv);
            setMessages(conv.messages || []);
            onConversationChange?.(conv);
        } catch (err) {
            setError('Failed to load conversation');
            console.error(err);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading || isStreaming || !conversation) return;

        const userMessage = input.trim();
        setInput('');
        setError(null);

        // Add user message
        const newUserMessage: ConversationMessage = {
            id: `msg_${Date.now()}`,
            role: 'user',
            content: userMessage,
            timestamp: new Date().toISOString(),
        };

        setMessages(prev => [...prev, newUserMessage]);
        setIsLoading(true);

        try {
            // Send query to AI Router
            const response = await conversationsApi.sendQuery({
                query: userMessage,
                conversation_id: conversation.id,
                user_id: userId,
            });

            // Add assistant message
            const newAssistantMessage: ConversationMessage = {
                id: `msg_${Date.now() + 1}`,
                role: 'assistant',
                content: response.response,
                timestamp: response.timestamp,
                metadata: {
                    intent: response.intent,
                    processing_time: response.metadata?.processing_time,
                },
                intent: response.intent,
                sources: response.sources,
            };

            setMessages(prev => [...prev, newAssistantMessage]);

            // Check if workflow execution was started
            if (response.workflow_state === 'EXECUTING' && response.metadata?.workflow_execution_id) {
                const workflowId = response.metadata.workflow_execution_id as string;
                const workflow = await conversationsApi.getWorkflowExecution(workflowId);
                setWorkflowExecution(workflow);
                startWorkflowPolling(workflowId);
            }

            // Check if approval is needed
            if (response.intent.requires_approval && response.intent.intent === 'ACTION') {
                const approval = await conversationsApi.createApproval({
                    conversation_id: conversation.id,
                    user_id: userId,
                    action_type: response.intent.action_type || 'unknown',
                    target_resources: response.intent.entities?.map(e => e.value) || [],
                    description: userMessage,
                    risk_level: response.intent.risk_level || 'MEDIUM',
                    impact_summary: 'Action requires approval before execution',
                });

                setApprovalModal({
                    isOpen: true,
                    approval: approval,
                });
            }

            setConversation(prev => prev ? { ...prev, state: 'COMPLETED' } : null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to send message');
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e as React.FormEvent);
        }
    };

    const handleApprovalApprove = async (reason?: string) => {
        if (!approvalModal.approval) return;

        try {
            await conversationsApi.approveAction({
                approval_id: approvalModal.approval.id,
                action: 'approve',
                reason,
            });

            const systemMessage: ConversationMessage = {
                id: `msg_${Date.now()}`,
                role: 'system',
                content: `✅ Action "${approvalModal.approval.action_type}" has been approved and will be executed.`,
                timestamp: new Date().toISOString(),
            };

            setMessages(prev => [...prev, systemMessage]);
            setApprovalModal({ isOpen: false, approval: null });
        } catch (err) {
            setError('Failed to approve action');
            console.error(err);
        }
    };

    const handleApprovalReject = async (reason: string) => {
        if (!approvalModal.approval) return;

        try {
            await conversationsApi.rejectAction({
                approval_id: approvalModal.approval.id,
                action: 'reject',
                reason,
            });

            const systemMessage: ConversationMessage = {
                id: `msg_${Date.now()}`,
                role: 'system',
                content: `❌ Action "${approvalModal.approval.action_type}" has been rejected. Reason: ${reason}`,
                timestamp: new Date().toISOString(),
            };

            setMessages(prev => [...prev, systemMessage]);
            setApprovalModal({ isOpen: false, approval: null });
        } catch (err) {
            setError('Failed to reject action');
            console.error(err);
        }
    };

    const handleApprovalEscalate = async (): Promise<void> => {
        if (!approvalModal.approval) return;
        console.log('Escalating approval:', approvalModal.approval.id);
    };

    // Workflow control handlers
    const handleWorkflowControlAction = async (action: WorkflowControlAction, stepId?: string) => {
        if (!workflowExecution) return;

        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const _loading = workflowLoading;
        setWorkflowLoading(true);
        try {
            // eslint-disable-next-line no-case-declarations
            switch (action) {
                case 'PAUSE':
                case 'RESUME':
                case 'CANCEL': {
                    const controlledWorkflow = await conversationsApi.controlWorkflow({
                        workflow_execution_id: workflowExecution.id,
                        user_id: userId,
                        action,
                    });
                    setWorkflowExecution(controlledWorkflow);
                    break;
                }
                case 'RETRY':
                    if (stepId) {
                        const retriedWorkflow = await conversationsApi.retryWorkflowStep(
                            workflowExecution.id,
                            stepId,
                            userId
                        );
                        setWorkflowExecution(retriedWorkflow);
                    }
                    break;
                case 'SKIP':
                    if (stepId) {
                        const skippedWorkflow = await conversationsApi.skipWorkflowStep(
                            workflowExecution.id,
                            stepId,
                            userId
                        );
                        setWorkflowExecution(skippedWorkflow);
                    }
                    break;
            }
        } catch (err) {
            setError(`Failed to ${action.toLowerCase()} workflow: ${err instanceof Error ? err.message : 'Unknown error'}`);
            console.error(err);
        } finally {
            setWorkflowLoading(false);
        }
    };

    const handleStepClick = (stepId: string | null) => {
        setExpandedStepId(stepId);
    };

    const latestAssistantMessage = [...messages].reverse().find(m => m.role === 'assistant');
    const latestIntent = latestAssistantMessage?.intent;

    return (
        <div className="flex flex-col h-full bg-gray-50">
            {/* Header */}
            <div className="bg-white border-b px-4 py-3">
                <div className="flex items-center justify-between gap-4">
                    {/* Left side - Title */}
                    <div className="flex-shrink-0">
                        <h1 className="text-lg font-semibold text-gray-900">AI Assistant</h1>
                        <p className="text-sm text-gray-500">
                            {conversation?.title || 'New Conversation'}
                        </p>
                    </div>

                    {/* Center - Cluster and Namespace selectors */}
                    <div className="flex items-center gap-2 flex-1 justify-center">
                        <ClusterContextSelector
                            clusters={clusters}
                            selectedClusterId={clusterContext.selected_cluster_id}
                            mode={clusterContext.mode}
                            onClusterChange={setSelectedCluster}
                            onModeChange={setMode}
                            onRefresh={refreshClusters}
                            loading={clusterLoading}
                            counts={clusterCounts}
                        />
                        {clusterContext.mode === 'single' && clusterContext.selected_cluster_id && (
                            <NamespaceSelector
                                namespaces={namespaces}
                                selectedNamespace={clusterContext.selected_namespace}
                                clusterId={clusterContext.selected_cluster_id}
                                onNamespaceChange={setSelectedNamespace}
                                rememberedNamespaces={getRememberedNamespaces(clusterContext.selected_cluster_id)}
                                onRememberNamespace={(ns) => clusterContext.selected_cluster_id && rememberNamespace(clusterContext.selected_cluster_id, ns)}
                                onForgetNamespace={(ns) => clusterContext.selected_cluster_id && forgetNamespace(clusterContext.selected_cluster_id, ns)}
                                loading={clusterLoading}
                            />
                        )}
                    </div>

                    {/* Right side - Intent, Preferences, Notifications */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                        {latestIntent && (
                            <IntentIndicator intent={latestIntent} showDetails />
                        )}
                        <UserPreferences
                            preferences={userPreferences}
                            onPreferencesChange={updatePreferences}
                            onSave={savePreferences}
                            onReset={resetPreferences}
                            onClearHistory={clearQueryHistory}
                            onExport={exportPreferences}
                            onImport={importPreferences}
                            loading={preferencesLoading}
                            hasChanges={preferencesHasChanges}
                        />
                        <ApprovalNotification
                            notifications={notifications}
                            pendingCount={notifications.filter(n => !n.read).length}
                            onMarkAsRead={(notificationId) => {
                                setNotifications(prev =>
                                    prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
                                );
                            }}
                            onApproveAll={async () => {
                                const pendingNotifications = notifications.filter(n => !n.read);
                                for (const notif of pendingNotifications) {
                                    try {
                                        await conversationsApi.approveAction({
                                            approval_id: notif.approval_id,
                                            action: 'approve',
                                            reason: 'Bulk approved',
                                        });
                                    } catch (err) {
                                        console.error(`Failed to approve ${notif.approval_id}:`, err);
                                    }
                                }
                                setNotifications([]);
                            }}
                            onViewApproval={(approvalId) => {
                                const fetchApproval = async () => {
                                    try {
                                        const approval = await conversationsApi.getApproval(approvalId);
                                        setApprovalModal({ isOpen: true, approval });
                                    } catch (err) {
                                        console.error('Failed to fetch approval:', err);
                                    }
                                };
                                fetchApproval();
                            }}
                            onTogglePreferences={() => {
                                setNotificationPreferences(prev => ({
                                    ...prev,
                                    in_app_enabled: !prev.in_app_enabled,
                                }));
                            }}
                            preferences={notificationPreferences}
                        />
                    </div>
                </div>

                {/* Cluster error toast */}
                {clusterError && (
                    <div className="mt-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                        {clusterError}
                    </div>
                )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4">
                <div className="max-w-4xl mx-auto">
                    <ConversationTimeline
                        messages={messages}
                        showTimestamps
                    />

                    {/* Workflow Progress Display */}
                    {workflowExecution && (
                        <div className="mt-4">
                            <WorkflowProgress
                                workflowExecution={workflowExecution}
                                expandedStepId={expandedStepId}
                                onStepClick={handleStepClick}
                                showControls={true}
                                onControlAction={handleWorkflowControlAction}
                                autoScroll={true}
                            />
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Error banner */}
            {error && (
                <div className="bg-red-50 border-t border-red-200 px-4 py-3">
                    <div className="max-w-4xl mx-auto flex items-center justify-between">
                        <span className="text-sm text-red-700">{error}</span>
                        <button
                            onClick={() => setError(null)}
                            className="text-red-500 hover:text-red-700"
                        >
                            Dismiss
                        </button>
                    </div>
                </div>
            )}

            {/* Input area */}
            <div className="bg-white border-t p-4">
                <div className="max-w-4xl mx-auto">
                    <form onSubmit={handleSubmit} className="relative">
                        <textarea
                            ref={inputRef}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask about your infrastructure..."
                            className="w-full px-4 py-3 pr-12 border rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                            rows={3}
                            disabled={isLoading || isStreaming}
                        />
                        <button
                            type="submit"
                            disabled={!input.trim() || isLoading || isStreaming}
                            className="absolute right-3 bottom-3 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {isLoading || isStreaming ? (
                                <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                </svg>
                            ) : (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                                </svg>
                            )}
                        </button>
                    </form>
                    <p className="mt-2 text-xs text-gray-500 text-center">
                        AI can make mistakes. Review changes before execution.
                    </p>
                </div>
            </div>

            {/* Approval Modal */}
            <ApprovalModal
                isOpen={approvalModal.isOpen}
                approval={approvalModal.approval}
                onApprove={handleApprovalApprove}
                onReject={handleApprovalReject}
                onClose={() => setApprovalModal({ isOpen: false, approval: null })}
                onEscalate={handleApprovalEscalate}
            />
        </div>
    );
};

export default ChatInterface;
