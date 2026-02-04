/**
 * Discovery Suggestions Panel Component
 * 
 * Shows infrastructure suggestions from discovery scans with
 * one-click onboarding options.
 */

import React, { useState } from 'react';
import { Card, Button, Badge, Spinner, Alert } from '@/components/ui';
import { useQuery, useMutation } from '@tanstack/react-query';

interface Suggestion {
    id: string;
    type: 'k8s_cluster' | 'aws_account' | 'azure_account' | 'gcp_account' | 'database' | 'load_balancer';
    confidence: number;
    title: string;
    description: string;
    recommendation: string;
    suggested_name: string;
    api_endpoint?: string;
    port?: number;
    host_count: number;
    hosts: string[];
    cloud_provider?: string;
    metadata: Record<string, unknown>;
}

interface SuggestionsResponse {
    scan_id: string;
    total_suggestions: number;
    k8s_suggestions: Suggestion[];
    cloud_suggestions: Suggestion[];
    database_suggestions: Suggestion[];
    load_balancer_suggestions: Suggestion[];
    generated_at: string;
}

interface DiscoverySuggestionsProps {
    scanId: string;
    onOnboard?: (suggestion: Suggestion) => void;
}

export const DiscoverySuggestions: React.FC<DiscoverySuggestionsProps> = ({
    scanId,
    onOnboard,
}) => {
    const [selectedSuggestion, setSelectedSuggestion] = useState<Suggestion | null>(null);

    // Fetch suggestions
    const {
        data: suggestionsData,
        isLoading,
        error,
        refetch,
    } = useQuery<SuggestionsResponse>({
        queryKey: ['suggestions', scanId],
        queryFn: async () => {
            const response = await fetch(`/api/v1/discovery/${scanId}/suggestions`);
            if (!response.ok) {
                throw new Error('Failed to fetch suggestions');
            }
            return response.json();
        },
        enabled: !!scanId,
        refetchInterval: false,
    });

    // Execute onboarding mutation
    const onboardMutation = useMutation({
        mutationFn: async (suggestion: Suggestion) => {
            const response = await fetch('/api/v1/discovery/suggestions/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    suggestion_id: suggestion.id,
                    suggestion_type: suggestion.type,
                    suggested_name: suggestion.suggested_name,
                    api_endpoint: suggestion.api_endpoint,
                    port: suggestion.port,
                    hosts: suggestion.hosts,
                    cloud_provider: suggestion.cloud_provider,
                    metadata: suggestion.metadata,
                }),
            });
            if (!response.ok) {
                throw new Error('Failed to execute onboarding');
            }
            return response.json();
        },
        onSuccess: (data, suggestion) => {
            if (onOnboard) {
                onOnboard(suggestion);
            }
        },
    });

    const getConfidenceBadge = (confidence: number) => {
        if (confidence >= 0.8) {
            return <Badge variant="success">High Confidence</Badge>;
        } else if (confidence >= 0.5) {
            return <Badge variant="warning">Medium Confidence</Badge>;
        }
        return <Badge variant="info">Low Confidence</Badge>;
    };

    const getTypeIcon = (type: Suggestion['type']) => {
        switch (type) {
            case 'k8s_cluster':
                return '☸️';
            case 'aws_account':
                return '☁️';
            case 'azure_account':
                return '🔵';
            case 'gcp_account':
                return '🔴';
            case 'database':
                return '🗄️';
            case 'load_balancer':
                return '⚖️';
            default:
                return '📦';
        }
    };

    const handleOnboard = (suggestion: Suggestion) => {
        if (suggestion.type === 'k8s_cluster') {
            onboardMutation.mutate(suggestion);
        } else {
            if (onOnboard) {
                onOnboard(suggestion);
            }
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center p-8">
                <Spinner size="lg" />
                <span className="ml-2">Analyzing scan results...</span>
            </div>
        );
    }

    if (error) {
        return (
            <Alert variant="error">
                Failed to load suggestions. Please try again.
            </Alert>
        );
    }

    if (!suggestionsData || suggestionsData.total_suggestions === 0) {
        return (
            <Card className="p-6">
                <div className="text-center text-gray-500">
                    <p className="text-lg">🔍 No infrastructure suggestions found</p>
                    <p className="text-sm">
                        Complete a network scan to see recommendations for onboarding discovered infrastructure.
                    </p>
                </div>
            </Card>
        );
    }

    const allSuggestions = [
        ...suggestionsData.k8s_suggestions,
        ...suggestionsData.cloud_suggestions,
        ...suggestionsData.database_suggestions,
        ...suggestionsData.load_balancer_suggestions,
    ];

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">Infrastructure Suggestions</h2>
                <Button variant="outline" onClick={() => refetch()}>
                    Refresh
                </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {allSuggestions.map((suggestion) => (
                    <SuggestionCard
                        key={suggestion.id}
                        suggestion={suggestion}
                        isLoading={onboardMutation.isPending && selectedSuggestion?.id === suggestion.id}
                        onOnboard={() => {
                            setSelectedSuggestion(suggestion);
                            handleOnboard(suggestion);
                        }}
                        getConfidenceBadge={getConfidenceBadge}
                        getTypeIcon={getTypeIcon}
                    />
                ))}
            </div>

            {suggestionsData.total_suggestions > 0 && (
                <div className="text-sm text-gray-500 text-center">
                    Generated at: {new Date(suggestionsData.generated_at).toLocaleString()}
                </div>
            )}
        </div>
    );
};

