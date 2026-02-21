import React, { useEffect, useRef } from 'react';
import type { WorkflowExecution, WorkflowStep, WorkflowControlAction } from '@/types/conversation';
import {
    WORKFLOW_STEP_STATUS_CONFIG,
    WORKFLOW_EXECUTION_STATUS_CONFIG,
    WORKFLOW_STEP_TYPE_ICONS,
    formatDuration,
    isWorkflowActive,
} from '@/types/conversation';
import StepDetails from './StepDetails';
import WorkflowControls from './WorkflowControls';

interface WorkflowProgressProps {
    workflowExecution: WorkflowExecution;
    expandedStepId?: string | null;
    onStepClick?: (stepId: string | null) => void;
    showControls?: boolean;
    onControlAction?: (action: WorkflowControlAction, stepId?: string) => void;
    autoScroll?: boolean;
}

const WorkflowProgress: React.FC<WorkflowProgressProps> = ({
    workflowExecution,
    expandedStepId = null,
    onStepClick = () => { },
    showControls = true,
    onControlAction = () => { },
    autoScroll = true,
}) => {
    const progressRef = useRef<HTMLDivElement>(null);
    const { steps, status, progress_percentage, current_step_id, name, description, error } = workflowExecution;

    // Sort steps by order
    const sortedSteps = [...steps].sort((a: WorkflowStep, b: WorkflowStep) => a.order - b.order);

    // Auto-scroll to latest update
    useEffect(() => {
        if (autoScroll && isWorkflowActive(status) && progressRef.current) {
            progressRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
    }, [current_step_id, progress_percentage, autoScroll, status]);

    const statusConfig = WORKFLOW_EXECUTION_STATUS_CONFIG[status];
    const isActive = isWorkflowActive(status);

    return (
        <div
            ref={progressRef}
            className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden"
        >
            {/* Header */}
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <span className={`text-lg ${statusConfig.color}`}>
                            {statusConfig.icon}
                        </span>
                        <div>
                            <h3 className="font-medium text-gray-900">{name}</h3>
                            {description && (
                                <p className="text-sm text-gray-500">{description}</p>
                            )}
                        </div>
                    </div>
                    <div className="flex items-center gap-4">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusConfig.color} bg-opacity-10`}>
                            {statusConfig.label}
                        </span>
                        <span className="text-sm font-medium text-gray-700">
                            {progress_percentage}%
                        </span>
                    </div>
                </div>

                {/* Progress bar */}
                <div className="mt-3 relative">
                    <div className="overflow-hidden h-2 bg-gray-200 rounded-full">
                        <div
                            className={`h-full transition-all duration-500 ${status === 'FAILED' ? 'bg-red-500' :
                                    status === 'COMPLETED' ? 'bg-green-500' : 'bg-blue-500'
                                }`}
                            style={{ width: `${progress_percentage}%` }}
                        />
                    </div>
                </div>

                {/* Error message */}
                {error && (
                    <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                        {error}
                    </div>
                )}
            </div>

            {/* Steps list */}
            <div className="divide-y divide-gray-100">
                {sortedSteps.map((step) => {
                    const stepStatusConfig = WORKFLOW_STEP_STATUS_CONFIG[step.status];
                    const typeIcon = WORKFLOW_STEP_TYPE_ICONS[step.type];
                    const isExpanded = expandedStepId === step.id;
                    const isCurrent = step.id === current_step_id;

                    return (
                        <div
                            key={step.id}
                            className={`${isCurrent && isActive
                                    ? 'bg-blue-50 border-l-4 border-l-blue-500'
                                    : step.status === 'FAILED'
                                        ? 'bg-red-50 border-l-4 border-l-red-500'
                                        : ''
                                }`}
                        >
                            {/* Step header - clickable */}
                            <button
                                onClick={() => onStepClick(isExpanded ? null : step.id)}
                                className="w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition-colors text-left"
                            >
                                {/* Step icon/status */}
                                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${isCurrent && isActive
                                        ? 'bg-blue-100'
                                        : step.status === 'FAILED'
                                            ? 'bg-red-100'
                                            : step.status === 'COMPLETED'
                                                ? 'bg-green-100'
                                                : 'bg-gray-100'
                                    }`}>
                                    <span className={stepStatusConfig.color}>
                                        {stepStatusConfig.icon}
                                    </span>
                                </div>

                                {/* Step info */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm">{typeIcon}</span>
                                        <span className="font-medium text-gray-900 truncate">
                                            Step {step.order}: {step.name}
                                        </span>
                                    </div>
                                    {step.description && (
                                        <p className="text-sm text-gray-500 truncate">
                                            {step.description}
                                        </p>
                                    )}
                                </div>

                                {/* Step status & duration */}
                                <div className="flex items-center gap-3">
                                    {step.duration_ms && (
                                        <span className="text-xs text-gray-500">
                                            {formatDuration(step.duration_ms)}
                                        </span>
                                    )}
                                    <span className={`text-xs ${stepStatusConfig.color}`}>
                                        {stepStatusConfig.label}
                                    </span>
                                    {/* Chevron */}
                                    <svg
                                        className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''
                                            }`}
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        stroke="currentColor"
                                    >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                </div>
                            </button>

                            {/* Expanded step details */}
                            {isExpanded && (
                                <StepDetails
                                    step={step}
                                    isExpanded={isExpanded}
                                    onToggleExpand={() => onStepClick(null)}
                                    showLogs={true}
                                    maxLogs={50}
                                />
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Controls */}
            {showControls && (
                <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
                    <WorkflowControls
                        workflowExecution={workflowExecution}
                        onControlAction={onControlAction}
                    />
                </div>
            )}
        </div>
    );
};

export default WorkflowProgress;
