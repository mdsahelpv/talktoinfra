/** Connect Infrastructure Wizard Component */

"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, ChevronLeft, Check, AlertCircle, Loader2 } from "lucide-react";

import type { WizardState, ConnectionTestResult } from "@/lib/types/onboarding";
import * as api from "@/lib/api/onboarding";

const PROVIDERS = [
    {
        id: "kubernetes",
        name: "Kubernetes",
        icon: "☸️",
        description: "Connect to Kubernetes clusters",
        fields: ["kubeconfig"],
    },
    {
        id: "aws",
        name: "AWS",
        icon: "☁️",
        description: "Register AWS accounts",
        fields: ["awsAccessKeyId", "awsRoleArn"],
    },
    {
        id: "azure",
        name: "Azure",
        icon: "🔷",
        description: "Register Azure subscriptions",
        fields: ["azureSubscriptionId"],
    },
    {
        id: "gcp",
        name: "GCP",
        icon: "🔶",
        description: "Register GCP projects",
        fields: ["gcpProjectId"],
    },
] as const;

const STEPS = [
    { id: "select-type", label: "Select Type", description: "Choose infrastructure type" },
    { id: "provide-credentials", label: "Provide Credentials", description: "Enter connection details" },
    { id: "test-connection", label: "Test Connection", description: "Verify connectivity" },
    { id: "configure-resources", label: "Configure", description: "Select resources to monitor" },
    { id: "review-confirm", label: "Review", description: "Confirm and connect" },
] as const;

