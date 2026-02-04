import React from 'react';
import type { IntentClassification } from '@/types/conversation';
import { INTENT_COLORS } from '@/types/conversation';

interface IntentIndicatorProps {
    intent: IntentClassification;
    showDetails?: boolean;
    size?: 'sm' | 'md' | 'lg';
}

const INTENT_LABELS: Record<string, string> = {
    QUERY: 'Query',
    ACTION: 'Action',
    DISCOVERY: 'Discovery',
    ONBOARDING: 'Onboarding',
    MANAGEMENT: 'Management',
    ANALYSIS: 'Analysis',
    HELP: 'Help',
    UNKNOWN: 'Unknown',
};

const INTENT_ICONS: Record<string, string> = {
    QUERY: '🔍',
    ACTION: '⚡',
    DISCOVERY: '🗺️',
    ONBOARDING: '➕',
    MANAGEMENT: '⚙️',
    ANALYSIS: '📊',
    HELP: '❓',
    UNKNOWN: '❔',
};

const RISK_BADGES: Record<string, { label: string; color: string }> = {
    LOW: { label: 'Low Risk', color: 'bg-green-100 text-green-800' },
    MEDIUM: { label: 'Medium Risk', color: 'bg-yellow-100 text-yellow-800' },
    HIGH: { label: 'High Risk', color: 'bg-orange-100 text-orange-800' },
    CRITICAL: { label: 'Critical Risk', color: 'bg-red-100 text-red-800' },
};

const APPROVAL_BADGES: Record<string, { label: string; color: string }> = {
    true: { label: 'Approval Required', color: 'bg-purple-100 text-purple-800' },
    false: { label: 'Auto-Execute', color: 'bg-blue-100 text-blue-800' },
};

export const IntentIndicator: React.FC<IntentIndicatorProps> = ({
    intent,
    showDetails = false,
    size = 'md',
}) => {
    const { intent: intentType, confidence, requires_approval, risk_level, entities } = intent;

    const colorClass = (INTENT_COLORS as Record<string, string>)[intentType] || INTENT_COLORS.UNKNOWN;
    const icon = INTENT_ICONS[intentType] || INTENT_ICONS.UNKNOWN;
    const label = INTENT_LABELS[intentType] || 'Unknown';

    const sizeClasses = {
        sm: 'text-xs px-2 py-0.5',
        md: 'text-sm px-2.5 py-1',
        lg: 'text-base px-3 py-1.5',
    };

    const confidencePercent = Math.round(confidence * 100);

    const getConfidenceColor = (conf: number): string => {
        if (conf >= 0.8) return 'text-green-600';
        if (conf >= 0.6) return 'text-yellow-600';
        return 'text-red-600';
    };

    return (
        <div className="inline-flex flex-wrap items-center gap-2">
            {/* Main intent badge */}
            <span
                className={`inline-flex items-center gap-1.5 rounded-full font-medium ${colorClass} ${sizeClasses[size]}`}
            >
                <span className="text-base">{icon}</span>
                <span>{label}</span>
            </span>

            {/* Confidence score */}
            {showDetails && (
                <span className={`text-xs font-medium ${getConfidenceColor(confidence)}`}>
                    {confidencePercent}% confidence
                </span>
            )}

            {/* Approval requirement */}
            {showDetails && requires_approval && (
                <span className={`inline-flex items-center gap-1 rounded-full text-xs font-medium px-2 py-0.5 ${APPROVAL_BADGES.true.color}`}>
                    ⏳ Approval Required
                </span>
            )}

            {/* Risk level */}
            {showDetails && risk_level && (
                <span className={`inline-flex items-center gap-1 rounded-full text-xs font-medium px-2 py-0.5 ${RISK_BADGES[risk_level]?.color || ''}`}>
                    {risk_level === 'CRITICAL' && '🚨'}
                    {risk_level === 'HIGH' && '⚠️'}
                    {risk_level === 'MEDIUM' && '⚡'}
                    {risk_level === 'LOW' && '✅'}
                    {RISK_BADGES[risk_level]?.label || risk_level}
                </span>
            )}

            {/* Entity tags */}
            {showDetails && entities && entities.length > 0 && (
                <div className="inline-flex flex-wrap items-center gap-1 ml-2">
                    {entities.slice(0, 3).map((entity, index) => (
                        <span
                            key={index}
                            className="inline-flex items-center gap-1 rounded bg-gray-100 text-gray-700 text-xs px-1.5 py-0.5"
                        >
                            <span className="text-gray-500">{entity.type}:</span>
                            <span className="font-medium">{entity.value}</span>
                        </span>
                    ))}
                    {entities.length > 3 && (
                        <span className="text-xs text-gray-500">+{entities.length - 3} more</span>
                    )}
                </div>
            )}
        </div>
    );
};

export default IntentIndicator;
