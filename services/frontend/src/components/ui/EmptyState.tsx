import { ReactNode } from 'react';
import Button from '@/components/ui/Button';
import { cn } from '@/utils';
import {
    Search,
    Server,
    MessageSquare,
    Bell,
    Workflow,
    CreditCard,
    FolderOpen,
    Plus,
    ArrowRight
} from 'lucide-react';

export interface EmptyStateProps {
    icon?: 'search' | 'server' | 'chat' | 'bell' | 'workflow' | 'cost' | 'folder' | 'custom';
    title: string;
    description: string;
    action?: {
        label: string;
        onClick: () => void;
    };
    secondaryAction?: {
        label: string;
        onClick: () => void;
    };
    customIcon?: ReactNode;
    className?: string;
}

const iconMap = {
    search: Search,
    server: Server,
    chat: MessageSquare,
    bell: Bell,
    workflow: Workflow,
    cost: CreditCard,
    folder: FolderOpen,
    custom: null,
};

export function EmptyState({
    icon = 'folder',
    title,
    description,
    action,
    secondaryAction,
    customIcon,
    className
}: EmptyStateProps) {
    const IconComponent = iconMap[icon] || FolderOpen;

    return (
        <div className={cn(
            'flex flex-col items-center justify-center py-12 px-4 text-center',
            className
        )}>
            <div className="rounded-full bg-muted p-4 mb-4">
                {customIcon ? (
                    customIcon
                ) : (
                    <IconComponent className="h-8 w-8 text-muted-foreground" />
                )}
            </div>

            <h3 className="text-lg font-semibold text-foreground mb-2">
                {title}
            </h3>

            <p className="text-sm text-muted-foreground max-w-md mb-6">
                {description}
            </p>

            <div className="flex flex-col sm:flex-row gap-3">
                {action && (
                    <Button onClick={action.onClick} className="gap-2">
                        <Plus className="h-4 w-4" />
                        {action.label}
                    </Button>
                )}
                {secondaryAction && (
                    <Button
                        variant="outline"
                        onClick={secondaryAction.onClick}
                        className="gap-2"
                    >
                        {secondaryAction.label}
                        <ArrowRight className="h-4 w-4" />
                    </Button>
                )}
            </div>
        </div>
    );
}

// Pre-configured empty states for common scenarios
export function EmptyInfrastructure() {
    return (
        <EmptyState
            icon="server"
            title="No Infrastructure Discovered"
            description="Connect a Kubernetes cluster to start discovering and managing your infrastructure resources."
            action={{
                label: 'Connect Cluster',
                onClick: () => window.location.href = '/onboarding',
            }}
            secondaryAction={{
                label: 'Learn More',
                onClick: () => window.location.href = '/welcome',
            }}
        />
    );
}

export function EmptyChat() {
    return (
        <EmptyState
            icon="chat"
            title="Start a Conversation"
            description="Ask questions about your infrastructure in natural language. Try asking things like 'What pods are running?' or 'Show me all services'."
            action={{
                label: 'Ask a Question',
                onClick: () => {
                    const input = document.querySelector('input[type="text"]') as HTMLInputElement;
                    if (input) input.focus();
                },
            }}
        />
    );
}

export function EmptyAlerts() {
    return (
        <EmptyState
            icon="bell"
            title="No Active Alerts"
            description="Your infrastructure is healthy! Set up monitoring alerts to get notified about issues."
            action={{
                label: 'Configure Alerts',
                onClick: () => window.location.href = '/monitoring',
            }}
        />
    );
}

export function EmptyWorkflows() {
    return (
        <EmptyState
            icon="workflow"
            title="No Workflows Yet"
            description="Create automated workflows to manage your infrastructure. Start with a template or build from scratch."
            action={{
                label: 'Create Workflow',
                onClick: () => window.location.href = '/workflows',
            }}
        />
    );
}

export function EmptyActions() {
    return (
        <EmptyState
            icon="search"
            title="No Pending Actions"
            description="All caught up! When you request actions through chat, they'll appear here for approval."
            action={{
                label: 'Go to Chat',
                onClick: () => window.location.href = '/chat',
            }}
        />
    );
}

export function EmptySearch({ onClear }: { onClear?: () => void }) {
    return (
        <EmptyState
            icon="search"
            title="No Results Found"
            description="We couldn't find anything matching your search. Try different keywords or filters."
            action={onClear ? {
                label: 'Clear Search',
                onClick: onClear,
            } : undefined}
        />
    );
}

export default EmptyState;
