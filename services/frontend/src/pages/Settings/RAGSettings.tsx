/** RAG Settings Page - Configure RAG and embedding settings */

import { useState, useEffect, useCallback } from 'react';
import { Save, RefreshCw, Plus, Trash2, Database, Search, Settings } from 'lucide-react';
import toast from 'react-hot-toast';
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    Button,
    Input,
    Badge,
    Spinner,
    Dialog,
    DialogHeader,
    DialogTitle,
} from '@/components/ui';
import { ragApi } from '@/lib/api/settings';
import type { RAGSettings } from '@/lib/types';

export default function RAGSettingsPage() {
    const [settings, setSettings] = useState<RAGSettings | null>(null);
    const [indexes, setIndexes] = useState<{ name: string; status: string; document_count: number; size_bytes: number }[]>([]);
    const [embeddings, setEmbeddings] = useState<{ provider: string; models: { name: string; dimensions: number }[] }[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [showAddIndexDialog, setShowAddIndexDialog] = useState(false);

    const loadData = useCallback(async () => {
        setIsLoading(true);
        try {
            const [settingsData, indexesData, embeddingsData] = await Promise.all([
                ragApi.getSettings(),
                ragApi.getIndexes(),
                ragApi.getAvailableEmbeddings(),
            ]);
            setSettings(settingsData);
            setIndexes(indexesData);
            setEmbeddings(embeddingsData);
        } catch {
            toast.error('Failed to load RAG settings');
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleSaveSettings = async () => {
        if (!settings) return;
        setIsSaving(true);
        try {
            const updated = await ragApi.update({
                vector_store_type: settings.vector_store_type,
                vector_store_config: settings.vector_store_config,
                embedding_config: settings.embedding_config,
                chunk_size: settings.chunk_size,
                chunk_overlap: settings.chunk_overlap,
                similarity_threshold: settings.similarity_threshold,
                max_results: settings.max_results,
                enable_hybrid_search: settings.enable_hybrid_search,
                enable_reranking: settings.enable_reranking,
                reranker_model: settings.reranker_model,
                enabled: settings.enabled,
            });
            setSettings(updated);
            toast.success('RAG settings saved');
        } catch {
            toast.error('Failed to save RAG settings');
        } finally {
            setIsSaving(false);
        }
    };

    const handleRebuildIndex = async (name: string) => {
        try {
            await ragApi.rebuildIndex(name);
            toast.success(`Index ${name} rebuild started`);
        } catch {
            toast.error('Failed to rebuild index');
        }
    };

    const handleDeleteIndex = async (name: string) => {
        if (window.confirm(`Delete index ${name}? This cannot be undone.`)) {
            try {
                await ragApi.deleteIndex(name);
                setIndexes((prev) => prev.filter((i) => i.name !== name));
                toast.success('Index deleted');
            } catch {
                toast.error('Failed to delete index');
            }
        }
    };

    const handleToggleEnabled = async () => {
        if (!settings) return;
        const updated = await ragApi.update({ enabled: !settings.enabled });
        setSettings(updated);
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Spinner className="h-8 w-8" />
            </div>
        );
    }

    if (!settings) {
        return (
            <Card>
                <CardContent className="py-12 text-center">
                    <p className="text-muted-foreground">Failed to load RAG settings</p>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">RAG Settings</h1>
                    <p className="text-sm text-muted-foreground">
                        Configure vector stores, embeddings, and indexing
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" onClick={loadData}>
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Refresh
                    </Button>
                    <Button onClick={handleSaveSettings} disabled={isSaving}>
                        <Save className="h-4 w-4 mr-1" />
                        {isSaving ? 'Saving...' : 'Save Changes'}
                    </Button>
                </div>
            </div>

            {/* Main Settings */}
            <div className="grid gap-6 lg:grid-cols-2">
                {/* Vector Store */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Database className="h-5 w-5" />
                            Vector Store
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Store Type</label>
                            <select
                                value={settings.vector_store_type}
                                onChange={(e) =>
                                    setSettings((prev) =>
                                        prev ? { ...prev, vector_store_type: e.target.value as typeof prev.vector_store_type } : prev
                                    )
                                }
                                className="w-full px-3 py-2 border rounded-lg text-sm"
                            >
                                <option value="qdrant">Qdrant</option>
                                <option value="pinecone">Pinecone</option>
                                <option value="weaviate">Weaviate</option>
                                <option value="chroma">Chroma</option>
                                <option value="local">Local</option>
                            </select>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium">Host URL</label>
                            <Input
                                value={(settings.vector_store_config?.host as string) ?? ''}
                                onChange={(e) =>
                                    setSettings((prev) =>
                                        prev
                                            ? {
                                                ...prev,
                                                vector_store_config: { ...prev.vector_store_config, host: e.target.value },
                                            }
                                            : prev
                                    )
                                }
                                placeholder="e.g., localhost:6333"
                            />
                        </div>

                        <div className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                id="rag-enabled"
                                checked={settings.enabled}
                                onChange={handleToggleEnabled}
                            />
                            <label htmlFor="rag-enabled" className="text-sm">
                                Enable RAG
                            </label>
                            <Badge variant={settings.enabled ? 'default' : 'secondary'}>
                                {settings.enabled ? 'Active' : 'Disabled'}
                            </Badge>
                        </div>
                    </CardContent>
                </Card>

                {/* Embeddings */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Search className="h-5 w-5" />
                            Embeddings
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Provider</label>
                            <select
                                value={settings.embedding_config.provider}
                                onChange={(e) =>
                                    setSettings((prev) =>
                                        prev
                                            ? {
                                                ...prev,
                                                embedding_config: { ...prev.embedding_config, provider: e.target.value },
                                            }
                                            : prev
                                    )
                                }
                                className="w-full px-3 py-2 border rounded-lg text-sm"
                            >
                                {embeddings.map((e) => (
                                    <option key={e.provider} value={e.provider}>
                                        {e.provider}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium">Model</label>
                            <select
                                value={settings.embedding_config.model}
                                onChange={(e) =>
                                    setSettings((prev) =>
                                        prev
                                            ? {
                                                ...prev,
                                                embedding_config: { ...prev.embedding_config, model: e.target.value },
                                            }
                                            : prev
                                    )
                                }
                                className="w-full px-3 py-2 border rounded-lg text-sm"
                            >
                                {embeddings
                                    .find((e) => e.provider === settings.embedding_config.provider)
                                    ?.models.map((m) => (
                                        <option key={m.name} value={m.name}>
                                            {m.name} ({m.dimensions} dims)
                                        </option>
                                    ))}
                            </select>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium">Dimensions</label>
                            <Input
                                type="number"
                                value={settings.embedding_config.dimensions}
                                disabled
                                className="bg-muted"
                            />
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Chunking Settings */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Settings className="h-5 w-5" />
                        Chunking & Search
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Chunk Size</label>
                            <Input
                                type="number"
                                value={settings.chunk_size}
                                onChange={(e) =>
                                    setSettings((prev) =>
                                        prev ? { ...prev, chunk_size: parseInt(e.target.value) } : prev
                                    )
                                }
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Chunk Overlap</label>
                            <Input
                                type="number"
                                value={settings.chunk_overlap}
                                onChange={(e) =>
                                    setSettings((prev) =>
                                        prev ? { ...prev, chunk_overlap: parseInt(e.target.value) } : prev
                                    )
                                }
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Similarity Threshold</label>
                            <Input
                                type="number"
                                step="0.1"
                                min="0"
                                max="1"
                                value={settings.similarity_threshold}
                                onChange={(e) =>
                                    setSettings((prev) =>
                                        prev ? { ...prev, similarity_threshold: parseFloat(e.target.value) } : prev
                                    )
                                }
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Max Results</label>
                            <Input
                                type="number"
                                value={settings.max_results}
                                onChange={(e) =>
                                    setSettings((prev) =>
                                        prev ? { ...prev, max_results: parseInt(e.target.value) } : prev
                                    )
                                }
                            />
                        </div>
                    </div>

                    <div className="flex items-center gap-6 mt-4">
                        <label className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                checked={settings.enable_hybrid_search}
                                onChange={(e) =>
                                    setSettings((prev) =>
                                        prev ? { ...prev, enable_hybrid_search: e.target.checked } : prev
                                    )
                                }
                            />
                            <span className="text-sm">Enable Hybrid Search</span>
                        </label>
                        <label className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                checked={settings.enable_reranking}
                                onChange={(e) =>
                                    setSettings((prev) =>
                                        prev ? { ...prev, enable_reranking: e.target.checked } : prev
                                    )
                                }
                            />
                            <span className="text-sm">Enable Reranking</span>
                        </label>
                    </div>
                </CardContent>
            </Card>

            {/* Indexes */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle>Indexes</CardTitle>
                        <Button size="sm" onClick={() => setShowAddIndexDialog(true)}>
                            <Plus className="h-4 w-4 mr-1" />
                            Create Index
                        </Button>
                    </div>
                </CardHeader>
                <CardContent>
                    {indexes.length === 0 ? (
                        <p className="text-muted-foreground text-center py-8">No indexes found</p>
                    ) : (
                        <div className="space-y-2">
                            {indexes.map((index) => (
                                <div
                                    key={index.name}
                                    className="flex items-center justify-between p-4 border rounded-lg"
                                >
                                    <div>
                                        <p className="font-medium">{index.name}</p>
                                        <p className="text-sm text-muted-foreground">
                                            {index.document_count.toLocaleString()} documents •{' '}
                                            {(index.size_bytes / 1024 / 1024).toFixed(2)} MB •{' '}
                                            <Badge
                                                variant={
                                                    index.status === 'active'
                                                        ? 'default'
                                                        : index.status === 'building'
                                                            ? 'secondary'
                                                            : 'destructive'
                                                }
                                            >
                                                {index.status}
                                            </Badge>
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => handleRebuildIndex(index.name)}
                                            disabled={index.status === 'building'}
                                        >
                                            <RefreshCw className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => handleDeleteIndex(index.name)}
                                            className="text-destructive"
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Add Index Dialog */}
            <Dialog open={showAddIndexDialog} onClose={() => setShowAddIndexDialog(false)}>
                <div className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>Create Index</DialogTitle>
                    </DialogHeader>
                </div>
            </Dialog>
        </div>
    );
}
