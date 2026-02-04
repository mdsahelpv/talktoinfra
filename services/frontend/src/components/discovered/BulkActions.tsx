/**
 * Bulk Actions Component.
 * Provides bulk operations for selected discovered infrastructure items.
 */

import React, { useState } from 'react';

interface BulkActionsProps {
    selectedCount: number;
    onOnboardSelected: () => void;
    onIgnoreSelected: (reason?: string) => void;
    onExportSelected: () => void;
    onClearSelection: () => void;
    loading?: boolean;
}

export const BulkActions: React.FC<BulkActionsProps> = ({
    selectedCount,
    onOnboardSelected,
    onIgnoreSelected,
    onExportSelected,
    onClearSelection,
    loading = false,
}) => {
    const [showIgnoreDialog, setShowIgnoreDialog] = useState(false);
    const [ignoreReason, setIgnoreReason] = useState('');

    if (selectedCount === 0) return null;

    const handleIgnore = () => {
        onIgnoreSelected(ignoreReason);
        setShowIgnoreDialog(false);
        setIgnoreReason('');
    };

    return (
        <>
            <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg z-40">
                <div className="max-w-7xl mx-auto px-4 py-3 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center">
                            <span className="text-sm text-gray-700 mr-4">
                                <strong>{selectedCount}</strong> item{selectedCount !== 1 ? 's' : ''} selected
                            </span>
                            <button
                                onClick={onClearSelection}
                                className="text-sm text-gray-500 hover:text-gray-700"
                            >
                                Clear selection
                            </button>
                        </div>
                        <div className="flex items-center space-x-3">
                            <button
                                onClick={onOnboardSelected}
                                disabled={loading}
                                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none disabled:opacity-50"
                            >
                                <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                                </svg>
                                Onboard Selected
                            </button>
                            <button
                                onClick={() => setShowIgnoreDialog(true)}
                                disabled={loading}
                                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none disabled:opacity-50"
                            >
                                <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                                Ignore Selected
                            </button>
                            <button
                                onClick={onExportSelected}
                                disabled={loading}
                                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none disabled:opacity-50"
                            >
                                <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                Export CSV
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Ignore Dialog */}
            {showIgnoreDialog && (
                <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
                    <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
                        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" onClick={() => setShowIgnoreDialog(false)} />
                        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

                        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                            <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                                <div className="sm:flex sm:items-start">
                                    <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-yellow-100 sm:mx-0 sm:h-10 sm:w-10">
                                        <svg className="h-6 w-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                        </svg>
                                    </div>
                                    <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                                        <h3 className="text-lg leading-6 font-medium text-gray-900" id="modal-title">
                                            Ignore {selectedCount} Item{selectedCount !== 1 ? 's' : ''}?
                                        </h3>
                                        <div className="mt-2">
                                            <p className="text-sm text-gray-500">
                                                These items will be hidden from suggestions and default views. You can undo this later.
                                            </p>
                                            <textarea
                                                className="mt-4 w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                                                rows={3}
                                                placeholder="Reason for ignoring (optional)"
                                                value={ignoreReason}
                                                onChange={(e) => setIgnoreReason(e.target.value)}
                                            />
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                                <button
                                    type="button"
                                    onClick={handleIgnore}
                                    className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-yellow-600 text-base font-medium text-white hover:bg-yellow-700 focus:outline-none sm:ml-3 sm:w-auto sm:text-sm"
                                >
                                    Ignore Selected
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setShowIgnoreDialog(false)}
                                    className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};
