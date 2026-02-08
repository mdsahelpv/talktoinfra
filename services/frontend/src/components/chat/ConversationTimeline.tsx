import React from 'react';
import type { ConversationMessage, ConversationState } from '@/types/conversation';
import { STATE_ICONS } from '@/types/conversation';
import { SourcesDisplay } from './SourcesDisplay';
import type { SourceCitation } from '@/types';

interface ConversationTimelineProps {
    messages: ConversationMessage[];
    currentMessageId?: string;
    showTimestamps?: boolean;
    maxMessages?: number;
}

const ROLE_STYLES: Record<string, { bg: string; border: string; avatar: string }> = {
    user: {
        bg: 'bg-blue-50',
        border: 'border-blue-200',
        avatar: '👤',
    },
    assistant: {
        bg: 'bg-white',
        border: 'border-gray-200',
        avatar: '🤖',
    },
    system: {
        bg: 'bg-yellow-50',
        border: 'border-yellow-200',
        avatar: '⚙️',
    },
};

const ROLE_LABELS: Record<string, string> = {
    user: 'You',
    assistant: 'Assistant',
    system: 'System',
};

const formatTimestamp = (timestamp: string) => {
    try {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
        return '';
    }
};

export const ConversationTimeline: React.FC<ConversationTimelineProps> = ({
    messages,
    currentMessageId,
    showTimestamps = true,
    maxMessages,
}) => {
    const displayMessages = maxMessages ? messages.slice(-maxMessages) : messages;

    if (displayMessages.length === 0) {
        return (
            <div className="text-center py-8 text-gray-500">
                <span className="text-4xl mb-2 block">💬</span>
                <p>No messages yet. Start a conversation!</p>
            </div>
        );
    }

    return (
        <div className="relative">
            {/* Timeline connector */}
            <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200" />

            <div className="space-y-4">
                {displayMessages.map((message, index) => {
                    const isCurrent = message.id === currentMessageId;
                    const isLast = index === displayMessages.length - 1;
                    const roleStyle = ROLE_STYLES[message.role] || ROLE_STYLES.assistant;

                    return (
                        <div key={message.id} className="relative flex gap-4">
                            {/* Avatar */}
                            <div
                                className={`relative z-10 flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-lg ${roleStyle.bg} border ${roleStyle.border}`}
                            >
                                {roleStyle.avatar}
                                {isLast && (
                                    <span className="absolute -bottom-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white" />
                                )}
                            </div>

                            {/* Message content */}
                            <div className={`flex-1 min-w-0 ${isCurrent ? 'ring-2 ring-blue-400 rounded-lg' : ''}`}>
                                {/* Header */}
                                <div className="flex items-center gap-2 mb-1">
                                    <span className="font-medium text-gray-900">{ROLE_LABELS[message.role]}</span>
                                    {showTimestamps && (
                                        <span className="text-xs text-gray-500">
                                            {formatTimestamp(message.timestamp)}
                                        </span>
                                    )}
                                </div>

                                {/* Content */}
                                <div
                                    className={`p-4 rounded-lg ${roleStyle.bg} border ${roleStyle.border}`}
                                >
                                    {message.role === 'assistant' ? (
                                        <div className="prose prose-sm max-w-none">
                                            <div className="whitespace-pre-wrap">{message.content}</div>
                                        </div>
                                    ) : (
                                        <div className="whitespace-pre-wrap text-gray-900">{message.content}</div>
                                    )}
                                </div>

                                {/* Sources */}
                                {message.sources && message.sources.length > 0 && (
                                    <SourcesDisplay
                                        sources={message.sources as SourceCitation[]}
                                        className="mt-3"
                                    />
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

// Compact version for sidebar/preview
export const ConversationPreview: React.FC<{
    messages: ConversationMessage[];
    state: ConversationState;
    onClick?: () => void;
}> = ({ messages, state, onClick }) => {
    const lastMessage = messages[messages.length - 1];
    const preview = lastMessage?.content.slice(0, 80) || 'New conversation';

    return (
        <button
            onClick={onClick}
            className="w-full text-left p-3 hover:bg-gray-50 rounded-lg transition-colors"
        >
            <div className="flex items-center gap-2 mb-1">
                <span>{STATE_ICONS[state] || '💬'}</span>
                <span className="text-xs text-gray-500">
                    {messages.length} message{messages.length !== 1 ? 's' : ''}
                </span>
            </div>
            <p className="text-sm text-gray-900 truncate">{preview}</p>
        </button>
    );
};

export default ConversationTimeline;
