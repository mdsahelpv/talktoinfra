import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Search,
    MessageSquare,
    LayoutDashboard,
    Server,
    Play,
    CheckCircle,
    Settings,
    Bell,
    Workflow,
    CreditCard,
    HelpCircle,
    X
} from 'lucide-react';
import Dialog from '@/components/ui/Dialog';
import Button from '@/components/ui/Button';
import { cn } from '@/utils';

export interface CommandItem {
    id: string;
    title: string;
    description?: string;
    icon: React.ReactNode;
    action: () => void;
    category: string;
    keywords?: string[];
}

interface CommandPaletteProps {
    items?: CommandItem[];
}

export function CommandPalette({ items: customItems }: CommandPaletteProps) {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const [search, setSearch] = useState('');
    const [selectedIndex, setSelectedIndex] = useState(0);

    const defaultItems: CommandItem[] = useMemo(() => [
        {
            id: 'chat',
            title: 'Chat',
            description: 'Ask questions about your infrastructure',
            icon: <MessageSquare className="w-4 h-4" />,
            action: () => { navigate('/chat'); setOpen(false); },
            category: 'Navigation',
            keywords: ['query', 'ask', 'ai', 'conversation'],
        },
        {
            id: 'dashboard',
            title: 'Dashboard',
            description: 'View infrastructure overview',
            icon: <LayoutDashboard className="w-4 h-4" />,
            action: () => { navigate('/dashboard'); setOpen(false); },
            category: 'Navigation',
            keywords: ['home', 'overview', 'stats'],
        },
        {
            id: 'infra',
            title: 'Infrastructure',
            description: 'Browse discovered resources',
            icon: <Server className="w-4 h-4" />,
            action: () => { navigate('/infra'); setOpen(false); },
            category: 'Navigation',
            keywords: ['servers', 'clusters', 'resources', 'discovered'],
        },
        {
            id: 'actions',
            title: 'Actions',
            description: 'View and manage actions',
            icon: <Play className="w-4 h-4" />,
            action: () => { navigate('/actions'); setOpen(false); },
            category: 'Navigation',
            keywords: ['execute', 'run', 'tasks'],
        },
        {
            id: 'approvals',
            title: 'Approvals',
            description: 'Review pending approvals',
            icon: <CheckCircle className="w-4 h-4" />,
            action: () => { navigate('/approvals'); setOpen(false); },
            category: 'Navigation',
            keywords: ['approve', 'reject', 'pending'],
        },
        {
            id: 'monitoring',
            title: 'Monitoring',
            description: 'View alerts and metrics',
            icon: <Bell className="w-4 h-4" />,
            action: () => { navigate('/monitoring'); setOpen(false); },
            category: 'Navigation',
            keywords: ['alerts', 'health', 'metrics'],
        },
        {
            id: 'workflows',
            title: 'Workflows',
            description: 'Manage workflow templates',
            icon: <Workflow className="w-4 h-4" />,
            action: () => { navigate('/workflows'); setOpen(false); },
            category: 'Navigation',
            keywords: ['automation', 'templates', 'runbook'],
        },
        {
            id: 'cost',
            title: 'Cost Management',
            description: 'View costs and optimization',
            icon: <CreditCard className="w-4 h-4" />,
            action: () => { navigate('/cost'); setOpen(false); },
            category: 'Navigation',
            keywords: ['budget', 'spending', 'optimization'],
        },
        {
            id: 'settings',
            title: 'Settings',
            description: 'Configure application settings',
            icon: <Settings className="w-4 h-4" />,
            action: () => { navigate('/settings'); setOpen(false); },
            category: 'Navigation',
            keywords: ['config', 'preferences', 'configure'],
        },
        {
            id: 'help',
            title: 'Help & Documentation',
            description: 'Get help using TalkAI',
            icon: <HelpCircle className="w-4 h-4" />,
            action: () => {
                setOpen(false);
            },
            category: 'Support',
            keywords: ['docs', 'documentation', 'guide'],
        },
    ], [navigate]);

    const items = customItems || defaultItems;

    const filteredItems = useMemo(() => {
        if (!search.trim()) return items;

        const searchLower = search.toLowerCase();
        return items.filter(item =>
            item.title.toLowerCase().includes(searchLower) ||
            item.description?.toLowerCase().includes(searchLower) ||
            item.category.toLowerCase().includes(searchLower) ||
            item.keywords?.some(k => k.toLowerCase().includes(searchLower))
        );
    }, [items, search]);

    const groupedItems = useMemo(() => {
        const groups: Record<string, CommandItem[]> = {};
        filteredItems.forEach(item => {
            if (!groups[item.category]) {
                groups[item.category] = [];
            }
            groups[item.category].push(item);
        });
        return groups;
    }, [filteredItems]);

    // Handle keyboard shortcut
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                setOpen(true);
            }
            if (e.key === 'Escape') {
                setOpen(false);
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, []);

    // Reset selection when search changes
    useEffect(() => {
        setSelectedIndex(0);
    }, [search]);

    const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setSelectedIndex(prev => Math.min(prev + 1, filteredItems.length - 1));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setSelectedIndex(prev => Math.max(prev - 1, 0));
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (filteredItems[selectedIndex]) {
                filteredItems[selectedIndex].action();
            }
        }
    }, [filteredItems, selectedIndex]);

    return (
        <>
            {/* Trigger Button */}
            <Button
                variant="outline"
                className="relative h-9 w-full justify-start rounded-md px-3 text-sm text-muted-foreground sm:pr-12 sm:w-64 lg:w-80"
                onClick={() => setOpen(true)}
            >
                <Search className="mr-2 h-4 w-4" />
                <span className="hidden lg:inline-flex">Search commands...</span>
                <span className="inline-flex lg:hidden">Search...</span>
                <kbd className="pointer-events-none absolute right-1.5 top-1.5 hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
                    <span className="text-xs">⌘</span>K
                </kbd>
            </Button>

            {/* Dialog */}
            <Dialog open={open} onClose={() => setOpen(false)} className="max-w-xl p-0">
                {/* Search Input */}
                <div className="flex items-center border-b px-3">
                    <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                    <input
                        className="flex h-11 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
                        placeholder="Type a command or search..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        onKeyDown={handleKeyDown}
                        autoFocus
                    />
                </div>

                {/* Results */}
                <div className="max-h-[300px] overflow-y-auto p-2">
                    {filteredItems.length === 0 ? (
                        <div className="py-6 text-center text-sm text-muted-foreground">
                            No results found.
                        </div>
                    ) : (
                        Object.entries(groupedItems).map(([category, categoryItems]) => (
                            <div key={category} className="mb-2">
                                <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
                                    {category}
                                </div>
                                {categoryItems.map((item) => {
                                    const globalIndex = filteredItems.indexOf(item);
                                    return (
                                        <button
                                            key={item.id}
                                            className={cn(
                                                'relative flex w-full items-center rounded-sm px-2 py-2 text-sm outline-none transition-colors',
                                                globalIndex === selectedIndex
                                                    ? 'bg-accent text-accent-foreground'
                                                    : 'text-foreground hover:bg-accent hover:text-accent-foreground'
                                            )}
                                            onClick={() => item.action()}
                                            onMouseEnter={() => setSelectedIndex(globalIndex)}
                                        >
                                            <span className="mr-2 flex h-5 w-5 items-center justify-center">
                                                {item.icon}
                                            </span>
                                            <div className="flex flex-col items-start">
                                                <span>{item.title}</span>
                                                {item.description && (
                                                    <span className="text-xs text-muted-foreground">
                                                        {item.description}
                                                    </span>
                                                )}
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        ))
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between border-t px-4 py-2 text-xs text-muted-foreground">
                    <div className="flex gap-4">
                        <span className="flex items-center gap-1">
                            <kbd className="rounded bg-muted px-1">↑↓</kbd> Navigate
                        </span>
                        <span className="flex items-center gap-1">
                            <kbd className="rounded bg-muted px-1">↵</kbd> Select
                        </span>
                        <span className="flex items-center gap-1">
                            <kbd className="rounded bg-muted px-1">esc</kbd> Close
                        </span>
                    </div>
                </div>
            </Dialog>
        </>
    );
}

export default CommandPalette;
