/* Service Health Component - Displays service health status grid with overall health score. */

import React from 'react';
import { Card, Row, Col, Badge, Progress, Space, Tooltip, Tag } from 'antd';
import {
    CheckCircleOutlined,
    WarningOutlined,
    CloseCircleOutlined,
    SyncOutlined,
    QuestionCircleOutlined,
} from '@ant-design/icons';

interface ServiceHealth {
    name: string;
    status: 'healthy' | 'warning' | 'error' | 'unknown' | 'pending';
    responseTime?: number;
    uptime?: number;
    lastCheck?: string;
    details?: string;
}

interface ServiceHealthGridProps {
    services: ServiceHealth[];
    title?: string;
    onServiceClick?: (service: ServiceHealth) => void;
}

const statusConfig = {
    healthy: { color: '#52c41a', icon: <CheckCircleOutlined />, text: 'Healthy' },
    warning: { color: '#faad14', icon: <WarningOutlined />, text: 'Warning' },
    error: { color: '#ff4d4f', icon: <CloseCircleOutlined />, text: 'Error' },
    unknown: { color: '#d9d9d9', icon: <QuestionCircleOutlined />, text: 'Unknown' },
    pending: { color: '#1890ff', icon: <SyncOutlined spin />, text: 'Pending' },
};

const calculateOverallHealth = (services: ServiceHealth[]): number => {
    if (services.length === 0) return 100;
    const weights = { healthy: 100, warning: 70, error: 0, unknown: 50, pending: 80 };
    const total = services.reduce((sum, s) => sum + (weights[s.status] || 50), 0);
    return Math.round(total / services.length);
};

const getHealthScoreColor = (score: number): string => {
    if (score >= 90) return '#52c41a';
    if (score >= 70) return '#faad14';
    if (score >= 50) return '#1890ff';
    return '#ff4d4f';
};

const getHealthScoreStatus = (score: number): string => {
    if (score >= 90) return 'success';
    if (score >= 70) return 'active';
    if (score >= 50) return 'normal';
    return 'exception';
};

export const ServiceHealthGrid: React.FC<ServiceHealthGridProps> = ({
    services = [],
    title = 'Service Health',
    onServiceClick,
}) => {
    const overallHealth = calculateOverallHealth(services);
    const healthyCount = services.filter(s => s.status === 'healthy').length;
    const warningCount = services.filter(s => s.status === 'warning').length;
    const errorCount = services.filter(s => s.status === 'error').length;

    return (
        <Card
            title={
                <Space>
                    <span>{title}</span>
                    <Tag color={getHealthScoreColor(overallHealth)}>
                        {overallHealth}% Healthy
                    </Tag>
                </Space>
            }
            extra={
                <Space size="large">
                    <Tooltip title="Healthy Services">
                        <Badge count={healthyCount} style={{ backgroundColor: '#52c41a' }}>
                            <CheckCircleOutlined style={{ fontSize: 16, color: '#52c41a' }} />
                        </Badge>
                    </Tooltip>
                    <Tooltip title="Services with Warnings">
                        <Badge count={warningCount} style={{ backgroundColor: '#faad14' }}>
                            <WarningOutlined style={{ fontSize: 16, color: '#faad14' }} />
                        </Badge>
                    </Tooltip>
                    <Tooltip title="Services with Errors">
                        <Badge count={errorCount} style={{ backgroundColor: '#ff4d4f' }}>
                            <CloseCircleOutlined style={{ fontSize: 16, color: '#ff4d4f' }} />
                        </Badge>
                    </Tooltip>
                </Space>
            }
        >
            <Row gutter={[16, 16]}>
                <Col xs={24} md={8}>
                    <Card size="small" bodyStyle={{ padding: 16 }}>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ marginBottom: 8 }}>
                                <span style={{ fontSize: 14, color: '#999' }}>Overall Health</span>
                            </div>
                            <Progress
                                type="dashboard"
                                percent={overallHealth}
                                strokeColor={getHealthScoreColor(overallHealth)}
                                status={getHealthScoreStatus(overallHealth)}
                                size={100}
                                format={(percent) => (
                                    <span style={{ fontSize: 24, fontWeight: 'bold' }}>
                                        {percent}%
                                    </span>
                                )}
                            />
                        </div>
                    </Card>
                </Col>
                <Col xs={24} md={16}>
                    <Row gutter={[12, 12]}>
                        {services.map((service, index) => {
                            const config = statusConfig[service.status];
                            return (
                                <Col xs={24} sm={12} lg={8} key={index}>
                                    <Card
                                        size="small"
                                        hoverable
                                        onClick={() => onServiceClick?.(service)}
                                        style={{
                                            cursor: onServiceClick ? 'pointer' : 'default',
                                            borderLeft: `3px solid ${config.color}`,
                                        }}
                                        bodyStyle={{ padding: '12px 16px' }}
                                    >
                                        <Space direction="vertical" size={4} style={{ width: '100%' }}>
                                            <Space>
                                                <span style={{ color: config.color }}>
                                                    {config.icon}
                                                </span>
                                                <span style={{ fontWeight: 500 }}>
                                                    {service.name}
                                                </span>
                                            </Space>
                                            <Space split="|">
                                                {service.responseTime !== undefined && (
                                                    <span style={{ fontSize: 12, color: '#999' }}>
                                                        {service.responseTime}ms
                                                    </span>
                                                )}
                                                {service.uptime !== undefined && (
                                                    <span style={{ fontSize: 12, color: '#999' }}>
                                                        {service.uptime}% uptime
                                                    </span>
                                                )}
                                            </Space>
                                            {service.details && (
                                                <span style={{ fontSize: 11, color: '#999' }}>
                                                    {service.details}
                                                </span>
                                            )}
                                        </Space>
                                    </Card>
                                </Col>
                            );
                        })}
                    </Row>
                </Col>
            </Row>
        </Card>
    );
};

export default ServiceHealthGrid;
