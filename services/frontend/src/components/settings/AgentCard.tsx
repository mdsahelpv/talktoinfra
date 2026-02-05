/** Agent Card Component */

import { useState } from 'react';
import { Edit, Trash2, ChevronDown, ChevronUp, Shield, Settings } from 'lucide-react';
import toast from 'react-hot-toast';
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    Button,
    Badge,
} from '@/components/ui';
import type { AgentConfig, ModelConfig } from '@/lib/types';

interface AgentCardProps {
    agent: AgentConfig;
    model?: ModelConfig;
    onEdit: (agent: AgentConfig) => void;
    onDelete: (agentId: string) => void;
}

export function AgentCard({ agent, model, onEdit, onDelete }: AgentCardProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);

    const handleDelete = async () => {
        if (window.confirm(`Are you sure you want to delete agent "${agent.name}"?`)) {
            setIsDeleting(true);
            try {
                onDelete(agent.id);
                toast.success('Agent deleted successfully');
            } catch {
                toast.error('Failed to delete agent');
            } finally {
                setIsDeleting(false);
            }
        }
    };

    const getAgentIcon = (type: string) => {
        const icons: Record<string, string> = {
            query: '🔍',
            action: '⚡',
            analysis: '📊',
            planning: '📋',
        };
        return icons[type] || '🤖';
    };

    const getAgentColor = (type: string) => {
        const colors: Record<string, string> = {
            query: 'bg-blue-100 text-blue-800',
            action: 'bg-orange-100 text-orange-800',
            analysis: 'bg-green-100 text-green-800',
            planning: 'bg-purple-100 text-purple-800',
        };
        return colors[type] || 'bg-gray-100 text-gray-800';
    };

    const getSafetyBadge = (level: string) => {
        const colors: Record<string, string> = {
            low: 'bg-green-100 text-green-800',
            medium: 'bg-yellow-100 text-yellow-800',
            high: 'bg-orange-100 text-orange-800',
            critical: 'bg-red-100 text-red-800',
        };
        return (
            <Badge className={colors[level] || 'bg-gray-100 text-gray-800'}>
                <Shield className="h-3 w-3 mr-1" />
                {level}
            </Badge>
        );
    };

    const getEnabledBadge = () => {
        if (!agent.enabled) {
            return <Badge variant="secondary">Disabled</Badge>;
        }
        return <Badge variant="default">Enabled</Badge>;
    };

    const enabledTools = agent.tools.filter((t) => t.enabled).length;

    return (
        <Card className="w-full">
            <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-xl">
                            {getAgentIcon(agent.type)}
                        </div>
                        <div>
                            <CardTitle className="text-lg">{agent.name}</CardTitle>
                            <p className="text-sm text-muted-foreground capitalize">{agent.type} Agent</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {getEnabledBadge()}
                        <Button variant="ghost" size="sm" onClick={() => setIsExpanded(!isExpanded)}>
                            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent>
                <div className="space-y-4">
                    {agent.description && (
                        <p className="text-sm text-muted-foreground">{agent.description}</p>
                    )}

                    <div className="flex flex-wrap gap-2">
                        <Badge className={getAgentColor(agent.type)}>{agent.type}</Badge>
                        {getSafetyBadge(agent.safety_level)}
                        {agent.requires_approval && (
                            <Badge variant="outline">
                                <Settings className="h-3 w-3 mr-1" />
                                Approval Required
                            </Badge>
                        )}
                    </div>

                    <div className="text-sm">
                        <span className="text-muted-foreground">Model: </span>
                        <span className="font-medium">{model?.display_name ?? agent.model_name ?? 'Not assigned'}</span>
                    </div>

                    <div className="text-sm">
                        <span className="text-muted-foreground">Tools: </span>
                        <span className="font-medium">{enabledTools}/{agent.tools.length} enabled</span>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-sm">
                        {agent.max_iterations && (
                            <div>
                                <span className="text-muted-foreground">Max Iterations:</span>{' '}
                                <span className="font-medium">{agent.max_iterations}</span>
                            </div>
                        )}
                        {agent.timeout_seconds && (
                            <div>
                                <span className="text-muted-foreground">Timeout:</span>{' '}
                                <span className="font-medium">{agent.timeout_seconds}s</span>
                            </div>
                        )}
                    </div>

                    {agent.system_prompt && (
                        <div className="text-sm">
                            <span className="text-muted-foreground">System Prompt:</span>
                            <p className="mt-1 line-clamp-2 text-muted-foreground/80 italic">{agent.system_prompt}</p>
                        </div>
                    )}

                    {isExpanded && (
                        <div className="rounded-lg bg-muted p-4 space-y-3">
                            <div>
                                <span className="text-sm font-medium">System Prompt</span>
                                <pre className="mt-1 text-xs bg-background p-3 rounded overflow-auto max-h-40">{agent.system_prompt}</pre>
                            </div>
                            <div>
                                <span className="text-sm font-medium">Tools Access</span>
                                <div className="mt-2 space-y-1">
                                    {agent.tools.map((tool) => (
                                        <div key={tool.tool_id} className="flex items-center justify-between text-sm">
                                            <span>{tool.tool_name}</span>
                                            {tool.enabled ? (
                                                <span className="text-green-600">✓</span>
                                            ) : (
                                                <span className="text-gray-400">✗</span>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    <div className="flex items-center justify-end gap-2 pt-2 border-t">
                        <Button variant="outline" size="sm" onClick={() => onEdit(agent)}>
                            <Edit className="h-4 w-4 mr-1" />
                            Edit
                        </Button>
                        <Button variant="outline" size="sm" onClick={handleDelete} disabled={isDeleting} className="text-destructive hover:bg-destructive/10">
                            <Trash2 className="h-4 w-4 mr-1" />
                            Delete
                        </Button>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

export default AgentCard;
