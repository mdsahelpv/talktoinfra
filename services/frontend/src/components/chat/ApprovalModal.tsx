import React, { useState } from 'react';
import type { ActionApproval } from '@/types/conversation';
import ApprovalChainIndicator from './ApprovalChainIndicator';

interface ApprovalModalProps {
    isOpen: boolean;
    approval: ActionApproval | null;
    onApprove: (reason?: string) => void;
    onReject: (reason: string) => void;
    onClose: () => void;
    onEscalate?: () => void;
}

const RISK_CONFIG: Record<string, { icon: string; bgColor: string; borderColor: string; textColor: string }> = {
    LOW: {
        icon: '✅',
        bgColor: 'bg-green-50',
        borderColor: 'border-green-200',
        textColor: 'text-green-800',
    },
    MEDIUM: {
        icon: '⚡',
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-200',
        textColor: 'text-yellow-800',
    },
    HIGH: {
        icon: '⚠️',
        bgColor: 'bg-orange-50',
        borderColor: 'border-orange-200',
        textColor: 'text-orange-800',
    },
    CRITICAL: {
        icon: '🚨',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
        textColor: 'text-red-800',
    },
};

const CHANGE_TYPE_ICONS: Record<string, string> = {
    create: '➕',
    update: '✏️',
    delete: '🗑️',
    read: '👁️',
};

