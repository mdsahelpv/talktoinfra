import React, { useState } from 'react';
import type { WorkflowExecution, WorkflowControlAction, WorkflowStep } from '@/types/conversation';
import { isWorkflowActive, getFailedSteps } from '@/types/conversation';

interface WorkflowControlsProps {
    workflowExecution: WorkflowExecution;
    onControlAction: (action: WorkflowControlAction, stepId?: string) => void;
    loading?: boolean;
    disabled?: boolean;
}

const WorkflowControls: React.FC<WorkflowControlsProps> = ({
    workflowExecution,
    onControlAction,
    loading = false,
    disabled = false,
}) => {
    const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
    const { status, current_step_id, steps } = workflowExecution;
    const isActive = isWorkflowActive(status);
    const failedSteps = getFailedSteps(steps);

    const handleAction = (action: WorkflowControlAction) => {
        if (action === 'RETRY' || action === 'SKIP') {
            if (selectedStepId) {
                onControlAction(action, selectedStepId);
            }
        } else {
            onControlAction(action);
        }
    };

    // currentStep kept for potential future UI enhancements
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const _currentStep = steps.find(s => s.id === current_step_id);

    // Don't show controls if workflow is completed or cancelled
    if (status === 'COMPLETED' || status === 'CANCELLED') {
        return null;
    }

    return (
        <div className="flex flex-wrap items-center gap-2">
            {/* Status indicator */}
            <div className="flex items-center gap-2 mr-2">
                <span className="text-sm text-gray-600">
                    {isActive ? 'Workflow is running' : 'Workflow is paused'}
                </span>
            </div>

            {/* Control buttons */}
            <div className="flex items-center gap-2">
                {/* Pause/Resume button */}
                {isActive && status === 'RUNNING' ? (
                    <button
                        onClick={() => handleAction('PAUSE')}
                        disabled={loading || disabled}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-yellow-700 bg-yellow-100 rounded-lg hover:bg-yellow-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Pause
                    </button>
                ) : status === 'PAUSED' ? (
                    <button
                        onClick={() => handleAction('RESUME')}
                        disabled={loading || disabled}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-blue-700 bg-blue-100 rounded-lg hover:bg-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Resume
                    </button>
                ) : null}

                {/* Cancel button */}
                <button
                    onClick={() => handleAction('CANCEL')}
                    disabled={loading || disabled}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-red-700 bg-red-100 rounded-lg hover:bg-red-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    Cancel
                </button>
            </div>

            {/* Step-specific controls (only when failed steps exist or current step selected) */}
            {failedSteps.length > 0 && (
                <div className="flex items-center gap-2 ml-4 pl-4 border-l border-gray-300">
                    <span className="text-xs text-gray-500">Failed steps:</span>
                    <select
                        title="Select a failed step"
                        className="text-sm border border-gray-300 rounded-lg px-2 py-1 max-w-[150px]"
                        value={selectedStepId || ''}
                        onChange={(e) => setSelectedStepId(e.target.value || null)}
                        disabled={loading || disabled}
                    >
                        <option value="">Select step...</option>
                        {failedSteps.map((step) => (
                            <option key={step.id} value={step.id}>
                                Step {step.order}: {step.name}
                            </option>
                        ))}
                    </select>

                    {/* Retry button */}
                    <button
                        onClick={() => handleAction('RETRY')}
                        disabled={loading || disabled || !selectedStepId}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-green-700 bg-green-100 rounded-lg hover:bg-green-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Retry
                    </button>

                    {/* Skip button */}
                    <button
                        onClick={() => handleAction('SKIP')}
                        disabled={loading || disabled || !selectedStepId}
                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                        </svg>
                        Skip
                    </button>
                </div>
            )}

            {/* Loading indicator */}
            {loading && (
                <svg className="w-5 h-5 animate-spin text-blue-500 ml-2" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
            )}
        </div>
    );
};

export default WorkflowControls;
