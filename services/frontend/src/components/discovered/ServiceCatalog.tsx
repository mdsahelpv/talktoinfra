/**
 * Service Catalog Component.
 * Displays discovered services in a catalog view.
 */

import React from 'react';
import type { ServiceCatalogEntry, ServiceCatalogResponse } from '@/lib/types/discovered';

interface ServiceCatalogProps {
    catalog: ServiceCatalogResponse;
    onServiceClick?: (service: ServiceCatalogEntry) => void;
}

export const ServiceCatalog: React.FC<ServiceCatalogProps> = ({
    catalog,
    onServiceClick,
}) => {
    const getMethodColor = (method: string) => {
        switch (method) {
            case 'GET': return 'bg-green-100 text-green-800';
            case 'POST': return 'bg-blue-100 text-blue-800';
            case 'PUT': return 'bg-yellow-100 text-yellow-800';
            case 'DELETE': return 'bg-red-100 text-red-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="bg-white rounded-lg shadow">
            <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
                <h3 className="text-lg leading-6 font-medium text-gray-900">Service Catalog</h3>
                <p className="mt-1 text-sm text-gray-500">
                    {catalog.total} services discovered across your infrastructure
                </p>
            </div>

            <div className="px-4 py-5 sm:p-6">
                {/* Service Type Summary */}
                <div className="flex flex-wrap gap-2 mb-6">
                    {Object.entries(catalog.by_type).map(([type, count]) => (
                        <span
                            key={type}
                            className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800"
                        >
                            <span className="capitalize">{type.replace('_', ' ')}</span>
                            <span className="ml-2 bg-gray-200 text-gray-700 px-2 py-0.5 rounded-full text-xs">
                                {count}
                            </span>
                        </span>
                    ))}
                </div>

                {/* Services List */}
                {catalog.services.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                        </svg>
                        <p className="mt-2">No services discovered yet</p>
                    </div>
                ) : (
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                        {catalog.services.map((service) => (
                            <div
                                key={service.id}
                                className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                                onClick={() => onServiceClick?.(service)}
                            >
                                <div className="flex items-center justify-between mb-2">
                                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getMethodColor(service.method)}`}>
                                        {service.method}
                                    </span>
                                    {service.auth_required && (
                                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800">
                                            🔒 Auth Required
                                        </span>
                                    )}
                                </div>

                                <h4 className="text-sm font-medium text-gray-900 truncate">
                                    {service.service_name || service.endpoint}
                                </h4>

                                <p className="text-xs text-gray-500 truncate mt-1">
                                    {service.path || service.endpoint}
                                </p>

                                {service.description && (
                                    <p className="text-xs text-gray-600 mt-2 line-clamp-2">
                                        {service.description}
                                    </p>
                                )}

                                <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
                                    <span className="text-xs text-gray-500">
                                        {service.service_type || 'API'}
                                        {service.api_version && ` v${service.api_version}`}
                                    </span>
                                    {service.response_time_ms && (
                                        <span className="text-xs text-gray-500">
                                            {service.response_time_ms}ms
                                        </span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
