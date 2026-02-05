/* Metrics Chart Component - Displays time-series metrics with interactive charts. */

import React, { useState, useEffect } from 'react';
import { Card, Select, Space, Spin, Tooltip, Badge } from 'antd';
import {
    LineChart,
    Line,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip as RechartsTooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';
import { InfoCircleOutlined, ReloadOutlined } from '@ant-design/icons';

interface DataPoint {
    timestamp: string;
    value: number;
    label?: string;
}

interface MetricsChartProps {
    title: string;
    data?: DataPoint[];
    loading?: boolean;
    unit?: string;
    threshold?: number;
    warningThreshold?: number;
    criticalThreshold?: number;
    onRefresh?: () => void;
    color?: string;
    chartType?: 'line' | 'area';
    height?: number;
}

const getStatusColor = (
    value: number,
    warningThreshold?: number,
    criticalThreshold?: number
): string => {
    if (criticalThreshold && value >= criticalThreshold) return '#ff4d4f';
    if (warningThreshold && value >= warningThreshold) return '#faad14';
    return '#52c41a';
};

export const MetricsChart: React.FC<MetricsChartProps> = ({
    title,
    data = [],
    loading = false,
    unit = '',
    threshold,
    warningThreshold,
    criticalThreshold,
    onRefresh,
    color = '#1890ff',
    chartType = 'area',
    height = 300,
}) => {
    const [timeRange, setTimeRange] = useState<string>('1h');
    const [displayData, setDisplayData] = useState<DataPoint[]>(data);

    useEffect(() => {
        setDisplayData(data);
    }, [data]);

    const formatTimestamp = (timestamp: string) => {
        const date = new Date(timestamp);
        switch (timeRange) {
            case '15m':
            case '1h':
                return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' });
            case '6h':
            case '24h':
                return date.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit' });
            default:
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        }
    };

    const latestValue = data.length > 0 ? data[data.length - 1].value : 0;
    const statusColor = getStatusColor(latestValue, warningThreshold, criticalThreshold);

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <Card size="small" style={{ background: 'rgba(255, 255, 255, 0.95)' }}>
                    <p style={{ margin: 0 }}>{formatTimestamp(label)}</p>
                    <p style={{ margin: 0, color: payload[0].color }}>
                        <strong>{payload[0].value.toFixed(2)}{unit}</strong>
                    </p>
                </Card>
            );
        }
        return null;
    };

    const ChartComponent = chartType === 'line' ? LineChart : AreaChart;

    return (
        <Card
            title={
                <Space>
                    <Badge color={statusColor} />
                    <span>{title}</span>
                    {threshold && (
                        <Tooltip title={`Threshold: ${threshold}${unit}`}>
                            <InfoCircleOutlined style={{ color: '#999' }} />
                        </Tooltip>
                    )}
                </Space>
            }
            extra={
                <Space>
                    <Select
                        value={timeRange}
                        onChange={setTimeRange}
                        style={{ width: 100 }}
                        options={[
                            { label: '15m', value: '15m' },
                            { label: '1h', value: '1h' },
                            { label: '6h', value: '6h' },
                            { label: '24h', value: '24h' },
                            { label: '7d', value: '7d' },
                        ]}
                    />
                    {onRefresh && (
                        <Tooltip title="Refresh">
                            <ReloadOutlined
                                onClick={onRefresh}
                                style={{ cursor: 'pointer', fontSize: 16 }}
                                spin={loading}
                            />
                        </Tooltip>
                    )}
                </Space>
            }
            bodyStyle={{ padding: '12px 24px' }}
        >
            {loading && data.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                    <Spin tip="Loading metrics..." />
                </div>
            ) : (
                <>
                    <div style={{ marginBottom: 8 }}>
                        <Space>
                            <span style={{ fontSize: 24, fontWeight: 'bold', color: statusColor }}>
                                {latestValue.toFixed(2)}{unit}
                            </span>
                            {latestValue > 0 && (
                                <span style={{ color: '#999' }}>current</span>
                            )}
                        </Space>
                    </div>
                    <ResponsiveContainer width="100%" height={height}>
                        {chartType === 'line' ? (
                            <LineChart data={displayData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                <XAxis
                                    dataKey="timestamp"
                                    tickFormatter={formatTimestamp}
                                    stroke="#999"
                                    fontSize={12}
                                />
                                <YAxis stroke="#999" fontSize={12} />
                                <RechartsTooltip content={<CustomTooltip />} />
                                <Line
                                    type="monotone"
                                    dataKey="value"
                                    stroke={color}
                                    strokeWidth={2}
                                    dot={false}
                                    activeDot={{ r: 6 }}
                                />
                                {threshold && (
                                    <Legend
                                        verticalAlign="top"
                                        height={36}
                                        formatter={() => `Threshold: ${threshold}${unit}`}
                                    />
                                )}
                            </LineChart>
                        ) : (
                            <AreaChart data={displayData}>
                                <defs>
                                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                                        <stop offset="95%" stopColor={color} stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                <XAxis
                                    dataKey="timestamp"
                                    tickFormatter={formatTimestamp}
                                    stroke="#999"
                                    fontSize={12}
                                />
                                <YAxis stroke="#999" fontSize={12} />
                                <RechartsTooltip content={<CustomTooltip />} />
                                <Area
                                    type="monotone"
                                    dataKey="value"
                                    stroke={color}
                                    fillOpacity={1}
                                    fill="url(#colorValue)"
                                    strokeWidth={2}
                                />
                                {threshold && (
                                    <Legend
                                        verticalAlign="top"
                                        height={36}
                                        formatter={() => `Threshold: ${threshold}${unit}`}
                                    />
                                )}
                            </AreaChart>
                        )}
                    </ResponsiveContainer>
                </>
            )}
        </Card>
    );
};

export default MetricsChart;
