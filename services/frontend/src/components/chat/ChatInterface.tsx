import React, { useState, useRef, useEffect } from 'react';
import type { Conversation, ConversationMessage, ActionApproval, ApprovalNotification as ApprovalNotificationType, NotificationPreferences } from '@/types/conversation';
import { conversationsApi } from '@/api/conversations';
import { ConversationTimeline } from './ConversationTimeline';
import { IntentIndicator } from './IntentIndicator';
import { ApprovalModal } from './ApprovalModal';
import ApprovalNotification from './ApprovalNotification';

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
    const [isStreaming, setIsStreaming] = useState(false);
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

    // Poll for pending approvals
    useEffect(() => {
        const fetchPendingApprovals = async () => {
            try {
                const pendingApprovals = await conversationsApi.listPendingApprovals();
                // Convert approvals to notifications
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

                // Play sound if new notifications and sound is enabled
                if (newNotifications.length > 0 && notificationPreferences.sound_enabled) {
                    // Sound notification would be played here
                }
            } catch (err) {
                console.error('Failed to fetch pending approvals:', err);
            }
        };

        fetchPendingApprovals();
        const interval = setInterval(fetchPendingApprovals, 30000); // Poll every 30 seconds

        return () => clearInterval(interval);
    }, [notificationPreferences.sound_enabled]);

    // Handlers for notifications
    const handleMarkAsRead = (notificationId: string): void => {
        setNotifications((prev) =>
            prev.map((n) => (n.id === notificationId ? { ...n, read: true } : n))
        );
    };

    const handleApproveAll = async (): Promise<void> => {
        const pendingNotifications = notifications.filter((n) => !n.read);
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
    };

    const handleViewApproval = (approvalId: string): void => {
        // Open the approval modal for the specific approval
        const fetchApproval = async () => {
            try {
                const approval = await conversationsApi.getApproval(approvalId);
                setApprovalModal({ isOpen: true, approval });
            } catch (err) {
                console.error('Failed to fetch approval:', err);
            }
        };
        fetchApproval();
    };

    const handleTogglePreferences = (): void => {
        // Toggle notification preferences panel
        setNotificationPreferences((prev) => ({
            ...prev,
            in_app_enabled: !prev.in_app_enabled,
        }));
    };

    const pendingCount = notifications.filter((n) => !n.read).length;

    // Refs
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Initialize conversation
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

            // Check if approval is needed
            if (response.intent.requires_approval && response.intent.intent === 'ACTION') {
                // Create approval request
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

            // Update conversation state
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

            // Add system message about approval
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

            // Add system message about rejection
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
        // This would call an API endpoint to escalate
    };

    const latestAssistantMessage = [...messages].reverse().find(m => m.role === 'assistant');
    const latestIntent = latestAssistantMessage?.intent;

    return (
        <div className="flex flex-col h-full bg-gray-50">
            {/* Header */}
            <div className="bg-white border-b px-4 py-3">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-lg font-semibold text-gray-900">AI Assistant</h1>
                        <p className="text-sm text-gray-500">
                            {conversation?.title || 'New Conversation'}
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        {latestIntent && (
                            <IntentIndicator intent={latestIntent} showDetails />
                        )}
                        <ApprovalNotification
                            notifications={notifications}
                            pendingCount={pendingCount}
                            onMarkAsRead={handleMarkAsRead}
                            onApproveAll={handleApproveAll}
                            onViewApproval={handleViewApproval}
                            onTogglePreferences={handleTogglePreferences}
                            preferences={notificationPreferences}
                        />
                    </div>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4">
                <div className="max-w-4xl mx-auto">
                    <ConversationTimeline
                        messages={messages}
                        showTimestamps
                    />
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
