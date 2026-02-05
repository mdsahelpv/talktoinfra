/** Model Card Component */

import { useState } from 'react';
import { Edit, Trash2, Play, ChevronDown, ChevronUp, Copy } from 'lucide-react';
import toast from 'react-hot-toast';
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    Button,
    Badge,
} from '@/components/ui';
import type { ModelConfig, ProviderConfig } from '@/lib/types';

interface ModelCardProps {
    model: ModelConfig;
    provider?: ProviderConfig;
    onEdit: (model: ModelConfig) => void;
    onDelete: (modelId: string) => void;
    onTest: (modelId: string) => void;
}

export function ModelCard({ model, provider, onEdit, onDelete, onTest }: ModelCardProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);

    const handleCopyId = async () => {
        await navigator.clipboard.writeText(model.id);
        toast.success('Model ID copied to clipboard');
    };

    const handleDelete = async () => {
        if (window.confirm(`Are you sure you want to delete model "${model.display_name}"?`)) {
            setIsDeleting(true);
            try {
                onDelete(model.id);
                toast.success('Model deleted successfully');
            } catch {
                toast.error('Failed to delete model');
            } finally {
                setIsDeleting(false);
            }
        }
    };

    const getCapabilityColor = (capability: string) => {
        const colors: Record<string, string> = {
            chat: 'bg-blue-100 text-blue-800',
            completion: 'bg-green-100 text-green-800',
            embedding: 'bg-purple-100 text-purple-800',
            function_calling: 'bg-orange-100 text-orange-800',
            vision: 'bg-pink-100 text-pink-800',
        };
        return colors[capability] || 'bg-gray-100 text-gray-800';
    };

    const getStatusBadge = () => {
        if (!model.enabled) {
            return <Badge variant="secondary">Disabled</Badge>;
        }
        if (model.is_default) {
            return <Badge variant="default">Default</Badge>;
        }
        return <Badge variant="outline">Enabled</Badge>;
    };

    return (
        <Card className="w-full">
            <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                            <span className="text-lg font-bold">{provider?.name?.[0] || model.name[0]}</span>
                        </div>
                        <div>
                            <CardTitle className="text-lg">{model.display_name}</CardTitle>
                            <p className="text-sm text-muted-foreground">{model.name}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {getStatusBadge()}
                        <Button variant="ghost" size="sm" onClick={() => setIsExpanded(!isExpanded)}>
                            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    {/* Quick Info */}
                    <div className="flex flex-wrap gap-2">
                        {model.capabilities.map((capability) => (
                            <Badge key={capability} className={getCapabilityColor(capability)}>
                                {capability}
                            </Badge>
                        ))}
                    </div>

                    {model.description && (
                        <p className="text-sm text-muted-foreground">{model.description}</p>
                    )}

                    {/* Parameters Summary */}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <span className="text-muted-foreground">Temperature:</span>{' '}
                            <span className="font-medium">{model.parameters.temperature ?? 'Default'}</span>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Max Tokens:</span>{' '}
                            <span className="font-medium">{model.parameters.max_tokens ?? model.max_output_tokens ?? 'Default'}</span>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Context Window:</span>{' '}
                            <span className="font-medium">{model.context_window?.toLocaleString() ?? 'N/A'}</span>
                        </div>
                        <div>
                            <span className="text-muted-foreground">Cost (1K):</span>{' '}
                            <span className="font-medium">
                                ${(model.cost_per_input ?? 0).toFixed(4)} / ${(model.cost_per_output ?? 0).toFixed(4)}
                            </span>
                        </div>
                    </div>

                    {/* Fallback Models */}
                    {model.fallback_models && model.fallback_models.length > 0 && (
                        <div className="text-sm">
                            <span className="text-muted-foreground">Fallbacks:</span>{' '}
                            <span className="font-medium">{model.fallback_models.join(', ')}</span>
                        </div>
                    )}

                    {/* Expanded Details */}
                    {isExpanded && (
                        <div className="rounded-lg bg-muted p-4 space-y-3">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium">Model ID</span>
                                <div className="flex items-center gap-2">
                                    <code className="text-xs bg-background px-2 py-1 rounded">{model.id}</code>
                                    <Button variant="ghost" size="sm" onClick={handleCopyId}>
                                        <Copy className="h-3 w-3" />
                                    </Button>
                                </div>
                            </div>
                            {model.parameters.top_p && (
                                <div className="text-sm">
                                    <span className="text-muted-foreground">Top P:</span>{' '}
                                    <span className="font-medium">{model.parameters.top_p}</span>
                                </div>
                            )}
                            {model.parameters.frequency_penalty !== undefined && (
                                <div className="text-sm">
                                    <span className="text-muted-foreground">Frequency Penalty:</span>{' '}
                                    <span className="font-medium">{model.parameters.frequency_penalty}</span>
                                </div>
                            )}
                            {model.parameters.presence_penalty !== undefined && (
                                <div className="text-sm">
                                    <span className="text-muted-foreground">Presence Penalty:</span>{' '}
                                    <span className="font-medium">{model.parameters.presence_penalty}</span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex items-center justify-end gap-2 pt-2 border-t">
                        <Button variant="outline" size="sm" onClick={() => onTest(model.id)}>
                            <Play className="h-4 w-4 mr-1" />
                            Test
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => onEdit(model)}>
                            <Edit className="h-4 w-4 mr-1" />
                            Edit
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={handleDelete}
                            disabled={isDeleting || model.is_default}
                            className="text-destructive hover:bg-destructive/10"
                        >
                            <Trash2 className="h-4 w-4 mr-1" />
                            Delete
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

export default ModelCard;