export const ApprovalModal: React.FC<ApprovalModalProps> = ({
    isOpen,
    approval,
    onApprove,
    onReject,
    onClose,
    onEscalate,
}) => {
    const [rejectReason, setRejectReason] = useState('');
    const [showRejectForm, setShowRejectForm] = useState(false);
    const [activeTab, setActiveTab] = useState<'details' | 'impact' | 'chain'>('details');

    if (!isOpen || !approval) return null;

    const riskConfig = RISK_CONFIG[approval.risk_level] || RISK_CONFIG.LOW;
    const expiresAt = new Date(approval.expires_at);
    const timeUntilExpiry = expiresAt.getTime() - Date.now();
    const hoursLeft = Math.floor(timeUntilExpiry / (1000 * 60 * 60));
    const minutesLeft = Math.floor((timeUntilExpiry % (1000 * 60 * 60)) / (1000 * 60));

    const formatTimeLeft = (): string => {
        if (timeUntilExpiry <= 0) return 'Expired';
        if (hoursLeft > 0) return `${hoursLeft}h ${minutesLeft}m`;
        return `${minutesLeft}m`;
    };

    const handleApprove = (): void => {
        onApprove();
        setShowRejectForm(false);
        setRejectReason('');
    };

    const handleReject = (): void => {
        if (rejectReason.trim()) {
            onReject(rejectReason);
            setShowRejectForm(false);
            setRejectReason('');
        }
    };

    const renderRiskIndicator = (label: string, value: string, icon: string): React.ReactNode => (
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${riskConfig.bgColor}`}>
            <span className="text-lg">{icon}</span>
            <div>
                <p className="text-xs text-gray-600 uppercase">{label}</p>
                <p className={`text-sm font-medium ${riskConfig.textColor}`}>{value}</p>
            </div>
        </div>
    );

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="w-full max-w-4xl bg-white rounded-xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className={`px-6 py-4 ${riskConfig.bgColor} border-b ${riskConfig.borderColor}`}>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <span className="text-3xl">{riskConfig.icon}</span>
                            <div>
                                <h2 className="text-xl font-semibold text-gray-900">
                                    Action Approval Required
                                </h2>
                                <p className="text-sm text-gray-600">
                                    Risk Level: <span className={`font-bold ${riskConfig.textColor}`}>{approval.risk_level}</span>
                                </p>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
                            aria-label="Close modal"
                        >
                            <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Tabs */}
                <div className="flex border-b">
                    {(['details', 'impact', 'chain'] as const).map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`px-4 py-3 text-sm font-medium transition-colors ${activeTab === tab
                                ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                                : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                                }`}
                        >
                            {tab.charAt(0).toUpperCase() + tab.slice(1)}
                        </button>
                    ))}
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto px-6 py-4">
                    {activeTab === 'details' && (
                        <>
                            {/* Quick Stats */}
                            <div className="grid grid-cols-4 gap-3 mb-6">
                                {renderRiskIndicator('Expires In', formatTimeLeft(), '⏱️')}
                                {renderRiskIndicator('Targets', approval.target_resources.length.toString(), '🎯')}
                                {renderRiskIndicator('Request ID', approval.id.slice(0, 8), '🆔')}
                                {renderRiskIndicator('Requested By', approval.user_id, '👤')}
                            </div>

                            {/* Action Details */}
                            <div className="mb-6">
                                <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
                                    Action Details
                                </h3>
                                <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Type:</span>
                                        <span className="font-medium text-gray-900">{approval.action_type}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Targets:</span>
                                        <span className="font-medium text-gray-900">
                                            {approval.target_resources.join(', ') || 'N/A'}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Description */}
                            <div className="mb-6">
                                <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
                                    Description
                                </h3>
                                <p className="text-gray-900 bg-gray-50 rounded-lg p-4">{approval.description}</p>
                            </div>

                            {/* Rollback Plan */}
                            {approval.rollback_plan && (
                                <div className="mb-6">
                                    <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
                                        Rollback Plan
                                    </h3>
                                    <p className="text-gray-900 bg-gray-50 rounded-lg p-4">{approval.rollback_plan}</p>
                                </div>
                            )}
                        </>
                    )}

                    {activeTab === 'impact' && (
                        <>
                            {/* Impact Summary */}
                            <div className="mb-6">
                                <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
                                    Expected Impact
                                </h3>
                                <p className="text-gray-900 bg-gray-50 rounded-lg p-4">{approval.impact_summary}</p>
                            </div>

                            {/* Affected Resources */}
                            {approval.affected_resources && approval.affected_resources.length > 0 && (
                                <div className="mb-6">
                                    <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
                                        Affected Resources
                                    </h3>
                                    <div className="bg-gray-50 rounded-lg p-4">
                                        <div className="space-y-3">
                                            {approval.affected_resources.map((resource, index) => (
                                                <div key={index} className="flex items-start gap-3 p-3 bg-white rounded-lg border border-gray-200">
                                                    <span className="text-xl">{CHANGE_TYPE_ICONS[resource.change_type] || '📦'}</span>
                                                    <div className="flex-1">
                                                        <p className="font-medium text-gray-900">
                                                            {resource.type}/{resource.name}
                                                        </p>
                                                        {resource.before_state && (
                                                            <div className="mt-2 text-sm">
                                                                <p className="text-gray-500">Before:</p>
                                                                <pre className="text-xs bg-gray-100 p-2 rounded mt-1 overflow-x-auto">
                                                                    {JSON.stringify(resource.before_state, null, 2)}
                                                                </pre>
                                                            </div>
                                                        )}
                                                        {resource.after_state && (
                                                            <div className="mt-2 text-sm">
                                                                <p className="text-gray-500">After:</p>
                                                                <pre className="text-xs bg-green-100 p-2 rounded mt-1 overflow-x-auto">
                                                                    {JSON.stringify(resource.after_state, null, 2)}
                                                                </pre>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Risk Analysis */}
                            {approval.risk_analysis && (
                                <div className="mb-6">
                                    <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
                                        Risk Analysis
                                    </h3>
                                    <div className="bg-gray-50 rounded-lg p-4 space-y-4">
                                        {/* What Could Go Wrong */}
                                        <div>
                                            <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                                                <span>⚠️</span> What Could Go Wrong
                                            </h4>
                                            <ul className="space-y-1">
                                                {approval.risk_analysis.what_could_go_wrong.map((risk, index) => (
                                                    <li key={index} className="text-sm text-gray-600 flex items-start gap-2">
                                                        <span className="text-red-500 mt-0.5">•</span>
                                                        {risk}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>

                                        {/* Dependencies */}
                                        <div>
                                            <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                                                <span>🔗</span> Dependencies
                                            </h4>
                                            <ul className="space-y-1">
                                                {approval.risk_analysis.dependencies.map((dep, index) => (
                                                    <li key={index} className="text-sm text-gray-600 flex items-start gap-2">
                                                        <span className="text-blue-500 mt-0.5">•</span>
                                                        {dep}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>

                                        {/* Time Estimates */}
                                        <div className="grid grid-cols-2 gap-4">
                                            <div className="p-3 bg-orange-50 rounded-lg border border-orange-200">
                                                <p className="text-xs text-orange-600 uppercase">Estimated Downtime</p>
                                                <p className="text-sm font-medium text-orange-800">{approval.risk_analysis.estimated_downtime}</p>
                                            </div>
                                            <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                                                <p className="text-xs text-blue-600 uppercase">Rollback Time</p>
                                                <p className="text-sm font-medium text-blue-800">{approval.risk_analysis.rollback_time_estimate}</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </>
                    )}

                    {activeTab === 'chain' && approval.approval_chain && (
                        <ApprovalChainIndicator
                            chain={approval.approval_chain}
                            onEscalate={onEscalate}
                            showActions={true}
                        />
                    )}
                </div>

                {/* Reject Form */}
                {showRejectForm && (
                    <div className="px-6 py-4 bg-red-50 border-t border-red-200">
                        <label className="block text-sm font-medium text-red-800 mb-2">
                            Please provide a reason for rejection:
                        </label>
                        <textarea
                            value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                            className="w-full px-3 py-2 border border-red-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                            rows={3}
                            placeholder="Enter the reason for rejecting this action..."
                        />
                        <div className="flex justify-end gap-2 mt-3">
                            <button
                                onClick={() => {
                                    setShowRejectForm(false);
                                    setRejectReason('');
                                }}
                                className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleReject}
                                disabled={!rejectReason.trim()}
                                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Confirm Rejection
                            </button>
                        </div>
                    </div>
                )}

                {/* Footer */}
                <div className="px-6 py-4 bg-gray-50 border-t flex items-center justify-between">
                    <div className="text-sm text-gray-500">
                        Request ID: {approval.id.slice(0, 12)}
                    </div>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => setShowRejectForm(true)}
                            className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
                        >
                            Reject
                        </button>
                        <button
                            onClick={handleApprove}
                            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                        >
                            Approve
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ApprovalModal;
