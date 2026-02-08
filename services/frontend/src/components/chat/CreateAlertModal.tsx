import React, { useState, useEffect } from 'react';
import { X, Bell, AlertTriangle, Clock, Zap, Plus, Trash2, Check } from 'lucide-react';
import type { CreateAlertModalProps, AlertSeverity, AlertConditionType, AlertNotificationChannel, AlertThreshold } from '@/types/conversation';

export const CreateAlertModal: React.FC<CreateAlertModalProps> = ({
    isOpen,
    onClose,
    onCreate,
    queryContext,
    loading = false,
}) => {
    const [step, setStep] = useState(1);
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [severity, setSeverity] = useState<AlertSeverity>('warning');
    const [conditionType, setConditionType] = useState<AlertConditionType>('threshold');
    const [thresholdMetric, setThresholdMetric] = useState('');
    const [thresholdOperator, setThresholdOperator] = useState<'gt' | 'lt' | 'gte' | 'lte' | 'eq'>('gt');
    const [thresholdValue, setThresholdValue] = useState('');
    const [timeRange, setTimeRange] = useState(300);
    const [channels, setChannels] = useState<AlertNotificationChannel[]>([]);
    const [newChannelType, setNewChannelType] = useState<'email' | 'slack' | 'webhook' | 'pagerduty'>('email');
    const [newChannelDestination, setNewChannelDestination] = useState('');
    const [errors, setErrors] = useState<Record<string, string>>({});

    // Reset form when modal opens
    useEffect(() => {
        if (isOpen) {
            setStep(1);
            setName('');
            setDescription('');
            setSeverity('warning');
            setConditionType('threshold');
            setThresholdMetric('');
            setThresholdValue('');
            setTimeRange(300);
            setChannels([]);
            setErrors({});
        }
    }, [isOpen]);

    const validateStep = (currentStep: number): boolean => {
        const newErrors: Record<string, string> = {};

        if (currentStep === 1) {
            if (!name.trim()) {
                newErrors.name = 'Alert name is required';
            }
            if (name.length > 100) {
                newErrors.name = 'Alert name must be 100 characters or less';
            }
        }

        if (currentStep === 2) {
            if (conditionType === 'threshold') {
                if (!thresholdMetric.trim()) {
                    newErrors.thresholdMetric = 'Metric is required';
                }
                if (!thresholdValue) {
                    newErrors.thresholdValue = 'Threshold value is required';
                }
            }
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleNext = () => {
        if (validateStep(step)) {
            setStep(step + 1);
        }
    };

    const handleBack = () => {
        setStep(step - 1);
    };

    const handleAddChannel = () => {
        if (newChannelDestination.trim()) {
            setChannels([
                ...channels,
                {
                    type: newChannelType,
                    destination: newChannelDestination,
                    enabled: true,
                },
            ]);
            setNewChannelDestination('');
        }
    };

    const handleRemoveChannel = (index: number) => {
        setChannels(channels.filter((_, i) => i !== index));
    };

    const handleSubmit = () => {
        if (!name.trim()) {
            setErrors({ name: 'Alert name is required' });
            return;
        }

        const threshold: AlertThreshold | undefined = conditionType === 'threshold' ? {
            metric: thresholdMetric,
            operator: thresholdOperator,
            value: parseFloat(thresholdValue),
            duration: 60,
        } : undefined;

        const alertRequest = {
            name,
            description: description || undefined,
            condition: {
                type: conditionType,
                threshold,
                timeRange: conditionType === 'time_based' ? timeRange : undefined,
                query: queryContext?.originalQuery,
            },
            severity,
            channels,
            enabled: true,
            labels: {
                source: 'talktoinfra',
                ...(queryContext?.resultType && { result_type: queryContext.resultType }),
            },
            annotations: description ? { summary: description } : undefined,
            query_context: queryContext ? {
                original_query: queryContext.originalQuery,
                result_type: queryContext.resultType,
                filters: queryContext.filters,
            } : undefined,
        };

        onCreate(alertRequest);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/50" onClick={onClose} />

            {/* Modal */}
            <div className="relative bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-orange-100 rounded-lg">
                            <Bell className="w-5 h-5 text-orange-600" />
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold text-gray-900">Create Alert</h2>
                            <p className="text-sm text-gray-500">Step {step} of 3</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                        disabled={loading}
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                {/* Progress bar */}
                <div className="h-1 bg-gray-100">
                    <div
                        className="h-full bg-blue-600 transition-all duration-300"
                        style={{ width: `${(step / 3) * 100}%` }}
                    />
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {/* Step 1: Basic Info */}
                    {step === 1 && (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Alert Name *
                                </label>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="e.g., High CPU Usage on Production"
                                    className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.name ? 'border-red-500' : 'border-gray-300'
                                        }`}
                                    disabled={loading}
                                />
                                {errors.name && (
                                    <p className="mt-1 text-sm text-red-600">{errors.name}</p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Description
                                </label>
                                <textarea
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    placeholder="Describe when this alert should trigger..."
                                    rows={3}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    disabled={loading}
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Severity
                                </label>
                                <div className="grid grid-cols-2 gap-2">
                                    {(['low', 'info', 'warning', 'critical'] as AlertSeverity[]).map((sev) => (
                                        <button
                                            key={sev}
                                            onClick={() => setSeverity(sev)}
                                            className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${severity === sev
                                                    ? 'bg-blue-50 border-blue-500 text-blue-700'
                                                    : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                                                }`}
                                            disabled={loading}
                                        >
                                            <AlertTriangle className={`w-4 h-4 ${sev === 'critical' ? 'text-red-500' :
                                                    sev === 'warning' ? 'text-yellow-500' :
                                                        sev === 'info' ? 'text-blue-500' : 'text-gray-500'
                                                }`} />
                                            <span className="capitalize">{sev}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Step 2: Condition */}
                    {step === 2 && (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Condition Type
                                </label>
                                <select
                                    value={conditionType}
                                    onChange={(e) => setConditionType(e.target.value as AlertConditionType)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    disabled={loading}
                                >
                                    <option value="threshold">Threshold-based</option>
                                    <option value="time_based">Time-based</option>
                                    <option value="resource_based">Resource-based</option>
                                </select>
                            </div>

                            {conditionType === 'threshold' && (
                                <div className="space-y-3 p-4 bg-gray-50 rounded-lg">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Metric *
                                        </label>
                                        <input
                                            type="text"
                                            value={thresholdMetric}
                                            onChange={(e) => setThresholdMetric(e.target.value)}
                                            placeholder="e.g., cpu_usage, memory_percent"
                                            className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.thresholdMetric ? 'border-red-500' : 'border-gray-300'
                                                }`}
                                            disabled={loading}
                                        />
                                        {errors.thresholdMetric && (
                                            <p className="mt-1 text-sm text-red-600">{errors.thresholdMetric}</p>
                                        )}
                                    </div>

                                    <div className="flex gap-2">
                                        <div className="flex-1">
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Operator
                                            </label>
                                            <select
                                                value={thresholdOperator}
                                                onChange={(e) => setThresholdOperator(e.target.value as 'gt' | 'lt' | 'gte' | 'lte' | 'eq')}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                                disabled={loading}
                                            >
                                                <option value="gt">Greater than</option>
                                                <option value="lt">Less than</option>
                                                <option value="gte">Greater or equal</option>
                                                <option value="lte">Less or equal</option>
                                                <option value="eq">Equals</option>
                                            </select>
                                        </div>
                                        <div className="flex-1">
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Value *
                                            </label>
                                            <input
                                                type="number"
                                                value={thresholdValue}
                                                onChange={(e) => setThresholdValue(e.target.value)}
                                                placeholder="e.g., 80"
                                                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${errors.thresholdValue ? 'border-red-500' : 'border-gray-300'
                                                    }`}
                                                disabled={loading}
                                            />
                                            {errors.thresholdValue && (
                                                <p className="mt-1 text-sm text-red-600">{errors.thresholdValue}</p>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {conditionType === 'time_based' && (
                                <div className="space-y-3 p-4 bg-gray-50 rounded-lg">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Time Range (seconds)
                                        </label>
                                        <select
                                            value={timeRange}
                                            onChange={(e) => setTimeRange(Number(e.target.value))}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                            disabled={loading}
                                        >
                                            <option value={60}>1 minute</option>
                                            <option value={300}>5 minutes</option>
                                            <option value={600}>10 minutes</option>
                                            <option value={1800}>30 minutes</option>
                                            <option value={3600}>1 hour</option>
                                        </select>
                                    </div>
                                    <div className="flex items-center gap-2 text-sm text-gray-600">
                                        <Clock className="w-4 h-4" />
                                        <span>Alert will trigger if condition persists for {timeRange} seconds</span>
                                    </div>
                                </div>
                            )}

                            {queryContext && (
                                <div className="p-3 bg-blue-50 rounded-lg">
                                    <div className="flex items-center gap-2 text-sm text-blue-700">
                                        <Zap className="w-4 h-4" />
                                        <span className="font-medium">Based on your query:</span>
                                    </div>
                                    <p className="mt-1 text-sm text-blue-600 italic">"{queryContext.originalQuery}"</p>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Step 3: Notifications */}
                    {step === 3 && (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Notification Channels
                                </label>
                                <p className="text-sm text-gray-500 mb-3">
                                    Add channels where alert notifications will be sent
                                </p>

                                {channels.length > 0 && (
                                    <div className="space-y-2 mb-4">
                                        {channels.map((channel, index) => (
                                            <div
                                                key={index}
                                                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                                            >
                                                <div className="flex items-center gap-2">
                                                    <span className={`px-2 py-0.5 text-xs rounded capitalize ${channel.type === 'email' ? 'bg-blue-100 text-blue-700' :
                                                            channel.type === 'slack' ? 'bg-purple-100 text-purple-700' :
                                                                channel.type === 'webhook' ? 'bg-green-100 text-green-700' :
                                                                    'bg-red-100 text-red-700'
                                                        }`}>
                                                        {channel.type}
                                                    </span>
                                                    <span className="text-sm text-gray-600">{channel.destination}</span>
                                                </div>
                                                <button
                                                    onClick={() => handleRemoveChannel(index)}
                                                    className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                                                    disabled={loading}
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                <div className="flex gap-2">
                                    <select
                                        value={newChannelType}
                                        onChange={(e) => setNewChannelType(e.target.value as 'email' | 'slack' | 'webhook' | 'pagerduty')}
                                        className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        disabled={loading}
                                    >
                                        <option value="email">Email</option>
                                        <option value="slack">Slack</option>
                                        <option value="webhook">Webhook</option>
                                        <option value="pagerduty">PagerDuty</option>
                                    </select>
                                    <input
                                        type="text"
                                        value={newChannelDestination}
                                        onChange={(e) => setNewChannelDestination(e.target.value)}
                                        placeholder={
                                            newChannelType === 'email' ? 'email@example.com' :
                                                newChannelType === 'slack' ? '#channel or @user' :
                                                    newChannelType === 'webhook' ? 'https://...' :
                                                        'service_key'
                                        }
                                        className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        disabled={loading}
                                    />
                                    <button
                                        onClick={handleAddChannel}
                                        disabled={!newChannelDestination.trim()}
                                        className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        <Plus className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>

                            {channels.length === 0 && (
                                <div className="p-4 bg-yellow-50 rounded-lg">
                                    <p className="text-sm text-yellow-700">
                                        No notification channels configured. The alert will be created but won't send notifications.
                                    </p>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50">
                    <div className="text-sm text-gray-500">
                        {step === 1 && 'Give your alert a name and severity'}
                        {step === 2 && 'Define when the alert should trigger'}
                        {step === 3 && 'Configure where to send notifications'}
                    </div>
                    <div className="flex gap-2">
                        {step > 1 && (
                            <button
                                onClick={handleBack}
                                disabled={loading}
                                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                Back
                            </button>
                        )}
                        {step < 3 ? (
                            <button
                                onClick={handleNext}
                                disabled={loading}
                                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                Continue
                            </button>
                        ) : (
                            <button
                                onClick={handleSubmit}
                                disabled={loading || !name.trim()}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-orange-600 rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                {loading ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        Creating...
                                    </>
                                ) : (
                                    <>
                                        <Check className="w-4 h-4" />
                                        Create Alert
                                    </>
                                )}
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CreateAlertModal;
