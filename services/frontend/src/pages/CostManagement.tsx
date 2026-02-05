/** Cost Management Dashboard Page */

import React, { useState, useEffect, useCallback } from 'react';
import { DollarSign, TrendingUp, AlertTriangle, ChevronDown } from 'lucide-react';
import { CostOverview, BudgetTracker, Recommendations } from '@/components/cost';
import {
    getDashboardOverview,
    costApi,
    budgetApi,
    recommendationApi,
} from '@/lib/api/cost';
import type {
    CostDashboardOverview,
    Budget,
    BudgetSummary,
    Recommendation,
    RecommendationSummary,
} from '@/types/cost';

type TabType = 'overview' | 'budgets' | 'recommendations' | 'estimation';

export const CostManagement: React.FC = () => {
    const [activeTab, setActiveTab] = useState<TabType>('overview');
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Data state
    const [overview, setOverview] = useState<CostDashboardOverview | null>(null);
    const [budgets, setBudgets] = useState<Budget[]>([]);
    const [budgetSummary, setBudgetSummary] = useState<BudgetSummary | null>(null);
    const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
    const [recommendationSummary, setRecommendationSummary] = useState<RecommendationSummary | null>(null);

    // Date range state
    const [dateRange, setDateRange] = useState({
        start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        end: new Date().toISOString().split('T')[0],
    });

    const fetchData = useCallback(async () => {
        setIsLoading(true);
        setError(null);

        try {
            const [overviewData, budgetsData, budgetSummaryData, recsData, recSummaryData] =
                await Promise.all([
                    getDashboardOverview(dateRange.start, dateRange.end).catch(() => null),
                    budgetApi.list().catch(() => []),
                    budgetApi.getSummary().catch(() => null),
                    recommendationApi.list({ limit: 50 }).catch(() => []),
                    recommendationApi.getSummary().catch(() => null),
                ]);

            if (overviewData) setOverview(overviewData);
            setBudgets(budgetsData);
            if (budgetSummaryData) setBudgetSummary(budgetSummaryData);
            setRecommendations(recsData);
            if (recSummaryData) setRecommendationSummary(recSummaryData);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch data');
        } finally {
            setIsLoading(false);
        }
    }, [dateRange]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleBudgetCreate = async (budget: Partial<Budget>) => {
        try {
            await budgetApi.create(budget);
            fetchData();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create budget');
        }
    };

    const handleBudgetUpdate = async (id: string, updates: Partial<Budget>) => {
        try {
            await budgetApi.update(id, updates);
            fetchData();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to update budget');
        }
    };

    const handleBudgetDelete = async (id: string) => {
        try {
            await budgetApi.delete(id);
            fetchData();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to delete budget');
        }
    };

    const handleRecommendationUpdate = async (id: string, status: string) => {
        try {
            await recommendationApi.update(id, { status });
            fetchData();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to update recommendation');
        }
    };

    const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
        { id: 'overview', label: 'Overview', icon: <DollarSign className="w-4 h-4" /> },
        { id: 'budgets', label: 'Budgets', icon: <TrendingUp className="w-4 h-4" /> },
        { id: 'recommendations', label: 'Recommendations', icon: <AlertTriangle className="w-4 h-4" /> },
    ];

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <div className="bg-white shadow-sm border-b">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Cost Management</h1>
                            <p className="text-sm text-gray-500 mt-1">
                                Track, analyze, and optimize your cloud infrastructure costs
                            </p>
                        </div>
                        <div className="flex items-center space-x-4">
                            {/* Date Range Picker */}
                            <div className="flex items-center space-x-2 bg-gray-100 rounded-lg p-1">
                                <input
                                    type="date"
                                    value={dateRange.start}
                                    onChange={(e) =>
                                        setDateRange((prev) => ({ ...prev, start: e.target.value }))
                                    }
                                    className="px-3 py-1 text-sm border-none bg-transparent focus:ring-0"
                                />
                                <span className="text-gray-400">to</span>
                                <input
                                    type="date"
                                    value={dateRange.end}
                                    onChange={(e) =>
                                        setDateRange((prev) => ({ ...prev, end: e.target.value }))
                                    }
                                    className="px-3 py-1 text-sm border-none bg-transparent focus:ring-0"
                                />
                            </div>
                            <button
                                onClick={fetchData}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                            >
                                Refresh
                            </button>
                        </div>
                    </div>

                    {/* Tabs */}
                    <div className="flex space-x-1 mt-6">
                        {tabs.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === tab.id
                                        ? 'bg-blue-100 text-blue-700'
                                        : 'text-gray-600 hover:bg-gray-100'
                                    }`}
                            >
                                {tab.icon}
                                <span>{tab.label}</span>
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Error Banner */}
                {error && (
                    <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
                        <p className="text-red-700">{error}</p>
                    </div>
                )}

                {/* Tab Content */}
                {isLoading ? (
                    <div className="space-y-6">
                        {[...Array(3)].map((_, i) => (
                            <div key={i} className="bg-gray-200 rounded-lg h-64 animate-pulse" />
                        ))}
                    </div>
                ) : (
                    <>
                        {activeTab === 'overview' && overview && (
                            <CostOverview overview={overview} isLoading={isLoading} />
                        )}

                        {activeTab === 'budgets' && budgetSummary && (
                            <BudgetTracker
                                budgets={budgets}
                                summary={budgetSummary}
                                onCreateBudget={handleBudgetCreate}
                                onUpdateBudget={handleBudgetUpdate}
                                onDeleteBudget={handleBudgetDelete}
                            />
                        )}

                        {activeTab === 'recommendations' && recommendationSummary && (
                            <Recommendations
                                recommendations={recommendations}
                                summary={recommendationSummary}
                                onUpdateStatus={handleRecommendationUpdate}
                            />
                        )}

                        {activeTab === 'estimation' && (
                            <CostEstimationPanel />
                        )}
                    </>
                )}
            </div>
        </div>
    );
};

// Cost Estimation Panel Component
const CostEstimationPanel: React.FC = () => {
    const [cloudProvider, setCloudProvider] = useState<'aws' | 'azure' | 'gcp'>('aws');
    const [cpuCores, setCpuCores] = useState(2);
    const [memoryGb, setMemoryGb] = useState(8);
    const [storageGb, setStorageGb] = useState(100);
    const [isLoading, setIsLoading] = useState(false);
    const [estimate, setEstimate] = useState<{
        monthly_cost: number;
        compute_cost: number;
        storage_cost: number;
        alternatives: Array<{ instance_type: string; monthly_cost: number; savings_percent: number }>;
    } | null>(null);

    const handleEstimate = async () => {
        setIsLoading(true);
        // Simulate API call
        await new Promise((resolve) => setTimeout(resolve, 1000));
        setEstimate({
            monthly_cost: cpuCores * 30 + memoryGb * 10 + storageGb * 0.1,
            compute_cost: cpuCores * 30 + memoryGb * 10,
            storage_cost: storageGb * 0.1,
            alternatives: [
                { instance_type: 't3.small', monthly_cost: 20, savings_percent: 20 },
                { instance_type: 't3.medium', monthly_cost: 40, savings_percent: 0 },
                { instance_type: 'm5.large', monthly_cost: 50, savings_percent: -25 },
            ],
        });
        setIsLoading(false);
    };

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    };

    return (
        <div className="bg-white rounded-lg shadow">
            <div className="p-6 border-b">
                <h3 className="text-lg font-semibold">Cost Estimation</h3>
                <p className="text-sm text-gray-500 mt-1">
                    Estimate costs before deploying resources
                </p>
            </div>

            <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Input Form */}
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Cloud Provider
                        </label>
                        <div className="flex space-x-2">
                            {['aws', 'azure', 'gcp'].map((provider) => (
                                <button
                                    key={provider}
                                    onClick={() => setCloudProvider(provider as 'aws' | 'azure' | 'gcp')}
                                    className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium capitalize transition-colors ${cloudProvider === provider
                                            ? 'bg-blue-600 text-white'
                                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                        }`}
                                >
                                    {provider}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                CPU Cores
                            </label>
                            <input
                                type="number"
                                value={cpuCores}
                                onChange={(e) => setCpuCores(parseInt(e.target.value) || 1)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                min="1"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Memory (GB)
                            </label>
                            <input
                                type="number"
                                value={memoryGb}
                                onChange={(e) => setMemoryGb(parseInt(e.target.value) || 1)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                min="1"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Storage (GB)
                        </label>
                        <input
                            type="number"
                            value={storageGb}
                            onChange={(e) => setStorageGb(parseInt(e.target.value) || 0)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            min="0"
                        />
                    </div>

                    <button
                        onClick={handleEstimate}
                        disabled={isLoading}
                        className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                    >
                        {isLoading ? 'Calculating...' : 'Estimate Cost'}
                    </button>
                </div>

                {/* Results */}
                <div>
                    {estimate ? (
                        <div className="space-y-4">
                            <div className="bg-gray-50 rounded-lg p-6">
                                <p className="text-sm text-gray-500">Estimated Monthly Cost</p>
                                <p className="text-4xl font-bold text-gray-900 mt-2">
                                    {formatCurrency(estimate.monthly_cost)}
                                </p>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-gray-50 rounded-lg p-4">
                                    <p className="text-sm text-gray-500">Compute</p>
                                    <p className="text-xl font-semibold mt-1">
                                        {formatCurrency(estimate.compute_cost)}
                                    </p>
                                </div>
                                <div className="bg-gray-50 rounded-lg p-4">
                                    <p className="text-sm text-gray-500">Storage</p>
                                    <p className="text-xl font-semibold mt-1">
                                        {formatCurrency(estimate.storage_cost)}
                                    </p>
                                </div>
                            </div>

                            {estimate.alternatives.length > 0 && (
                                <div>
                                    <h4 className="text-sm font-medium text-gray-700 mb-2">
                                        Alternative Configurations
                                    </h4>
                                    <div className="space-y-2">
                                        {estimate.alternatives.map((alt) => (
                                            <div
                                                key={alt.instance_type}
                                                className="flex items-center justify-between bg-gray-50 rounded-lg p-3"
                                            >
                                                <div>
                                                    <p className="font-medium">{alt.instance_type}</p>
                                                    <p className="text-sm text-gray-500">
                                                        {formatCurrency(alt.monthly_cost)}/mo
                                                    </p>
                                                </div>
                                                <span
                                                    className={`text-sm font-medium ${alt.savings_percent > 0
                                                            ? 'text-green-600'
                                                            : alt.savings_percent < 0
                                                                ? 'text-red-600'
                                                                : 'text-gray-500'
                                                        }`}
                                                >
                                                    {alt.savings_percent > 0 ? '-' : '+'}
                                                    {Math.abs(alt.savings_percent)}%
                                                </span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="flex items-center justify-center h-full text-gray-500">
                            <p>Configure resources and click "Estimate Cost"</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CostManagement;
