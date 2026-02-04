/**
 * Infrastructure List Component.
 * Displays a list of discovered infrastructure items with filtering and selection.
 */

import React, { useState } from 'react';
import type { DiscoveredInfrastructure, InfrastructureType } from '@/lib/types/discovered';
import { INFRA_TYPE_ICONS, STATE_COLORS } from '@/lib/types/discovered';

interface InfrastructureListProps {
    items: DiscoveredInfrastructure[];
    selectedIds: Set<string>;
    onSelect: (id: string, selected: boolean) => void;
    onSelectAll: (selected: boolean) => void;
    onItemClick: (item: DiscoveredInfrastructure) => void;
    loading?: boolean;
}

export const InfrastructureList: React.FC<InfrastructureListProps> = ({
    items,
    selectedIds,
    onSelect,
    onSelectAll,
    onItemClick,
    loading = false,
}) => {
    const [sortField, setSortField] = useState<keyof DiscoveredInfrastructure>('discovered_at');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

    const handleSort = (field: keyof DiscoveredInfrastructure) => {
        if (sortField === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortOrder('desc');
        }
    };

    const sortedItems = [...items].sort((a, b) => {
        const aVal = a[sortField];
        const bVal = b[sortField];
        if (aVal === undefined || bVal === undefined) return 0;
        if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
        return 0;
    });

    const allSelected = items.length > 0 && items.every((item) => selectedIds.has(item.id));

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (items.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                <svg className="w-12 h-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                </svg>
                <p>No discovered infrastructure found</p>
            </div>
        );
    }

    return (
        <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            <input
                                type="checkbox"
                                checked={allSelected}
                                onChange={(e) => onSelectAll(e.target.checked)}
                                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            />
                        </th>
                        <th
                            className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                            onClick={() => handleSort('ip_address')}
                        >
                            Infrastructure
                            {sortField === 'ip_address' && (
                                <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                            )}
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Type
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Open Ports
                        </th>
                        <th
                            className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                            onClick={() => handleSort('confidence_score')}
                        >
                            Confidence
                            {sortField === 'confidence_score' && (
                                <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                            )}
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            State
                        </th>
                        <th
                            className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                            onClick={() => handleSort('discovered_at')}
                        >
                            Discovered
                            {sortField === 'discovered_at' && (
                                <span className="ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                            )}
                        </th>
                        <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Actions
                        </th>
                    </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                    {sortedItems.map((item) => (
                        <tr
                            key={item.id}
                            className={`hover:bg-gray-50 cursor-pointer ${selectedIds.has(item.id) ? 'bg-blue-50' : ''
                                }`}
                            onClick={() => onItemClick(item)}
                        >
                            <td className="px-6 py-4 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                                <input
                                    type="checkbox"
                                    checked={selectedIds.has(item.id)}
                                    onChange={(e) => onSelect(item.id, e.target.checked)}
                                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <div className="flex items-center">
                                    <div className="flex-shrink-0 h-10 w-10 flex items-center justify-center bg-gray-100 rounded-lg">
                                        <span className="text-xl">{INFRA_TYPE_ICONS[item.infra_type as InfrastructureType] || '❓'}</span>
                                    </div>
                                    <div className="ml-4">
                                        <div className="text-sm font-medium text-gray-900">
                                            {item.hostname || item.ip_address || 'Unknown'}
                                        </div>
                                        {item.fqdn && (
                                            <div className="text-sm text-gray-500">{item.fqdn}</div>
                                        )}
                                    </div>
                                </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                    {item.infra_type.replace('_', ' ')}
                                </span>
                                {item.service_type && (
                                    <div className="text-xs text-gray-500 mt-1">{item.service_type}</div>
                                )}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <div className="flex flex-wrap gap-1">
                                    {item.open_ports.slice(0, 3).map((port) => (
                                        <span
                                            key={port.port}
                                            className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                                        >
                                            {port.port}
                                        </span>
                                    ))}
                                    {item.open_ports.length > 3 && (
                                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                                            +{item.open_ports.length - 3}
                                        </span>
                                    )}
                                </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <div className="flex items-center">
                                    <div className="flex-1 h-2 bg-gray-200 rounded-full mr-2">
                                        <div
                                            className={`h-2 rounded-full ${item.confidence_score >= 80
                                                    ? 'bg-green-500'
                                                    : item.confidence_score >= 50
                                                        ? 'bg-yellow-500'
                                                        : 'bg-red-500'
                                                }`}
                                            style={{ width: `${item.confidence_score}%` }}
                                        />
                                    </div>
                                    <span className="text-sm text-gray-600">{item.confidence_score}%</span>
                                </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                                <span
                                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                                    style={{
                                        backgroundColor: `${STATE_COLORS[item.state]}20`,
                                        color: STATE_COLORS[item.state],
                                    }}
                                >
                                    {item.state.replace('_', ' ')}
                                </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {new Date(item.discovered_at).toLocaleDateString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium" onClick={(e) => e.stopPropagation()}>
                                <button
                                    onClick={() => onItemClick(item)}
                                    className="text-blue-600 hover:text-blue-900"
                                >
                                    View
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};
