/** Cost Overview Dashboard Component */

import React from 'react';
import { TrendingUp, TrendingDown, DollarSign, AlertTriangle, CheckCircle } from 'lucide-react';
import type { CostDashboardOverview } from '@/types/cost';

interface CostOverviewProps {
    overview: CostDashboardOverview;
    isLoading?: boolean;
}

export const CostOverview: React.FC<CostOverviewProps> = ({
    overview,
    isLoading = false,
}) => {
    if (isLoading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                    <div key={i} className="bg-gray-100 rounded-lg h-32 animate-pulse" />
                ))}
            </div>
        );
    }

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: overview.currency || 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    };

    const isPositiveChange = (overview.cost_change_percent || 0) > 0;

    return (
        <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {/* Total Cost */}
                <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-500">Total Cost</p>
                            <p className="text-2xl font-bold mt-1">
                                {formatCurrency(overview.total_cost)}
                            </p>
                        </div>
                        <div className="bg-blue-100 p-3 rounded-full">
                            <DollarSign className="w-6 h-6 text-blue-600" />
                        </div>
                    </div>
                    <div className="flex items-center mt-4 text-sm">
                        {isPositiveChange ? (
                            <>
                                <TrendingUp className="w-4 h-4 text-red-500 mr-1" />
                                <span className="text-red-500">
                                    +{overview.cost_change_percent?.toFixed(1)}%
                                </span>
                            </>
                        ) : (
                            <>
                                <TrendingDown className="w-4 h-4 text-green-500 mr-1" />
                                <span className="text-green-500">
                                    {overview.cost_change_percent?.toFixed(1)}%
                                </span>
                            </>
                        )}
                        <span className="text-gray-500 ml-2">vs previous period</span>
                    </div>
                </div>

                {/* Active Budgets */}
                <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-500">Active Budgets</p>
                            <p className="text-2xl font-bold mt-1">{overview.active_budgets}</p>
                        </div>
                        <div className="bg-green-100 p-3 rounded-full">
                            <CheckCircle className="w-6 h-6 text-green-600" />
                        </div>
                    </div>
                    <div className="mt-4 text-sm text-gray-500">
                        {overview.budgets_near_limit} near limit,{' '}
                        {overview.budgets_exceeded} exceeded
                    </div>
                </div>

                {/* Alerts */}
                <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-500">Budget Alerts</p>
                            <p className="text-2xl font-bold mt-1">
                                {overview.budgets_exceeded > 0 ? (
                                    <span className="text-red-600">{overview.budgets_exceeded}</span>
                                ) : (
                                    <span className="text-green-600">0</span>
                                )}
                            </p>
                        </div>
                        <div className="bg-yellow-100 p-3 rounded-full">
                            <AlertTriangle className="w-6 h-6 text-yellow-600" />
                        </div>
                    </div>
                    <div className="mt-4 text-sm text-gray-500">
                        {overview.budgets_near_limit} budgets approaching limits
                    </div>
                </div>

                {/* Period */}
                <div className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-500">Current Period</p>
                            <p className="text-lg font-semibold mt-1">
                                {new Date(overview.period_start).toLocaleDateString()} -{' '}
                                {new Date(overview.period_end).toLocaleDateString()}
                            </p>
                        </div>
                        <div className="bg-purple-100 p-3 rounded-full">
                            <TrendingUp className="w-6 h-6 text-purple-600" />
                        </div>
                    </div>
                    <div className="mt-4 text-sm text-gray-500 capitalize">
                        {overview.period} reporting
                    </div>
                </div>
            </div>

            {/* Cost by Provider */}
            <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">Cost by Cloud Provider</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(overview.cost_by_provider || {}).map(([provider, cost]) => (
                        <div key={provider} className="text-center">
                            <div
                                className={`inline-flex items-center justify-center w-16 h-16 rounded-full ${provider === 'aws'
                                        ? 'bg-yellow-100'
                                        : provider === 'azure'
                                            ? 'bg-blue-100'
                                            : provider === 'gcp'
                                                ? 'bg-red-100'
                                                : 'bg-green-100'
                                    }`}
                            >
                                <span className="text-lg font-bold uppercase">{provider.slice(0, 2)}</span>
                            </div>
                            <p className="text-xl font-semibold mt-2">{formatCurrency(cost)}</p>
                            <p className="text-sm text-gray-500 capitalize">{provider}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Top Resources */}
            <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">Top Expensive Resources</h3>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead>
                            <tr className="text-left text-sm text-gray-500 border-b">
                                <th className="pb-3 font-medium">Resource</th>
                                <th className="pb-3 font-medium">Type</th>
                                <th className="pb-3 font-medium">Provider</th>
                                <th className="pb-3 font-medium text-right">Cost</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(overview.top_resources || []).slice(0, 5).map((resource, index) => (
                                <tr key={index} className="border-b last:border-0">
                                    <td className="py-3">
                                        <p className="font-medium">{resource.resource_name || resource.resource_id}</p>
                                        <p className="text-sm text-gray-500">{resource.resource_id?.slice(0, 8)}...</p>
                                    </td>
                                    <td className="py-3 text-sm capitalize">
                                        {resource.resource_type?.replace('_', ' ')}
                                    </td>
                                    <td className="py-3 text-sm capitalize">
                                        <span
                                            className={`inline-flex items-center px-2 py-1 rounded-full text-xs ${resource.cloud_provider === 'aws'
                                                    ? 'bg-yellow-100 text-yellow-800'
                                                    : resource.cloud_provider === 'azure'
                                                        ? 'bg-blue-100 text-blue-800'
                                                        : resource.cloud_provider === 'gcp'
                                                            ? 'bg-red-100 text-red-800'
                                                            : 'bg-green-100 text-green-800'
                                                }`}
                                        >
                                            {resource.cloud_provider}
                                        </span>
                                    </td>
                                    <td className="py-3 text-right font-medium">
                                        {formatCurrency(resource.total_cost)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};
