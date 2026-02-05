/** Cost Optimization Recommendations Component */

import React, { useState } from 'react';
import { TrendingDown, AlertTriangle, CheckCircle, X, Zap, Server, Trash2, Clock } from 'lucide-react';
import type { Recommendation, RecommendationSummary } from '@/types/cost';

interface RecommendationsProps {
    recommendations: Recommendation[];
    summary: RecommendationSummary;
    onUpdateStatus?: (id: string, status: string) => void;
}

export const Recommendations: React.FC<RecommendationsProps> = ({
    recommendations,
    summary,
    onUpdateStatus,
}) => {
    const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'implemented'>('all');

    const filteredRecommendations =
        filter === 'all'
            ? recommendations
            : recommendations.filter((r) => r.status === filter);

    const formatCurrency = (amount?: number) => {
        if (!amount) return '$0';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'critical':
                return 'bg-red-100 text-red-800 border-red-200';
            case 'high':
                return 'bg-orange-100 text-orange-800 border-orange-200';
            case 'medium':
                return 'bg-yellow-100 text-yellow-800 border-yellow-200';
            case 'low':
                return 'bg-green-100 text-green-800 border-green-200';
            default:
                return 'bg-gray-100 text-gray-800 border-gray-200';
        }
    };

    const getTypeIcon = (type: string) => {
        switch (type) {
            case 'right_size':
                return <Server className="w-5 h-5" />;
            case 'delete_idle':
                return <Trash2 className="w-5 h-5" />;
            case 'spot_instance':
                return <Zap className="w-5 h-5" />;
            case 'reserved_instance':
                return <Clock className="w-5 h-5" />;
            default:
                return <TrendingDown className="w-5 h-5" />;
        }
    };

    const getTypeLabel = (type: string) => {
        switch (type) {
            case 'right_size':
                return 'Right-size';
            case 'delete_idle':
                return 'Delete Idle';
            case 'spot_instance':
                return 'Spot Instance';
            case 'reserved_instance':
                return 'Reserved Instance';
            case 'storage_optimize':
                return 'Storage Optimization';
            case 'network_optimize':
                return 'Network Optimization';
            default:
                return type.replace('_', ' ');
        }
    };

    return (
        <div className="space-y-6">
            {/* Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-lg shadow p-6">
                    <p className="text-sm text-gray-500">Total Recommendations</p>
                    <p className="text-3xl font-bold mt-1">{summary.total_recommendations}</p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                    <p className="text-sm text-gray-500">Potential Monthly Savings</p>
                    <p className="text-3xl font-bold mt-1 text-green-600">
                        {formatCurrency(summary.total_potential_savings_monthly)}
                    </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                    <p className="text-sm text-gray-500">Potential Annual Savings</p>
                    <p className="text-3xl font-bold mt-1 text-green-600">
                        {formatCurrency(summary.total_potential_savings_yearly)}
                    </p>
                </div>
            </div>

            {/* Priority Summary */}
            <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">Recommendations by Priority</h3>
                <div className="grid grid-cols-4 gap-4">
                    {['critical', 'high', 'medium', 'low'].map((priority) => {
                        const data = summary.by_priority?.[priority] || { count: 0, savings: 0 };
                        return (
                            <div
                                key={priority}
                                className={`p-4 rounded-lg border ${priority === 'critical'
                                        ? 'bg-red-50 border-red-200'
                                        : priority === 'high'
                                            ? 'bg-orange-50 border-orange-200'
                                            : priority === 'medium'
                                                ? 'bg-yellow-50 border-yellow-200'
                                                : 'bg-green-50 border-green-200'
                                    }`}
                            >
                                <p className="text-sm font-medium capitalize">{priority}</p>
                                <p className="text-2xl font-bold mt-1">{data.count}</p>
                                <p className="text-xs text-gray-500 mt-1">
                                    {formatCurrency(data.savings)}/mo potential
                                </p>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Filter Tabs */}
            <div className="flex space-x-2">
                {(['all', 'pending', 'approved', 'implemented'] as const).map((status) => (
                    <button
                        key={status}
                        onClick={() => setFilter(status)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === status
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        {status.charAt(0).toUpperCase() + status.slice(1)}
                    </button>
                ))}
            </div>

            {/* Recommendations List */}
            <div className="space-y-4">
                {filteredRecommendations.map((rec) => (
                    <RecommendationCard
                        key={rec.id}
                        recommendation={rec}
                        formatCurrency={formatCurrency}
                        getPriorityColor={getPriorityColor}
                        getTypeIcon={getTypeIcon}
                        getTypeLabel={getTypeLabel}
                        onUpdateStatus={(status) => onUpdateStatus?.(rec.id, status)}
                    />
                ))}

                {filteredRecommendations.length === 0 && (
                    <div className="bg-white rounded-lg shadow p-12 text-center text-gray-500">
                        <CheckCircle className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                        <p>No {filter === 'all' ? '' : filter} recommendations</p>
                    </div>
                )}
            </div>
        </div>
    );
};

// Individual Recommendation Card
interface RecommendationCardProps {
    recommendation: Recommendation;
    formatCurrency: (amount?: number) => string;
    getPriorityColor: (priority: string) => string;
    getTypeIcon: (type: string) => React.ReactNode;
    getTypeLabel: (type: string) => string;
    onUpdateStatus: (status: string) => void;
}

const RecommendationCard: React.FC<RecommendationCardProps> = ({
    recommendation,
    formatCurrency,
    getPriorityColor,
    getTypeIcon,
    getTypeLabel,
    onUpdateStatus,
}) => {
    const [expanded, setExpanded] = useState(false);

    return (
        <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-6">
                <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-4">
                        <div
                            className={`p-2 rounded-lg ${recommendation.priority === 'critical'
                                    ? 'bg-red-100 text-red-600'
                                    : recommendation.priority === 'high'
                                        ? 'bg-orange-100 text-orange-600'
                                        : recommendation.priority === 'medium'
                                            ? 'bg-yellow-100 text-yellow-600'
                                            : 'bg-green-100 text-green-600'
                                }`}
                        >
                            {getTypeIcon(recommendation.recommendation_type)}
                        </div>
                        <div>
                            <div className="flex items-center space-x-2">
                                <h4 className="font-semibold">{recommendation.title}</h4>
                                <span
                                    className={`px-2 py-0.5 rounded-full text-xs border ${getPriorityColor(
                                        recommendation.priority
                                    )}`}
                                >
                                    {recommendation.priority}
                                </span>
                                <span
                                    className={`px-2 py-0.5 rounded-full text-xs ${recommendation.status === 'pending'
                                            ? 'bg-gray-100 text-gray-800'
                                            : recommendation.status === 'approved'
                                                ? 'bg-blue-100 text-blue-800'
                                                : recommendation.status === 'implemented'
                                                    ? 'bg-green-100 text-green-800'
                                                    : 'bg-gray-100 text-gray-800'
                                        }`}
                                >
                                    {recommendation.status}
                                </span>
                            </div>
                            <p className="text-sm text-gray-500 mt-1">{recommendation.description}</p>
                        </div>
                    </div>
                    <div className="text-right">
                        <p className="text-lg font-bold text-green-600">
                            {formatCurrency(recommendation.estimated_savings)}/mo
                        </p>
                        <p className="text-xs text-gray-500">potential savings</p>
                    </div>
                </div>

                <div className="mt-4 flex items-center justify-between">
                    <div className="flex items-center space-x-4 text-sm text-gray-500">
                        <span className="capitalize">{getTypeLabel(recommendation.recommendation_type)}</span>
                        {recommendation.cloud_provider && (
                            <span className="capitalize">• {recommendation.cloud_provider}</span>
                        )}
                        {recommendation.resource_type && (
                            <span className="capitalize">• {recommendation.resource_type.replace('_', ' ')}</span>
                        )}
                    </div>
                    <button
                        onClick={() => setExpanded(!expanded)}
                        className="text-sm text-blue-600 hover:text-blue-700"
                    >
                        {expanded ? 'Show less' : 'Show details'}
                    </button>
                </div>

                {/* Expanded Details */}
                {expanded && (
                    <div className="mt-6 pt-6 border-t space-y-4">
                        {/* Action Steps */}
                        {recommendation.action_steps && recommendation.action_steps.length > 0 && (
                            <div>
                                <h5 className="text-sm font-medium text-gray-700 mb-2">Action Steps</h5>
                                <ol className="list-decimal list-inside text-sm text-gray-600 space-y-1">
                                    {recommendation.action_steps.map((step, idx) => (
                                        <li key={idx}>{step}</li>
                                    ))}
                                </ol>
                            </div>
                        )}

                        {/* Risks */}
                        {recommendation.risks && recommendation.risks.length > 0 && (
                            <div>
                                <h5 className="text-sm font-medium text-gray-700 mb-2">Risks</h5>
                                <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                                    {recommendation.risks.map((risk, idx) => (
                                        <li key={idx}>{risk}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Current Cost */}
                        {recommendation.current_cost && (
                            <div>
                                <h5 className="text-sm font-medium text-gray-700 mb-1">Current Cost</h5>
                                <p className="text-lg font-semibold">{formatCurrency(recommendation.current_cost)}/mo</p>
                            </div>
                        )}

                        {/* Actions */}
                        {recommendation.status === 'pending' && (
                            <div className="flex space-x-3 pt-4">
                                <button
                                    onClick={() => onUpdateStatus('approved')}
                                    className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                                >
                                    <CheckCircle className="w-4 h-4 mr-2" />
                                    Approve
                                </button>
                                <button
                                    onClick={() => onUpdateStatus('dismissed')}
                                    className="flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                                >
                                    <X className="w-4 h-4 mr-2" />
                                    Dismiss
                                </button>
                            </div>
                        )}

                        {recommendation.status === 'approved' && (
                            <div className="flex space-x-3 pt-4">
                                <button
                                    onClick={() => onUpdateStatus('implemented')}
                                    className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                                >
                                    <CheckCircle className="w-4 h-4 mr-2" />
                                    Mark as Implemented
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};
