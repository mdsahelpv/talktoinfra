/**
 * Infrastructure Detail Component.
 * Shows detailed information about a discovered infrastructure item.
 */

import React, { useState } from 'react';
import type { DiscoveredInfrastructureDetail } from '@/lib/types/discovered';
import { INFRA_TYPE_ICONS, STATE_COLORS } from '@/lib/types/discovered';

interface InfrastructureDetailProps {
    item: DiscoveredInfrastructureDetail | null;
    onClose: () => void;
    onOnboard: (itemId: string) => void;
    onIgnore: (itemId: string, reason?: string) => void;
    onRescan: (itemId: string) => void;
}

export const InfrastructureDetail: React.FC<InfrastructureDetailProps> = ({
    item,
    onClose,
    onOnboard,
    onIgnore,
    onRescan,
}) => {
    const [ignoreReason, setIgnoreReason] = useState('');

    if (!item) return null;

    const handleIgnore = () => {
        onIgnore(item.id, ignoreReason);
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
            <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
                <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" onClick={onClose} />
                <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

                <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
                    {/* Header */}
                    <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4 border-b">
                        <div className="flex items-start">
                            <div className="flex-shrink-0 h-16 w-16 flex items-center justify-center bg-gray-100 rounded-xl text-3xl">
                                {INFRA_TYPE_ICONS[item.infra_type] || '❓'}
                            </div>
                            <div className="mt-2 ml-4 flex-1">
                                <h3 className="text-lg leading-6 font-medium text-gray-900" id="modal-title">
                                    {item.hostname || item.ip_address || 'Unknown Infrastructure'}
                                </h3>
                                <p className="text-sm text-gray-500 mt-1">
                                    {item.fqdn && <span className="mr-3">{item.fqdn}</span>}
                                    <span
                                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                                        style={{
                                            backgroundColor: `${STATE_COLORS[item.state]}20`,
                                            color: STATE_COLORS[item.state],
                                        }}
                                    >
                                        {item.state.replace('_', ' ')}
                                    </span>
                                </p>
                            </div>
                            <button
                                onClick={onClose}
                                className="bg-white rounded-md text-gray-400 hover:text-gray-500 focus:outline-none"
                            >
                                <span className="sr-only">Close</span>
                                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="px-4 pt-5 pb-4 sm:p-6 sm:pb-4 max-h-96 overflow-y-auto">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Basic Information */}
                            <div className="bg-gray-50 rounded-lg p-4">
                                <h4 className="text-sm font-medium text-gray-900 mb-3">Basic Information</h4>
                                <dl className="grid grid-cols-1 gap-2 text-sm">
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">IP Address</dt>
                                        <dd className="font-mono text-gray-900">{item.ip_address || 'N/A'}</dd>
                                    </div>
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Hostname</dt>
                                        <dd className="text-gray-900">{item.hostname || 'N/A'}</dd>
                                    </div>
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Type</dt>
                                        <dd className="text-gray-900 capitalize">{item.infra_type.replace('_', ' ')}</dd>
                                    </div>
                                    {item.service_type && (
                                        <div className="flex justify-between">
                                            <dt className="text-gray-500">Service</dt>
                                            <dd className="text-gray-900">{item.service_type}</dd>
                                        </div>
                                    )}
                                    {item.service_version && (
                                        <div className="flex justify-between">
                                            <dt className="text-gray-500">Version</dt>
                                            <dd className="text-gray-900">{item.service_version}</dd>
                                        </div>
                                    )}
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Confidence</dt>
                                        <dd className="text-gray-900">{item.confidence_score}%</dd>
                                    </div>
                                </dl>
                            </div>

                            {/* Network Information */}
                            <div className="bg-gray-50 rounded-lg p-4">
                                <h4 className="text-sm font-medium text-gray-900 mb-3">Network Information</h4>
                                <dl className="grid grid-cols-1 gap-2 text-sm">
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Open Ports</dt>
                                        <dd className="text-gray-900">{item.open_ports.length} ports</dd>
                                    </div>
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Response Time</dt>
                                        <dd className="text-gray-900">{item.response_time_ms ? `${item.response_time_ms}ms` : 'N/A'}</dd>
                                    </div>
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Availability</dt>
                                        <dd className="text-gray-900">{item.availability_score}%</dd>
                                    </div>
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Discovered</dt>
                                        <dd className="text-gray-900">{new Date(item.discovered_at).toLocaleString()}</dd>
                                    </div>
                                    <div className="flex justify-between">
                                        <dt className="text-gray-500">Last Seen</dt>
                                        <dd className="text-gray-900">{new Date(item.last_seen_at).toLocaleString()}</dd>
                                    </div>
                                </dl>
                            </div>

                            {/* Open Ports */}
                            <div className="bg-gray-50 rounded-lg p-4 md:col-span-2">
                                <h4 className="text-sm font-medium text-gray-900 mb-3">Open Ports & Services</h4>
                                <div className="overflow-x-auto">
                                    <table className="min-w-full divide-y divide-gray-200">
                                        <thead className="bg-gray-100">
                                            <tr>
                                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Port</th>
                                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Protocol</th>
                                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Service</th>
                                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Version</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-200">
                                            {item.open_ports.map((port) => (
                                                <tr key={port.port}>
                                                    <td className="px-3 py-2 text-sm font-mono text-gray-900">{port.port}</td>
                                                    <td className="px-3 py-2 text-sm text-gray-500">{port.protocol}</td>
                                                    <td className="px-3 py-2 text-sm">
                                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${port.status === 'open' ? 'bg-green-100 text-green-800' :
                                                                port.status === 'closed' ? 'bg-red-100 text-red-800' :
                                                                    'bg-yellow-100 text-yellow-800'
                                                            }`}>
                                                            {port.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-3 py-2 text-sm text-gray-900">{port.service || 'Unknown'}</td>
                                                    <td className="px-3 py-2 text-sm text-gray-500">{port.service_version || '-'}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            {/* Service Banner */}
                            {item.service_banner && (
                                <div className="bg-gray-50 rounded-lg p-4 md:col-span-2">
                                    <h4 className="text-sm font-medium text-gray-900 mb-3">Service Banner</h4>
                                    <pre className="text-xs bg-gray-900 text-green-400 p-3 rounded overflow-x-auto">
                                        {item.service_banner}
                                    </pre>
                                </div>
                            )}

                            {/* State History */}
                            {item.state_history.length > 0 && (
                                <div className="bg-gray-50 rounded-lg p-4 md:col-span-2">
                                    <h4 className="text-sm font-medium text-gray-900 mb-3">State History</h4>
                                    <div className="flow-root">
                                        <ul className="-mb-8">
                                            {item.state_history.map((entry, index) => (
                                                <li key={entry.id}>
                                                    <div className="relative pb-8">
                                                        {index !== item.state_history.length - 1 && (
                                                            <span className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true" />
                                                        )}
                                                        <div className="relative flex space-x-3">
                                                            <div>
                                                                <span className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center ring-8 ring-white">
                                                                    <svg className="h-4 w-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                                                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                                                                    </svg>
                                                                </span>
                                                            </div>
                                                            <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                                                                <div>
                                                                    <p className="text-sm text-gray-500">
                                                                        Changed from <span className="font-medium text-gray-900">{entry.from_state}</span> to <span className="font-medium text-gray-900">{entry.to_state}</span>
                                                                    </p>
                                                                    {entry.trigger_reason && (
                                                                        <p className="text-xs text-gray-400 mt-1">{entry.trigger_reason}</p>
                                                                    )}
                                                                </div>
                                                                <div className="text-right text-sm whitespace-nowrap text-gray-500">
                                                                    {new Date(entry.created_at).toLocaleString()}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                        <button
                            type="button"
                            onClick={() => onOnboard(item.id)}
                            className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm"
                        >
                            Onboard / Connect
                        </button>
                        <button
                            type="button"
                            onClick={() => onRescan(item.id)}
                            className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                        >
                            Re-scan
                        </button>
                        <button
                            type="button"
                            onClick={handleIgnore}
                            className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:w-auto sm:text-sm"
                        >
                            Ignore
                        </button>
                        <button
                            type="button"
                            onClick={onClose}
                            className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                        >
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