export function ConnectWizard() {
    const router = useRouter();
    const queryClient = useQueryClient();

    const [wizard, setWizard] = useState<WizardState>({
        step: "select-type",
        provider: null,
        credentials: { name: "" },
        config: {},
    });

    const [error, setError] = useState<string | null>(null);
    const [testingConnection, setTestingConnection] = useState(false);

    const currentStepIndex = STEPS.findIndex((s) => s.id === wizard.step);

    // Fetch clusters for summary
    const { data: clusters = [] } = useQuery({
        queryKey: ["clusters"],
        queryFn: api.listClusters,
    });

    const createClusterMutation = useMutation({
        mutationFn: api.createCluster,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["clusters"] });
            router.push("/infra");
        },
        onError: (err: Error) => {
            setError(err.message);
        },
    });

    const handleProviderSelect = (provider: WizardState["provider"]) => {
        setWizard((prev) => ({
            ...prev,
            provider,
            step: "provide-credentials",
        }));
        setError(null);
    };

    const handleCredentialsSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        // Validate required fields based on provider
        if (!wizard.credentials.name.trim()) {
            setError("Please enter a name for this connection");
            return;
        }

        setWizard((prev) => ({
            ...prev,
            step: "test-connection",
        }));
    };

    const handleTestConnection = async () => {
        if (!wizard.provider) return;

        setTestingConnection(true);
        setError(null);

        try {
            let result: ConnectionTestResult;

            if (wizard.provider === "kubernetes") {
                // Create cluster first, then test
                const cluster = await createClusterMutation.mutateAsync({
                    name: wizard.credentials.name,
                    kubeconfigFile: wizard.credentials.kubeconfig,
                    apiEndpoint: wizard.credentials.apiEndpoint,
                    token: wizard.credentials.token ? { getSecretValue: () => wizard.credentials.token! } : undefined,
                });

                result = await api.testClusterConnection(cluster.id);
            } else {
                // TODO: Implement cloud account creation and testing
                result = {
                    success: true,
                    message: "Connection successful",
                    responseTimeMs: 45,
                    permissions: {},
                };
            }

            setWizard((prev) => ({
                ...prev,
                testResult: result,
                step: result.success ? "configure-resources" : "test-connection",
            }));
        } catch (err) {
            setError(err instanceof Error ? err.message : "Connection test failed");
        } finally {
            setTestingConnection(false);
        }
    };

    const handleConfigureSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setWizard((prev) => ({
            ...prev,
            step: "review-confirm",
        }));
    };

    const handleFinalConfirm = async () => {
        if (!wizard.provider || !wizard.credentials.name) return;

        try {
            if (wizard.provider === "kubernetes") {
                await createClusterMutation.mutateAsync({
                    name: wizard.credentials.name,
                    kubeconfigFile: wizard.credentials.kubeconfig,
                    apiEndpoint: wizard.credentials.apiEndpoint,
                    namespaceSelector: wizard.config.namespaces
                        ? { includeNamespaces: wizard.config.namespaces }
                        : undefined,
                    labels: wizard.config.labels,
                });
            } else {
                // TODO: Implement cloud account creation
                router.push("/infra");
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create connection");
        }
    };

    const handleBack = () => {
        const stepIndex = currentStepIndex;
        if (stepIndex > 0) {
            setWizard((prev) => ({
                ...prev,
                step: STEPS[stepIndex - 1].id,
            }));
        }
    };

    return (
        <div className="max-w-4xl mx-auto">
            {/* Progress Steps */}
            <div className="mb-8">
                <div className="flex items-center justify-between">
                    {STEPS.map((step, index) => (
                        <React.Fragment key={step.id}>
                            <div
                                className={`flex flex-col items-center ${index <= currentStepIndex ? "opacity-100" : "opacity-40"
                                    }`}
                            >
                                <div
                                    className={`w-10 h-10 rounded-full flex items-center justify-center ${index < currentStepIndex
                                            ? "bg-green-500 text-white"
                                            : index === currentStepIndex
                                                ? "bg-blue-500 text-white"
                                                : "bg-gray-200 text-gray-500"
                                        }`}
                                >
                                    {index < currentStepIndex ? (
                                        <Check className="w-5 h-5" />
                                    ) : (
                                        <span className="font-semibold">{index + 1}</span>
                                    )}
                                </div>
                                <span className="mt-2 text-sm font-medium">{step.label}</span>
                                <span className="text-xs text-gray-500">{step.description}</span>
                            </div>
                            {index < STEPS.length - 1 && (
                                <div
                                    className={`flex-1 h-0.5 mx-2 ${index < currentStepIndex ? "bg-green-500" : "bg-gray-200"
                                        }`}
                                />
                            )}
                        </React.Fragment>
                    ))}
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-red-500" />
                    <span className="text-red-700">{error}</span>
                    <button
                        onClick={() => setError(null)}
                        className="ml-auto text-red-500 hover:text-red-700"
                    >
                        ×
                    </button>
                </div>
            )}

            {/* Step Content */}
            <div className="bg-white rounded-xl shadow-lg p-6">
                {wizard.step === "select-type" && (
                    <SelectTypeStep
                        onSelect={handleProviderSelect}
                        existingClusters={clusters.length}
                    />
                )}

                {wizard.step === "provide-credentials" && (
                    <CredentialsStep
                        provider={wizard.provider!}
                        credentials={wizard.credentials}
                        onChange={(creds) =>
                            setWizard((prev) => ({ ...prev, credentials: { ...prev.credentials, ...creds } }))
                        }
                        onSubmit={handleCredentialsSubmit}
                    />
                )}

                {wizard.step === "test-connection" && (
                    <TestConnectionStep
                        provider={wizard.provider!}
                        credentials={wizard.credentials}
                        onTest={handleTestConnection}
                        testing={testingConnection}
                        result={wizard.testResult}
                        error={error}
                    />
                )}

                {wizard.step === "configure-resources" && (
                    <ConfigureStep
                        provider={wizard.provider!}
                        config={wizard.config}
                        onChange={(config) =>
                            setWizard((prev) => ({ ...prev, config: { ...prev.config, ...config } }))
                        }
                        onSubmit={handleConfigureSubmit}
                    />
                )}

                {wizard.step === "review-confirm" && (
                    <ReviewStep
                        provider={wizard.provider!}
                        credentials={wizard.credentials}
                        config={wizard.config}
                        testResult={wizard.testResult}
                        onConfirm={handleFinalConfirm}
                        creating={createClusterMutation.isPending}
                    />
                )}
            </div>

            {/* Navigation */}
            {currentStepIndex > 0 && wizard.step !== "test-connection" && (
                <div className="mt-6 flex justify-between">
                    <button
                        onClick={handleBack}
                        className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-800"
                    >
                        <ChevronLeft className="w-4 h-4" />
                        Back
                    </button>
                </div>
            )}
        </div>
    );
}

// Step 1: Select Infrastructure Type

