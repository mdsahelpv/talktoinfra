import { useState, useEffect, useCallback, useMemo } from 'react';
import { conversationsApi } from '@/api/conversations';
import type {
    UserPreferences,
    OutputFormat,
    UserQueryHistory,
    UserPreferenceClusterUsage,
} from '@/types/conversation';

interface UseUserPreferencesProps {
    userId: string;
    autoLoad?: boolean;
}

interface UseUserPreferencesReturn {
    // State
    preferences: UserPreferences;
    loading: boolean;
    error: string | null;
    hasChanges: boolean;

    // Preference actions
    updatePreferences: (updates: Partial<UserPreferences>) => void;
    savePreferences: () => Promise<void>;
    resetPreferences: () => Promise<void>;

    // Output format
    setOutputFormat: (format: OutputFormat) => void;

    // Cluster preferences
    setPreferredCluster: (clusterId: string | null) => void;
    incrementClusterUsage: (clusterId: string) => void;
    getPreferredCluster: () => string | null;

    // Query history
    addQueryToHistory: (query: Omit<UserQueryHistory, 'timestamp'>) => void;
    clearQueryHistory: () => Promise<void>;
    getRecentQueries: (limit?: number) => UserQueryHistory[];

    // Common queries
    addCommonQuery: (query: string) => void;
    removeCommonQuery: (query: string) => void;
    getCommonQueries: () => string[];

    // Namespace memory
    rememberNamespace: (clusterId: string, namespace: string) => Promise<void>;
    forgetNamespace: (clusterId: string, namespace: string) => Promise<void>;
    getRememberedNamespaces: (clusterId: string) => string[];

    // Suggestions
    getQuerySuggestions: () => Promise<string[]>;

    // Export/Import
    exportPreferences: () => string;
    importPreferences: (data: string) => Promise<void>;
}

const STORAGE_KEY = 'talktoinfra_user_preferences';

const defaultPreferences: UserPreferences = {
    user_id: '',
    preferred_output_format: 'table',
    preferred_cluster_id: null,
    cluster_usage: [],
    query_history: [],
    common_queries: [],
    remembered_namespaces: {},
    show_cluster_badges: true,
    auto_include_all_clusters: false,
    query_suggestions_enabled: true,
    last_active_at: new Date().toISOString(),
    created_at: new Date().toISOString(),
};

