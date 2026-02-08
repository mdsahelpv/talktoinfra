import React, { useState } from 'react';
import { Search, Filter, X, ChevronDown, ChevronUp } from 'lucide-react';
import type { QueryResultFiltersProps, FilterPreset, FilterCondition } from '@/types/conversation';
import { FILTER_PRESETS } from '@/types/conversation';

export const QueryResultFilters: React.FC<QueryResultFiltersProps> = ({
    filters,
    onFiltersChange,
    availableFields = [],
    resultType,
}) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [customFilterField, setCustomFilterField] = useState('');
    const [customFilterOperator, setCustomFilterOperator] = useState<'eq' | 'ne' | 'contains'>('eq');
    const [customFilterValue, setCustomFilterValue] = useState('');

    const presets = Object.entries(FILTER_PRESETS) as [FilterPreset, { label: string; icon: string; description: string }][];

    const handlePresetChange = (preset: FilterPreset) => {
        onFiltersChange({
            ...filters,
            preset,
            customConditions: preset === 'all' ? [] : filters.customConditions,
        });
    };

    const handleSearchChange = (searchQuery: string) => {
        onFiltersChange({
            ...filters,
            searchQuery,
        });
    };

    const addCustomFilter = () => {
        if (customFilterField && customFilterValue) {
            const newCondition: FilterCondition = {
                field: customFilterField,
                operator: customFilterOperator,
                value: customFilterValue,
            };
            onFiltersChange({
                ...filters,
                preset: 'all',
                customConditions: [...filters.customConditions, newCondition],
            });
            setCustomFilterField('');
            setCustomFilterValue('');
        }
    };

    const removeCustomFilter = (index: number) => {
        const newConditions = filters.customConditions.filter((_: FilterCondition, i: number) => i !== index);
        onFiltersChange({
            ...filters,
            customConditions: newConditions,
        });
    };

    const clearAllFilters = () => {
        onFiltersChange({
            preset: 'all',
            customConditions: [],
            searchQuery: '',
        });
    };

    const hasActiveFilters = filters.preset !== 'all' || filters.customConditions.length > 0 || filters.searchQuery;

    return (
        <div className="space-y-3">
            {/* Header with search and expand toggle */}
            <div className="flex items-center gap-3">
                {/* Search input */}
                <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Filter results..."
                        value={filters.searchQuery}
                        onChange={(e) => handleSearchChange(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        aria-label="Filter results"
                    />
                    {filters.searchQuery && (
                        <button
                            onClick={() => handleSearchChange('')}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                            aria-label="Clear search"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    )}
                </div>

                {/* Expand/collapse button */}
                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className={`flex items-center gap-2 px-3 py-2 text-sm rounded-lg border transition-colors ${hasActiveFilters
                            ? 'bg-blue-50 border-blue-200 text-blue-700'
                            : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                        }`}
                    aria-label={isExpanded ? 'Collapse filters' : 'Expand filters'}
                >
                    <Filter className="w-4 h-4" />
                    <span>Filters</span>
                    {hasActiveFilters && (
                        <span className="flex items-center justify-center w-5 h-5 text-xs bg-blue-600 text-white rounded-full">
                            {(filters.preset !== 'all' ? 1 : 0) + filters.customConditions.length + (filters.searchQuery ? 1 : 0)}
                        </span>
                    )}
                    {isExpanded ? (
                        <ChevronUp className="w-4 h-4" />
                    ) : (
                        <ChevronDown className="w-4 h-4" />
                    )}
                </button>

                {/* Clear all filters */}
                {hasActiveFilters && (
                    <button
                        onClick={clearAllFilters}
                        className="text-sm text-gray-500 hover:text-gray-700 underline"
                    >
                        Clear all
                    </button>
                )}
            </div>

            {/* Expanded filter options */}
            {isExpanded && (
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 space-y-4">
                    {/* Preset filters */}
                    <div>
                        <h4 className="text-sm font-medium text-gray-700 mb-2">Quick Filters</h4>
                        <div className="flex flex-wrap gap-2">
                            {presets.map(([key, preset]) => (
                                <button
                                    key={key}
                                    onClick={() => handlePresetChange(key)}
                                    className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-full border transition-colors ${filters.preset === key
                                            ? 'bg-blue-600 border-blue-600 text-white'
                                            : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-100'
                                        }`}
                                    title={preset.description}
                                >
                                    <span>{preset.icon}</span>
                                    <span>{preset.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Custom filters */}
                    {filters.customConditions.length > 0 && (
                        <div>
                            <h4 className="text-sm font-medium text-gray-700 mb-2">Active Filters</h4>
                            <div className="flex flex-wrap gap-2">
                                {filters.customConditions.map((condition: FilterCondition, index: number) => (
                                    <span
                                        key={index}
                                        className="inline-flex items-center gap-1 px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-full"
                                    >
                                        <span className="text-gray-500">{condition.field}</span>
                                        <span className="text-gray-400">
                                            {condition.operator === 'eq' ? '=' : condition.operator === 'ne' ? '!=' : '~='}
                                        </span>
                                        <span className="font-medium">{String(condition.value)}</span>
                                        <button
                                            onClick={() => removeCustomFilter(index)}
                                            className="ml-1 text-gray-400 hover:text-gray-600"
                                            aria-label={`Remove filter ${condition.field}`}
                                        >
                                            <X className="w-3 h-3" />
                                        </button>
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Add custom filter */}
                    {availableFields.length > 0 && (
                        <div>
                            <h4 className="text-sm font-medium text-gray-700 mb-2">Add Custom Filter</h4>
                            <div className="flex flex-wrap items-center gap-2">
                                <select
                                    value={customFilterField}
                                    onChange={(e) => setCustomFilterField(e.target.value)}
                                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    aria-label="Select field to filter"
                                >
                                    <option value="">Select field...</option>
                                    {availableFields.map((field: string) => (
                                        <option key={field} value={field}>
                                            {field}
                                        </option>
                                    ))}
                                </select>

                                <select
                                    value={customFilterOperator}
                                    onChange={(e) => setCustomFilterOperator(e.target.value as 'eq' | 'ne' | 'contains')}
                                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    aria-label="Select operator"
                                >
                                    <option value="eq">equals</option>
                                    <option value="ne">not equals</option>
                                    <option value="contains">contains</option>
                                </select>

                                <input
                                    type="text"
                                    placeholder="Value..."
                                    value={customFilterValue}
                                    onChange={(e) => setCustomFilterValue(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && addCustomFilter()}
                                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 w-32"
                                    aria-label="Filter value"
                                />

                                <button
                                    onClick={addCustomFilter}
                                    disabled={!customFilterField || !customFilterValue}
                                    className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    Add
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Result type indicator */}
                    {resultType && (
                        <div className="text-xs text-gray-500 pt-2 border-t">
                            Filtering: <span className="font-medium text-gray-700">{resultType}</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default QueryResultFilters;