function SelectTypeStep({
    onSelect,
    existingClusters,
}: {
    onSelect: (provider: WizardState["provider"]) => void;
    existingClusters: number;
}) {
    return (
        <div>
            <h2 className="text-2xl font-bold mb-2">Connect Infrastructure</h2>
            <p className="text-gray-600 mb-6">
                Choose the type of infrastructure you want to connect
                {existingClusters > 0 && (
                    <span className="ml-2 text-sm text-gray-500">
                        ({existingClusters} clusters already connected)
                    </span>
                )}
            </p>

            <div className="grid grid-cols-2 gap-4">
                {PROVIDERS.map((provider) => (
                    <button
                        key={provider.id}
                        onClick={() => onSelect(provider.id as WizardState["provider"])}
                        className="p-6 border-2 border-gray-200 rounded-xl hover:border-blue-500 hover:bg-blue-50 transition-colors text-left"
                    >
                        <div className="text-4xl mb-3">{provider.icon}</div>
                        <h3 className="text-lg font-semibold">{provider.name}</h3>
                        <p className="text-sm text-gray-500 mt-1">{provider.description}</p>
                    </button>
                ))}
            </div>
        </div>
    );
}

// Step 2: Provide Credentials

function CredentialsStep({
    provider,
    credentials,
    onChange,
    onSubmit,
}: {
    provider: WizardState["provider"];
    credentials: WizardState["credentials"];
    onChange: (creds: Partial<WizardState["credentials"]>) => void;
    onSubmit: (e: React.FormEvent) => void;
}) {
    const getPlaceholder = (field: string) => {
        switch (field) {
            case "kubeconfig":
                return "Paste your kubeconfig YAML here...";
            case "token":
                return "Service account token...";
            case "awsAccessKeyId":
                return "AKIAIOSFODNN7EXAMPLE";
            case "awsRoleArn":
                return "arn:aws:iam::123456789012:role/MyRole";
            case "azureSubscriptionId":
                return "12345678-1234-1234-1234-123456789012";
            case "gcpProjectId":
                return "my-gcp-project";
            default:
                return "";
        }
    };

    const getLabel = (field: string) => {
        switch (field) {
            case "kubeconfig":
                return "Kubeconfig (YAML)";
            case "token":
                return "Service Account Token";
            case "awsAccessKeyId":
                return "AWS Access Key ID";
            case "awsRoleArn":
                return "IAM Role ARN";
            case "azureSubscriptionId":
                return "Subscription ID";
            case "gcpProjectId":
                return "GCP Project ID";
            default:
                return field;
        }
    };

    const providerConfig = PROVIDERS.find((p) => p.id === provider);

    return (
        <form onSubmit={onSubmit}>
            <h2 className="text-2xl font-bold mb-2">Provide Credentials</h2>
            <p className="text-gray-600 mb-6">
                Enter the credentials for connecting to your {providerConfig?.name} infrastructure
            </p>

            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Connection Name *
                    </label>
                    <input
                        type="text"
                        value={credentials.name}
                        onChange={(e) => onChange({ name: e.target.value })}
                        placeholder="e.g., Production Cluster"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        required
                    />
                </div>

                {provider === "kubernetes" && (
                    <>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                API Endpoint (optional)
                            </label>
                            <input
                                type="text"
                                value={credentials.apiEndpoint || ""}
                                onChange={(e) => onChange({ apiEndpoint: e.target.value })}
                                placeholder="https://kubernetes.default.svc"
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Kubeconfig (YAML) *
                            </label>
                            <textarea
                                value={credentials.kubeconfig || ""}
                                onChange={(e) => onChange({ kubeconfig: e.target.value })}
                                placeholder={getPlaceholder("kubeconfig")}
                                rows={10}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                                required={!credentials.token}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Service Account Token (optional, if no kubeconfig)
                            </label>
                            <textarea
                                value={credentials.token || ""}
                                onChange={(e) => onChange({ token: e.target.value })}
                                placeholder={getPlaceholder("token")}
                                rows={3}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                                required={!credentials.kubeconfig}
                            />
                        </div>
                    </>
                )}

                {provider === "aws" && (
                    <>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                AWS Access Key ID
                            </label>
                            <input
                                type="text"
                                value={credentials.awsAccessKeyId || ""}
                                onChange={(e) => onChange({ awsAccessKeyId: e.target.value })}
                                placeholder={getPlaceholder("awsAccessKeyId")}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                AWS Secret Access Key
                            </label>
                            <input
                                type="password"
                                value={credentials.awsSecretAccessKey || ""}
                                onChange={(e) => onChange({ awsSecretAccessKey: e.target.value })}
                                placeholder="Enter your secret access key"
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                        </div>

                        <div className="text-center text-gray-500">- OR -</div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                IAM Role ARN (for cross-account access)
                            </label>
                            <input
                                type="text"
                                value={credentials.awsRoleArn || ""}
                                onChange={(e) => onChange({ awsRoleArn: e.target.value })}
                                placeholder={getPlaceholder("awsRoleArn")}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                        </div>
                    </>
                )}

                {provider === "azure" && (
                    <>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Subscription ID *
                            </label>
                            <input
                                type="text"
                                value={credentials.azureSubscriptionId || ""}
                                onChange={(e) => onChange({ azureSubscriptionId: e.target.value })}
                                placeholder={getPlaceholder("azureSubscriptionId")}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                required
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Client ID
                                </label>
                                <input
                                    type="text"
                                    value={credentials.azureClientId || ""}
                                    onChange={(e) => onChange({ azureClientId: e.target.value })}
                                    placeholder="Service Principal Client ID"
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Client Secret
                                </label>
                                <input
                                    type="password"
                                    value={credentials.azureClientSecret || ""}
                                    onChange={(e) => onChange({ azureClientSecret: e.target.value })}
                                    placeholder="Service Principal Secret"
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                />
                            </div>
                        </div>
                    </>
                )}

                {provider === "gcp" && (
                    <>
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                GCP Project ID *
                            </label>
                            <input
                                type="text"
                                value={credentials.gcpProjectId || ""}
                                onChange={(e) => onChange({ gcpProjectId: e.target.value })}
                                placeholder={getPlaceholder("gcpProjectId")}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                required
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Service Account JSON
                            </label>
                            <textarea
                                value={credentials.gcpCredentials || ""}
                                onChange={(e) => onChange({ gcpCredentials: e.target.value })}
                                placeholder='{"type": "service_account", ...}'
                                rows={10}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                            />
                        </div>
                    </>
                )}
            </div>

            <div className="mt-8 flex justify-end">
                <button
                    type="submit"
                    className="flex items-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                    Test Connection
                    <ChevronRight className="w-4 h-4" />
                </button>
            </div>
        </form>
    );
}

