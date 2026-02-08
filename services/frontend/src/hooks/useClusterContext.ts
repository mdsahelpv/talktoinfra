import { useState, useEffect, useCallback, useMemo } from 'react';
import { conversationsApi } from '@/api/conversations';
import type {
    ClusterInfo,
    NamespaceInfo,
    ClusterContext,
    ClusterContextMode,
} from '@/types/conversation';

interface UseClusterContextProps {
    userId: string;
    initialClusterId?: string | null;
    initialNamespace?: string | null;
    autoLoad?: boolean;
}

interface UseClusterContextReturn {
    // State
    clusters: ClusterInfo[];
    namespaces: NamespaceInfo[];
    context: ClusterContext;
    loading: boolean;
    error: string | null;

    // Cluster actions
    setSelectedCluster: (clusterId: string | null) => void;
    selectCluster: (clusterId: string) => Promise<void>;
    refreshClusters: () => Promise<void>;
    testClusterConnection: (clusterId: string) => Promise<{ success: boolean; message: string }>;

    // Mode actions
    setMode: (mode: ClusterContextMode) => void;
    toggleMode: () => void;

    // Namespace actions
    setSelectedNamespace: (namespace: string | null) => void;
    refreshNamespaces: (clusterId: string) => Promise<void>;

    // Context persistence
    saveContext: () => Promise<void>;
    loadContext: () => Promise<void>;

    // Computed
    selectedCluster: ClusterInfo | null;
    selectedNamespace: NamespaceInfo | null;
    connectedClusters: ClusterInfo[];
    isAllClustersMode: boolean;
    clusterCounts: { total: number; connected: number; disconnected: number };
}

const STORAGE_KEY = 'talktoinfra_cluster_context';

const defaultContext: ClusterContext = {
    mode: 'single',
    selected_cluster_id: null,
    selected_namespace: null,
    available_clusters: [],
    available_namespaces: [],
};

