/** Budget Tracker Component */

import React, { useState } from 'react';
import { Plus, Edit2, Trash2, AlertTriangle, CheckCircle } from 'lucide-react';
import type { Budget, BudgetSummary } from '@/types/cost';

interface BudgetTrackerProps {
    budgets: Budget[];
    summary: BudgetSummary;
    onCreateBudget?: (budget: Partial<Budget>) => void;
    onUpdateBudget?: (id: string, updates: Partial<Budget>) => void;
    onDeleteBudget?: (id: string) => void;
}

export const BudgetTracker: React.FC<BudgetTrackerProps> = ({
    budgets,
    summary,
    onCreateBudget,
    onUpdateBudget,
    onDeleteBudget,
}) => {
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [editingBudget, setEditingBudget] = useState<Budget | null>(null);

    const formatCurrency = (amount: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    };

    const getStatusColor = (percentage: number) => {
        if (percentage >= 100) return 'bg-red-500';
        if (percentage >= 80) return 'bg-yellow-500';
        if (percentage >= 50) return 'bg-blue-500';
        return 'bg-green-500';
    };

    return (
        <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-lg shadow p-6">
                    <p className="text-sm text-gray-500">Total Budget</p>
                    <p className="text-2xl font-bold mt-1">
                        {formatCurrency(summary.total_budget_amount)}
                    </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                    <p className="text-sm text-gray-500">Total Spend</p>
                    <p className="text-2xl font-bold mt-1">
                        {formatCurrency(summary.total_spend)}
                    </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                    <p className="text-sm text-gray-500">Utilization</p>
                    <p className="text-2xl font-bold mt-1">
                        {summary.utilization_percent.toFixed(1)}%
                    </p>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                    <p className="text-sm text-gray-500">Active Alerts</p>
                    <p className={`text-2xl font-bold mt-1 ${summary.active_alerts > 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {summary.active_alerts}
                    </p>
                </div>
            </div>

            {/* Budgets List */}
            <div className="bg-white rounded-lg shadow">
                <div className="flex items-center justify-between p-6 border-b">
                    <h3 className="text-lg font-semibold">Budgets</h3>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        <Plus className="w-4 h-4 mr-2" />
                        Create Budget
                    </button>
                </div>

                <div className="divide-y">
                    {budgets.map((budget) => (
                        <div key={budget.id} className="p-6">
                            <div className="flex items-center justify-between mb-4">
                                <div>
                                    <h4 className="font-semibold">{budget.name}</h4>
                                    <p className="text-sm text-gray-500">{budget.description}</p>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <button
                                        onClick={() => setEditingBudget(budget)}
                                        className="p-2 text-gray-500 hover:text-blue-600 rounded-lg hover:bg-gray-100"
                                    >
                                        <Edit2 className="w-4 h-4" />
                                    </button>
                                    <button
                                        onClick={() => onDeleteBudget?.(budget.id)}
                                        className="p-2 text-gray-500 hover:text-red-600 rounded-lg hover:bg-gray-100"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>

                            {/* Progress Bar */}
                            <div className="mb-4">
                                <div className="flex items-center justify-between text-sm mb-1">
                                    <span className="text-gray-500">
                                        {formatCurrency(budget.current_spend)} / {formatCurrency(budget.amount)}
                                    </span>
                                    <span
                                        className={`font-medium ${budget.percentage_used >= 100
                                                ? 'text-red-600'
                                                : budget.percentage_used >= 80
                                                    ? 'text-yellow-600'
                                                    : 'text-green-600'
                                            }`}
                                    >
                                        {budget.percentage_used.toFixed(1)}%
                                    </span>
                                </div>
                                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full ${getStatusColor(budget.percentage_used)} transition-all duration-300`}
                                        style={{ width: `${Math.min(budget.percentage_used, 100)}%` }}
                                    />
                                </div>
                            </div>

                            {/* Details */}
                            <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                                <span>Period: {budget.period}</span>
                                {budget.cloud_provider && (
                                    <span className="capitalize">Provider: {budget.cloud_provider}</span>
                                )}
                                {budget.cluster_id && <span>Cluster: {budget.cluster_id}</span>}
                                <span>
                                    Ends: {budget.end_date ? new Date(budget.end_date).toLocaleDateString() : 'Ongoing'}
                                </span>
                            </div>

                            {/* Alert Thresholds */}
                            {budget.alert_thresholds && budget.alert_thresholds.length > 0 && (
                                <div className="mt-4 flex items-center gap-2">
                                    <AlertTriangle className="w-4 h-4 text-yellow-500" />
                                    <span className="text-sm text-gray-500">Alerts at:</span>
                                    {budget.alert_thresholds.map((threshold) => (
                                        <span
                                            key={threshold}
                                            className={`inline-flex items-center px-2 py-1 rounded-full text-xs ${budget.percentage_used >= threshold
                                                    ? 'bg-red-100 text-red-800'
                                                    : 'bg-gray-100 text-gray-800'
                                                }`}
                                        >
                                            {threshold}%
                                        </span>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}

                    {budgets.length === 0 && (
                        <div className="p-12 text-center text-gray-500">
                            <CheckCircle className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                            <p>No budgets configured</p>
                            <button
                                onClick={() => setShowCreateModal(true)}
                                className="mt-4 text-blue-600 hover:text-blue-700 font-medium"
                            >
                                Create your first budget
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Create/Edit Modal */}
            {(showCreateModal || editingBudget) && (
                <BudgetModal
                    budget={editingBudget}
                    onClose={() => {
                        setShowCreateModal(false);
                        setEditingBudget(null);
                    }}
                    onSave={(budget) => {
                        if (editingBudget) {
                            onUpdateBudget?.(editingBudget.id, budget);
                        } else {
                            onCreateBudget?.(budget);
                        }
                        setShowCreateModal(false);
                        setEditingBudget(null);
                    }}
                />
            )}
        </div>
    );
};

// Budget Modal Component
interface BudgetModalProps {
    budget: Budget | null;
    onClose: () => void;
    onSave: (budget: Partial<Budget>) => void;
}

const BudgetModal: React.FC<BudgetModalProps> = ({ budget, onClose, onSave }) => {
    const [formData, setFormData] = useState({
        name: budget?.name || '',
        description: budget?.description || '',
        amount: budget?.amount?.toString() || '',
        period: budget?.period || 'monthly',
        cloud_provider: budget?.cloud_provider || '',
        alert_thresholds: budget?.alert_thresholds?.join(',') || '50,80,90,100',
        notify_email: budget?.notify_email?.join(',') || '',
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSave({
            name: formData.name,
            description: formData.description,
            amount: parseFloat(formData.amount),
            period: formData.period as Budget['period'],
            cloud_provider: formData.cloud_provider as Budget['cloud_provider'] || undefined,
            alert_thresholds: formData.alert_thresholds.split(',').map((t) => parseInt(t.trim())),
            notify_email: formData.notify_email.split(',').map((e) => e.trim()).filter(Boolean),
        });
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
                <h3 className="text-lg font-semibold mb-4">
                    {budget ? 'Edit Budget' : 'Create Budget'}
                </h3>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Budget Name
                        </label>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Description
                        </label>
                        <textarea
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            rows={2}
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Amount (USD)
                        </label>
                        <input
                            type="number"
                            value={formData.amount}
                            onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            required
                            min="0"
                            step="0.01"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Period
                        </label>
                        <select
                            value={formData.period}
                            onChange={(e) => setFormData({ ...formData, period: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                            <option value="daily">Daily</option>
                            <option value="weekly">Weekly</option>
                            <option value="monthly">Monthly</option>
                            <option value="quarterly">Quarterly</option>
                            <option value="yearly">Yearly</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Alert Thresholds (comma-separated)
                        </label>
                        <input
                            type="text"
                            value={formData.alert_thresholds}
                            onChange={(e) => setFormData({ ...formData, alert_thresholds: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="50,80,90,100"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Notification Emails (comma-separated)
                        </label>
                        <input
                            type="text"
                            value={formData.notify_email}
                            onChange={(e) => setFormData({ ...formData, notify_email: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="team@example.com"
                        />
                    </div>

                    <div className="flex justify-end space-x-3 pt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            {budget ? 'Update' : 'Create'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
