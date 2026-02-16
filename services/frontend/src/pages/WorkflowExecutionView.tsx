import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Play, XCircle, RotateCcw, Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { workflowApi } from '@/api/workflow';
import { Card, CardContent, CardHeader, Button, Badge, Spinner } from '@/components/ui';
import { formatDate } from '@/utils';
import type { WorkflowExecution, ExecutionStatus } from '@/types';

export default function WorkflowExecutionView() {
    const { executionId } = useParams<{ executionId: string }>();
    const [isPolling, setIsPolling] = useState(true);
    const queryClient = useQueryClient();

    const { data: execution, isLoading, error } = useQuery<WorkflowExecution>({
        queryKey: ['execution', executionId],
        queryFn: () => workflowApi.getExecutionStatus(executionId!),
        enabled: !!executionId,
    });

    // Stop polling when execution is no longer running
    useEffect(() => {
        if (execution?.status && !['running', 'pending'].includes(execution.status)) {
            setIsPolling(false);
        }
    }, [execution?.status]);

    // Poll when running
    useQuery<WorkflowExecution>({
        queryKey: ['execution', executionId],
        queryFn: () => workflowApi.getExecutionStatus(executionId!),
        enabled: !!executionId && isPolling,
        refetchInterval: isPolling && execution?.status === 'running' ? 3000 : false,
    });

    const cancelMutation = useMutation({
        mutationFn: () => workflowApi.cancelExecution(executionId!),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['execution', executionId] });
        },
    });

    const rollbackMutation = useMutation({
        mutationFn: (targetStepId?: string) => workflowApi.rollbackExecution(executionId!, targetStepId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['execution', executionId] });
        },
    });

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Spinner size="lg" />
            </div>
        );
    }

    if (error || !execution) {
        return (
            <div className="text-center py-12">
                <p className="text-red-500">Execution not found</p>
                <Button className="mt-4" variant="outline" onClick={() => window.history.back()}>
                    Go Back
                </Button>
            </div>
        );
    }

    const statusConfig: Record<ExecutionStatus, { variant: 'default' | 'secondary' | 'destructive' | 'warning'; icon: React.ElementType }> = {
        pending: { variant: 'secondary', icon: Clock },
        running: { variant: 'default', icon: Loader2 },
        completed: { variant: 'default', icon: CheckCircle },
        failed: { variant: 'destructive', icon: AlertCircle },
        cancelled: { variant: 'secondary', icon: XCircle },
        rolled_back: { variant: 'warning', icon: RotateCcw },
    };

    const config = statusConfig[execution.status];
    const StatusIcon = config.icon;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => window.history.back()}>
                        <ArrowLeft className="h-4 w-4" />
                    </Button>
                    <div>
                        <h1 className="text-2xl font-bold">Execution Details</h1>
                        <p className="text-sm text-muted-foreground font-mono">{execution.id}</p>
                    </div>
                </div>
                <Badge variant={config.variant} className="flex items-center gap-2">
                    <StatusIcon className={`h-4 w-4 ${execution.status === 'running' ? 'animate-spin' : ''}`} />
                    {execution.status.charAt(0).toUpperCase() + execution.status.slice(1)}
                </Badge>
            </div>

            {/* Execution Info */}
            <Card>
                <CardHeader>
                    <h2 className="text-lg font-semibold">Execution Information</h2>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                        <div>
                            <p className="text-sm font-medium text-muted-foreground">Started</p>
                            <p>{execution.started_at ? formatDate(execution.started_at) : '-'}</p>
                        </div>
                        <div>
                            <p className="text-sm font-medium text-muted-foreground">Completed</p>
                            <p>{execution.completed_at ? formatDate(execution.completed_at) : '-'}</p>
                        </div>
                        <div>
                            <p className="text-sm font-medium text-muted-foreground">Created</p>
                            <p>{formatDate(execution.created_at)}</p>
                        </div>
                        <div>
                            <p className="text-sm font-medium text-muted-foreground">Current Step</p>
                            <p>{execution.current_step_id || '-'}</p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Error Message */}
            {execution.error && (
                <Card className="border-red-200 bg-red-50">
                    <CardContent className="pt-6">
                        <div className="flex items-start gap-3">
                            <AlertCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
                            <div>
                                <h3 className="font-semibold text-red-700">Execution Error</h3>
                                <p className="text-sm text-red-600 mt-1">{execution.error}</p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Execution Timeline */}
            <Card>
                <CardHeader>
                    <h2 className="text-lg font-semibold">Step Timeline</h2>
                </CardHeader>
                <CardContent>
                    {execution.step_history && execution.step_history.length > 0 ? (
                        <div className="space-y-0">
                            {execution.step_history.map((step, index) => (
                                <StepTimelineItem
                                    key={step.id}
                                    step={step}
                                    index={index}
                                    isLast={index === execution.step_history!.length - 1}
                                />
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-8 text-muted-foreground">
                            <Clock className="mx-auto h-8 w-8 mb-2" />
                            <p>No steps have been executed yet</p>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Outputs */}
            {execution.outputs && Object.keys(execution.outputs).length > 0 && (
                <Card>
                    <CardHeader>
                        <h2 className="text-lg font-semibold">Outputs</h2>
                    </CardHeader>
                    <CardContent>
                        <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                            {JSON.stringify(execution.outputs, null, 2)}
                        </pre>
                    </CardContent>
                </Card>
            )}

            {/* Actions */}
            <div className="flex gap-2">
                {execution.status === 'running' && (
                    <Button
                        variant="destructive"
                        onClick={() => cancelMutation.mutate()}
                        disabled={cancelMutation.isPending}
                    >
                        {cancelMutation.isPending ? (
                            <>
                                <Spinner size="sm" className="mr-2" />
                                Cancelling...
                            </>
                        ) : (
                            <>
                                <XCircle className="mr-2 h-4 w-4" />
                                Cancel Execution
                            </>
                        )}
                    </Button>
                )}

                {(execution.status === 'failed' || execution.status === 'cancelled') && (
                    <Button
                        variant="outline"
                        onClick={() => rollbackMutation.mutate(undefined)}
                        disabled={rollbackMutation.isPending}
                    >
                        {rollbackMutation.isPending ? (
                            <>
                                <Spinner size="sm" className="mr-2" />
                                Rolling back...
                            </>
                        ) : (
                            <>
                                <RotateCcw className="mr-2 h-4 w-4" />
                                Rollback
                            </>
                        )}
                    </Button>
                )}

                {execution.status === 'completed' && (
                    <Button
                        variant="outline"
                        onClick={() => window.location.href = `/workflows/${execution.workflow_id}`}
                    >
                        <Play className="mr-2 h-4 w-4" />
                        Re-execute
                    </Button>
                )}
            </div>
        </div>
    );
}

interface StepTimelineItemProps {
    step: {
        id: string;
        step_id: string;
        step_name: string;
        step_type: string;
        status: ExecutionStatus;
        inputs?: Record<string, unknown>;
        outputs?: Record<string, unknown>;
        error?: string;
        started_at?: string;
        completed_at?: string;
    };
    index: number;
    isLast: boolean;
}

function StepTimelineItem({ step, isLast }: StepTimelineItemProps) {
    const statusConfig: Record<ExecutionStatus, { variant: 'default' | 'secondary' | 'destructive' | 'warning'; icon: React.ElementType }> = {
        pending: { variant: 'secondary', icon: Clock },
        running: { variant: 'default', icon: Loader2 },
        completed: { variant: 'default', icon: CheckCircle },
        failed: { variant: 'destructive', icon: AlertCircle },
        cancelled: { variant: 'secondary', icon: XCircle },
        rolled_back: { variant: 'warning', icon: RotateCcw },
    };

    const config = statusConfig[step.status];
    const StatusIcon = config.icon;

    return (
        <div className="flex gap-4">
            <div className="flex flex-col items-center">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${step.status === 'completed' ? 'bg-green-100 text-green-600' :
                    step.status === 'running' ? 'bg-blue-100 text-blue-600' :
                        step.status === 'failed' ? 'bg-red-100 text-red-600' :
                            'bg-gray-100 text-gray-600'
                    }`}>
                    {step.status === 'running' ? (
                        <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                        <StatusIcon className="h-5 w-5" />
                    )}
                </div>
                {!isLast && (
                    <div className="w-0.5 flex-1 bg-gray-200 min-h-[60px]" />
                )}
            </div>
            <div className="flex-1 pb-6">
                <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="font-semibold">{step.step_name}</h4>
                    <Badge variant="outline" className="text-xs">
                        {step.step_type}
                    </Badge>
                    <Badge variant={config.variant} className="text-xs">
                        {step.status}
                    </Badge>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                    Step ID: {step.step_id}
                </p>
                {step.started_at && (
                    <p className="text-xs text-muted-foreground mt-1">
                        Started: {formatDate(step.started_at)}
                    </p>
                )}
                {step.completed_at && (
                    <p className="text-xs text-muted-foreground">
                        Completed: {formatDate(step.completed_at)}
                    </p>
                )}
                {step.error && (
                    <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-600">
                        {step.error}
                    </div>
                )}
                {step.outputs && Object.keys(step.outputs).length > 0 && (
                    <details className="mt-2">
                        <summary className="text-sm cursor-pointer text-muted-foreground hover:text-foreground">
                            View Outputs
                        </summary>
                        <pre className="mt-2 bg-muted p-2 rounded text-xs overflow-x-auto">
                            {JSON.stringify(step.outputs, null, 2)}
                        </pre>
                    </details>
                )}
            </div>
        </div>
    );
}
