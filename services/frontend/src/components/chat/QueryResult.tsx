import React, { useState, useCallback, useMemo } from 'react';
import type {
    QuerySource,
    IntentClassification,
    QueryResultMetadata,
    PaginationState,
    FilterState,
    SortState,
    ClusterQueryResult,
    CrossClusterQueryMetadata,
} from '@/types/conversation';
import { QueryResultPagination } from './QueryResultPagination';
import { QueryResultFilters } from './QueryResultFilters';
import { ExportDropdown } from './ExportDropdown';
import { CreateAlertModal } from './CreateAlertModal';
import {
    ChevronDown,
    ChevronUp,
    ArrowUpDown,
    Download,
    Bell,
    Filter,
    BarChart3,
    Globe,
    Server,
    CheckCircle,
    AlertCircle,
    XCircle,
} from 'lucide-react';

interface QueryResultProps {
    response: string;
    sources: QuerySource[];
    intent: IntentClassification;
    showSources?: boolean;
    metadata?: QueryResultMetadata;
    parsedData?: Record<string, unknown>[];
    // Cross-cluster support
    crossClusterMetadata?: CrossClusterQueryMetadata;
    clusterResults?: ClusterQueryResult[];
    showClusterBadges?: boolean;
}

// Cluster badge colors
const CLUSTER_BADGE_COLORS: Record<string, string> = {
    default: 'bg-gray-100 text-gray-800 border-gray-200',
    aws: 'bg-orange-100 text-orange-800 border-orange-200',
    gcp: 'bg-blue-100 text-blue-800 border-blue-200',
    azure: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    onprem: 'bg-purple-100 text-purple-800 border-purple-200',
};

// Status icons
const STATUS_ICONS: Record<string, React.ReactNode> = {
    success: <CheckCircle className="w-4 h-4 text-green-500" />,
    error: <XCircle className="w-4 h-4 text-red-500" />,
    partial: <AlertCircle className="w-4 h-4 text-yellow-500" />,
};

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

// Parse table data from response for export
const parseTableData = (response: string): Record<string, unknown>[] => {
    const lines = response.split('\n');
    const data: Record<string, unknown>[] = [];
    let headers: string[] = [];

    for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
            const cells = trimmed.split('|').filter((c, i) => i !== 0 && i !== trimmed.split('|').length - 1).map(c => c.trim());

            // Check if it's a header row (contains dashes)
            if (trimmed.includes('---')) {
                continue;
            }

            // Check if first cell looks like a header
            if (headers.length === 0 && cells.every(c => !/^\d+$/.test(c))) {
                headers = cells;
            } else if (headers.length > 0) {
                const row: Record<string, unknown> = {};
                headers.forEach((header, index) => {
                    row[header] = cells[index] || '';
                });
                data.push(row);
            }
        }
    }

    return data;
};

