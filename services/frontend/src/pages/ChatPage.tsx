import { useState, useRef, useEffect } from 'react';
import { Send, Plus, ChevronRight, ExternalLink, Play, CheckCircle, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { Button, Input, Badge, Spinner } from '@/components/ui';
import { useChatStore } from '@/stores';
import { cn, formatDate, generateId } from '@/utils';
import type { Message, Source, Action } from '@/types';

const suggestions = [
  'Check pod status in production namespace',
  'Scale deployment to 3 replicas',
  'Analyze CPU usage trends',
  'List failed deployments',
];

export default function ChatPage() {
  const { sessions, currentSession, createSession, addMessage, updateMessage, setLoading } = useChatStore();
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentSession?.messages]);

  useEffect(() => {
    if (!currentSession && sessions.length === 0) {
      createSession();
    }
  }, []);

  const handleSend = async () => {
    if (!input.trim() || !currentSession || isStreaming) return;

    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    addMessage(currentSession.id, userMessage);
    setInput('');
    setIsStreaming(true);
    setLoading(true);

    const assistantMessage: Message = {
      id: generateId(),
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
    };

    addMessage(currentSession.id, assistantMessage);

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSession.id,
          content: input.trim(),
        }),
      });

      if (!response.ok) throw new Error('Failed to send message');

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              setIsStreaming(false);
              setLoading(false);
              updateMessage(currentSession.id, assistantMessage.id, {
                isStreaming: false,
              });
              break;
            }

            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                fullContent += parsed.content;
                updateMessage(currentSession.id, assistantMessage.id, {
                  content: fullContent,
                });
              }
              if (parsed.sources) {
                updateMessage(currentSession.id, assistantMessage.id, {
                  sources: parsed.sources,
                });
              }
              if (parsed.actions) {
                updateMessage(currentSession.id, assistantMessage.id, {
                  actions: parsed.actions,
                });
              }
            } catch {
              // Ignore parsing errors for non-JSON lines
            }
          }
        }
      }
    } catch (error) {
      toast.error('Failed to send message');
      setIsStreaming(false);
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold">Chat</h1>
          <p className="text-sm text-muted-foreground">
            Ask about your infrastructure or execute operations
          </p>
        </div>
        <Button onClick={createSession} variant="outline" size="sm">
          <Plus className="mr-2 h-4 w-4" />
          New Chat
        </Button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-4">
        {!currentSession || currentSession.messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center space-y-4">
            <div className="text-center">
              <h3 className="text-lg font-semibold">How can I help you today?</h3>
              <p className="text-sm text-muted-foreground">
                Ask about your infrastructure or execute operations
              </p>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setInput(suggestion);
                    inputRef.current?.focus();
                  }}
                  className="flex items-center justify-between rounded-md border p-3 text-left text-sm transition-colors hover:bg-accent"
                >
                  {suggestion}
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {currentSession.messages.map((message) => (
              <MessageItem key={message.id} message={message} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t pt-4">
        <div className="flex items-center space-x-2">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your infrastructure..."
            disabled={isStreaming}
            className="flex-1"
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            size="icon"
          >
            {isStreaming ? (
              <Spinner size="sm" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

function MessageItem({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex w-full',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-3',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted'
        )}
      >
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <p className={cn('whitespace-pre-wrap', message.isStreaming && 'streaming-cursor')}>
            {message.content || (message.isStreaming ? '' : '...')}
          </p>
        </div>

        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-3 border-t pt-2">
            <p className="text-xs font-medium text-muted-foreground mb-2">Sources:</p>
            <div className="flex flex-wrap gap-2">
              {message.sources.map((source) => (
                <SourceBadge key={source.id} source={source} />
              ))}
            </div>
          </div>
        )}

        {!isUser && message.actions && message.actions.length > 0 && (
          <div className="mt-3 border-t pt-2">
            <p className="text-xs font-medium text-muted-foreground mb-2">Actions:</p>
            <div className="space-y-2">
              {message.actions.map((action) => (
                <ActionBadge key={action.id} action={action} />
              ))}
            </div>
          </div>
        )}

        <p className={cn(
          'mt-1 text-xs',
          isUser ? 'text-primary-foreground/70' : 'text-muted-foreground'
        )}>
          {formatDate(message.timestamp)}
        </p>
      </div>
    </div>
  );
}

function SourceBadge({ source }: { source: Source }) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 rounded-md bg-secondary px-2 py-1 text-xs hover:bg-secondary/80"
    >
      <ExternalLink className="h-3 w-3" />
      {source.title}
      <span className="text-muted-foreground">
        ({Math.round(source.relevance * 100)}%)
      </span>
    </a>
  );
}

function ActionBadge({ action }: { action: Action }) {
  const statusIcons = {
    pending: <Play className="h-3 w-3" />,
    approved: <CheckCircle className="h-3 w-3" />,
    rejected: <XCircle className="h-3 w-3" />,
    executing: <Spinner size="sm" />,
    completed: <CheckCircle className="h-3 w-3" />,
    failed: <XCircle className="h-3 w-3" />,
  };

  return (
    <div className="flex items-center gap-2 rounded-md border p-2 text-sm">
      {statusIcons[action.status]}
      <span className="font-medium">{action.name}</span>
      <Badge variant={action.requiresApproval ? 'warning' : 'default'} size="sm">
        {action.requiresApproval ? 'Approval Required' : 'Auto'}
      </Badge>
    </div>
  );
}
