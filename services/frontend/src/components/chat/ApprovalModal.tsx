import React, { useState } from 'react';
import type { ActionApproval } from '@/types/conversation';
import { RISK_COLORS } from '@/types/conversation';

interface ApprovalModalProps {
    isOpen: boolean;
    approval: ActionApproval | null;
    onApprove: (reason?: string) => void;
    onReject: (reason: string) => void;
    onClose: () => void;
}

const RISK_CONFIG: Record<string, { icon: string; bgColor: string; borderColor: string }> = {
    LOW: {
        icon: '✅',
        bgColor: 'bg-green-50',
        borderColor: 'border-green-200',
    },
    MEDIUM: {
        icon: '⚡',
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-200',
    },
    HIGH: {
        icon: '⚠️',
        bgColor: 'bg-orange-50',
        borderColor: 'border-orange-200',
    },
    CRITICAL: {
        icon: '🚨',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
    },
};

export const ApprovalModal: React.FC<ApprovalModalProps> = ({
    isOpen,
    approval,
    onApprove,
    onReject,
    onClose,
}) => {
    const [rejectReason, setRejectReason] = useState('');
    const [showRejectForm, setShowRejectForm] = useState(false);

    if (!isOpen || !approval) return null;

    const riskConfig = RISK_CONFIG[approval.risk_level] || RISK_CONFIG.LOW;
    const expiresAt = new Date(approval.expires_at);
    const timeUntilExpiry = expiresAt.getTime() - Date.now();
    const hoursLeft = Math.floor(timeUntilExpiry / (1000 * 60 * 60));
    const minutesLeft = Math.floor((timeUntilExpiry % (1000 * 60 * 60)) / (1000 * 60));

    const formatTimeLeft = () => {
        if (hoursLeft > 0) return `${hoursLeft}h ${minutesLeft}m`;
        return `${minutesLeft}m`;
    };

    const handleApprove = () => {
        onApprove();
        setShowRejectForm(false);
        setRejectReason('');
    };

    const handleReject = () => {
        if (rejectReason.trim()) {
            onReject(rejectReason);
            setShowRejectForm(false);
            setRejectReason('');
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="w-full max-w-2xl bg-white rounded-xl shadow-2xl overflow-hidden">
                {/* Header */}
                <div className={`px-6 py-4 ${riskConfig.bgColor} border-b ${riskConfig.borderColor}`}>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <span className="text-2xl">{riskConfig.icon}</span>
                            <div>
                                <h2 className="text-lg font-semibold text-gray-900">
                                    Action Approval Required
                                </h2>
                                <p className="text-sm text-gray-600">
                                    Risk Level: <span className="font-medium">{approval.risk_level}</span>
                                </p>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-gray-200 rounded-lg transition-colors"
                        >
                            <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="px-6 py-4 max-h-96 overflow-y-auto">
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
                            <div className="flex justify-between">
                                <span className="text-gray-600">Requested by:</span>
                                <span className="font-medium text-gray-900">{approval.user_id}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-600">Expires in:</span>
                                <span className="font-medium text-gray-900">{formatTimeLeft()}</span>
                            </div>
                        </div>
                    </div>

                    {/* Description */}
                    <div className="mb-6">
                        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
                            Description
                        </h3>
                        <p className="text-gray-900">{approval.description}</p>
                    </div>

                    {/* Impact Summary */}
                    <div className="mb-6">
                        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
                            Expected Impact
                        </h3>
                        <p className="text-gray-900">{approval.impact_summary}</p>
                    </div>

                    {/* Rollback Plan */}
                    {approval.rollback_plan && (
                        <div className="mb-6">
                            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">
                                Rollback Plan
                            </h3>
                            <p className="text-gray-900">{approval.rollback_plan}</p>
                        </div>
                    )}

                    {/* Reject Form */}
                    {showRejectForm && (
                        <div className="mb-6 p-4 bg-red-50 rounded-lg border border-red-200">
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
                </div>

                {/* Footer */}
                <div className="px-6 py-4 bg-gray-50 border-t flex items-center justify-between">
                    <div className="text-sm text-gray-500">
                        Request ID: {approval.id.slice(0, 8)}...
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
