import React, { useState, useMemo } from 'react';
import {
    ChevronDown,
    ChevronUp,
    Globe,
    Server,
    RefreshCw,
    Check,
    AlertCircle,
} from 'lucide-react';
import type { ClusterInfo, ClusterContextMode } from '@/types/conversation';

interface ClusterContextSelectorProps {
    clusters: ClusterInfo[];
    selectedClusterId: string | null;
    mode: ClusterContextMode;
    onClusterChange: (clusterId: string | null) => void;
    onModeChange: (mode: ClusterContextMode) => void;
    onRefresh?: () => void;
    loading?: boolean;
    disabled?: boolean;
    showCounts?: boolean;
    counts?: { total: number; connected: number; disconnected: number };
}

const PROVIDER_ICONS: Record<string, string> = {
    aws: '🔴',
    gcp: '🔵',
    azure: '🟠',
    onprem: '⚫',
    other: '⚪',
};

const STATUS_COLORS: Record<string, string> = {
    connected: 'bg-green-100 text-green-800 border-green-200',
    disconnected: 'bg-gray-100 text-gray-800 border-gray-200',
    error: 'bg-red-100 text-red-800 border-red-200',
};

const STATUS_DOT_COLORS: Record<string, string> = {
    connected: 'bg-green-500',
    disconnected: 'bg-gray-400',
    error: 'bg-red-500',
};

