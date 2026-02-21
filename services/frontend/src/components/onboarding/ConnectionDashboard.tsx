/** Connection Management Dashboard Component */

"use client";

import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    Plus,
    RefreshCw,
    Trash2,
    Settings,
    ExternalLink,
    CheckCircle,
    XCircle,
    AlertTriangle,
    AlertCircle,
    Loader2,
} from "lucide-react";

import type { Cluster, CloudAccount, ConnectionTestResult } from "@/lib/types/onboarding";
import * as api from "@/lib/api/onboarding";

interface ConnectionDashboardProps {
    onAddConnection: () => void;
}

export function ConnectionDashboard({ onAddConnection }: ConnectionDashboardProps) {
    const queryClient = useQueryClient();

    // Fetch clusters
    const {
        data: clusters = [],
        isLoading: clustersLoading,
        error: clustersError,
    } = useQuery({
        queryKey: ["clusters"],
        queryFn: api.listClusters,
    });

    // Fetch cloud accounts
    const { data: cloudAccounts = [] } = useQuery({
        queryKey: ["cloudAccounts"],
        queryFn: () => api.listCloudAccounts("aws"), // TODO: fetch all providers
    });

    // Delete mutation
    const deleteMutation = useMutation({
        mutationFn: (id: string) => api.deleteCluster(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["clusters"] });
        },
    });

    // Test connection mutation
    const testMutation = useMutation({
        mutationFn: (id: string) => api.testClusterConnection(id),
    });

    const getStatusIcon = (status: string) => {
        switch (status) {
            case "connected":
            case "active":
                return <CheckCircle className="w-5 h-5 text-green-500" />;
            case "failed":
            case "error":
                return <XCircle className="w-5 h-5 text-red-500" />;
            case "testing":
                return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
            default:
                return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
        }
    };

    const getStatusBadge = (status: string) => {
        const classes: Record<string, string> = {
            connected: "bg-green-100 text-green-700",
            active: "bg-green-100 text-green-700",
            failed: "bg-red-100 text-red-700",
            error: "bg-red-100 text-red-700",
            testing: "bg-blue-100 text-blue-700",
            pending: "bg-yellow-100 text-yellow-700",
            disconnected: "bg-gray-100 text-gray-700",
        };

        return (
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${classes[status] || classes.pending}`}>
                {status}
            </span>
        );
    };

    if (clustersLoading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            </div>
        );
    }

    if (clustersError) {
        return (
            <div className="text-center py-12">
                <AlertCircle className="w-12 h-12 mx-auto text-red-500" />
                <p className="mt-4 text-gray-600">Failed to load connections</p>
            </div>
        );
    }

    const totalClusters = clusters.length;
    const activeClusters = clusters.filter((c: Cluster) => c.status === "active" || c.connectionStatus === "connected").length;
    const errorClusters = clusters.filter((c: Cluster) => c.status === "error" || c.connectionStatus === "failed").length;

    return (
        <div>
            {/* Summary Cards */}
            <div className="grid grid-cols-4 gap-4 mb-8">
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                    <div className="text-3xl font-bold">{totalClusters}</div>
                    <div className="text-gray-500 text-sm mt-1">Total Connections</div>
                </div>
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                    <div className="text-3xl font-bold text-green-600">{activeClusters}</div>
                    <div className="text-gray-500 text-sm mt-1">Active</div>
                </div>
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                    <div className="text-3xl font-bold text-red-600">{errorClusters}</div>
                    <div className="text-gray-500 text-sm mt-1">Errors</div>
                </div>
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                    <div className="text-3xl font-bold text-blue-600">{cloudAccounts.length}</div>
                    <div className="text-gray-500 text-sm mt-1">Cloud Accounts</div>
                </div>
            </div>

            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h2 className="text-2xl font-bold">Connected Infrastructure</h2>
                    <p className="text-gray-500">Manage your connected clusters and cloud accounts</p>
                </div>
                <button
                    onClick={onAddConnection}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                    <Plus className="w-4 h-4" />
                    Add Connection
                </button>
            </div>

            {/* Clusters List */}
            {clusters.length === 0 ? (
                <div className="text-center py-16 bg-gray-50 rounded-xl">
                    <div className="text-6xl mb-4">☸️</div>
                    <h3 className="text-xl font-semibold text-gray-700">No Clusters Connected</h3>
                    <p className="text-gray-500 mt-2 mb-6">Connect your first Kubernetes cluster to get started</p>
                    <button
                        onClick={onAddConnection}
                        className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                    >
                        Connect Your First Cluster
                    </button>
                </div>
            ) : (
                <div className="space-y-4">
                    {(clusters as Cluster[]).map((cluster) => (
                        <div
                            key={cluster.id}
                            className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex items-start gap-4">
                                    <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center text-2xl">
                                        {cluster.provider === "kubernetes" ? "☸️" : cluster.provider === "aws" ? "☁️" : cluster.provider === "azure" ? "🔷" : "🔶"}
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-semibold">{cluster.name}</h3>
                                        {cluster.apiEndpoint && (
                                            <p className="text-sm text-gray-500 font-mono truncate max-w-md">
                                                {cluster.apiEndpoint}
                                            </p>
                                        )}
                                        <div className="flex items-center gap-2 mt-2">
                                            {getStatusIcon(cluster.connectionStatus || "unknown")}
                                            {getStatusBadge(cluster.connectionStatus || "unknown")}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => testMutation.mutate(cluster.id)}
                                        disabled={testMutation.isPending}
                                        className="p-2 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-colors"
                                        title="Test Connection"
                                    >
                                        <RefreshCw className={`w-4 h-4 ${testMutation.isPending ? "animate-spin" : ""}`} />
                                    </button>
                                    <button
                                        className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                                        title="Settings"
                                    >
                                        <Settings className="w-4 h-4" />
                                    </button>
                                    <button
                                        onClick={() => {
                                            if (confirm("Are you sure you want to delete this connection?")) {
                                                deleteMutation.mutate(cluster.id);
                                            }
                                        }}
                                        className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                                        title="Delete"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>

                            {/* Additional Info */}
                            <div className="mt-4 pt-4 border-t border-gray-100 flex items-center gap-6 text-sm text-gray-500">
                                <span>
                                    Namespaces: <strong className="text-gray-700">{cluster.namespaces?.length || 0}</strong>
                                </span>
                                {cluster.lastSyncAt && (
                                    <span>
                                        Last sync: <strong className="text-gray-700">{new Date(cluster.lastSyncAt).toLocaleDateString()}</strong>
                                    </span>
                                )}
                                {cluster.errorMessage && (
                                    <span className="text-red-500">
                                        Error: {cluster.errorMessage}
                                    </span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Cloud Accounts Section */}
            {cloudAccounts.length > 0 && (
                <>
                    <h3 className="text-xl font-bold mt-12 mb-6">Cloud Accounts</h3>
                    <div className="space-y-4">
                        {(cloudAccounts as CloudAccount[]).map((account) => (
                            <div
                                key={account.id}
                                className="bg-white rounded-xl p-6 shadow-sm border border-gray-100"
                            >
                                <div className="flex items-center gap-4">
                                    <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center text-xl">
                                        {account.provider === "aws" ? "☁️" : account.provider === "azure" ? "🔷" : "🔶"}
                                    </div>
                                    <div>
                                        <h4 className="font-semibold">{account.name}</h4>
                                        <p className="text-sm text-gray-500">
                                            {account.provider} • {account.regions?.length || 0} regions
                                        </p>
                                    </div>
                                    {getStatusBadge(account.status)}
                                </div>
                            </div>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
}

// Status Badge Component
function StatusBadge({ status }: { status: string }) {
    const colors: Record<string, string> = {
        active: "bg-green-100 text-green-700",
        connected: "bg-green-100 text-green-700",
        error: "bg-red-100 text-red-700",
        failed: "bg-red-100 text-red-700",
        pending: "bg-yellow-100 text-yellow-700",
        testing: "bg-blue-100 text-blue-700",
    };

    return (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || colors.pending}`}>
            {status}
        </span>
    );
}
