/** AI Settings Main Page - Tabbed interface for AI Engine configuration */

import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Brain, Users, BookOpen, Shield, Database, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, Button, Spinner } from '@/components/ui';
import { settingsApi } from '@/lib/api/settings';
import toast from 'react-hot-toast';

type SettingsTab = 'models' | 'agents' | 'rag' | 'prompts' | 'safety';

interface TabConfig {
    id: SettingsTab;
    label: string;
    icon: React.ElementType;
    description: string;
}

const TABS: TabConfig[] = [
    { id: 'models', label: 'Models', icon: Brain, description: 'Configure AI models and providers' },
    { id: 'agents', label: 'Agents', icon: Users, description: 'Manage agent configurations' },
    { id: 'rag', label: 'RAG', icon: Database, description: 'RAG and embedding settings' },
    { id: 'prompts', label: 'Prompts', icon: BookOpen, description: 'Prompt template library' },
    { id: 'safety', label: 'Safety', icon: Shield, description: 'Safety and approval rules' },
];

export default function AISettingsPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const [activeTab, setActiveTab] = useState<SettingsTab>('models');
    const [isLoading, setIsLoading] = useState(false);
    const [isExporting, setIsExporting] = useState(false);

    // Get active tab from URL hash or state
    useEffect(() => {
        const hash = location.hash.replace('#', '');
        if (TABS.some((tab) => tab.id === hash)) {
            setActiveTab(hash as SettingsTab);
        }
    }, [location.hash]);

    const handleTabChange = (tab: SettingsTab) => {
        setActiveTab(tab);
        navigate(`#${tab}`, { replace: true });
    };

    const handleExportConfig = async () => {
        setIsExporting(true);
        try {
            const blob = await settingsApi.downloadExport({
                include_models: true,
                include_agents: true,
                include_rag: true,
                include_prompts: true,
                include_safety: true,
                include_secrets: false,
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ai-settings-${new Date().toISOString().split('T')[0]}.json`;
            a.click();
            URL.revokeObjectURL(url);
            toast.success('Configuration exported successfully');
        } catch {
            toast.error('Failed to export configuration');
        } finally {
            setIsExporting(false);
        }
    };

    const handleImportConfig = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setIsLoading(true);
        try {
            const result = await settingsApi.uploadImport(file, 'merge');
            toast.success(`Imported ${result.imported} items, skipped ${result.skipped}`);
            if (result.errors.length > 0) {
                toast.error(`Errors: ${result.errors.join(', ')}`);
            }
        } catch {
            toast.error('Failed to import configuration');
        } finally {
            setIsLoading(false);
            event.target.value = '';
        }
    };

    const renderTabContent = () => {
        switch (activeTab) {
            case 'models':
                return <ModelsTabContent />;
            case 'agents':
                return <AgentsTabContent />;
            case 'rag':
                return <RAGTabContent />;
            case 'prompts':
                return <PromptsTabContent />;
            case 'safety':
                return <SafetyTabContent />;
            default:
                return null;
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold">AI Engine Settings</h1>
                    <p className="text-sm text-muted-foreground">
                        Configure models, agents, RAG, prompts, and safety settings
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" onClick={handleExportConfig} disabled={isExporting}>
                        {isExporting ? <Spinner className="h-4 w-4 mr-2" /> : null}
                        Export Config
                    </Button>
                    <label className="inline-flex items-center justify-center whitespace-nowrap rounded-md border border-input bg-background px-4 py-2 text-sm font-medium ring-offset-background transition-colors hover:bg-accent hover:text-accent-foreground cursor-pointer disabled:opacity-50" onClick={() => document.getElementById('import-config')?.click()}>
                        {isLoading ? <Spinner className="h-4 w-4 mr-2" /> : null}
                        Import Config
                    </label>
                    <input
                        id="import-config"
                        type="file"
                        accept=".json"
                        onChange={handleImportConfig}
                        className="hidden"
                    />
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 border-b pb-2 overflow-x-auto">
                {TABS.map((tab) => {
                    const Icon = tab.icon;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => handleTabChange(tab.id)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${activeTab === tab.id
                                ? 'bg-primary text-primary-foreground'
                                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                                }`}
                        >
                            <Icon className="h-4 w-4" />
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {/* Tab Content */}
            <div className="min-h-[400px]">{renderTabContent()}</div>
        </div>
    );
}

// Placeholder tab components
function ModelsTabContent() {
    const navigate = useNavigate();
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    <span>AI Models</span>
                    <Button onClick={() => navigate('models')}>
                        <ChevronRight className="h-4 w-4 mr-1" />
                        Manage Models
                    </Button>
                </CardTitle>
            </CardHeader>
            <CardContent>
                <p className="text-muted-foreground">
                    Configure AI model providers, models, and parameters. Go to the Models page for full management.
                </p>
            </CardContent>
        </Card>
    );
}

function AgentsTabContent() {
    const navigate = useNavigate();
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    <span>AI Agents</span>
                    <Button onClick={() => navigate('agents')}>
                        <ChevronRight className="h-4 w-4 mr-1" />
                        Manage Agents
                    </Button>
                </CardTitle>
            </CardHeader>
            <CardContent>
                <p className="text-muted-foreground">
                    Configure agent types, system prompts, and tool access. Go to the Agents page for full management.
                </p>
            </CardContent>
        </Card>
    );
}

function RAGTabContent() {
    const navigate = useNavigate();
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    <span>RAG Settings</span>
                    <Button onClick={() => navigate('rag')}>
                        <ChevronRight className="h-4 w-4 mr-1" />
                        Manage RAG
                    </Button>
                </CardTitle>
            </CardHeader>
            <CardContent>
                <p className="text-muted-foreground">
                    Configure vector stores, embedding models, and chunking settings. Go to the RAG page for full management.
                </p>
            </CardContent>
        </Card>
    );
}

function PromptsTabContent() {
    const navigate = useNavigate();
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    <span>Prompt Templates</span>
                    <Button onClick={() => navigate('prompts')}>
                        <ChevronRight className="h-4 w-4 mr-1" />
                        Manage Prompts
                    </Button>
                </CardTitle>
            </CardHeader>
            <CardContent>
                <p className="text-muted-foreground">
                    Manage prompt template library with version control. Go to the Prompts page for full management.
                </p>
            </CardContent>
        </Card>
    );
}

function SafetyTabContent() {
    const navigate = useNavigate();
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    <span>Safety Settings</span>
                    <Button onClick={() => navigate('safety')}>
                        <ChevronRight className="h-4 w-4 mr-1" />
                        Manage Safety
                    </Button>
                </CardTitle>
            </CardHeader>
            <CardContent>
                <p className="text-muted-foreground">
                    Configure approval thresholds, blocking rules, and risk levels. Go to the Safety page for full management.
                </p>
            </CardContent>
        </Card>
    );
}