export const QueryResult: React.FC<QueryResultProps> = ({
    response,
    sources,
    intent,
    showSources = true,
    metadata,
    parsedData = [],
    crossClusterMetadata,
    clusterResults,
    showClusterBadges = true,
}) => {
    const [showAllSources, setShowAllSources] = useState(false);

    // Pagination state
    const [pagination, setPagination] = useState<PaginationState>({
        currentPage: 1,
        pageSize: 10,
        totalItems: metadata?.totalItems || parsedData.length || 20,
        totalPages: Math.ceil((metadata?.totalItems || parsedData.length || 20) / 10),
    });

    // Filter state
    const [filters, setFilters] = useState<FilterState>({
        preset: 'all',
        customConditions: [],
        searchQuery: '',
    });

    // Sort state
    const [sort, setSort] = useState<SortState>({
        field: '',
        direction: 'asc',
    });

    // UI state
    const [showAlertModal, setShowAlertModal] = useState(false);
    const [showFilters, setShowFilters] = useState(false);

    const displayedSources = showAllSources ? sources : sources.slice(0, 3);

    // Calculate displayed items
    const totalDisplayed = useMemo(() => {
        const base = metadata?.displayedItems || parsedData.length || 20;
        return Math.min(base, pagination.pageSize);
    }, [metadata, parsedData, pagination.pageSize]);

    const formatTimestamp = (timestamp: string) => {
        try {
            const date = new Date(timestamp);
            return date.toLocaleString();
        } catch {
            return timestamp;
        }
    };

    // Parse response for tables
    const renderResponse = useCallback((text: string) => {
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
    }, []);

    // Handle pagination
    const handlePageChange = useCallback((page: number) => {
        setPagination(prev => ({ ...prev, currentPage: page }));
    }, []);

    const handlePageSizeChange = useCallback((pageSize: number) => {
        setPagination(prev => ({
            ...prev,
            pageSize,
            totalPages: Math.ceil(prev.totalItems / pageSize),
            currentPage: 1,
        }));
    }, []);

    // Get export data
    const exportData = useMemo(() => {
        if (parsedData.length > 0) {
            return parsedData;
        }
        // Fall back to parsing response
        return parseTableData(response);
    }, [parsedData, response]);

    // Get available filter fields from parsed data
    const availableFilterFields = useMemo(() => {
        if (parsedData.length > 0 && typeof parsedData[0] === 'object') {
            return Object.keys(parsedData[0]);
        }
        return [];
    }, [parsedData]);

    // Generate result summary
    const resultSummary = useMemo(() => {
        const total = metadata?.totalItems || parsedData.length || 20;
        const displayed = Math.min(total, pagination.pageSize);

        if (total === displayed) {
            return `Found ${total.toLocaleString()} result${total !== 1 ? 's' : ''}`;
        }
        return `Found ${total.toLocaleString()} results. Showing first ${displayed}.`;
    }, [metadata, parsedData, pagination.pageSize]);

    return (
        <div className="space-y-4">
            {/* Result header with actions */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b">
                <div className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-gray-400" />
                    <span className="text-sm font-medium text-gray-700">{resultSummary}</span>
                </div>

                <div className="flex items-center gap-2">
                    {/* Filter toggle */}
                    <button
                        onClick={() => setShowFilters(!showFilters)}
                        className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border transition-colors ${filters.preset !== 'all' || filters.searchQuery
                            ? 'bg-blue-50 border-blue-200 text-blue-700'
                            : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                            }`}
                    >
                        <Filter className="w-4 h-4" />
                        Filter
                        {(filters.preset !== 'all' || filters.searchQuery) && (
                            <span className="w-2 h-2 bg-blue-600 rounded-full" />
                        )}
                    </button>

                    {/* Export dropdown */}
                    <ExportDropdown
                        data={exportData}
                        filename={`query_results_${new Date().toISOString().slice(0, 10)}`}
                    />

                    {/* Create alert button */}
                    <button
                        onClick={() => setShowAlertModal(true)}
                        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-orange-50 border border-orange-200 text-orange-700 rounded-lg hover:bg-orange-100 transition-colors"
                    >
                        <Bell className="w-4 h-4" />
                        Create Alert
                    </button>
                </div>
            </div>

            {/* Filters */}
            {showFilters && (
                <QueryResultFilters
                    filters={filters}
                    onFiltersChange={setFilters}
                    availableFields={availableFilterFields}
                    resultType={metadata?.resultType}
                />
            )}

            {/* Cross-Cluster Results */}
            {crossClusterMetadata && clusterResults && clusterResults.length > 0 && (
                <div className="space-y-4">
                    {/* Cross-cluster header */}
                    <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                        <Globe className="w-5 h-5 text-blue-600" />
                        <div className="flex-1">
                            <span className="font-medium text-blue-900">
                                Cross-Cluster Query Results
                            </span>
                            <p className="text-sm text-blue-700">
                                Query executed across {crossClusterMetadata.target_clusters.length} cluster(s)
                            </p>
                        </div>
                        <div className="text-right">
                            <span className="text-2xl font-bold text-blue-700">
                                {crossClusterMetadata.aggregated_count.toLocaleString()}
                            </span>
                            <span className="block text-xs text-blue-600">Total results</span>
                        </div>
                    </div>

                    {/* Cluster results breakdown */}
                    <div className="grid gap-3">
                        {clusterResults.map((result) => (
                            <div
                                key={result.cluster_id}
                                className={`p-4 rounded-lg border ${result.status === 'error'
                                    ? 'bg-red-50 border-red-200'
                                    : result.status === 'partial'
                                        ? 'bg-yellow-50 border-yellow-200'
                                        : 'bg-white border-gray-200'
                                    }`}
                            >
                                <div className="flex items-center justify-between mb-3">
                                    <div className="flex items-center gap-2">
                                        {STATUS_ICONS[result.status]}
                                        <Server className="w-4 h-4 text-gray-500" />
                                        <span className="font-medium text-gray-900">
                                            {result.cluster_name}
                                        </span>
                                        {result.namespace && (
                                            <span className="text-sm text-gray-500">
                                                ({result.namespace})
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className={`px-2 py-1 text-sm rounded-full ${result.status === 'success'
                                                ? 'bg-green-100 text-green-800'
                                                : result.status === 'partial'
                                                    ? 'bg-yellow-100 text-yellow-800'
                                                    : 'bg-red-100 text-red-800'
                                            }`}>
                                            {result.total_count} result{result.total_count !== 1 ? 's' : ''}
                                        </span>
                                        <span className="text-xs text-gray-500">
                                            {result.execution_time_ms}ms
                                        </span>
                                    </div>
                                </div>

                                {result.status === 'error' && result.error_message && (
                                    <div className="p-2 bg-red-100 rounded text-sm text-red-700">
                                        {result.error_message}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>

                    {/* Cross-cluster summary */}
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                        <span>
                            Total execution time: <strong>{crossClusterMetadata.execution_time_ms}ms</strong>
                        </span>
                        {crossClusterMetadata.namespaces_scoped && (
                            <span className="flex items-center gap-1">
                                <Filter className="w-4 h-4" />
                                Namespace-scoped query
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* Main Response */}
            <div className="prose prose-sm max-w-none">
                {renderResponse(response)}
            </div>

            {/* Result summary footer */}
            {metadata?.totalItems && metadata.totalItems > pagination.pageSize && (
                <div className="flex items-center justify-between py-2 px-3 bg-blue-50 rounded-lg text-sm text-blue-700">
                    <span>
                        Showing {resultSummary.toLowerCase().replace('found', '').trim()}
                    </span>
                    <span className="font-medium">
                        Use pagination below to see more
                    </span>
                </div>
            )}

            {/* Pagination */}
            {pagination.totalItems > pagination.pageSize && (
                <QueryResultPagination
                    pagination={pagination}
                    onPageChange={handlePageChange}
                    onPageSizeChange={handlePageSizeChange}
                />
            )}

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
                    {metadata?.executionTimeMs && (
                        <span>
                            Query time: <span className="font-medium">{metadata.executionTimeMs}ms</span>
                        </span>
                    )}
                </div>
            )}

            {/* Create Alert Modal */}
            <CreateAlertModal
                isOpen={showAlertModal}
                onClose={() => setShowAlertModal(false)}
                onCreate={(alert) => {
                    console.log('Creating alert:', alert);
                    // API call would go here
                    setShowAlertModal(false);
                }}
                queryContext={{
                    originalQuery: intent?.target_resource || 'query',
                    resultType: metadata?.resultType || 'unknown',
                    filters,
                    sampleData: exportData.slice(0, 5),
                }}
            />
        </div>
    );
};

export default QueryResult;
