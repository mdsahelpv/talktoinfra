/**
 * Discovered Infrastructure Page.
 * Main page for viewing and managing all discovered infrastructure.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
    InfrastructureList,
    InfrastructureDetail,
    ServiceCatalog,
    BulkActions,
    DiscoveredStatsCards,
    DiscoveredFilters,
} from '@/components/discovered';
import {
    listDiscovered,
    getDiscoveredStats,
    getDiscoveredDetail,
    onboardItem,
    ignoreItem,
    exportDiscovered,
    bulkOnboard,
    bulkIgnore,
    getServiceCatalog,
} from '@/lib/api/discovered';
import type {
    DiscoveredInfrastructure,
    DiscoveredInfrastructureDetail,
    DiscoveredStats,
    DiscoveredFilter,
    ServiceCatalogResponse,
    ServiceCatalogEntry,
    InfrastructureType,
} from '@/lib/types/discovered';
import { INFRA_TYPE_ICONS } from '@/lib/types/discovered';

type TabType = 'all' | InfrastructureType | 'services';

const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: 'all', label: 'All Discovered', icon: '🌐' },
    { id: 'kubernetes_cluster', label: 'Kubernetes', icon: '🏢' },
    { id: 'cloud_resource', label: 'Cloud', icon: '☁️' },
    { id: 'database', label: 'Databases', icon: '🗄️' },
    { id: 'load_balancer', label: 'Load Balancers', icon: '⚖️' },
    { id: 'service', label: 'Services', icon: '🌐' },
    { id: 'network_device', label: 'Network Devices', icon: '🔌' },
    { id: 'host', label: 'Hosts', icon: '💻' },
    { id: 'services', label: 'Service Catalog', icon: '📚' },
];

export const DiscoveredInfrastructurePage: React.FC = () => {
    // State
    const [activeTab, setActiveTab] = useState<TabType>('all');
    const [items, setItems] = useState<DiscoveredInfrastructure[]>([]);
    const [stats, setStats] = useState<DiscoveredStats | null>(null);
    const [serviceCatalog, setServiceCatalog] = useState<ServiceCatalogResponse | null>(null);
    const [selectedItem, setSelectedItem] = useState<DiscoveredInfrastructureDetail | null>(null);
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [filters, setFilters] = useState<DiscoveredFilter>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    // Fetch items
    const fetchItems = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const infraType = activeTab !== 'all' && activeTab !== 'services' ? activeTab : undefined;
            const result = await listDiscovered(
                page,
                50,
                infraType,
                filters.states?.[0],
                filters.search_query
            );
            setItems(result.items);
            setTotalPages(result.pages);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch items');
        } finally {
            setLoading(false);
        }
    }, [activeTab, page, filters]);

    // Fetch stats
    const fetchStats = useCallback(async () => {
        try {
            const result = await getDiscoveredStats();
            setStats(result);
        } catch (err) {
            console.error('Failed to fetch stats:', err);
        }
    }, []);

    // Fetch service catalog
    const fetchServiceCatalog = useCallback(async () => {
        try {
            const result = await getServiceCatalog();
            setServiceCatalog(result);
        } catch (err) {
            console.error('Failed to fetch service catalog:', err);
        }
    }, []);

    // Fetch items when tab or filters change
    useEffect(() => {
        if (activeTab !== 'services') {
            fetchItems();
        }
    }, [activeTab, fetchItems]);

    // Fetch stats on mount
    useEffect(() => {
        fetchStats();
        fetchServiceCatalog();
    }, [fetchStats, fetchServiceCatalog]);

    // Handle item click
    const handleItemClick = async (item: DiscoveredInfrastructure) => {
        try {
            const detail = await getDiscoveredDetail(item.id);
            setSelectedItem(detail);
        } catch (err) {
            console.error('Failed to fetch item detail:', err);
        }
    };

    // Handle selection
    const handleSelect = (id: string, selected: boolean) => {
        const newSelected = new Set(selectedIds);
        if (selected) {
            newSelected.add(id);
        } else {
            newSelected.delete(id);
        }
        setSelectedIds(newSelected);
    };

    // Handle select all
    const handleSelectAll = (selected: boolean) => {
        if (selected) {
            setSelectedIds(new Set(items.map((item) => item.id)));
        } else {
            setSelectedIds(new Set());
        }
    };

    // Handle onboarding
    const handleOnboard = async (itemId: string) => {
        try {
            await onboardItem(itemId);
            fetchItems();
            fetchStats();
            setSelectedItem(null);
        } catch (err) {
            console.error('Failed to onboard item:', err);
        }
    };

    // Handle ignore
    const handleIgnore = async (itemId: string, reason?: string) => {
        try {
            await ignoreItem(itemId, { reason });
            fetchItems();
            fetchStats();
            setSelectedItem(null);
        } catch (err) {
            console.error('Failed to ignore item:', err);
        }
    };

    // Handle bulk onboard
    const handleBulkOnboard = async () => {
        if (selectedIds.size === 0) return;
        try {
            await bulkOnboard({
                item_ids: Array.from(selectedIds),
                action_type: 'onboard',
                options: {},
            });
            setSelectedIds(new Set());
            fetchItems();
            fetchStats();
        } catch (err) {
            console.error('Failed to bulk onboard:', err);
        }
    };

    // Handle bulk ignore
    const handleBulkIgnore = async (reason?: string) => {
        if (selectedIds.size === 0) return;
        try {
            await bulkIgnore({
                item_ids: Array.from(selectedIds),
                reason,
            });
            setSelectedIds(new Set());
            fetchItems();
            fetchStats();
        } catch (err) {
            console.error('Failed to bulk ignore:', err);
        }
    };

    // Handle export
    const handleExport = async () => {
        try {
            const blob = await exportDiscovered({
                item_ids: Array.from(selectedIds),
                format: 'csv',
                include_fields: [],
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `discovered_infrastructure_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Failed to export:', err);
        }
    };

    // Handle rescan (placeholder)
    const handleRescan = async (itemId: string) => {
        console.log('Rescan requested for:', itemId);
        // TODO: Implement rescan functionality
    };

    return (
        <div className="min-h-screen bg-gray-100 pb-24">
            {/* Header */}
            <div className="bg-white shadow">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                    <h1 className="text-2xl font-bold text-gray-900">Discovered Infrastructure</h1>
                    <p className="mt-1 text-sm text-gray-500">
                        View, manage, and onboard all infrastructure discovered by your scans
                    </p>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                {/* Stats Cards */}
                {stats && <DiscoveredStatsCards stats={stats} />}

                {/* Tabs */}
                <div className="border-b border-gray-200 mb-6">
                    <nav className="-mb-px flex space-x-8 overflow-x-auto" aria-label="Tabs">
                        {tabs.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => {
                                    setActiveTab(tab.id);
                                    setPage(1);
                                }}
                                className={`${activeTab === tab.id
                                    ? 'border-blue-500 text-blue-600'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm flex items-center`}
                            >
                                <span className="mr-2">{tab.icon}</span>
                                {tab.label}
                            </button>
                        ))}
                    </nav>
                </div>

                {/* Content */}
                {activeTab === 'services' ? (
                    // Service Catalog View
                    serviceCatalog && (
                        <ServiceCatalog
                            catalog={serviceCatalog}
                            onServiceClick={(service: ServiceCatalogEntry) => {
                                // Navigate to host detail
                                console.log('Service clicked:', service);
                            }}
                        />
                    )
                ) : (
                    // Infrastructure List View
                    <>
                        {/* Filters */}
                        <DiscoveredFilters
                            filters={filters}
                            onFiltersChange={setFilters}
                            onSearch={(query: string) => setFilters({ ...filters, search_query: query })}
                        />

                        {/* Error Message */}
                        {error && (
                            <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
                                <div className="flex">
                                    <div className="flex-shrink-0">
                                        <svg className="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                        </svg>
                                    </div>
                                    <div className="ml-3">
                                        <h3 className="text-sm font-medium text-red-800">Error loading data</h3>
                                        <p className="mt-2 text-sm text-red-700">{error}</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* List */}
                        <InfrastructureList
                            items={items}
                            selectedIds={selectedIds}
                            onSelect={handleSelect}
                            onSelectAll={handleSelectAll}
                            onItemClick={handleItemClick}
                            loading={loading}
                        />

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3 sm:px-6 mt-4">
                                <div className="flex flex-1 justify-between sm:hidden">
                                    <button
                                        onClick={() => setPage(page - 1)}
                                        disabled={page === 1}
                                        className="relative inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                                    >
                                        Previous
                                    </button>
                                    <button
                                        onClick={() => setPage(page + 1)}
                                        disabled={page === totalPages}
                                        className="relative ml-3 inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                                    >
                                        Next
                                    </button>
                                </div>
                                <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                                    <div>
                                        <p className="text-sm text-gray-700">
                                            Showing page <span className="font-medium">{page}</span> of{' '}
                                            <span className="font-medium">{totalPages}</span>
                                        </p>
                                    </div>
                                    <div>
                                        <nav className="isolate inline-flex -space-x-px rounded-md shadow-sm" aria-label="Pagination">
                                            <button
                                                onClick={() => setPage(page - 1)}
                                                disabled={page === 1}
                                                className="relative inline-flex items-center rounded-l-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                                            >
                                                <span className="sr-only">Previous</span>
                                                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                                    <path fillRule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clipRule="evenodd" />
                                                </svg>
                                            </button>
                                            {[...Array(Math.min(5, totalPages))].map((_, i) => {
                                                const pageNum = i + 1;
                                                return (
                                                    <button
                                                        key={pageNum}
                                                        onClick={() => setPage(pageNum)}
                                                        className={`relative inline-flex items-center px-4 py-2 text-sm font-semibold ${page === pageNum
                                                            ? 'z-10 bg-blue-600 text-white focus:z-20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600'
                                                            : 'text-gray-900 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:outline-offset-0'
                                                            }`}
                                                    >
                                                        {pageNum}
                                                    </button>
                                                );
                                            })}
                                            <button
                                                onClick={() => setPage(page + 1)}
                                                disabled={page === totalPages}
                                                className="relative inline-flex items-center rounded-r-md px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50"
                                            >
                                                <span className="sr-only">Next</span>
                                                <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                                    <path fillRule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clipRule="evenodd" />
                                                </svg>
                                            </button>
                                        </nav>
                                    </div>
                                </div>
                            </div>
                        )}
                    </>
                )}
            </div>

            {/* Bulk Actions Bar */}
            <BulkActions
                selectedCount={selectedIds.size}
                onOnboardSelected={handleBulkOnboard}
                onIgnoreSelected={handleBulkIgnore}
                onExportSelected={handleExport}
                onClearSelection={() => setSelectedIds(new Set())}
            />

            {/* Detail Modal */}
            {selectedItem && (
                <InfrastructureDetail
                    item={selectedItem}
                    onClose={() => setSelectedItem(null)}
                    onOnboard={handleOnboard}
                    onIgnore={handleIgnore}
                    onRescan={handleRescan}
                />
            )}
        </div>
    );
};

export default DiscoveredInfrastructurePage;
