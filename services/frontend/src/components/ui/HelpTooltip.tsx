import { useState, ReactNode } from 'react';
import { HelpCircle, X, ExternalLink, MessageSquare, Book, Video, ChevronRight } from 'lucide-react';
import { cn } from '@/utils';
import Dialog from '@/components/ui/Dialog';
import Button from '@/components/ui/Button';

interface HelpItem {
    id: string;
    title: string;
    description: string;
    icon?: ReactNode;
    link?: string;
}

interface HelpSection {
    id: string;
    title: string;
    items: HelpItem[];
}

interface HelpTooltipProps {
    content?: string;
    title?: string;
    sections?: HelpSection[];
    children?: ReactNode;
    className?: string;
}

const defaultHelpSections: HelpSection[] = [
    {
        id: 'getting-started',
        title: 'Getting Started',
        items: [
            {
                id: 'welcome',
                title: 'Welcome Tour',
                description: 'Take a guided tour of TalkAI features',
                link: '/welcome',
            },
            {
                id: 'connect-cluster',
                title: 'Connect a Cluster',
                description: 'Learn how to add your Kubernetes cluster',
                link: '/onboarding',
            },
        ],
    },
    {
        id: 'chat',
        title: 'Using Chat',
        items: [
            {
                id: 'ask-questions',
                title: 'Ask Questions',
                description: 'Natural language queries like "Show me all pods"',
            },
            {
                id: 'actions',
                title: 'Request Actions',
                description: 'Ask AI to perform tasks with approval workflow',
            },
        ],
    },
    {
        id: 'resources',
        title: 'Resources',
        items: [
            {
                id: 'docs',
                title: 'Documentation',
                description: 'Full documentation and API reference',
                link: '#',
            },
            {
                id: 'api',
                title: 'API Reference',
                description: 'Programmatic access to TalkAI',
                link: '#',
            },
        ],
    },
];

export function HelpTooltip({
    content,
    title = 'Help',
    sections = defaultHelpSections,
    children,
    className
}: HelpTooltipProps) {
    const [showDialog, setShowDialog] = useState(false);
    const [activeSection, setActiveSection] = useState(sections[0]?.id || '');

    return (
        <>
            {children ? (
                <div
                    className={cn('cursor-help', className)}
                    onClick={() => setShowDialog(true)}
                >
                    {children}
                </div>
            ) : (
                <Button
                    variant="ghost"
                    size="icon"
                    className={cn('h-8 w-8 rounded-full', className)}
                    onClick={() => setShowDialog(true)}
                >
                    <HelpCircle className="h-4 w-4" />
                </Button>
            )}

            <Dialog
                open={showDialog}
                onClose={() => setShowDialog(false)}
                className="max-w-3xl p-0"
            >
                <div className="flex">
                    {/* Sidebar */}
                    <div className="w-48 border-r bg-muted/30 p-4">
                        <div className="mb-4">
                            <h3 className="font-semibold text-foreground">Help Center</h3>
                            <p className="text-xs text-muted-foreground mt-1">
                                Find answers and learn more
                            </p>
                        </div>
                        <nav className="space-y-1">
                            {sections.map((section) => (
                                <button
                                    key={section.id}
                                    onClick={() => setActiveSection(section.id)}
                                    className={cn(
                                        'w-full flex items-center justify-between px-3 py-2 text-sm rounded-md transition-colors',
                                        activeSection === section.id
                                            ? 'bg-primary text-primary-foreground'
                                            : 'text-muted-foreground hover:bg-muted'
                                    )}
                                >
                                    {section.title}
                                    <ChevronRight className="h-3 w-3" />
                                </button>
                            ))}
                        </nav>
                    </div>

                    {/* Content */}
                    <div className="flex-1 p-6">
                        {sections.map((section) => (
                            <div
                                key={section.id}
                                className={cn(activeSection === section.id ? 'block' : 'hidden')}
                            >
                                <h2 className="text-xl font-semibold mb-4">{section.title}</h2>
                                <div className="space-y-3">
                                    {section.items.map((item) => (
                                        <div
                                            key={item.id}
                                            className={cn(
                                                'p-4 rounded-lg border transition-colors',
                                                item.link
                                                    ? 'hover:bg-muted cursor-pointer'
                                                    : 'bg-muted/30'
                                            )}
                                            onClick={() => {
                                                if (item.link) {
                                                    window.location.href = item.link;
                                                    setShowDialog(false);
                                                }
                                            }}
                                        >
                                            <div className="flex items-start gap-3">
                                                <div className="mt-0.5">
                                                    {item.icon || <MessageSquare className="h-5 w-5 text-muted-foreground" />}
                                                </div>
                                                <div className="flex-1">
                                                    <div className="flex items-center justify-between">
                                                        <h4 className="font-medium">{item.title}</h4>
                                                        {item.link && (
                                                            <ExternalLink className="h-3 w-3 text-muted-foreground" />
                                                        )}
                                                    </div>
                                                    <p className="text-sm text-muted-foreground mt-1">
                                                        {item.description}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}

                        {/* Quick Actions */}
                        <div className="mt-8 pt-6 border-t">
                            <h4 className="text-sm font-medium mb-3">Quick Actions</h4>
                            <div className="flex gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="gap-2"
                                    onClick={() => {
                                        window.location.href = '/welcome';
                                        setShowDialog(false);
                                    }}
                                >
                                    <Book className="h-4 w-4" />
                                    Take Tour
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="gap-2"
                                    onClick={() => {
                                        // Open chat with help message
                                        setShowDialog(false);
                                    }}
                                >
                                    <MessageSquare className="h-4 w-4" />
                                    Ask AI
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>
            </Dialog>
        </>
    );
}

// Contextual help for specific pages
export const PageHelp = {
    chat: (
        <HelpTooltip
            title="Chat Help"
            sections={[
                {
                    id: 'basics',
                    title: 'Basics',
                    items: [
                        { id: 'ask', title: 'Ask Questions', description: 'Type naturally to query your infrastructure' },
                        { id: 'actions', title: 'Request Actions', description: 'Ask to perform tasks like scaling deployments' },
                    ],
                },
                {
                    id: 'examples',
                    title: 'Example Queries',
                    items: [
                        { id: 'pods', title: 'Show pods', description: 'List all pods in a namespace' },
                        { id: 'scale', title: 'Scale deployment', description: 'Scale a deployment to N replicas' },
                        { id: 'logs', title: 'Get logs', description: 'View pod logs in real-time' },
                    ],
                },
            ]}
        />
    ),
    infra: (
        <HelpTooltip
            title="Infrastructure Help"
            sections={[
                {
                    id: 'discovered',
                    title: 'Discovered Resources',
                    items: [
                        { id: 'scan', title: 'Scan Resources', description: 'Run a discovery scan to find resources' },
                        { id: 'manage', title: 'Manage Resources', description: 'Promote discovered resources to managed' },
                    ],
                },
            ]}
        />
    ),
    monitoring: (
        <HelpTooltip
            title="Monitoring Help"
            sections={[
                {
                    id: 'alerts',
                    title: 'Alerts',
                    items: [
                        { id: 'create', title: 'Create Alert', description: 'Set up custom alert rules' },
                        { id: 'channels', title: 'Notification Channels', description: 'Configure email, Slack, PagerDuty' },
                    ],
                },
            ]}
        />
    ),
};

export default HelpTooltip;
