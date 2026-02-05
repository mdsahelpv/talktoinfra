/* Monitoring Dashboard Page - Main monitoring overview with alerts, metrics, and service health. */

import React, { useState, useEffect, useCallback } from 'react';
import { Layout, Row, Col, Card, Space, Button, DatePicker, Select, Typography, Tabs, Badge } from 'antd';
import {
    ReloadOutlined,
    FullscreenOutlined,
    DownloadOutlined,
    BellOutlined,
    DashboardOutlined,
    SettingOutlined,
} from '@ant-design/icons';
import { AlertList } from './AlertList';
import { MetricsChart } from './MetricsChart';
import { ServiceHealthGrid } from './ServiceHealth';

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// Mock data for demonstration
const mockServices = [
    { name: 'API Gateway', status: 'healthy' as const, responseTime: 45, uptime: 99.9, details: 'Low latency' },
    { name: 'Auth Service', status: 'healthy' as const, responseTime: 32, uptime: 99.95, details: 'All systems nominal' },
    { name: 'Database Primary', status: 'healthy' as const, responseTime: 12, uptime: 99.99, details: 'Replication lag: 0ms' },
    { name: 'Cache Cluster', status: 'warning' as const, responseTime: 8, uptime: 99.5, details: 'Hit rate: 85%' },
    { name: 'Message Queue', status: 'healthy' as const, responseTime: 5, uptime: 99.99, details: 'Queue depth: 150' },
    { name: 'Search Service', status: 'error' as const, responseTime: 250, uptime: 98.5, details: 'Indexing delayed' },
    { name: 'ML Service', status: 'healthy' as const, responseTime: 150, uptime: 99.8, details: 'GPU utilization: 45%' },
    { name: 'Storage Service', status: 'healthy' as const, responseTime: 28, uptime: 99.9, details: 'IOPS: 25000' },
];

const mockAlerts = [
    {
        id: 1,
        title: 'High CPU Usage',
        description: 'CPU usage exceeded 90% threshold',
        severity: 'WARNING' as const,
        status: 'ACTIVE' as const,
        current_value: 92.5,
        threshold_value: 90,
        starts_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
        id: 2,
        title: 'Database Connection Pool Exhausted',
        description: 'Connection pool reached maximum capacity',
        severity: 'CRITICAL' as const,
        status: 'ACTIVE' as const,
        current_value: 100,
        threshold_value: 80,
        starts_at: new Date(Date.now() - 1800000).toISOString(),
    },
    {
        id: 3,
        title: 'SSL Certificate Expiring Soon',
        description: 'Certificate expires in 15 days',
        severity: 'WARNING' as const,
        status: 'ACKNOWLEDGED' as const,
        current_value: 15,
        threshold_value: 30,
        starts_at: new Date(Date.now() - 86400000).toISOString(),
        acknowledged_by: 'admin@example.com',
    },
];

const generateMetricData = (points: number = 60) => {
    const data = [];
    const now = Date.now();
    for (let i = points; i >= 0; i--) {
        data.push({
            timestamp: new Date(now - i * 60000).toISOString(),
            value: Math.random() * 30 + 40 + Math.sin(i / 10) * 10,
        });
    }
    return data;
};

