import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink, Database } from 'lucide-react';
import type { SourceCitation, UICitationCard } from '@/types/citations';
import { toUICitationCard, getConfidenceColor } from '@/types/citations';

interface SourcesDisplayProps {
    sources: SourceCitation[];
    queryTimeMs?: number;
    className?: string;
}

export const SourcesDisplay: React.FC<SourcesDisplayProps> = ({
    sources,
    queryTimeMs,
    className = '',
}) => {
    const [isExpanded, setIsExpanded] = useState(false);

    if (!sources || sources.length === 0) {
        return null;
    }

    const uiCitations = sources.map(toUICitationCard);
    const displayCitations = isExpanded ? uiCitations : uiCitations.slice(0, 3);
    const remainingCount = uiCitations.length - 3;

    return (
        <div className={`mt-3 border-t border-gray-100 pt-3 ${className}`}>
            {/* Header */}
            <div className="flex items-center gap-2 mb-2">
                <Database className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium text-gray-700">
                    Based on {uiCitations.length} source{uiCitations.length !== 1 ? 's' : ''}
                </span>
                {queryTimeMs && (
                    <span className="text-xs text-gray-400">
                        ({Math.round(queryTimeMs)}ms)
                    </span>
                )}
            </div>

            {/* Sources List */}
            <div className="space-y-2">
                {displayCitations.map((citation) => (
                    <SourceCard key={citation.id} citation={citation} />
                ))}
            </div>

            {/* Expand/Collapse Button */}
            {remainingCount > 0 && (
                <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="mt-2 flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 transition-colors"
                >
                    {isExpanded ? (
                        <>
                            <ChevronUp className="w-4 h-4" />
                            Show less
                        </>
                    ) : (
                        <>
                            <ChevronDown className="w-4 h-4" />
                            Show {remainingCount} more source{remainingCount !== 1 ? 's' : ''}
                        </>
                    )}
                </button>
            )}
        </div>
    );
};

interface SourceCardProps {
    citation: UICitationCard;
}

const SourceCard: React.FC<SourceCardProps> = ({ citation }) => {
    const [showDetails, setShowDetails] = useState(false);

    return (
        <div className="bg-gray-50 rounded-lg p-3 hover:bg-gray-100 transition-colors">
            <div className="flex items-start gap-3">
                {/* Icon */}
                <span className="text-xl flex-shrink-0">{citation.icon}</span>

                {/* Main Info */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-gray-900 truncate">
                            {citation.name}
                        </span>
                        <ConfidenceBadge confidence={citation.confidence} />
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-500 mt-1">
                        <span className="capitalize">{citation.type.replace(/_/g, ' ')}</span>
                        <span>•</span>
                        <span>{citation.source}</span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                        {citation.description}
                    </p>
                </div>

                {/* Toggle Details Button */}
                <button
                    onClick={() => setShowDetails(!showDetails)}
                    className={`p-1 rounded transition-colors ${showDetails ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-gray-600'
                        }`}
                    title="View raw data"
                >
                    <ExternalLink className="w-4 h-4" />
                </button>
            </div>

            {/* Expanded Details */}
            {showDetails && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                    <div className="text-xs text-gray-500 mb-2">
                        Retrieved: {new Date(citation.retrieved_at).toLocaleString()}
                    </div>
                    {citation.metadata && Object.keys(citation.metadata).length > 0 && (
                        <div className="bg-white rounded p-2 text-xs font-mono overflow-x-auto">
                            <pre className="whitespace-pre-wrap">
                                {JSON.stringify(citation.metadata, null, 2)}
                            </pre>
                        </div>
                    )}
                    {citation.raw_data && (
                        <div className="bg-white rounded p-2 text-xs font-mono overflow-x-auto mt-2">
                            <pre className="whitespace-pre-wrap">
                                {JSON.stringify(citation.raw_data, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

interface ConfidenceBadgeProps {
    confidence: number;
}

const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({ confidence }) => {
    const colorClass = getConfidenceColor(confidence);
    const label =
        confidence >= 0.9 ? 'High' :
            confidence >= 0.7 ? 'Medium' :
                confidence >= 0.5 ? 'Low' : 'Uncertain';

    return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${colorClass}`}>
            {label}
        </span>
    );
};

export default SourcesDisplay;
