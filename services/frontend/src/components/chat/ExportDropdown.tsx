import React, { useState, useRef, useEffect } from 'react';
import { Download, FileSpreadsheet, ChevronDown } from 'lucide-react';
import type { ExportDropdownProps } from '@/types/conversation';

export const ExportDropdown: React.FC<ExportDropdownProps> = ({
    data,
    filename = 'export',
    disabled = false,
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const convertToCSV = (data: Record<string, unknown>[]): string => {
        if (data.length === 0) return '';

        // Flatten nested objects and extract headers
        const flattenObject = (obj: Record<string, unknown>, prefix = ''): Record<string, unknown> => {
            const flattened: Record<string, unknown> = {};

            for (const [key, value] of Object.entries(obj)) {
                const newKey = prefix ? `${prefix}.${key}` : key;

                if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
                    Object.assign(flattened, flattenObject(value as Record<string, unknown>, newKey));
                } else {
                    flattened[newKey] = value;
                }
            }

            return flattened;
        };

        // Flatten all rows
        const flattenedData = data.map(row => flattenObject(row));

        // Get all unique headers
        const headers = new Set<string>();
        flattenedData.forEach(row => {
            Object.keys(row).forEach(key => headers.add(key));
        });
        const headerArray = Array.from(headers);

        // Build CSV content
        const csvRows: string[] = [];

        // Add header row
        csvRows.push(headerArray.join(','));

        // Add data rows
        flattenedData.forEach(row => {
            const values = headerArray.map(header => {
                const value = row[header];
                if (value === null || value === undefined) {
                    return '';
                }
                const stringValue = String(value);
                // Escape quotes and wrap in quotes if contains comma, quote, or newline
                if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
                    return `"${stringValue.replace(/"/g, '""')}"`;
                }
                return stringValue;
            });
            csvRows.push(values.join(','));
        });

        return csvRows.join('\n');
    };

    const downloadCSV = () => {
        if (data.length === 0) return;

        const csvContent = convertToCSV(data);
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const fileName = `${filename}_${timestamp}.csv`;

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');

        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', fileName);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }

        setIsOpen(false);
    };

    const downloadJSON = () => {
        if (data.length === 0) return;

        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const fileName = `${filename}_${timestamp}.json`;

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const link = document.createElement('a');

        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', fileName);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }

        setIsOpen(false);
    };

    const itemCount = data.length;
    const isEmpty = itemCount === 0;

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => !disabled && setIsOpen(!isOpen)}
                disabled={disabled || isEmpty}
                className={`flex items-center gap-2 px-3 py-2 text-sm rounded-lg border transition-colors ${disabled || isEmpty
                    ? 'bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed'
                    : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                aria-expanded={isOpen ? 'true' : 'false'}
                aria-haspopup="true"
            >
                <Download className="w-4 h-4" />
                <span>Export</span>
                <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div className="absolute right-0 top-full mt-1 z-50 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1">
                    <div className="px-3 py-2 text-xs text-gray-500 border-b">
                        {itemCount} item{itemCount !== 1 ? 's' : ''} to export
                    </div>

                    <button
                        onClick={downloadCSV}
                        disabled={isEmpty}
                        className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        <FileSpreadsheet className="w-4 h-4 text-green-600" />
                        <div className="text-left">
                            <div className="font-medium">Export as CSV</div>
                            <div className="text-xs text-gray-400">Comma-separated values</div>
                        </div>
                    </button>

                    <button
                        onClick={downloadJSON}
                        disabled={isEmpty}
                        className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        <FileSpreadsheet className="w-4 h-4 text-blue-600" />
                        <div className="text-left">
                            <div className="font-medium">Export as JSON</div>
                            <div className="text-xs text-gray-400">Full data structure</div>
                        </div>
                    </button>
                </div>
            )}

            {/* Backdrop to close dropdown */}
            {isOpen && (
                <div
                    className="fixed inset-0 z-40"
                    onClick={() => setIsOpen(false)}
                />
            )}
        </div>
    );
};

export default ExportDropdown;