export const useClusterContext = ({
    userId,
    initialClusterId = null,
    initialNamespace = null,
    autoLoad = true,
}: UseClusterContextProps): UseClusterContextReturn => {
    // State
    const [clusters, setClusters] = useState<ClusterInfo[]>([]);
    const [namespaces, setNamespaces] = useState<NamespaceInfo[]>([]);
    const [context, setContext] = useState<ClusterContext>(defaultContext);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Load clusters on mount
    useEffect(() => {
        if (autoLoad) {
            refreshClusters();
        }
    }, [autoLoad]);

    // Initialize context with initial values
    useEffect(() => {
        if (initialClusterId !== undefined) {
            setContext(prev => ({
                ...prev,
                selected_cluster_id: initialClusterId,
            }));
        }
        if (initialNamespace !== undefined) {
            setContext(prev => ({
                ...prev,
                selected_namespace: initialNamespace,
            }));
        }
    }, [initialClusterId, initialNamespace]);

    // Refresh clusters
    const refreshClusters = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const clustersData = await conversationsApi.listClusters();
            setClusters(clustersData);

            // If no cluster selected and we have clusters, select the first one
            if (!context.selected_cluster_id && clustersData.length > 0) {
                setContext(prev => ({
                    ...prev,
                    selected_cluster_id: clustersData[0].id,
                }));
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load clusters');
            console.error('Failed to load clusters:', err);
        } finally {
            setLoading(false);
        }
    }, [context.selected_cluster_id]);

    // Select a cluster
    const selectCluster = useCallback(async (clusterId: string) => {
        setContext(prev => ({
            ...prev,
            selected_cluster_id: clusterId,
            selected_namespace: null, // Reset namespace when changing cluster
        }));

        // Load namespaces for the selected cluster
        await refreshNamespaces(clusterId);
    }, []);

    // Set selected cluster (without loading namespaces)
    const setSelectedCluster = useCallback((clusterId: string | null) => {
        setContext(prev => ({
            ...prev,
            selected_cluster_id: clusterId,
        }));
    }, []);

    // Test cluster connection
    const testClusterConnection = useCallback(async (clusterId: string) => {
        try {
            const result = await conversationsApi.testClusterConnection(clusterId);
            return result;
        } catch (err) {
            return {
                success: false,
                message: err instanceof Error ? err.message : 'Connection test failed',
            };
        }
    }, []);

    // Set mode
    const setMode = useCallback((mode: ClusterContextMode) => {
        setContext(prev => ({
            ...prev,
            mode,
        }));
    }, []);

    // Toggle mode
    const toggleMode = useCallback(() => {
        setContext(prev => ({
            ...prev,
            mode: prev.mode === 'single' ? 'all' : 'single',
        }));
    }, []);

    // Refresh namespaces for a cluster
    const refreshNamespaces = useCallback(async (clusterId: string) => {
        try {
            const namespacesData = await conversationsApi.getClusterNamespaces(clusterId);
            setNamespaces(namespacesData);
        } catch (err) {
            console.error('Failed to load namespaces:', err);
            setNamespaces([]);
        }
    }, []);

    // Set selected namespace
    const setSelectedNamespace = useCallback((namespace: string | null) => {
        setContext(prev => ({
            ...prev,
            selected_namespace: namespace,
        }));
    }, []);

    // Save context to local storage and backend
    const saveContext = useCallback(async () => {
        try {
            // Save to local storage
            const contextToSave: ClusterContext & { last_updated: string } = {
                ...context,
                available_clusters: clusters,
                available_namespaces: namespaces,
                last_updated: new Date().toISOString(),
            };
            localStorage.setItem(`${STORAGE_KEY}_${userId}`, JSON.stringify(contextToSave));

            // Save to backend
            await conversationsApi.saveClusterContext(userId, context);
        } catch (err) {
            console.error('Failed to save cluster context:', err);
        }
    }, [context, clusters, namespaces, userId]);

    // Load context from local storage and backend
    const loadContext = useCallback(async () => {
        setLoading(true);
        try {
            // Try to load from backend first
            try {
                const backendContext = await conversationsApi.loadClusterContext(userId);
                setContext(backendContext);

                // Also load namespaces for selected cluster
                if (backendContext.selected_cluster_id) {
                    await refreshNamespaces(backendContext.selected_cluster_id);
                }
            } catch {
                // Fallback to local storage
                const localStorageKey = `${STORAGE_KEY}_${userId}`;
                const stored = localStorage.getItem(localStorageKey);
                if (stored) {
                    const storedContext = JSON.parse(stored) as ClusterContext;
                    setContext(storedContext);

                    if (storedContext.selected_cluster_id) {
                        await refreshNamespaces(storedContext.selected_cluster_id);
                    }
                }
            }
        } catch (err) {
            console.error('Failed to load cluster context:', err);
        } finally {
            setLoading(false);
        }
    }, [userId, refreshNamespaces]);

    // Computed values
    const selectedCluster = useMemo(() => {
        return clusters.find(c => c.id === context.selected_cluster_id) || null;
    }, [clusters, context.selected_cluster_id]);

    const selectedNamespace = useMemo(() => {
        if (!context.selected_namespace) return null;
        return namespaces.find(n => n.name === context.selected_namespace) || null;
    }, [namespaces, context.selected_namespace]);

    const connectedClusters = useMemo(() => {
        return clusters.filter(c => c.status === 'connected');
    }, [clusters]);

    const isAllClustersMode = context.mode === 'all';

    const clusterCounts = useMemo(() => {
        return {
            total: clusters.length,
            connected: clusters.filter(c => c.status === 'connected').length,
            disconnected: clusters.filter(c => c.status === 'disconnected').length,
        };
    }, [clusters]);

    // Auto-save context when it changes
    useEffect(() => {
        if (context.selected_cluster_id) {
            saveContext();
        }
    }, [context, saveContext]);

    return {
        // State
        clusters,
        namespaces,
        context,
        loading,
        error,

        // Cluster actions
        setSelectedCluster,
        selectCluster,
        refreshClusters,
        testClusterConnection,

        // Mode actions
        setMode,
        toggleMode,

        // Namespace actions
        setSelectedNamespace,
        refreshNamespaces,

        // Context persistence
        saveContext,
        loadContext,

        // Computed
        selectedCluster,
        selectedNamespace,
        connectedClusters,
        isAllClustersMode,
        clusterCounts,
    };
};

export default useClusterContext;