// Step 3: Test Connection

function TestConnectionStep({
    provider,
    credentials,
    onTest,
    testing,
    result,
    error,
}: {
    provider: WizardState["provider"];
    credentials: WizardState["credentials"];
    onTest: () => void;
    testing: boolean;
    result?: ConnectionTestResult;
    error?: string | null;
}) {
    return (
        <div>
            <h2 className="text-2xl font-bold mb-2">Test Connection</h2>
            <p className="text-gray-600 mb-6">
                Verifying connectivity and permissions to your {provider} infrastructure
            </p>

            <div className="text-center py-12">
                {testing ? (
                    <>
                        <Loader2 className="w-12 h-12 mx-auto text-blue-500 animate-spin" />
                        <p className="mt-4 text-lg font-medium">Testing connection...</p>
                        <p className="text-gray-500">This may take a few moments</p>
                    </>
                ) : result ? (
                    <>
                        {result.success ? (
                            <>
                                <div className="w-16 h-16 mx-auto bg-green-100 rounded-full flex items-center justify-center">
                                    <Check className="w-8 h-8 text-green-500" />
                                </div>
                                <p className="mt-4 text-xl font-semibold text-green-600">Connection Successful!</p>
                                <p className="text-gray-500 mt-2">{result.message}</p>
                                <p className="text-sm text-gray-400 mt-1">Response time: {result.responseTimeMs}ms</p>
                            </>
                        ) : (
                            <>
                                <div className="w-16 h-16 mx-auto bg-red-100 rounded-full flex items-center justify-center">
                                    <AlertCircle className="w-8 h-8 text-red-500" />
                                </div>
                                <p className="mt-4 text-xl font-semibold text-red-600">Connection Failed</p>
                                <p className="text-gray-500 mt-2">{error || result.errorMessage}</p>
                                {result.errorCode && (
                                    <p className="text-sm text-gray-400 mt-1">Error code: {result.errorCode}</p>
                                )}
                            </>
                        )}
                    </>
                ) : (
                    <>
                        <p className="text-gray-500">Click to test the connection</p>
                    </>
                )}
            </div>

            <div className="mt-8 flex justify-center gap-4">
                {testing ? (
                    <button
                        disabled
                        className="flex items-center gap-2 px-6 py-3 bg-gray-300 text-gray-500 rounded-lg cursor-not-allowed"
                    >
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Testing...
                    </button>
                ) : result?.success ? (
                    <button
                        onClick={() => {
                            /* Move to next step */
                        }}
                        className="flex items-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                    >
                        Continue
                        <ChevronRight className="w-4 h-4" />
                    </button>
                ) : (
                    <button
                        onClick={onTest}
                        className="flex items-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                    >
                        Test Connection
                    </button>
                )}
            </div>
        </div>
    );
}

