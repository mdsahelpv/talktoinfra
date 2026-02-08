import React from 'react';
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import type { QueryResultPaginationProps } from '@/types/conversation';

export const QueryResultPagination: React.FC<QueryResultPaginationProps> = ({
    pagination,
    onPageChange,
    onPageSizeChange,
    loading = false,
}) => {
    const { currentPage, pageSize, totalItems, totalPages } = pagination;

    const startItem = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
    const endItem = Math.min(currentPage * pageSize, totalItems);

    const handlePageSizeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        onPageSizeChange(Number(e.target.value));
        onPageChange(1); // Reset to first page when page size changes
    };

    const handlePageChange = (newPage: number) => {
        if (newPage >= 1 && newPage <= totalPages) {
            onPageChange(newPage);
        }
    };

    // Generate page numbers to show
    const getPageNumbers = (): (number | string)[] => {
        const pages: (number | string)[] = [];
        const maxVisiblePages = 5;

        if (totalPages <= maxVisiblePages + 2) {
            // Show all pages
            for (let i = 1; i <= totalPages; i++) {
                pages.push(i);
            }
        } else {
            // Always show first page
            pages.push(1);

            // Calculate range around current page
            const leftBound = Math.max(2, currentPage - Math.floor(maxVisiblePages / 2));
            const rightBound = Math.min(totalPages - 1, currentPage + Math.floor(maxVisiblePages / 2));

            // Add ellipsis if needed
            if (leftBound > 2) {
                pages.push('...');
            }

            // Add pages in range
            for (let i = leftBound; i <= rightBound; i++) {
                pages.push(i);
            }

            // Add ellipsis if needed
            if (rightBound < totalPages - 1) {
                pages.push('...');
            }

            // Always show last page
            pages.push(totalPages);
        }

        return pages;
    };

    if (totalItems === 0) {
        return null;
    }

    return (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 py-3 px-4 bg-gray-50 rounded-lg border border-gray-200">
            {/* Results info */}
            <div className="flex items-center gap-2 text-sm text-gray-600">
                {loading ? (
                    <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Loading...</span>
                    </>
                ) : (
                    <>
                        <span className="font-medium">Showing</span>
                        <span className="font-semibold">{startItem}-{endItem}</span>
                        <span className="font-medium">of {totalItems.toLocaleString()}</span>
                    </>
                )}
            </div>

            {/* Page size selector */}
            <div className="flex items-center gap-2">
                <label htmlFor="page-size" className="text-sm text-gray-600">
                    Results per page:
                </label>
                <select
                    id="page-size"
                    value={pageSize}
                    onChange={handlePageSizeChange}
                    disabled={loading}
                    className="px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                >
                    <option value={10}>10</option>
                    <option value={25}>25</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                </select>
            </div>

            {/* Page navigation */}
            <div className="flex items-center gap-1">
                {/* Previous page button */}
                <button
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1 || loading}
                    className="p-2 rounded-md hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    aria-label="Previous page"
                >
                    <ChevronLeft className="w-4 h-4" />
                </button>

                {/* Page numbers */}
                <div className="flex items-center gap-1">
                    {getPageNumbers().map((page, index) => (
                        <React.Fragment key={index}>
                            {typeof page === 'string' ? (
                                <span className="px-2 py-1 text-gray-400">...</span>
                            ) : (
                                <button
                                    onClick={() => handlePageChange(page as number)}
                                    disabled={loading}
                                    className={`min-w-[2rem] h-8 px-2 text-sm rounded-md transition-colors ${page === currentPage
                                            ? 'bg-blue-600 text-white font-medium'
                                            : 'hover:bg-gray-200'
                                        }`}
                                >
                                    {page}
                                </button>
                            )}
                        </React.Fragment>
                    ))}
                </div>

                {/* Next page button */}
                <button
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages || loading}
                    className="p-2 rounded-md hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    aria-label="Next page"
                >
                    <ChevronRight className="w-4 h-4" />
                </button>
            </div>

            {/* Page info */}
            <div className="text-xs text-gray-500 hidden sm:block">
                Page {currentPage} of {totalPages}
            </div>
        </div>
    );
};

export default QueryResultPagination;
