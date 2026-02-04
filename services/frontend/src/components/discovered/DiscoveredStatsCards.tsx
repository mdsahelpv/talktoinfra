/**
 * Discovered Stats Cards Component.
 * Displays statistics about discovered infrastructure.
 */

import React from 'react';
import type { DiscoveredStats } from '@/lib/types/discovered';
import { INFRA_TYPE_ICONS, STATE_COLORS } from '@/lib/types/discovered';

interface DiscoveredStatsCardsProps {
    stats: DiscoveredStats;
    onTypeClick?: (type: string) => void;
}

export const DiscoveredStatsCards: React.FC<DiscoveredStatsCardsProps> = ({
    stats,
    onTypeClick,
}) => {
    const formatNumber = (num: number) => {
        if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
        if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
        return num.toString();
    };

    return (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-6">
            {/* Total Items */}
            <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                    <div className="flex items-center">
                        <div className="flex-shrink-0">
                            <svg className="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                            </svg>
                        </div>
                        <div className="ml-5 w-0 flex-1">
                            <dl>
                                <dt className="text-sm font-medium text-gray-500 truncate">Total Discovered</dt>
                                <dd className="text-lg font-medium text-gray-900">{formatNumber(stats.total_items)}</dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>

            {/* Pending Onboarding */}
            <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                    <div className="flex items-center">
                        <div className="flex-shrink-0">
                            <svg className="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <div className="ml-5 w-0 flex-1">
                            <dl>
                                <dt className="text-sm font-medium text-gray-500 truncate">Pending Onboarding</dt>
                                <dd className="text-lg font-medium text-gray-900">{formatNumber(stats.pending_onboarding)}</dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>

            {/* Onboarded */}
            <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                    <div className="flex items-center">
                        <div className="flex-shrink-0">
                            <svg className="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <div className="ml-5 w-0 flex-1">
                            <dl>
                                <dt className="text-sm font-medium text-gray-500 truncate">Onboarded</dt>
                                <dd className="text-lg font-medium text-gray-900">{formatNumber(stats.onboarded)}</dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>

            {/* Recently Discovered */}
            <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                    <div className="flex items-center">
                        <div className="flex-shrink-0">
                            <svg className="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <div className="ml-5 w-0 flex-1">
                            <dl>
                                <dt className="text-sm font-medium text-gray-500 truncate">Last 24 Hours</dt>
                                <dd className="text-lg font-medium text-gray-900">{formatNumber(stats.recently_discovered)}</dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>

            {/* By Type */}
            <div className="bg-white overflow-hidden shadow rounded-lg sm:col-span-2 lg:col-span-4">
                <div className="px-4 py-5 sm:p-6">
                    <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">By Type</h3>
                    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                        {Object.entries(stats.by_type).map(([type, count]) => (
                            <div
                                key={type}
                                className={`bg-gray-50 rounded-lg p-4 cursor-pointer hover:bg-gray-100 transition-colors ${onTypeClick ? 'border border-transparent hover:border-gray-300' : ''
                                    }`}
                                onClick={() => onTypeClick?.(type)}
                            >
                                <div className="flex items-center justify-between">
                                    <span className="text-2xl">{INFRA_TYPE_ICONS[type as keyof typeof INFRA_TYPE_ICONS] || '❓'}</span>
                                    <span className="text-2xl font-bold text-gray-900">{formatNumber(count)}</span>
                                </div>
                                <p className="mt-2 text-sm text-gray-500 capitalize">{type.replace('_', ' ')}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* By State */}
            <div className="bg-white overflow-hidden shadow rounded-lg sm:col-span-2 lg:col-span-4">
                <div className="px-4 py-5 sm:p-6">
                    <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">By State</h3>
                    <div className="space-y-3">
                        {Object.entries(stats.by_state).map(([state, count]) => (
                            <div key={state} className="flex items-center">
                                <div className="flex-1">
                                    <div className="flex items-center justify-between mb-1">
                                        <span className="text-sm text-gray-700 capitalize">{state.replace('_', ' ')}</span>
                                        <span className="text-sm font-medium text-gray-900">{count}</span>
                                    </div>
                                    <div className="w-full h-2 bg-gray-200 rounded-full">
                                        <div
                                            className="h-2 rounded-full"
                                            style={{
                                                width: `${stats.total_items > 0 ? (count / stats.total_items) * 100 : 0}%`,
                                                backgroundColor: STATE_COLORS[state as keyof typeof STATE_COLORS] || '#6b7280',
                                            }}
                                        />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};