export const useUserPreferences = ({
    userId,
    autoLoad = true,
}: UseUserPreferencesProps): UseUserPreferencesReturn => {
    // State
    const [preferences, setPreferences] = useState<UserPreferences>({
        ...defaultPreferences,
        user_id: userId,
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [hasChanges, setHasChanges] = useState(false);
    const [originalPreferences, setOriginalPreferences] = useState<UserPreferences>(preferences);

    // Load preferences on mount
    useEffect(() => {
        if (autoLoad) {
            loadPreferences();
        }
    }, [autoLoad]);

    // Update last active timestamp periodically
    useEffect(() => {
        const interval = setInterval(() => {
            setPreferences(prev => ({
                ...prev,
                last_active_at: new Date().toISOString(),
            }));
            setHasChanges(true);
        }, 60000); // Every minute

        return () => clearInterval(interval);
    }, []);

    // Load preferences
    const loadPreferences = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            // Try to load from backend first
            try {
                const backendPrefs = await conversationsApi.getUserPreferences(userId);
                setPreferences(backendPrefs);
                setOriginalPreferences(backendPrefs);
            } catch {
                // Fallback to local storage
                const stored = localStorage.getItem(`${STORAGE_KEY}_${userId}`);
                if (stored) {
                    const storedPrefs = JSON.parse(stored) as UserPreferences;
                    setPreferences(storedPrefs);
                    setOriginalPreferences(storedPrefs);
                }
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load preferences');
            console.error('Failed to load preferences:', err);
        } finally {
            setLoading(false);
        }
    }, [userId]);

    // Update preferences
    const updatePreferences = useCallback((updates: Partial<UserPreferences>) => {
        setPreferences(prev => {
            const newPrefs = { ...prev, ...updates };
            setHasChanges(JSON.stringify(newPrefs) !== JSON.stringify(originalPreferences));
            return newPrefs;
        });
    }, [originalPreferences]);

    // Save preferences
    const savePreferences = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            // Save to backend
            await conversationsApi.updateUserPreferences(userId, preferences);

            // Save to local storage
            localStorage.setItem(`${STORAGE_KEY}_${userId}`, JSON.stringify(preferences));

            setOriginalPreferences(preferences);
            setHasChanges(false);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to save preferences');
            console.error('Failed to save preferences:', err);
            throw err;
        } finally {
            setLoading(false);
        }
    }, [preferences, userId]);

    // Reset preferences to defaults
    const resetPreferences = useCallback(async () => {
        const defaultPrefs: UserPreferences = {
            ...defaultPreferences,
            user_id: userId,
        };
        setPreferences(defaultPrefs);
        setHasChanges(true);
        await savePreferences();
    }, [userId, savePreferences]);

    // Set output format
    const setOutputFormat = useCallback((format: OutputFormat) => {
        updatePreferences({ preferred_output_format: format });

        // Also save to backend
        conversationsApi.updatePreferredOutputFormat(userId, format).catch(console.error);
    }, [updatePreferences, userId]);

    // Set preferred cluster
    const setPreferredCluster = useCallback((clusterId: string | null) => {
        updatePreferences({ preferred_cluster_id: clusterId });

        // Also save to backend
        conversationsApi.updatePreferredCluster(userId, clusterId).catch(console.error);
    }, [updatePreferences, userId]);

    // Increment cluster usage
    const incrementClusterUsage = useCallback((clusterId: string) => {
        setPreferences(prev => {
            const existingUsage = prev.cluster_usage.find(u => u.cluster_id === clusterId);
            const now = new Date().toISOString();

            if (existingUsage) {
                const updatedUsage = prev.cluster_usage.map(u =>
                    u.cluster_id === clusterId
                        ? { ...u, usage_count: u.usage_count + 1, last_used_at: now }
                        : u
                );
                return { ...prev, cluster_usage: updatedUsage };
            }

            return {
                ...prev,
                cluster_usage: [
                    ...prev.cluster_usage,
                    { cluster_id: clusterId, usage_count: 1, last_used_at: now },
                ],
            };
        });
        setHasChanges(true);
    }, []);

    // Get preferred cluster
    const getPreferredCluster = useCallback(() => {
        // First check explicit preference
        if (preferences.preferred_cluster_id) {
            return preferences.preferred_cluster_id;
        }

        // Fall back to most frequently used
        if (preferences.cluster_usage.length > 0) {
            const sorted = [...preferences.cluster_usage].sort((a, b) => b.usage_count - a.usage_count);
            return sorted[0].cluster_id;
        }

        return null;
    }, [preferences]);

    // Add query to history
    const addQueryToHistory = useCallback((query: Omit<UserQueryHistory, 'timestamp'>) => {
        setPreferences(prev => {
            const newQuery: UserQueryHistory = {
                ...query,
                timestamp: new Date().toISOString(),
            };

            // Add to front, limit to 100 entries
            const updatedHistory = [newQuery, ...prev.query_history].slice(0, 100);

            return { ...prev, query_history: updatedHistory };
        });
        setHasChanges(true);

        // Also save to backend
        conversationsApi.addQueryToHistory(userId, query).catch(console.error);
    }, [userId]);

    // Clear query history
    const clearQueryHistory = useCallback(async () => {
        setPreferences(prev => ({
            ...prev,
            query_history: [],
        }));
        setHasChanges(true);

        // Also clear in backend
        await conversationsApi.clearQueryHistory(userId);
    }, [userId]);

    // Get recent queries
    const getRecentQueries = useCallback((limit: number = 10) => {
        return preferences.query_history.slice(0, limit);
    }, [preferences]);

    // Add common query
    const addCommonQuery = useCallback((query: string) => {
        setPreferences(prev => {
            if (prev.common_queries.includes(query)) {
                return prev;
            }
            return {
                ...prev,
                common_queries: [query, ...prev.common_queries].slice(0, 20),
            };
        });
        setHasChanges(true);
    }, []);

    // Remove common query
    const removeCommonQuery = useCallback((query: string) => {
        setPreferences(prev => ({
            ...prev,
            common_queries: prev.common_queries.filter(q => q !== query),
        }));
        setHasChanges(true);
    }, []);

    // Get common queries
    const getCommonQueries = useCallback(() => {
        return preferences.common_queries;
    }, [preferences]);

    // Remember namespace for a cluster
    const rememberNamespace = useCallback(async (clusterId: string, namespace: string) => {
        setPreferences(prev => {
            const clusterNamespaces = prev.remembered_namespaces[clusterId] || [];
            if (clusterNamespaces.includes(namespace)) {
                return prev;
            }
            return {
                ...prev,
                remembered_namespaces: {
                    ...prev.remembered_namespaces,
                    [clusterId]: [namespace, ...clusterNamespaces].slice(0, 10),
                },
            };
        });
        setHasChanges(true);

        // Also save to backend
        await conversationsApi.rememberNamespace(userId, clusterId, namespace);
    }, [userId]);

    // Forget namespace for a cluster
    const forgetNamespace = useCallback(async (clusterId: string, namespace: string) => {
        setPreferences(prev => {
            const clusterNamespaces = prev.remembered_namespaces[clusterId] || [];
            return {
                ...prev,
                remembered_namespaces: {
                    ...prev.remembered_namespaces,
                    [clusterId]: clusterNamespaces.filter(n => n !== namespace),
                },
            };
        });
        setHasChanges(true);

        // Also forget in backend
        await conversationsApi.forgetNamespace(userId, clusterId, namespace);
    }, [userId]);

    // Get remembered namespaces for a cluster
    const getRememberedNamespaces = useCallback((clusterId: string) => {
        return preferences.remembered_namespaces[clusterId] || [];
    }, [preferences]);

    // Get query suggestions
    const getQuerySuggestions = useCallback(async (): Promise<string[]> => {
        if (!preferences.query_suggestions_enabled) {
            return [];
        }

        try {
            return await conversationsApi.getQuerySuggestions(userId);
        } catch {
            // Fallback to common queries
            return preferences.common_queries.slice(0, 5);
        }
    }, [preferences, userId]);

    // Export preferences
    const exportPreferences = useCallback(() => {
        return JSON.stringify(preferences, null, 2);
    }, [preferences]);

    // Import preferences
    const importPreferences = useCallback(async (data: string) => {
        try {
            const imported = JSON.parse(data) as UserPreferences;
            setPreferences({
                ...imported,
                user_id: userId,
            });
            setHasChanges(true);
            await savePreferences();
        } catch (err) {
            throw new Error('Invalid preferences data');
        }
    }, [userId, savePreferences]);

    return {
        // State
        preferences,
        loading,
        error,
        hasChanges,

        // Preference actions
        updatePreferences,
        savePreferences,
        resetPreferences,

        // Output format
        setOutputFormat,

        // Cluster preferences
        setPreferredCluster,
        incrementClusterUsage,
        getPreferredCluster,

        // Query history
        addQueryToHistory,
        clearQueryHistory,
        getRecentQueries,

        // Common queries
        addCommonQuery,
        removeCommonQuery,
        getCommonQueries,

        // Namespace memory
        rememberNamespace,
        forgetNamespace,
        getRememberedNamespaces,

        // Suggestions
        getQuerySuggestions,

        // Export/Import
        exportPreferences,
        importPreferences,
    };
};

export default useUserPreferences;
