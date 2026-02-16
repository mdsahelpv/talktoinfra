import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Play, Plus, ChevronLeft, ChevronRight, Search, Filter } from 'lucide-react';
import { workflowApi } from '@/api/workflow';
import { Card, CardContent, Button, Badge, Spinner, Input } from '@/components/ui';
import { formatDate } from '@/utils';
import type { Workflow, WorkflowStatus } from '@/types';

const statusFilters: (WorkflowStatus | 'all')[] = ['all', 'draft', 'active', 'paused', 'archived'];

export default function WorkflowDashboard() {
    const [page, setPage] = useState(1);
    const [statusFilter, setStatusFilter] = useState<WorkflowStatus | 'all'>('all');
    const [searchQuery, setSearchQuery] = useState('');

    const { data, isLoading, error } = useQuery({
        queryKey: ['workflows', page, statusFilter],
        queryFn: () => workflowApi.listWorkflows({ page, limit: 10, status: statusFilter === 'all' ? undefined : statusFilter }),
    });

    const queryClient = useQueryClient();

    const executeMutation = useMutation({
        mutationFn: (id: string) => workflowApi.executeWorkflowAsync(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['executions'] });
        },
    });

    const handleExecute = async (workflowId: string) => {
        try {
            await executeMutation.mutateAsync(workflowId);
        } catch (error) {
            console.error('Failed to execute workflow:', error);
        }
    };

    const filteredWorkflows = data?.items?.filter((workflow) =>
        workflow.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        workflow.description?.toLowerCase().includes(searchQuery.toLowerCase())
    ) || [];

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Spinner size="lg" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center py-12">
                <p className="text-red-500">Error loading workflows</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">Workflows</h1>
                    <p className="text-sm text-muted-foreground">
                        Manage and execute multi-step infrastructure workflows
                    </p>
                </div>
                <Button onClick={() => window.location.href = '/workflows/new'}>
                    <Plus className="mr-2 h-4 w-4" />
                    Create Workflow
                </Button>
            </div>

            {/* Filters */}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                        placeholder="Search workflows..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-9"
                    />
                </div>
                <div className="flex items-center gap-2 overflow-x-auto pb-2 sm:pb-0">
                    <Filter className="h-4 w-4 text-muted-foreground shrink-0" />
                    {statusFilters.map((status) => (
                        <Button
                            key={status}
                            variant={statusFilter === status ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setStatusFilter(status)}
                            className="capitalize whitespace-nowrap"
                        >
                            {status}
                        </Button>
                    ))}
                </div>
            </div>

            {/* Workflow List */}
            {filteredWorkflows.length > 0 ? (
                <div className="space-y-4">
                    {filteredWorkflows.map((workflow) => (
                        <WorkflowCard
                            key={workflow.id}
                            workflow={workflow}
                            onExecute={() => handleExecute(workflow.id)}
                            isExecuting={executeMutation.isPending && executeMutation.variables === workflow.id}
                        />
                    ))}
                </div>
            ) : (
                <div className="text-center py-12">
                    <div className="mx-auto h-12 w-12 text-muted-foreground" />
                    <h3 className="mt-4 text-lg font-semibold">No workflows found</h3>
                    <p className="text-sm text-muted-foreground">
                        {searchQuery ? 'Try adjusting your search query' : 'Create your first workflow to get started'}
                    </p>
                    {!searchQuery && (
                        <Button className="mt-4" onClick={() => window.location.href = '/workflows/new'}>
                            <Plus className="mr-2 h-4 w-4" />
                            Create Workflow
                        </Button>
                    )}
                </div>
            )}

            {/* Pagination */}
            {data && data.pages > 1 && (
                <div className="flex items-center justify-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                    >
                        <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="text-sm text-muted-foreground">
                        Page {page} of {data.pages}
                    </span>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(p => p + 1)}
                        disabled={page >= data.pages}
                    >
                        <ChevronRight className="h-4 w-4" />
                    </Button>
                </div>
            )}
        </div>
    );
}

interface WorkflowCardProps {
    workflow: Workflow;
    onExecute: () => void;
    isExecuting: boolean;
}

function WorkflowCard({ workflow, onExecute, isExecuting }: WorkflowCardProps) {
    const [expanded, setExpanded] = useState(false);

    const statusConfig: Record<WorkflowStatus, { variant: 'default' | 'secondary' | 'destructive' | 'warning'; label: string }> = {
        draft: { variant: 'secondary', label: 'Draft' },
        active: { variant: 'default', label: 'Active' },
        paused: { variant: 'warning', label: 'Paused' },
        archived: { variant: 'secondary', label: 'Archived' },
    };

    const config = statusConfig[workflow.status];

    return (
        <Card className="overflow-hidden">
            <CardContent className="p-0">
                <div
                    className="flex items-center gap-4 p-4 cursor-pointer hover:bg-accent/50"
                    onClick={() => setExpanded(!expanded)}
                >
                    <div className="rounded-full bg-primary/10 p-2">
                        <Play className="h-4 w-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                            <h3 className="font-semibold truncate">{workflow.name}</h3>
                            <Badge variant={config.variant}>{config.label}</Badge>
                            <span className="text-xs text-muted-foreground">v{workflow.version}</span>
                        </div>
                        {workflow.description && (
                            <p className="text-sm text-muted-foreground truncate">
                                {workflow.description}
                            </p>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground hidden sm:block">
                            {formatDate(workflow.created_at)}
                        </span>
                        <Badge variant="outline">{workflow.steps.length} steps</Badge>
                    </div>
                </div>

                {expanded && (
                    <div className="border-t px-4 py-4 space-y-4">
                        <div className="grid gap-4 sm:grid-cols-3">
                            <div>
                                <p className="text-sm font-medium text-muted-foreground">Created</p>
                                <p>{formatDate(workflow.created_at)}</p>
                            </div>
                            <div>
                                <p className="text-sm font-medium text-muted-foreground">Updated</p>
                                <p>{formatDate(workflow.updated_at)}</p>
                            </div>
                            <div>
                                <p className="text-sm font-medium text-muted-foreground">Steps</p>
                                <div className="flex gap-1 mt-1">
                                    {workflow.steps.slice(0, 5).map((step, index) => (
                                        <Badge key={step.id} variant="outline" className="text-xs">
                                            {index + 1}. {step.name}
                                        </Badge>
                                    ))}
                                    {workflow.steps.length > 5 && (
                                        <Badge variant="outline" className="text-xs">
                                            +{workflow.steps.length - 5} more
                                        </Badge>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="flex gap-2">
                            <Button
                                size="sm"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    window.location.href = `/workflows/${workflow.id}`;
                                }}
                            >
                                View Details
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onExecute();
                                }}
                                disabled={workflow.status !== 'active' || isExecuting}
                            >
                                {isExecuting ? (
                                    <>
                                        <Spinner size="sm" className="mr-2" />
                                        Executing...
                                    </>
                                ) : (
                                    <>
                                        <Play className="mr-2 h-4 w-4" />
                                        Execute
                                    </>
                                )}
                            </Button>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