const MonitoringPage: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const [services] = useState(mockServices);
    const [alerts, setAlerts] = useState(mockAlerts);
    const [cpuMetrics, setCpuMetrics] = useState(generateMetricData());
    const [memoryMetrics, setMemoryMetrics] = useState(generateMetricData());
    const [requestMetrics, setRequestMetrics] = useState(generateMetricData());

    const handleRefresh = useCallback(() => {
        setLoading(true);
        setTimeout(() => {
            setCpuMetrics(generateMetricData());
            setMemoryMetrics(generateMetricData());
            setRequestMetrics(generateMetricData());
            setLoading(false);
        }, 1000);
    }, []);

    const handleAlertAcknowledge = (alertId: number, notes: string) => {
        setAlerts(prev =>
            prev.map(a =>
                a.id === alertId ? { ...a, status: 'ACKNOWLEDGED' as const, acknowledged_by: 'current-user' } : a
            )
        );
    };

    const handleAlertResolve = (alertId: number, notes: string) => {
        setAlerts(prev =>
            prev.map(a =>
                a.id === alertId ? { ...a, status: 'RESOLVED' as const, resolved_by: 'current-user' } : a
            )
        );
    };

    const activeAlertsCount = alerts.filter(a => a.status === 'ACTIVE').length;
    const criticalAlertsCount = alerts.filter(a => a.severity === 'CRITICAL' && a.status === 'ACTIVE').length;

    return (
        <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
            <Header
                style={{
                    background: '#001529',
                    padding: '0 24px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                }}
            >
                <Space>
                    <DashboardOutlined style={{ color: '#fff', fontSize: 20, marginRight: 12 }} />
                    <Title level={4} style={{ color: '#fff', margin: 0 }}>
                        Monitoring Dashboard
                    </Title>
                </Space>
                <Space>
                    <Badge count={activeAlertsCount} size="small" style={{ backgroundColor: criticalAlertsCount > 0 ? '#ff4d4f' : '#faad14' }}>
                        <Button type="primary" icon={<BellOutlined />}>
                            Alerts
                        </Button>
                    </Badge>
                    <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
                        Refresh
                    </Button>
                    <Button icon={<SettingOutlined />}>
                        Settings
                    </Button>
                </Space>
            </Header>

            <Content style={{ padding: '24px' }}>
                <Row gutter={[24, 24]}>
                    {/* Service Health Grid */}
                    <Col xs={24}>
                        <ServiceHealthGrid
                            services={services}
                            title="Cluster Health Overview"
                            onServiceClick={(service) => console.log('Service clicked:', service)}
                        />
                    </Col>

                    {/* Active Alerts */}
                    <Col xs={24} lg={14}>
                        <AlertList
                            alerts={alerts}
                            loading={loading}
                            onAcknowledge={handleAlertAcknowledge}
                            onResolve={handleAlertResolve}
                            onViewDetail={(alert) => console.log('Alert detail:', alert)}
                        />
                    </Col>

                    {/* Quick Stats */}
                    <Col xs={24} lg={10}>
                        <Card title="Quick Stats" size="small">
                            <Row gutter={[16, 16]}>
                                <Col span={12}>
                                    <Card size="small" bodyStyle={{ padding: 12, textAlign: 'center' }}>
                                        <Text type="secondary">Active Alerts</Text>
                                        <Title level={2} style={{ margin: '8px 0 0', color: criticalAlertsCount > 0 ? '#ff4d4f' : '#faad14' }}>
                                            {activeAlertsCount}
                                        </Title>
                                    </Card>
                                </Col>
                                <Col span={12}>
                                    <Card size="small" bodyStyle={{ padding: 12, textAlign: 'center' }}>
                                        <Text type="secondary">Healthy Services</Text>
                                        <Title level={2} style={{ margin: '8px 0 0', color: '#52c41a' }}>
                                            {services.filter(s => s.status === 'healthy').length}/{services.length}
                                        </Title>
                                    </Card>
                                </Col>
                                <Col span={12}>
                                    <Card size="small" bodyStyle={{ padding: 12, textAlign: 'center' }}>
                                        <Text type="secondary">Avg Response Time</Text>
                                        <Title level={2} style={{ margin: '8px 0 0' }}>
                                            {Math.round(services.reduce((sum, s) => sum + (s.responseTime || 0), 0) / services.length)}ms
                                        </Title>
                                    </Card>
                                </Col>
                                <Col span={12}>
                                    <Card size="small" bodyStyle={{ padding: 12, textAlign: 'center' }}>
                                        <Text type="secondary">Uptime (24h)</Text>
                                        <Title level={2} style={{ margin: '8px 0 0', color: '#52c41a' }}>
                                            99.9%
                                        </Title>
                                    </Card>
                                </Col>
                            </Row>
                        </Card>
                    </Col>

                    {/* CPU Metrics */}
                    <Col xs={24} lg={12}>
                        <MetricsChart
                            title="CPU Usage"
                            data={cpuMetrics}
                            loading={loading}
                            unit="%"
                            threshold={80}
                            warningThreshold={70}
                            criticalThreshold={90}
                            onRefresh={() => setCpuMetrics(generateMetricData())}
                            color="#1890ff"
                            chartType="area"
                        />
                    </Col>

                    {/* Memory Metrics */}
                    <Col xs={24} lg={12}>
                        <MetricsChart
                            title="Memory Usage"
                            data={memoryMetrics}
                            loading={loading}
                            unit="%"
                            threshold={85}
                            warningThreshold={75}
                            criticalThreshold={95}
                            onRefresh={() => setMemoryMetrics(generateMetricData())}
                            color="#722ed1"
                            chartType="area"
                        />
                    </Col>

                    {/* Request Metrics */}
                    <Col xs={24}>
                        <MetricsChart
                            title="Request Rate"
                            data={requestMetrics}
                            loading={loading}
                            unit=" req/s"
                            threshold={1000}
                            warningThreshold={800}
                            onRefresh={() => setRequestMetrics(generateMetricData())}
                            color="#52c41a"
                            chartType="line"
                        />
                    </Col>
                </Row>
            </Content>
        </Layout>
    );
};

export default MonitoringPage;
