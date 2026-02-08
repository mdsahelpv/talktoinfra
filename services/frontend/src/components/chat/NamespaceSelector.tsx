import React, { useState, useMemo } from 'react';
import {
    ChevronDown,
    ChevronUp,
    Layers,
    Star,
    StarOff,
    RefreshCw,
} from 'lucide-react';
import type { NamespaceInfo } from '@/types/conversation';

interface NamespaceSelectorProps {
    namespaces: NamespaceInfo[];
    selectedNamespace: string | null;
    clusterId: string | null;
    onNamespaceChange: (namespace: string | null) => void;
    rememberedNamespaces?: string[];
    onRememberNamespace?: (namespace: string) => void;
    onForgetNamespace?: (namespace: string) => void;
    loading?: boolean;
    disabled?: boolean;
    showAllOption?: boolean;
    showRememberOption?: boolean;
}

const STATUS_COLORS: Record<string, string> = {
    active: 'bg-green-100 text-green-800 border-green-200',
    terminating: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    unknown: 'bg-gray-100 text-gray-800 border-gray-200',
};

export const NamespaceSelector: React.FC<NamespaceSelectorProps> = ({
    namespaces,
    selectedNamespace,
    clusterId,
    onNamespaceChange,
    rememberedNamespaces = [],
    onRememberNamespace,
    onForgetNamespace,
    loading = false,
    disabled = false,
    showAllOption = true,
    showRememberOption = true,
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

    // Filter namespaces based on search query
    const filteredNamespaces = useMemo(() => {
        if (!searchQuery.trim()) return namespaces;
        return namespaces.filter(ns =>
            ns.name.toLowerCase().includes(searchQuery.toLowerCase())
        );
    }, [namespaces, searchQuery]);

    // Group namespaces into remembered and others
    const { remembered, others } = useMemo(() => {
        const remembered = filteredNamespaces.filter(ns =>
            rememberedNamespaces.includes(ns.name)
        );
        const others = filteredNamespaces.filter(ns =>
            !rememberedNamespaces.includes(ns.name)
        );
        return { remembered, others };
    }, [filteredNamespaces, rememberedNamespaces]);

    // Check if a namespace is remembered
    const isRemembered = (name: string) => rememberedNamespaces.includes(name);

    const handleNamespaceSelect = (namespace: string | null) => {
        if (disabled || loading) return;
        onNamespaceChange(namespace);
        setIsOpen(false);
    };

    const handleRememberToggle = (namespace: string, e: React.MouseEvent) => {
        e.stopPropagation();
        if (disabled || loading) return;

        if (isRemembered(namespace)) {
            onForgetNamespace?.(namespace);
        } else {
            onRememberNamespace?.(namespace);
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
                `}
            >
                <Layers className="w-4 h-4 text-gray-600" />

                <div className="flex flex-col items-start">
                    <span className="text-sm font-medium">
                        {selectedNamespace || (showAllOption ? 'All Namespaces' : 'Select Namespace')}
                    </span>
                    {selectedNamespace && (
                        <span className="text-xs text-gray-500">
                            {namespaces.find(n => n.name === selectedNamespace)?.resource_count || 0} resources
                        </span>
                    )}
                </div>

                {!disabled && (
                    isOpen
                        ? <ChevronUp className="w-4 h-4 text-gray-400" />
                        : <ChevronDown className="w-4 h-4 text-gray-400" />
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
                    <div className="absolute z-20 mt-2 w-72 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
                        {/* Search input */}
                        <div className="p-3 border-b border-gray-100">
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Search namespaces..."
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>

                        {/* "All Namespaces" option */}
                        {showAllOption && (
                            <button
                                type="button"
                                onClick={() => handleNamespaceSelect(null)}
                                className={`
                                    w-full flex items-center gap-3 px-4 py-3 text-left
                                    transition-colors
                                    ${selectedNamespace === null
                                        ? 'bg-blue-50 border-l-4 border-blue-600'
                                        : 'hover:bg-gray-50'
                                    }
                                `}
                            >
                                <Layers className="w-4 h-4 text-gray-400" />
                                <span className="font-medium text-gray-900">All Namespaces</span>
                                <span className="ml-auto text-xs text-gray-500">
                                    {namespaces.length} total
                                </span>
                            </button>
                        )}

                        {/* Loading state */}
                        {loading ? (
                            <div className="flex items-center justify-center py-8 text-gray-400">
                                <RefreshCw className="w-5 h-5 animate-spin mr-2" />
                                Loading namespaces...
                            </div>
                        ) : namespaces.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-8 text-gray-500">
                                <Layers className="w-8 h-8 mb-2 text-gray-300" />
                                <p className="text-sm">No namespaces found</p>
                                {clusterId && (
                                    <p className="text-xs text-gray-400 mt-1">
                                        Select a cluster first
                                    </p>
                                )}
                            </div>
                        ) : (
                            <div className="max-h-64 overflow-y-auto">
                                {/* Remembered namespaces section */}
                                {showRememberOption && remembered.length > 0 && (
                                    <div className="py-1">
                                        <div className="px-4 py-2 text-xs font-medium text-gray-500 uppercase bg-gray-50">
                                            <Star className="w-3 h-3 inline mr-1" />
                                            Remembered
                                        </div>
                                        {remembered.map((namespace) => (
                                            <NamespaceItem
                                                key={namespace.id}
                                                namespace={namespace}
                                                isSelected={selectedNamespace === namespace.name}
                                                isRemembered={true}
                                                onSelect={handleNamespaceSelect}
                                                onRememberToggle={handleRememberToggle}
                                                disabled={disabled || loading}
                                            />
                                        ))}
                                    </div>
                                )}

                                {/* Other namespaces section */}
                                {others.length > 0 && (
                                    <div className="py-1">
                                        {showRememberOption && remembered.length > 0 && (
                                            <div className="px-4 py-2 text-xs font-medium text-gray-500 uppercase bg-gray-50">
                                                All Namespaces
                                            </div>
                                        )}
                                        {others.map((namespace) => (
                                            <NamespaceItem
                                                key={namespace.id}
                                                namespace={namespace}
                                                isSelected={selectedNamespace === namespace.name}
                                                isRemembered={isRemembered(namespace.name)}
                                                onSelect={handleNamespaceSelect}
                                                onRememberToggle={handleRememberToggle}
                                                disabled={disabled || loading}
                                            />
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Footer */}
                        <div className="flex items-center justify-between p-3 border-t border-gray-100 bg-gray-50">
                            <span className="text-xs text-gray-500">
                                {namespaces.length} namespace{namespaces.length !== 1 ? 's' : ''}
                            </span>

                            {showRememberOption && selectedNamespace && !isRemembered(selectedNamespace) && (
                                <button
                                    type="button"
                                    onClick={(e) => handleRememberToggle(selectedNamespace, e)}
                                    className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
                                >
                                    <Star className="w-3 h-3" />
                                    Remember
                                </button>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

// Namespace item sub-component
interface NamespaceItemProps {
    namespace: NamespaceInfo;
    isSelected: boolean;
    isRemembered: boolean;
    onSelect: (namespace: string) => void;
    onRememberToggle: (namespace: string, e: React.MouseEvent) => void;
    disabled: boolean;
}

const NamespaceItem: React.FC<NamespaceItemProps> = ({
    namespace,
    isSelected,
    isRemembered,
    onSelect,
    onRememberToggle,
    disabled,
}) => {
    const letter = namespace.name.charAt(0).toUpperCase();

    return (
        <button
            type="button"
            onClick={() => onSelect(namespace.name)}
            disabled={disabled}
            className={`
                w-full flex items-center gap-3 px-4 py-2
                text-left transition-colors
                ${isSelected
                    ? 'bg-blue-50 border-l-4 border-blue-600'
                    : 'hover:bg-gray-50'
                }
                ${namespace.status === 'terminating' ? 'opacity-60' : ''}
            `}
        >
            {/* First letter indicator */}
            <span className="w-6 h-6 flex items-center justify-center bg-gray-100 text-gray-600 text-xs font-medium rounded">
                {letter}
            </span>

            {/* Namespace name */}
            <div className="flex-1 min-w-0">
                <span className="font-medium text-gray-900 truncate block">
                    {namespace.name}
                </span>
                {namespace.resource_count !== undefined && (
                    <span className="text-xs text-gray-500">
                        {namespace.resource_count} resource{namespace.resource_count !== 1 ? 's' : ''}
                    </span>
                )}
            </div>

            {/* Status indicator */}
            <span className={`px-2 py-0.5 text-xs rounded-full border ${STATUS_COLORS[namespace.status]}`}>
                {namespace.status}
            </span>

            {/* Remember toggle */}
            {onRememberToggle && (
                <button
                    type="button"
                    onClick={(e) => onRememberToggle(namespace.name, e)}
                    disabled={disabled}
                    className={`
                        p-1 rounded
                        ${isRemembered
                            ? 'text-yellow-500 hover:text-yellow-600'
                            : 'text-gray-300 hover:text-gray-400'
                        }
                    `}
                    title={isRemembered ? 'Forget namespace' : 'Remember namespace'}
                >
                    {isRemembered ? (
                        <Star className="w-4 h-4" />
                    ) : (
                        <StarOff className="w-4 h-4" />
                    )}
                </button>
            )}
        </button>
    );
};

export default NamespaceSelector;