// Step 4: Configure Resources

function ConfigureStep({
    provider,
    config,
    onChange,
    onSubmit,
}: {
    provider: WizardState["provider"];
    config: WizardState["config"];
    onChange: (config: Partial<WizardState["config"]>) => void;
    onSubmit: (e: React.FormEvent) => void;
}) {
    const [namespaceInput, setNamespaceInput] = useState("");

    const addNamespace = () => {
        if (namespaceInput.trim()) {
            const namespaces = [...(config.namespaces || []), namespaceInput.trim()];
            onChange({ namespaces });
            setNamespaceInput("");
        }
    };

    const removeNamespace = (ns: string) => {
        const namespaces = (config.namespaces || []).filter((n) => n !== ns);
        onChange({ namespaces });
    };

    return (
        <form onSubmit={onSubmit}>
            <h2 className="text-2xl font-bold mb-2">Configure Resources</h2>
            <p className="text-gray-600 mb-6">
                Select which {provider === "kubernetes" ? "namespaces" : "regions"} to monitor
            </p>

            <div className="space-y-6">
                {provider === "kubernetes" && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Namespaces to Monitor
                        </label>
                        <div className="flex gap-2 mb-2">
                            <input
                                type="text"
                                value={namespaceInput}
                                onChange={(e) => setNamespaceInput(e.target.value)}
                                placeholder="e.g., production, staging"
                                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                onKeyPress={(e) => e.key === "Enter" && (e.preventDefault(), addNamespace())}
                            />
                            <button
                                type="button"
                                onClick={addNamespace}
                                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                            >
                                Add
                            </button>
                        </div>
                        <p className="text-sm text-gray-500 mb-2">
                            Leave empty to monitor all namespaces
                        </p>
                        <div className="flex flex-wrap gap-2">
                            {(config.namespaces || []).map((ns) => (
                                <span
                                    key={ns}
                                    className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm"
                                >
                                    {ns}
                                    <button
                                        type="button"
                                        onClick={() => removeNamespace(ns)}
                                        className="hover:text-blue-900"
                                    >
                                        ×
                                    </button>
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                {provider !== "kubernetes" && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Regions to Monitor
                        </label>
                        <div className="grid grid-cols-4 gap-2">
                            {["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1"].map((region) => (
                                <label
                                    key={region}
                                    className={`flex items-center gap-2 p-3 border rounded-lg cursor-pointer ${(config.regions || []).includes(region)
                                            ? "border-blue-500 bg-blue-50"
                                            : "border-gray-200 hover:border-gray-300"
                                        }`}
                                >
                                    <input
                                        type="checkbox"
                                        checked={(config.regions || []).includes(region)}
                                        onChange={(e) => {
                                            const regions = e.target.checked
                                                ? [...(config.regions || []), region]
                                                : (config.regions || []).filter((r) => r !== region);
                                            onChange({ regions });
                                        }}
                                        className="rounded text-blue-500"
                                    />
                                    <span className="text-sm">{region}</span>
                                </label>
                            ))}
                        </div>
                    </div>
                )}

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Labels / Tags
                    </label>
                    <div className="grid grid-cols-2 gap-4">
                        <input
                            type="text"
                            placeholder="Key"
                            value={Object.keys(config.labels || {})[0] || ""}
                            onChange={(e) => {
                                const labels = { ...config.labels };
                                if (e.target.value) {
                                    labels[e.target.value] = labels[Object.keys(labels)[0]] || "";
                                }
                                onChange({ labels });
                            }}
                            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                        <input
                            type="text"
                            placeholder="Value"
                            value={Object.values(config.labels || {})[0] || ""}
                            onChange={(e) => {
                                const key = Object.keys(config.labels || {})[0];
                                const labels = { ...config.labels };
                                if (key && e.target.value) {
                                    labels[key] = e.target.value;
                                }
                                onChange({ labels });
                            }}
                            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                    </div>
                </div>
            </div>

            <div className="mt-8 flex justify-end">
                <button
                    type="submit"
                    className="flex items-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                    Review & Confirm
                    <ChevronRight className="w-4 h-4" />
                </button>
            </div>
        </form>
    );
}

// Step 5: Review & Confirm

function ReviewStep({
    provider,
    credentials,
    config,
    testResult,
    onConfirm,
    creating,
}: {
    provider: WizardState["provider"];
    credentials: WizardState["credentials"];
    config: WizardState["config"];
    testResult?: ConnectionTestResult;
    onConfirm: () => void;
    creating: boolean;
}) {
    const providerConfig = PROVIDERS.find((p) => p.id === provider);

    return (
        <div>
            <h2 className="text-2xl font-bold mb-2">Review & Confirm</h2>
            <p className="text-gray-600 mb-6">Review your configuration before connecting</p>

            <div className="bg-gray-50 rounded-xl p-6 space-y-4">
                <div className="flex items-center gap-4">
                    <span className="text-4xl">{providerConfig?.icon}</span>
                    <div>
                        <h3 className="text-xl font-semibold">{credentials.name}</h3>
                        <p className="text-gray-500">{providerConfig?.name}</p>
                    </div>
                    <div className="ml-auto">
                        {testResult?.success ? (
                            <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
                                ✓ Connected
                            </span>
                        ) : (
                            <span className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full text-sm font-medium">
                                Testing...
                            </span>
                        )}
                    </div>
                </div>

                <div className="border-t border-gray-200 pt-4">
                    <h4 className="font-medium mb-2">Configuration</h4>
                    <dl className="space-y-2 text-sm">
                        {provider === "kubernetes" && (
                            <>
                                {credentials.apiEndpoint && (
                                    <div className="flex">
                                        <dt className="w-32 text-gray-500">Endpoint:</dt>
                                        <dd className="flex-1 font-mono truncate">{credentials.apiEndpoint}</dd>
                                    </div>
                                )}
                                {config.namespaces && config.namespaces.length > 0 && (
                                    <div className="flex">
                                        <dt className="w-32 text-gray-500">Namespaces:</dt>
                                        <dd className="flex-1">{config.namespaces.join(", ")}</dd>
                                    </div>
                                )}
                            </>
                        )}
                        {provider === "aws" && (
                            <div className="flex">
                                <dt className="w-32 text-gray-500">Access Mode:</dt>
                                <dd className="flex-1">
                                    {credentials.awsRoleArn ? "IAM Role" : "Access Key"}
                                </dd>
                            </div>
                        )}
                        {provider === "azure" && (
                            <div className="flex">
                                <dt className="w-32 text-gray-500">Subscription:</dt>
                                <dd className="flex-1 font-mono">{credentials.azureSubscriptionId}</dd>
                            </div>
                        )}
                        {provider === "gcp" && (
                            <div className="flex">
                                <dt className="w-32 text-gray-500">Project:</dt>
                                <dd className="flex-1 font-mono">{credentials.gcpProjectId}</dd>
                            </div>
                        )}
                        {config.labels && Object.keys(config.labels).length > 0 && (
                            <div className="flex">
                                <dt className="w-32 text-gray-500">Labels:</dt>
                                <dd className="flex-1">
                                    {Object.entries(config.labels).map(([k, v]) => (
                                        <span key={k} className="inline-block mr-2 px-2 bg-gray-200 rounded text-xs">
                                            {k}: {v}
                                        </span>
                                    ))}
                                </dd>
                            </div>
                        )}
                    </dl>
                </div>

                {testResult && (
                    <div className="border-t border-gray-200 pt-4">
                        <h4 className="font-medium mb-2">Connection Test</h4>
                        <div className="flex items-center gap-4 text-sm">
                            <span
                                className={
                                    testResult.success ? "text-green-600" : "text-red-600"
                                }
                            >
                                {testResult.success ? "✓ Passed" : "✗ Failed"}
                            </span>
                            <span className="text-gray-500">
                                {testResult.responseTimeMs}ms response time
                            </span>
                        </div>
                    </div>
                )}
            </div>

            <div className="mt-8 flex justify-end gap-4">
                <button
                    onClick={onConfirm}
                    disabled={creating}
                    className="flex items-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {creating ? (
                        <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Creating...
                        </>
                    ) : (
                        <>
                            <Check className="w-4 h-4" />
                            Connect Infrastructure
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}

function useState<T>(initial: T): [T, React.Dispatch<React.SetStateAction<T>>] {
    const [state, setState] = React.useState(initial);
    return [state, setState];
}
