/** Prompt Editor Component */

import { useState, useEffect, useRef } from 'react';
import { Save, X, History, Play, Copy, RotateCcw } from 'lucide-react';
import toast from 'react-hot-toast';
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    Button,
    Input,
    Badge,
    Dialog,
    DialogHeader,
    DialogTitle,
} from '@/components/ui';
import type { PromptTemplate, PromptVersion } from '@/lib/types';

interface PromptEditorProps {
    prompt?: PromptTemplate;
    onSave: (data: { name: string; description?: string; content: string; category: string; tags?: string[] }) => void;
    onCancel: () => void;
    onTest: (content: string, variables: Record<string, string>) => Promise<string>;
    readOnly?: boolean;
}

export function PromptEditor({ prompt, onSave, onCancel, onTest, readOnly = false }: PromptEditorProps) {
    const [name, setName] = useState(prompt?.name ?? '');
    const [description, setDescription] = useState(prompt?.description ?? '');
    const [content, setContent] = useState(prompt?.content ?? '');
    const [category, setCategory] = useState(prompt?.category ?? '');
    const [tags, setTags] = useState<string>(prompt?.tags?.join(', ') ?? '');
    const [showHistory, setShowHistory] = useState(false);
    const [versions] = useState<PromptVersion[]>(prompt?.versions ?? []);
    const [showTestDialog, setShowTestDialog] = useState(false);
    const [testVariables, setTestVariables] = useState<Record<string, string>>({});
    const [testResult, setTestResult] = useState<string>('');
    const [isTesting, setIsTesting] = useState(false);

    const textAreaRef = useRef<HTMLTextAreaElement>(null);

    const extractVariables = (text: string): string[] => {
        const matches = text.match(/\{\{([^}]+)\}\}/g) || [];
        return matches.map((match) => match.slice(2, -2).trim());
    };

    const variables = extractVariables(content);

    useEffect(() => {
        const newVariables = extractVariables(content);
        const updatedTestVariables = { ...testVariables };
        newVariables.forEach((v) => {
            if (!Object.prototype.hasOwnProperty.call(updatedTestVariables, v)) {
                updatedTestVariables[v] = '';
            }
        });
        setTestVariables(updatedTestVariables);
    }, [content, testVariables]);

    const handleSave = () => {
        if (!name.trim()) {
            toast.error('Prompt name is required');
            return;
        }
        if (!content.trim()) {
            toast.error('Prompt content is required');
            return;
        }
        if (!category.trim()) {
            toast.error('Category is required');
            return;
        }

        onSave({
            name: name.trim(),
            description: description.trim() || undefined,
            content: content.trim(),
            category: category.trim(),
            tags: tags.trim() ? tags.split(',').map((t) => t.trim()).filter(Boolean) : undefined,
        });
    };

    const handleTest = async () => {
        setIsTesting(true);
        try {
            const result = await onTest(content, testVariables);
            setTestResult(result);
        } catch (error) {
            setTestResult(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
        } finally {
            setIsTesting(false);
        }
    };

    const handleRevertToVersion = (version: PromptVersion) => {
        if (window.confirm(`Revert to version ${version.version}? This will replace the current content.`)) {
            setContent(version.content);
            toast.success(`Reverted to version ${version.version}`);
        }
    };

    const handleCopyVariables = async () => {
        const varBlock = variables.map((v) => `{{${v}}}`).join('\n');
        await navigator.clipboard.writeText(varBlock);
        toast.success('Variables copied to clipboard');
    };

    const highlightVariables = (text: string) => {
        const parts = text.split(/(\{\{[^}]+\}\})/g);
        return parts.map((part, index) => {
            if (part.match(/^\{\{[^}]+\}\}$/)) {
                return (
                    <span key={index} className="bg-yellow-100 text-yellow-800 px-1 rounded font-medium">
                        {part}
                    </span>
                );
            }
            return part;
        });
    };

    return (
        <Card className="w-full">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle>{prompt ? `Edit: ${prompt.name}` : 'Create New Prompt'}</CardTitle>
                    <div className="flex items-center gap-2">
                        {prompt && prompt.version && (
                            <Badge variant="secondary">v{prompt.version}</Badge>
                        )}
                        <Button variant="ghost" size="sm" onClick={() => setShowHistory(!showHistory)}>
                            <History className="h-4 w-4 mr-1" />
                            History
                        </Button>
                    </div>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {showHistory && versions.length > 0 && (
                    <div className="rounded-lg bg-muted p-4">
                        <h4 className="text-sm font-medium mb-2">Version History</h4>
                        <div className="space-y-2 max-h-40 overflow-auto">
                            {versions.map((version) => (
                                <div key={version.version} className="flex items-center justify-between text-sm p-2 bg-background rounded">
                                    <div>
                                        <span className="font-medium">v{version.version}</span>
                                        <span className="text-muted-foreground ml-2">
                                            {new Date(version.created_at).toLocaleString()}
                                        </span>
                                    </div>
                                    <Button variant="ghost" size="sm" onClick={() => handleRevertToVersion(version)}>
                                        <RotateCcw className="h-3 w-3 mr-1" />
                                        Revert
                                    </Button>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Name *</label>
                        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Enter prompt name" disabled={readOnly} />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Category *</label>
                        <Input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="e.g., greeting, analysis, action" disabled={readOnly} />
                    </div>
                </div>

                <div className="space-y-2">
                    <label className="text-sm font-medium">Description</label>
                    <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Brief description of this prompt" disabled={readOnly} />
                </div>

                <div className="space-y-2">
                    <label className="text-sm font-medium">Tags (comma-separated)</label>
                    <Input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="e.g., kubernetes, monitoring, production" disabled={readOnly} />
                </div>

                {variables.length > 0 && (
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <label className="text-sm font-medium">Variables</label>
                            <Button variant="ghost" size="sm" onClick={handleCopyVariables}>
                                <Copy className="h-3 w-3 mr-1" />
                                Copy All
                            </Button>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {variables.map((variable) => (
                                <Badge key={variable} variant="secondary">{`{{${variable}}}`}</Badge>
                            ))}
                        </div>
                    </div>
                )}

                <div className="space-y-2">
                    <label className="text-sm font-medium">Prompt Template *</label>
                    <div className="relative">
                        <textarea
                            ref={textAreaRef}
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            placeholder="Enter your prompt template. Use {{variable_name}} for dynamic content."
                            className="w-full min-h-[200px] p-3 text-sm border rounded-lg resize-y font-mono"
                            disabled={readOnly}
                        />
                        <div className="absolute inset-0 pointer-events-none p-3 overflow-hidden">
                            <div className="whitespace-pre-wrap font-mono text-sm text-transparent">
                                {highlightVariables(content)}
                            </div>
                        </div>
                    </div>
                    <p className="text-xs text-muted-foreground">
                        Use <code className="bg-muted px-1 rounded">{'{{variable_name}}'}</code> syntax for dynamic variables.
                    </p>
                </div>

                {variables.length > 0 && (
                    <div className="space-y-3 border-t pt-4">
                        <div className="flex items-center justify-between">
                            <h4 className="text-sm font-medium">Test Prompt</h4>
                            <Button variant="outline" size="sm" onClick={() => setShowTestDialog(true)}>
                                <Play className="h-4 w-4 mr-1" />
                                Test
                            </Button>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            {variables.slice(0, 6).map((variable) => (
                                <div key={variable} className="space-y-1">
                                    <label className="text-xs text-muted-foreground">{`{{${variable}}}`}</label>
                                    <Input
                                        value={testVariables[variable] ?? ''}
                                        onChange={(e) => setTestVariables((prev) => ({ ...prev, [variable]: e.target.value }))}
                                        placeholder={`Value for ${variable}`}
                                        className="h-8"
                                    />
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {testResult && (
                    <div className="rounded-lg bg-muted p-4">
                        <h4 className="text-sm font-medium mb-2">Test Result</h4>
                        <pre className="text-xs bg-background p-3 rounded overflow-auto max-h-40 whitespace-pre-wrap">{testResult}</pre>
                    </div>
                )}

                <div className="flex items-center justify-end gap-2 pt-4 border-t">
                    <Button variant="outline" onClick={onCancel} disabled={readOnly}>
                        <X className="h-4 w-4 mr-1" />
                        Cancel
                    </Button>
                    <Button onClick={handleSave} disabled={readOnly}>
                        <Save className="h-4 w-4 mr-1" />
                        {prompt ? 'Save Changes' : 'Create Prompt'}
                    </Button>
                </div>
            </CardContent>

            <Dialog open={showTestDialog} onClose={() => setShowTestDialog(false)}>
                <div className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>Test Prompt Template</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div className="space-y-3">
                            {variables.map((variable) => (
                                <div key={variable} className="space-y-1">
                                    <label className="text-sm font-medium">{`{{${variable}}}`}</label>
                                    <Input
                                        value={testVariables[variable] ?? ''}
                                        onChange={(e) => setTestVariables((prev) => ({ ...prev, [variable]: e.target.value }))}
                                        placeholder={`Enter value for ${variable}`}
                                    />
                                </div>
                            ))}
                        </div>
                        <div className="flex justify-end gap-2">
                            <Button variant="outline" onClick={() => setShowTestDialog(false)}>Close</Button>
                            <Button onClick={handleTest} disabled={isTesting}>{isTesting ? 'Testing...' : 'Run Test'}</Button>
                        </div>
                    </div>
                </div>
            </Dialog>
        </Card>
    );
}

export default PromptEditor;
