import React, { useState } from 'react';
import type { QuerySource, IntentClassification } from '@/types/conversation';

interface QueryResultProps {
    response: string;
    sources: QuerySource[];
    intent: IntentClassification;
    showSources?: boolean;
}

const SOURCE_ICONS: Record<string, string> = {
    vector_search: '📚',
    k8s_api: '☸️',
    cloud_api: '☁️',
    intent_classification: '🧠',
    conversation_history: '💬',
};

const SOURCE_LABELS: Record<string, string> = {
    vector_search: 'Knowledge Base',
    k8s_api: 'Kubernetes API',
    cloud_api: 'Cloud API',
    intent_classification: 'AI Analysis',
    conversation_history: 'Context',
};

export const QueryResult: React.FC<QueryResultProps> = ({
    response,
    sources,
    intent,
    showSources = true,
}) => {
    const [showAllSources, setShowAllSources] = useState(false);
    const displayedSources = showAllSources ? sources : sources.slice(0, 3);

    const formatTimestamp = (timestamp: string) => {
        try {
            const date = new Date(timestamp);
            return date.toLocaleString();
        } catch {
            return timestamp;
        }
    };

    // Parse response for tables
    const renderResponse = (text: string) => {
        const parts = text.split(/(\|.*\|)/g);
        const isTable = parts.some(p => p.trim().startsWith('|') && p.trim().endsWith('|'));

        if (isTable) {
            return (
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200 border border-gray-300 rounded-lg">
                        <thead className="bg-gray-50">
                            {parts.filter(p => p.trim().startsWith('|') && !p.includes('---')).map((row, i) => {
                                if (row.includes('---')) return null;
                                const cells = row.split('|').filter(c => c.trim());
                                return (
                                    <tr key={i}>
                                        {cells.map((cell, j) => (
                                            <th key={j} className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">
                                                {cell.trim()}
                                            </th>
                                        ))}
                                    </tr>
                                );
                            })}
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {parts.filter(p => p.trim().startsWith('|') && !p.includes('---')).slice(1).map((row, i) => {
                                const cells = row.split('|').filter(c => c.trim());
                                return (
                                    <tr key={i}>
                                        {cells.map((cell, j) => (
                                            <td key={j} className="px-4 py-2 text-sm text-gray-900">
                                                {cell.trim()}
                                            </td>
                                        ))}
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            );
        }

        return <div className="whitespace-pre-wrap">{text}</div>;
    };

    return (
        <div className="space-y-4">
            {/* Main Response */}
            <div className="prose prose-sm max-w-none">
                {renderResponse(response)}
            </div>

            {/* Sources Section */}
            {showSources && sources.length > 0 && (
                <div className="border-t pt-4 mt-4">
                    <button
                        onClick={() => setShowAllSources(!showAllSources)}
                        className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
                    >
                        <span>📑</span>
                        <span>
                            Sources ({sources.length})
                        </span>
                        <span className="text-xs">
                            {showAllSources ? '▲ Hide' : '▼ Show'}
                        </span>
                    </button>

                    {(showAllSources || sources.length <= 3) && (
                        <div className="mt-3 space-y-2">
                            {displayedSources.map((source, index) => (
                                <div
                                    key={index}
                                    className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                                >
                                    <span className="text-lg">{SOURCE_ICONS[source.type] || '📄'}</span>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="text-sm font-medium text-gray-900">
                                                {SOURCE_LABELS[source.type] || source.type}
                                            </span>
                                            <span className="text-xs text-gray-500">
                                                {(source.confidence * 100).toFixed(0)}% confident
                                            </span>
                                        </div>
                                        {source.resource_id && (
                                            <p className="text-xs text-gray-600 truncate">
                                                {source.resource_type && <span className="font-medium">{source.resource_type}:</span>}{' '}
                                                {source.resource_id}
                                            </p>
                                        )}
                                        {source.metadata && Object.keys(source.metadata).length > 0 && (
                                            <div className="mt-2 flex flex-wrap gap-1">
                                                {Object.entries(source.metadata).slice(0, 3).map(([key, value]) => (
                                                    <span
                                                        key={key}
                                                        className="inline-flex items-center gap-1 text-xs bg-white px-2 py-0.5 rounded border"
                                                    >
                                                        <span className="text-gray-500">{key}:</span>
                                                        <span className="text-gray-700">{String(value)}</span>
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Processing metadata */}
            {intent && (
                <div className="flex items-center gap-4 pt-2 border-t text-xs text-gray-500">
                    <span>
                        Intent: <span className="font-medium">{intent.intent}</span>
                    </span>
                    <span>
                        Confidence: <span className="font-medium">{(intent.confidence * 100).toFixed(0)}%</span>
                    </span>
                    {intent.target_resource && (
                        <span>
                            Target: <span className="font-medium">{intent.target_resource}</span>
                        </span>
                    )}
                </div>
            )}
        </div>
    );
};

export default QueryResult;
