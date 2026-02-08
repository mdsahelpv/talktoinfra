import React, { useState } from 'react';
import type { WorkflowStep, StepDetailsProps } from '@/types/conversation';
import { WORKFLOW_STEP_STATUS_CONFIG, formatDuration } from '@/types/conversation';

const StepDetails: React.FC<StepDetailsProps> = ({
    step,
    isExpanded,
    onToggleExpand,
    showLogs = true,
    maxLogs = 50,
}) => {
    const [showLogsPanel, setShowLogsPanel] = useState(true);

    const statusConfig = WORKFLOW_STEP_STATUS_CONFIG[step.status];

    // Format timestamp
    const formatTimestamp = (timestamp: string): string => {
        try {
            return new Date(timestamp).toLocaleTimeString();
        } catch {
            return timestamp;
        }
    };

    // Get log level color
    const getLogLevelColor = (level: string): string => {
        switch (level) {
            case 'DEBUG':
                return 'text-gray-500';
            case 'INFO':
                return 'text-blue-500';
            case 'WARN':
                return 'text-yellow-500';
            case 'ERROR':
                return 'text-red-500';
            default:
                return 'text-gray-500';
        }
    };

    // Get log level icon
    const getLogLevelIcon = (level: string): string => {
        switch (level) {
            case 'DEBUG':
                return '🐛';
            case 'INFO':
                return 'ℹ️';
            case 'WARN':
                return '⚠️';
            case 'ERROR':
                return '🚨';
            default:
                return '📝';
        }
    };

    // Calculate duration
    const getDuration = (): string | null => {
        if (!step.started_at) return null;
        const start = new Date(step.started_at).getTime();
        const end = step.completed_at ? new Date(step.completed_at).getTime() : Date.now();
        return formatDuration(end - start);
    };

    const duration = getDuration();
    const displayLogs = step.logs.slice(-maxLogs);

    return (
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
            {/* Step metadata */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
                <div className="text-xs">
                    <span className="text-gray-500">Type:</span>
                    <span className="ml-1 font-medium text-gray-700">{step.type}</span>
                </div>
                <div className="text-xs">
                    <span className="text-gray-500">Status:</span>
                    <span className={`ml-1 font-medium ${statusConfig.color}`}>
                        {statusConfig.label}
                    </span>
                </div>
                {duration && (
                    <div className="text-xs">
                        <span className="text-gray-500">Duration:</span>
                        <span className="ml-1 font-medium text-gray-700">{duration}</span>
                    </div>
                )}
                {step.retry_count > 0 && (
                    <div className="text-xs">
                        <span className="text-gray-500">Retries:</span>
                        <span className="ml-1 font-medium text-gray-700">
                            {step.retry_count}/{step.max_retries}
                        </span>
                    </div>
                )}
            </div>

            {/* Input/Output data */}
            {(step.input || step.output) && (
                <div className="mb-3">
                    {step.input && (
                        <div className="mb-2">
                            <h5 className="text-xs font-medium text-gray-500 mb-1">Input</h5>
                            <pre className="text-xs bg-gray-100 p-2 rounded overflow-x-auto">
                                {JSON.stringify(step.input.data, null, 2)}
                            </pre>
                        </div>
                    )}
                    {step.output && (
                        <div className="mb-2">
                            <h5 className="text-xs font-medium text-gray-500 mb-1">Output</h5>
                            <pre className={`text-xs p-2 rounded overflow-x-auto ${step.output.error ? 'bg-red-100' : 'bg-green-100'
                                }`}>
                                {JSON.stringify(step.output.data, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>
            )}

            {/* Error message */}
            {step.error && (
                <div className="mb-3 p-2 bg-red-100 border border-red-200 rounded">
                    <h5 className="text-xs font-medium text-red-700 mb-1">Error</h5>
                    <p className="text-xs text-red-600">{step.error}</p>
                </div>
            )}

            {/* Dependencies */}
            {step.dependencies && step.dependencies.length > 0 && (
                <div className="mb-3">
                    <h5 className="text-xs font-medium text-gray-500 mb-1">Dependencies</h5>
                    <div className="flex flex-wrap gap-1">
                        {step.dependencies.map((depId) => (
                            <span
                                key={depId}
                                className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-200 text-gray-700"
                            >
                                {depId}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Logs toggle */}
            {showLogs && step.logs.length > 0 && (
                <div>
                    <button
                        onClick={() => setShowLogsPanel(!showLogsPanel)}
                        className="flex items-center gap-1 text-xs font-medium text-gray-600 hover:text-gray-800"
                    >
                        <svg
                            className={`w-4 h-4 transition-transform ${showLogsPanel ? 'rotate-180' : ''}`}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                        Logs ({step.logs.length})
                    </button>

                    {showLogsPanel && (
                        <div className="mt-2 max-h-48 overflow-y-auto bg-gray-900 rounded">
                            <pre className="p-2 text-xs text-gray-100">
                                {displayLogs.map((log, index) => (
                                    <div key={index} className="mb-1">
                                        <span className="text-gray-500">
                                            [{formatTimestamp(log.timestamp)}]
                                        </span>{' '}
                                        <span className={getLogLevelColor(log.level)}>
                                            {getLogLevelIcon(log.level)}
                                        </span>{' '}
                                        <span className="text-gray-300">{log.message}</span>
                                    </div>
                                ))}
                            </pre>
                        </div>
                    )}
                </div>
            )}

            {/* Timestamp info */}
            <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
                {step.started_at && (
                    <span>Started: {formatTimestamp(step.started_at)}</span>
                )}
                {step.completed_at && (
                    <span>Completed: {formatTimestamp(step.completed_at)}</span>
                )}
            </div>
        </div>
    );
};

export default StepDetails;
