import React, { useState } from 'react';
import {
    Settings,
    Save,
    RotateCcw,
    Download,
    Upload,
    Clock,
    BarChart3,
    Globe,
    Zap,
    History,
    Sparkles,
} from 'lucide-react';
import type { UserPreferences as UserPreferencesType, OutputFormat } from '@/types/conversation';

interface UserPreferencesProps {
    preferences: UserPreferencesType;
    onPreferencesChange: (preferences: Partial<UserPreferencesType>) => void;
    onSave: () => Promise<void>;
    onReset: () => Promise<void>;
    onClearHistory: () => Promise<void>;
    onExport: () => string;
    onImport: (data: string) => Promise<void>;
    loading?: boolean;
    hasChanges?: boolean;
}

const OUTPUT_FORMAT_OPTIONS: { value: OutputFormat; label: string }[] = [
    { value: 'table', label: 'Table' },
    { value: 'json', label: 'JSON' },
    { value: 'yaml', label: 'YAML' },
    { value: 'summary', label: 'Summary' },
];

export const UserPreferences: React.FC<UserPreferencesProps> = ({
    preferences,
    onPreferencesChange,
    onSave,
    onReset,
    onClearHistory,
    onExport,
    onImport,
    loading = false,
    hasChanges = false,
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [activeTab, setActiveTab] = useState<'general' | 'output' | 'history'>('general');
    const [importData, setImportData] = useState('');
    const [showImportModal, setShowImportModal] = useState(false);

    const handleToggleClusterBadges = () => {
        onPreferencesChange({ show_cluster_badges: !preferences.show_cluster_badges });
    };

    const handleToggleAutoIncludeAll = () => {
        onPreferencesChange({ auto_include_all_clusters: !preferences.auto_include_all_clusters });
    };

    const handleToggleSuggestions = () => {
        onPreferencesChange({ query_suggestions_enabled: !preferences.query_suggestions_enabled });
    };

    const handleOutputFormatChange = (format: OutputFormat) => {
        onPreferencesChange({ preferred_output_format: format });
    };

    const handleExport = () => {
        const data = onExport();
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `talktoinfra-preferences-${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const handleImportConfirm = async () => {
        try {
            await onImport(importData);
            setShowImportModal(false);
            setImportData('');
        } catch {
            alert('Failed to import preferences. Please check the format.');
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    return (
        <div className="relative">
            {/* Settings button */}
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                disabled={loading}
                className={`
                    flex items-center gap-2 px-3 py-2 rounded-lg border
                    transition-all duration-200
                    ${loading
                        ? 'bg-gray-50 border-gray-200 text-gray-400 cursor-not-allowed'
                        : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400'
                    }
                    ${hasChanges ? 'border-blue-300 bg-blue-50' : ''}
                `}
            >
                <Settings className="w-4 h-4" />
                <span className="text-sm font-medium">Preferences</span>
                {hasChanges && (
                    <span className="w-2 h-2 bg-blue-500 rounded-full" />
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
                    <div className="absolute z-20 mt-2 w-96 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
                        {/* Tabs */}
                        <div className="flex border-b border-gray-100">
                            <button
                                type="button"
                                onClick={() => setActiveTab('general')}
                                className={`
                                    flex-1 px-4 py-3 text-sm font-medium
                                    ${activeTab === 'general'
                                        ? 'text-blue-700 border-b-2 border-blue-600'
                                        : 'text-gray-600 hover:bg-gray-50'
                                    }
                                `}
                            >
                                <Globe className="w-4 h-4 inline mr-1" />
                                General
                            </button>
                            <button
                                type="button"
                                onClick={() => setActiveTab('output')}
                                className={`
                                    flex-1 px-4 py-3 text-sm font-medium
                                    ${activeTab === 'output'
                                        ? 'text-blue-700 border-b-2 border-blue-600'
                                        : 'text-gray-600 hover:bg-gray-50'
                                    }
                                `}
                            >
                                <BarChart3 className="w-4 h-4 inline mr-1" />
                                Output
                            </button>
                            <button
                                type="button"
                                onClick={() => setActiveTab('history')}
                                className={`
                                    flex-1 px-4 py-3 text-sm font-medium
                                    ${activeTab === 'history'
                                        ? 'text-blue-700 border-b-2 border-blue-600'
                                        : 'text-gray-600 hover:bg-gray-50'
                                    }
                                `}
                            >
                                <History className="w-4 h-4 inline mr-1" />
                                History
                            </button>
                        </div>

                        {/* Tab content */}
                        <div className="p-4 max-h-80 overflow-y-auto">
                            {/* General tab */}
                            {activeTab === 'general' && (
                                <div className="space-y-4">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <span className="font-medium text-gray-900">Cluster Badges</span>
                                            <p className="text-xs text-gray-500">Show cluster badges in results</p>
                                        </div>
                                        <button
                                            type="button"
                                            onClick={handleToggleClusterBadges}
                                            className={`
                                                relative inline-flex h-6 w-11 items-center rounded-full
                                                ${preferences.show_cluster_badges ? 'bg-blue-600' : 'bg-gray-200'}
                                            `}
                                        >
                                            <span className={`
                                                inline-block h-4 w-4 transform rounded-full bg-white transition
                                                ${preferences.show_cluster_badges ? 'translate-x-6' : 'translate-x-1'}
                                            `}
                                            />
                                        </button>
                                    </div>

                                    <div className="flex items-center justify-between">
                                        <div>
                                            <span className="font-medium text-gray-900">Auto All Clusters</span>
                                            <p className="text-xs text-gray-500">Include all clusters by default</p>
                                        </div>
                                        <button
                                            type="button"
                                            onClick={handleToggleAutoIncludeAll}
                                            className={`
                                                relative inline-flex h-6 w-11 items-center rounded-full
                                                ${preferences.auto_include_all_clusters ? 'bg-blue-600' : 'bg-gray-200'}
                                            `}
                                        >
                                            <span className={`
                                                inline-block h-4 w-4 transform rounded-full bg-white transition
                                                ${preferences.auto_include_all_clusters ? 'translate-x-6' : 'translate-x-1'}
                                            `}
                                            />
                                        </button>
                                    </div>

                                    <div className="flex items-center justify-between">
                                        <div>
                                            <span className="font-medium text-gray-900">Query Suggestions</span>
                                            <p className="text-xs text-gray-500">Show intelligent suggestions</p>
                                        </div>
                                        <button
                                            type="button"
                                            onClick={handleToggleSuggestions}
                                            className={`
                                                relative inline-flex h-6 w-11 items-center rounded-full
                                                ${preferences.query_suggestions_enabled ? 'bg-blue-600' : 'bg-gray-200'}
                                            `}
                                        >
                                            <span className={`
                                                inline-block h-4 w-4 transform rounded-full bg-white transition
                                                ${preferences.query_suggestions_enabled ? 'translate-x-6' : 'translate-x-1'}
                                            `}
                                            />
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* Output tab */}
                            {activeTab === 'output' && (
                                <div className="space-y-4">
                                    <div>
                                        <span className="font-medium text-gray-900 block mb-2">Preferred Output Format</span>
                                        <div className="grid grid-cols-2 gap-2">
                                            {OUTPUT_FORMAT_OPTIONS.map((option) => (
                                                <button
                                                    key={option.value}
                                                    type="button"
                                                    onClick={() => handleOutputFormatChange(option.value)}
                                                    className={`
                                                        flex items-center gap-2 px-3 py-2 rounded-lg border text-sm
                                                        ${preferences.preferred_output_format === option.value
                                                            ? 'bg-blue-50 border-blue-300 text-blue-700'
                                                            : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                                                        }
                                                    `}
                                                >
                                                    {option.label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Usage stats */}
                                    <div>
                                        <span className="font-medium text-gray-900 block mb-2">Cluster Usage</span>
                                        {preferences.cluster_usage.length === 0 ? (
                                            <p className="text-sm text-gray-500">No usage data yet</p>
                                        ) : (
                                            <div className="space-y-2">
                                                {preferences.cluster_usage
                                                    .sort((a, b) => b.usage_count - a.usage_count)
                                                    .slice(0, 5)
                                                    .map((usage) => (
                                                        <div
                                                            key={usage.cluster_id}
                                                            className="flex items-center gap-2 text-sm"
                                                        >
                                                            <div className="flex-1 bg-gray-100 rounded-full h-2">
                                                                <div
                                                                    className="bg-blue-500 h-2 rounded-full"
                                                                    style={{
                                                                        width: `${Math.min(100, (usage.usage_count / Math.max(...preferences.cluster_usage.map(u => u.usage_count))) * 100)}%`,
                                                                    }}
                                                                />
                                                            </div>
                                                            <span className="text-gray-600 w-8">{usage.usage_count}</span>
                                                        </div>
                                                    ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {/* History tab */}
                            {activeTab === 'history' && (
                                <div className="space-y-4">
                                    {/* Recent queries */}
                                    <div>
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="font-medium text-gray-900">Recent Queries</span>
                                            <button
                                                type="button"
                                                onClick={onClearHistory}
                                                className="text-xs text-red-600 hover:text-red-700"
                                            >
                                                Clear All
                                            </button>
                                        </div>
                                        {preferences.query_history.length === 0 ? (
                                            <p className="text-sm text-gray-500">No query history yet</p>
                                        ) : (
                                            <ul className="space-y-1 max-h-48 overflow-y-auto">
                                                {preferences.query_history.slice(0, 10).map((query, index) => (
                                                    <li
                                                        key={index}
                                                        className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg text-sm"
                                                    >
                                                        <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                                        <span className="flex-1 truncate text-gray-700">
                                                            {query.query}
                                                        </span>
                                                        {query.result_count !== undefined && (
                                                            <span className="text-xs text-gray-500">
                                                                {query.result_count} results
                                                            </span>
                                                        )}
                                                    </li>
                                                ))}
                                            </ul>
                                        )}
                                    </div>

                                    {/* Common queries */}
                                    {preferences.common_queries.length > 0 && (
                                        <div>
                                            <span className="font-medium text-gray-900 block mb-2">Common Queries</span>
                                            <ul className="space-y-1">
                                                {preferences.common_queries.slice(0, 5).map((query, index) => (
                                                    <li
                                                        key={index}
                                                        className="flex items-center gap-2 px-3 py-1 text-sm text-gray-600"
                                                    >
                                                        <Sparkles className="w-4 h-4 text-yellow-500" />
                                                        <span className="truncate">{query}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Footer */}
                        <div className="flex items-center justify-between p-4 border-t border-gray-100 bg-gray-50">
                            <div className="flex items-center gap-2">
                                <button
                                    type="button"
                                    onClick={onSave}
                                    disabled={!hasChanges || loading}
                                    className={`
                                        flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg
                                        ${hasChanges
                                            ? 'bg-blue-600 text-white hover:bg-blue-700'
                                            : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                        }
                                    `}
                                >
                                    <Save className="w-4 h-4" />
                                    Save
                                </button>
                                <button
                                    type="button"
                                    onClick={onReset}
                                    disabled={loading}
                                    className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-200 rounded-lg"
                                >
                                    <RotateCcw className="w-4 h-4" />
                                    Reset
                                </button>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    type="button"
                                    onClick={handleExport}
                                    className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
                                    title="Export preferences"
                                >
                                    <Download className="w-4 h-4" />
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setShowImportModal(true)}
                                    className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
                                    title="Import preferences"
                                >
                                    <Upload className="w-4 h-4" />
                                </button>
                            </div>
                        </div>

                        {/* Last saved info */}
                        <div className="px-4 py-2 bg-gray-100 text-xs text-gray-500">
                            Last active: {formatDate(preferences.last_active_at)}
                        </div>
                    </div>
                </>
            )}

            {/* Import modal */}
            {showImportModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
                    <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
                        <h3 className="text-lg font-semibold mb-4">Import Preferences</h3>
                        <textarea
                            value={importData}
                            onChange={(e) => setImportData(e.target.value)}
                            placeholder="Paste preferences JSON here..."
                            className="w-full h-48 px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono resize-none focus:ring-2 focus:ring-blue-500"
                        />
                        <div className="flex justify-end gap-2 mt-4">
                            <button
                                type="button"
                                onClick={() => setShowImportModal(false)}
                                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={handleImportConfirm}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                            >
                                Import
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default UserPreferences;