export const ClusterContextSelector: React.FC<ClusterContextSelectorProps> = ({
    clusters,
    selectedClusterId,
    mode,
    onClusterChange,
    onModeChange,
    onRefresh,
    loading = false,
    disabled = false,
    showCounts = true,
    counts,
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [isTestingConnection, setIsTestingConnection] = useState<string | null>(null);

    const selectedCluster = useMemo(() => {
        return clusters.find(c => c.id === selectedClusterId) || null;
    }, [clusters, selectedClusterId]);

    const connectedClusters = useMemo(() => {
        return clusters.filter(c => c.status === 'connected');
    }, [clusters]);

    const handleClusterSelect = (clusterId: string) => {
        if (disabled || loading) return;
        onClusterChange(clusterId);
        setIsOpen(false);
    };

    const handleModeChange = (newMode: ClusterContextMode) => {
        if (disabled || loading) return;
        onModeChange(newMode);
    };

    const handleRefresh = () => {
        if (disabled || loading) return;
        onRefresh?.();
    };

    const handleTestConnection = async (clusterId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (disabled || loading) return;

        setIsTestingConnection(clusterId);
        try {
            // Connection test would be handled by parent
            await new Promise(resolve => setTimeout(resolve, 1000)); // Mock delay
        } finally {
            setIsTestingConnection(null);
        }
    };

    return (
        <div className="relative">
            {/* Main selector button */}
            <button
                type="button"
                onClick={() => !disabled && setIsOpen(!isOpen)}
                disabled={disabled}
                className={`
                    flex items-center gap-2 px-3 py-2 rounded-lg border
                    transition-all duration-200
                    ${disabled
                        ? 'bg-gray-50 border-gray-200 text-gray-400 cursor-not-allowed'
                        : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400'
                    }
                    ${mode === 'all' ? 'border-blue-300 bg-blue-50' : ''}
                `}
            >
                {mode === 'all' ? (
                    <Globe className="w-4 h-4 text-blue-600" />
                ) : (
                    <Server className="w-4 h-4 text-gray-600" />
                )}

                <div className="flex flex-col items-start">
                    <span className="text-sm font-medium">
                        {mode === 'all'
                            ? `All Clusters (${connectedClusters.length})`
                            : selectedCluster?.name || 'Select Cluster'}
                    </span>
                    {selectedCluster && mode === 'single' && (
                        <span className="text-xs text-gray-500">
                            {selectedCluster.provider && PROVIDER_ICONS[selectedCluster.provider]} {selectedCluster.region}
                        </span>
                    )}
                </div>

                {!disabled && (
                    isOpen
                        ? <ChevronUp className="w-4 h-4 text-gray-400" />
                        : <ChevronDown className="w-4 h-4 text-gray-400" />
                )}

                {/* Status indicator */}
                {mode === 'single' && selectedCluster && (
                    <span className={`w-2 h-2 rounded-full ${STATUS_DOT_COLORS[selectedCluster.status]}`} />
                )}
            </button>

            {/* Dropdown panel */}
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <div
                        className="fixed inset-0 z-10"
                        onClick={() => setIsOpen(false)}
                    />

                    {/* Dropdown content */}
                    <div className="absolute z-20 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
                        {/* Mode toggle */}
                        <div className="flex border-b border-gray-100">
                            <button
                                type="button"
                                onClick={() => handleModeChange('single')}
                                className={`
                                    flex-1 px-4 py-2 text-sm font-medium
                                    ${mode === 'single'
                                        ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-600'
                                        : 'text-gray-600 hover:bg-gray-50'
                                    }
                                `}
                            >
                                <Server className="w-4 h-4 inline mr-1" />
                                Single
                            </button>
                            <button
                                type="button"
                                onClick={() => handleModeChange('all')}
                                className={`
                                    flex-1 px-4 py-2 text-sm font-medium
                                    ${mode === 'all'
                                        ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-600'
                                        : 'text-gray-600 hover:bg-gray-50'
                                    }
                                `}
                            >
                                <Globe className="w-4 h-4 inline mr-1" />
                                All Clusters
                            </button>
                        </div>

                        {/* Cluster list (only in single mode) */}
                        {mode === 'single' && (
                            <div className="max-h-64 overflow-y-auto">
                                {loading ? (
                                    <div className="flex items-center justify-center py-8 text-gray-400">
                                        <RefreshCw className="w-5 h-5 animate-spin mr-2" />
                                        Loading clusters...
                                    </div>
                                ) : clusters.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center py-8 text-gray-500">
                                        <Server className="w-8 h-8 mb-2 text-gray-300" />
                                        <p className="text-sm">No clusters available</p>
                                    </div>
                                ) : (
                                    <ul className="py-1">
                                        {clusters.map((cluster) => (
                                            <li key={cluster.id}>
                                                <button
                                                    type="button"
                                                    onClick={() => handleClusterSelect(cluster.id)}
                                                    disabled={disabled}
                                                    className={`
                                                        w-full flex items-center gap-3 px-4 py-3
                                                        text-left transition-colors
                                                        ${selectedClusterId === cluster.id
                                                            ? 'bg-blue-50 border-l-4 border-blue-600'
                                                            : 'hover:bg-gray-50'
                                                        }
                                                        ${cluster.status === 'disconnected' ? 'opacity-60' : ''}
                                                    `}
                                                >
                                                    {/* Provider icon */}
                                                    <span className="text-lg">
                                                        {PROVIDER_ICONS[cluster.provider || 'other'] || '⚪'}
                                                    </span>

                                                    {/* Cluster info */}
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-2">
                                                            <span className="font-medium text-gray-900 truncate">
                                                                {cluster.name}
                                                            </span>
                                                            {selectedClusterId === cluster.id && (
                                                                <Check className="w-4 h-4 text-blue-600 flex-shrink-0" />
                                                            )}
                                                        </div>
                                                        <div className="flex items-center gap-2 text-xs text-gray-500">
                                                            {cluster.region && (
                                                                <span>{cluster.region}</span>
                                                            )}
                                                        </div>
                                                    </div>

                                                    {/* Status */}
                                                    <div className="flex items-center gap-2">
                                                        <span className={`px-2 py-0.5 text-xs rounded-full border ${STATUS_COLORS[cluster.status]}`}>
                                                            {cluster.status === 'connected' ? (
                                                                <>
                                                                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full inline-block mr-1" />
                                                                    Connected
                                                                </>
                                                            ) : cluster.status === 'disconnected' ? (
                                                                <>
                                                                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full inline-block mr-1" />
                                                                    Disconnected
                                                                </>
                                                            ) : (
                                                                <>
                                                                    <AlertCircle className="w-3 h-3 inline mr-1" />
                                                                    Error
                                                                </>
                                                            )}
                                                        </span>

                                                        {/* Test connection button */}
                                                        <button
                                                            type="button"
                                                            onClick={(e) => handleTestConnection(cluster.id, e)}
                                                            disabled={isTestingConnection === cluster.id}
                                                            className="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100"
                                                            title="Test connection"
                                                        >
                                                            {isTestingConnection === cluster.id ? (
                                                                <RefreshCw className="w-4 h-4 animate-spin" />
                                                            ) : (
                                                                <RefreshCw className="w-4 h-4" />
                                                            )}
                                                        </button>
                                                    </div>
                                                </button>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        )}

                        {/* All clusters info (in all mode) */}
                        {mode === 'all' && (
                            <div className="p-4">
                                <div className="text-sm text-gray-600 mb-3">
                                    Query will run across all connected clusters
                                </div>

                                {showCounts && counts && (
                                    <div className="grid grid-cols-3 gap-2">
                                        <div className="text-center p-2 bg-gray-50 rounded-lg">
                                            <div className="text-lg font-semibold text-gray-900">
                                                {counts.total}
                                            </div>
                                            <div className="text-xs text-gray-500">Total</div>
                                        </div>
                                        <div className="text-center p-2 bg-green-50 rounded-lg">
                                            <div className="text-lg font-semibold text-green-700">
                                                {counts.connected}
                                            </div>
                                            <div className="text-xs text-green-600">Connected</div>
                                        </div>
                                        <div className="text-center p-2 bg-gray-50 rounded-lg">
                                            <div className="text-lg font-semibold text-gray-600">
                                                {counts.disconnected}
                                            </div>
                                            <div className="text-xs text-gray-500">Offline</div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Footer with refresh */}
                        <div className="flex items-center justify-between p-3 border-t border-gray-100 bg-gray-50">
                            <button
                                type="button"
                                onClick={handleRefresh}
                                disabled={disabled || loading}
                                className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 disabled:opacity-50"
                            >
                                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                                Refresh
                            </button>

                            <span className="text-xs text-gray-400">
                                {connectedClusters.length} of {clusters.length} connected
                            </span>
                        </div>
                    </div>
                </>
            )
            }
        </div >
    );
};

export default ClusterContextSelector;
