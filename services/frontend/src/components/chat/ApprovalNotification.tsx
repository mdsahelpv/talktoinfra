import React, { useState, useRef, useEffect } from 'react';
import type { ApprovalNotificationProps } from '@/types/conversation';

const ApprovalNotification: React.FC<ApprovalNotificationProps> = ({
    notifications,
    pendingCount,
    onMarkAsRead,
    onApproveAll,
    onViewApproval,
    onTogglePreferences,
    preferences,
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

    const getRiskColor = (risk: string): string => {
        switch (risk) {
            case 'LOW':
                return 'bg-green-100 text-green-800';
            case 'MEDIUM':
                return 'bg-yellow-100 text-yellow-800';
            case 'HIGH':
                return 'bg-orange-100 text-orange-800';
            case 'CRITICAL':
                return 'bg-red-100 text-red-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="relative" ref={dropdownRef}>
            {/* Bell Icon Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="relative p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                    />
                </svg>
                {pendingCount > 0 && (
                    <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
                        {pendingCount > 9 ? '9+' : pendingCount}
                    </span>
                )}
            </button>

            {/* Dropdown */}
            {isOpen && (
                <div className="absolute right-0 mt-2 w-96 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
                    {/* Header */}
                    <div className="px-4 py-3 bg-gray-50 border-b flex items-center justify-between">
                        <h3 className="font-semibold text-gray-800">
                            Approval Notifications
                        </h3>
                        <div className="flex items-center gap-2">
                            {/* Settings Button */}
                            <button
                                onClick={onTogglePreferences}
                                className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded transition-colors"
                                title="Notification preferences"
                            >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                </svg>
                            </button>
                            {/* Approve All Button */}
                            {pendingCount > 0 && (
                                <button
                                    onClick={() => {
                                        onApproveAll();
                                        setIsOpen(false);
                                    }}
                                    className="px-3 py-1 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                                >
                                    Approve All
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Notification Preferences Panel */}
                    {false && (
                        <div className="px-4 py-3 bg-blue-50 border-b">
                            <h4 className="text-sm font-medium text-gray-700 mb-2">Notification Preferences</h4>
                            <div className="flex flex-wrap gap-3">
                                <label className="flex items-center gap-2 text-sm">
                                    <input
                                        type="checkbox"
                                        checked={preferences.email_enabled}
                                        onChange={() => { }}
                                        className="rounded text-blue-600"
                                    />
                                    Email
                                </label>
                                <label className="flex items-center gap-2 text-sm">
                                    <input
                                        type="checkbox"
                                        checked={preferences.slack_enabled}
                                        onChange={() => { }}
                                        className="rounded text-blue-600"
                                    />
                                    Slack
                                </label>
                                <label className="flex items-center gap-2 text-sm">
                                    <input
                                        type="checkbox"
                                        checked={preferences.in_app_enabled}
                                        onChange={() => { }}
                                        className="rounded text-blue-600"
                                    />
                                    In-App
                                </label>
                                <label className="flex items-center gap-2 text-sm">
                                    <input
                                        type="checkbox"
                                        checked={preferences.sound_enabled}
                                        onChange={() => { }}
                                        className="rounded text-blue-600"
                                    />
                                    Sound
                                </label>
                            </div>
                        </div>
                    )}

                    {/* Notifications List */}
                    <div className="max-h-96 overflow-y-auto">
                        {notifications.length === 0 ? (
                            <div className="px-4 py-8 text-center text-gray-500">
                                <svg className="w-12 h-12 mx-auto mb-2 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                No pending approvals
                            </div>
                        ) : (
                            <ul className="divide-y divide-gray-100">
                                {notifications.map((notification) => (
                                    <li
                                        key={notification.id}
                                        className={`px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors ${!notification.read ? 'bg-blue-50' : ''}`}
                                        onClick={() => {
                                            onViewApproval(notification.approval_id);
                                            onMarkAsRead(notification.id);
                                        }}
                                    >
                                        <div className="flex items-start gap-3">
                                            <div className="flex-shrink-0 mt-0.5">
                                                {notification.risk_level === 'CRITICAL' ? (
                                                    <span className="text-xl">🚨</span>
                                                ) : notification.risk_level === 'HIGH' ? (
                                                    <span className="text-xl">⚠️</span>
                                                ) : notification.risk_level === 'MEDIUM' ? (
                                                    <span className="text-xl">⚡</span>
                                                ) : (
                                                    <span className="text-xl">✅</span>
                                                )}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium text-gray-900 truncate">
                                                    {notification.action_type} Approval Required
                                                </p>
                                                <p className="text-sm text-gray-600 mt-0.5 line-clamp-2">
                                                    {notification.message}
                                                </p>
                                                <div className="flex items-center gap-2 mt-2">
                                                    <span className={`text-xs px-2 py-0.5 rounded-full ${getRiskColor(notification.risk_level)}`}>
                                                        {notification.risk_level}
                                                    </span>
                                                    <span className="text-xs text-gray-400">
                                                        {new Date(notification.created_at).toLocaleString()}
                                                    </span>
                                                </div>
                                            </div>
                                            {!notification.read && (
                                                <div className="flex-shrink-0">
                                                    <span className="w-2 h-2 bg-blue-500 rounded-full block" />
                                                </div>
                                            )}
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>

                    {/* Footer */}
                    {notifications.length > 0 && (
                        <div className="px-4 py-2 bg-gray-50 border-t text-center">
                            <button
                                onClick={() => setIsOpen(false)}
                                className="text-sm text-gray-600 hover:text-gray-800"
                            >
                                Close
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default ApprovalNotification;
