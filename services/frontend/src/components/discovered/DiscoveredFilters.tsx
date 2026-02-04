/**
 * Discovered Filters Component.
 * Provides filtering controls for discovered infrastructure.
 */

import React, { useState } from 'react';
import type { DiscoveredFilter, InfrastructureType, DiscoveredState } from '@/lib/types/discovered';
import { INFRA_TYPE_ICONS, STATE_COLORS } from '@/lib/types/discovered';

interface DiscoveredFiltersProps {
    filters: DiscoveredFilter;
    onFiltersChange: (filters: DiscoveredFilter) => void;
    onSearch: (query: string) => void;
}

export const DiscoveredFilters: React.FC<DiscoveredFiltersProps> = ({
    filters,
    onFiltersChange,
    onSearch,
}) => {
    const [searchQuery, setSearchQuery] = useState('');

    const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setSearchQuery(e.target.value);
    };

    const handleSearchSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSearch(searchQuery);
    };

    const toggleType = (type: InfrastructureType) => {
        const currentTypes = filters.infra_types || [];
        const newTypes = currentTypes.includes(type)
            ? currentTypes.filter((t) => t !== type)
            : [...currentTypes, type];
        onFiltersChange({ ...filters, infra_types: newTypes });
    };

    const toggleState = (state: DiscoveredState) => {
        const currentStates = filters.states || [];
        const newStates = currentStates.includes(state)
            ? currentStates.filter((s) => s !== state)
            : [...currentStates, state];
        onFiltersChange({ ...filters, states: newStates });
    };

    const infraTypes: InfrastructureType[] = [
        'kubernetes_cluster',
        'cloud_resource',
        'database',
        'load_balancer',
        'service',
        'network_device',
        'host',
        'unknown',
    ];

    const states: DiscoveredState[] = [
        'discovered',
        'analyzed',
        'suggested',
        'pending_onboarding',
        'onboarding',
        'onboarded',
        'failed',
        'ignored',
    ];

    return (
        <div className="bg-white shadow rounded-lg mb-6">
            <div className="px-4 py-5 sm:p-6">
                {/* Search Bar */}
                <form onSubmit={handleSearchSubmit} className="mb-6">
                    <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                        </div>
                        <input
                            type="text"
                            className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                            placeholder="Search by IP address, hostname, or FQDN..."
                            value={searchQuery}
                            onChange={handleSearchChange}
                        />
                    </div>
                </form>

                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                    {/* Infrastructure Types */}
                    <div>
                        <h4 className="text-sm font-medium text-gray-900 mb-3">Infrastructure Type</h4>
                        <div className="flex flex-wrap gap-2">
                            {infraTypes.map((type) => {
                                const isSelected = filters.infra_types?.includes(type);
                                return (
                                    <button
                                        key={type}
                                        onClick={() => toggleType(type)}
                                        className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${isSelected
                                                ? 'bg-blue-100 text-blue-800 border-2 border-blue-300'
                                                : 'bg-gray-100 text-gray-700 border-2 border-transparent hover:bg-gray-200'
                                            }`}
                                    >
                                        <span className="mr-1.5">{INFRA_TYPE_ICONS[type] || '❓'}</span>
                                        <span className="capitalize">{type.replace('_', ' ')}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* State */}
                    <div>
                        <h4 className="text-sm font-medium text-gray-900 mb-3">State</h4>
                        <div className="flex flex-wrap gap-2">
                            {states.map((state) => {
                                const isSelected = filters.states?.includes(state);
                                return (
                                    <button
                                        key={state}
                                        onClick={() => toggleState(state)}
                                        className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${isSelected
                                                ? 'bg-blue-100 text-blue-800 border-2 border-blue-300'
                                                : 'bg-gray-100 text-gray-700 border-2 border-transparent hover:bg-gray-200'
                                            }`}
                                        style={isSelected ? { borderColor: STATE_COLORS[state] } : undefined}
                                    >
                                        <span
                                            className="w-2 h-2 rounded-full mr-1.5"
                                            style={{ backgroundColor: STATE_COLORS[state] }}
                                        />
                                        <span className="capitalize">{state.replace('_', ' ')}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* Active Filters */}
                {(filters.infra_types?.length || filters.states?.length) && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-500">Active filters:</span>
                            <button
                                onClick={() => onFiltersChange({})}
                                className="text-sm text-blue-600 hover:text-blue-800"
                            >
                                Clear all filters
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
