import React from 'react';
import type { ApprovalChainIndicatorProps } from '@/types/conversation';
import { APPROVAL_LEVEL_CONFIG, APPROVAL_LEVEL_ORDER } from '@/types/conversation';

const ApprovalChainIndicator: React.FC<ApprovalChainIndicatorProps> = ({
    chain,
    onEscalate,
    showActions = true,
}) => {
    const currentLevelIndex = APPROVAL_LEVEL_ORDER.indexOf(chain.current_level);
    const targetLevelIndex = APPROVAL_LEVEL_ORDER.indexOf(chain.target_level);
    const totalLevels = targetLevelIndex + 1;

    const getLevelStatus = (levelIndex: number): 'completed' | 'current' | 'pending' => {
        if (levelIndex < currentLevelIndex) return 'completed';
        if (levelIndex === currentLevelIndex) return 'current';
        return 'pending';
    };

    return (
        <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <h4 className="text-sm font-medium text-gray-700 uppercase tracking-wider">
                    Approval Chain
                </h4>
                <span className="text-sm text-gray-500">
                    Level {currentLevelIndex + 1} of {totalLevels}
                </span>
            </div>

            {/* Progress Steps */}
            <div className="flex items-center justify-between mb-4">
                {APPROVAL_LEVEL_ORDER.slice(0, totalLevels).map((level, index) => {
                    const config = APPROVAL_LEVEL_CONFIG[level];
                    const status = getLevelStatus(index);
                    const isLast = index === totalLevels - 1;

                    return (
                        <React.Fragment key={level}>
                            <div className="flex flex-col items-center">
                                <div
                                    className={`
                                        w-10 h-10 rounded-full flex items-center justify-center text-lg font-medium
                                        ${status === 'completed' ? 'bg-green-100 text-green-800' : ''}
                                        ${status === 'current' ? 'bg-blue-100 text-blue-800 ring-2 ring-blue-300 ring-offset-2' : ''}
                                        ${status === 'pending' ? 'bg-gray-100 text-gray-400' : ''}
                                    `}
                                >
                                    {status === 'completed' ? '✓' : config.icon}
                                </div>
                                <span className={`text-xs mt-1 ${status === 'pending' ? 'text-gray-400' : 'text-gray-700'}`}>
                                    {config.label}
                                </span>
                            </div>
                            {!isLast && (
                                <div className={`flex-1 h-1 mx-2 ${status === 'completed' ? 'bg-green-300' : 'bg-gray-200'}`} />
                            )}
                        </React.Fragment>
                    );
                })}
            </div>

            {/* Rules Display */}
            {chain.rules.length > 0 && (
                <div className="mb-4">
                    <h5 className="text-xs font-medium text-gray-500 uppercase mb-2">
                        Approval Rules
                    </h5>
                    <ul className="space-y-1">
                        {chain.rules.map((rule) => (
                            <li key={rule.id} className="text-sm text-gray-600 flex items-start gap-2">
                                <span className="text-blue-500 mt-0.5">•</span>
                                <span>
                                    <strong>{APPROVAL_LEVEL_CONFIG[rule.level].label}:</strong> {rule.description}
                                </span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Approver History */}
            {chain.history.length > 0 && (
                <div className="mb-4">
                    <h5 className="text-xs font-medium text-gray-500 uppercase mb-2">
                        Approver History
                    </h5>
                    <ul className="space-y-1">
                        {chain.history.map((entry, index) => (
                            <li key={index} className="text-sm text-gray-600">
                                {entry.action === 'approved' ? (
                                    <span className="text-green-600">✓</span>
                                ) : (
                                    <span className="text-red-600">✗</span>
                                )}
                                {' '}
                                {entry.approver_id} ({APPROVAL_LEVEL_CONFIG[entry.level].label}) - {new Date(entry.timestamp).toLocaleString()}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Escalate Button */}
            {showActions && onEscalate && chain.status === 'PENDING' && (
                <div className="flex justify-end">
                    <button
                        onClick={onEscalate}
                        className="px-3 py-1.5 text-sm bg-amber-100 text-amber-800 rounded-lg hover:bg-amber-200 transition-colors flex items-center gap-1"
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                        </svg>
                        Escalate to {APPROVAL_LEVEL_ORDER[Math.min(currentLevelIndex + 1, targetLevelIndex)]}
                    </button>
                </div>
            )}
        </div>
    );
};

export default ApprovalChainIndicator;