interface SuggestionCardProps {
    suggestion: Suggestion;
    isLoading: boolean;
    onOnboard: () => void;
    getConfidenceBadge: (confidence: number) => React.ReactNode;
    getTypeIcon: (type: Suggestion['type']) => string;
}

const SuggestionCard: React.FC<SuggestionCardProps> = ({
    suggestion,
    isLoading,
    onOnboard,
    getConfidenceBadge,
    getTypeIcon,
}) => {
    const [expanded, setExpanded] = useState(false);

    return (
        <Card className="overflow-hidden hover:shadow-md transition-shadow">
            <div className="p-4">
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                        <span className="text-2xl">{getTypeIcon(suggestion.type)}</span>
                        <div>
                            <h3 className="font-medium">{suggestion.title}</h3>
                            <p className="text-sm text-gray-500">{suggestion.suggested_name}</p>
                        </div>
                    </div>
                    {getConfidenceBadge(suggestion.confidence)}
                </div>

                <p className="mt-3 text-sm text-gray-600">{suggestion.description}</p>

                {suggestion.api_endpoint && (
                    <div className="mt-2 text-xs text-gray-500 font-mono">
                        {suggestion.api_endpoint}:{suggestion.port || 6443}
                    </div>
                )}

                <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                    <span>{suggestion.host_count} host(s)</span>
                    {suggestion.cloud_provider && (
                        <Badge variant="info">{suggestion.cloud_provider}</Badge>
                    )}
                </div>

                <button
                    className="mt-2 text-xs text-blue-600 hover:underline"
                    onClick={() => setExpanded(!expanded)}
                >
                    {expanded ? 'Show less' : 'Show hosts'}
                </button>

                {expanded && (
                    <div className="mt-2 p-2 bg-gray-50 rounded text-xs font-mono max-h-24 overflow-y-auto">
                        {suggestion.hosts.map((host, i) => (
                            <div key={i}>{host}</div>
                        ))}
                    </div>
                )}

                <div className="mt-4 pt-4 border-t flex items-center justify-between">
                    <p className="text-xs text-gray-500">{suggestion.recommendation}</p>
                    <Button
                        size="sm"
                        onClick={onOnboard}
                        disabled={isLoading}
                    >
                        {isLoading ? (
                            <>
                                <Spinner size="sm" className="mr-1" />
                                Onboarding...
                            </>
                        ) : (
                            'Import'
                        )}
                    </Button>
                </div>
            </div>
        </Card>
    );
};

export default DiscoverySuggestions;
