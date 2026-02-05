"""Alert List Component - Displays alerts with filtering and actions."""

import React, { useState, useEffect } from 'react';
import { Badge, Button, Card, Table, Tag, Modal, Form, Input, Select, Space, Tooltip } from 'antd';
import { CheckCircleOutlined, ExclamationCircleOutlined, EyeOutlined, BellOutlined } from '@ant-design/icons';

interface Alert {
    id: number;
    title: string;
    description?: string;
    severity: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
    status: 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED' | 'SUPPRESSED';
    current_value?: number;
    threshold_value?: number;
    starts_at: string;
    acknowledged_by?: string;
    resolved_by?: string;
}

interface AlertListProps {
    alerts?: Alert[];
    loading?: boolean;
    onAcknowledge?: (alertId: number, notes: string) => void;
    onResolve?: (alertId: number, notes: string) => void;
    onViewDetail?: (alert: Alert) => void;
}

const severityColors: Record<string, string> = {
    INFO: 'blue',
    WARNING: 'gold',
    ERROR: 'orange',
    CRITICAL: 'red',
};

const statusColors: Record<string, string> = {
    ACTIVE: 'red',
    ACKNOWLEDGED: 'orange',
    RESOLVED: 'green',
    SUPPRESSED: 'default',
};

export const AlertList: React.FC<AlertListProps> = ({
    alerts = [],
    loading = false,
    onAcknowledge,
    onResolve,
    onViewDetail,
}) => {
    const [filteredAlerts, setFilteredAlerts] = useState<Alert[]>(alerts);
    const [statusFilter, setStatusFilter] = useState<string | null>(null);
    const [severityFilter, setSeverityFilter] = useState<string | null>(null);
    const [ackModalVisible, setAckModalVisible] = useState(false);
    const [resolveModalVisible, setResolveModalVisible] = useState(false);
    const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
    const [notes, setNotes] = useState('');

    useEffect(() => {
        let filtered = [...alerts];
        if (statusFilter) {
            filtered = filtered.filter(a => a.status === statusFilter);
        }
        if (severityFilter) {
            filtered = filtered.filter(a => a.severity === severityFilter);
        }
        setFilteredAlerts(filtered);
    }, [alerts, statusFilter, severityFilter]);

    const handleAcknowledge = (alert: Alert) => {
        setSelectedAlert(alert);
        setAckModalVisible(true);
    };

    const handleResolve = (alert: Alert) => {
        setSelectedAlert(alert);
        setResolveModalVisible(true);
    };

    const submitAcknowledge = () => {
        if (selectedAlert && onAcknowledge) {
            onAcknowledge(selectedAlert.id, notes);
        }
        setAckModalVisible(false);
        setSelectedAlert(null);
        setNotes('');
    };

    const submitResolve = () => {
        if (selectedAlert && onResolve) {
            onResolve(selectedAlert.id, notes);
        }
        setResolveModalVisible(false);
        setSelectedAlert(null);
        setNotes('');
    };

    const columns = [
        {
            title: 'Severity',
            dataIndex: 'severity',
            key: 'severity',
            width: 100,
            render: (severity: string) => (
                <Tag color={severityColors[severity]}>{severity}</Tag>
            ),
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            width: 120,
            render: (status: string) => (
                <Tag color={statusColors[status]}>{status}</Tag>
            ),
        },
        {
            title: 'Title',
            dataIndex: 'title',
            key: 'title',
            ellipsis: true,
        },
        {
            title: 'Current',
            dataIndex: 'current_value',
            key: 'current_value',
            width: 100,
            render: (value: number, record: Alert) => (
                <span>
                    {value?.toFixed(2)}
                    {record.threshold_value && ` / ${record.threshold_value.toFixed(2)}`}
                </span>
            ),
        },
        {
            title: 'Started',
            dataIndex: 'starts_at',
            key: 'starts_at',
            width: 180,
            render: (timestamp: string) => new Date(timestamp).toLocaleString(),
        },
        {
            title: 'Actions',
            key: 'actions',
            width: 200,
            render: (_: any, record: Alert) => (
                <Space>
                    {record.status === 'ACTIVE' && (
                        <Button
                            type="primary"
                            size="small"
                            icon={<CheckCircleOutlined />}
                            onClick={() => handleAcknowledge(record)}
                        >
                            Ack
                        </Button>
                    )}
                    {record.status !== 'RESOLVED' && (
                        <Button
                            size="small"
                            icon={<CheckCircleOutlined />}
                            onClick={() => handleResolve(record)}
                        >
                            Resolve
                        </Button>
                    )}
                    <Tooltip title="View Details">
                        <Button
                            size="small"
                            icon={<EyeOutlined />}
                            onClick={() => onViewDetail?.(record)}
                        />
                    </Tooltip>
                </Space>
            ),
        },
    ];

    return (
        <Card
            title={
                <Space>
                    <BellOutlined />
                    <span>Active Alerts</span>
                    <Badge count={filteredAlerts.filter(a => a.status === 'ACTIVE').length} style={{ backgroundColor: '#ff4d4f' }} />
                </Space>
            }
            extra={
                <Space>
                    <Select
                        placeholder="Status"
                        allowClear
                        style={{ width: 140 }}
                        onChange={setStatusFilter}
                        options={[
                            { label: 'Active', value: 'ACTIVE' },
                            { label: 'Acknowledged', value: 'ACKNOWLEDGED' },
                            { label: 'Resolved', value: 'RESOLVED' },
                            { label: 'Suppressed', value: 'SUPPRESSED' },
                        ]}
                    />
                    <Select
                        placeholder="Severity"
                        allowClear
                        style={{ width: 120 }}
                        onChange={setSeverityFilter}
                        options={[
                            { label: 'Info', value: 'INFO' },
                            { label: 'Warning', value: 'WARNING' },
                            { label: 'Error', value: 'ERROR' },
                            { label: 'Critical', value: 'CRITICAL' },
                        ]}
                    />
                </Space>
            }
        >
            <Table
                dataSource={filteredAlerts}
                columns={columns}
                rowKey="id"
                loading={loading}
                pagination={{ pageSize: 10 }}
                size="small"
            />

            {/* Acknowledge Modal */}
            <Modal
                title="Acknowledge Alert"
                open={ackModalVisible}
                onOk={submitAcknowledge}
                onCancel={() => setAckModalVisible(false)}
            >
                <p>Are you sure you want to acknowledge this alert?</p>
                <Form layout="vertical">
                    <Form.Item label="Notes">
                        <Input.TextArea
                            value={notes}
                            onChange={e => setNotes(e.target.value)}
                            placeholder="Add acknowledgment notes..."
                            rows={3}
                        />
                    </Form.Item>
                </Form>
            </Modal>

            {/* Resolve Modal */}
            <Modal
                title="Resolve Alert"
                open={resolveModalVisible}
                onOk={submitResolve}
                onCancel={() => setResolveModalVisible(false)}
            >
                <p>Are you sure you want to resolve this alert?</p>
                <Form layout="vertical">
                    <Form.Item label="Notes">
                        <Input.TextArea
                            value={notes}
                            onChange={e => setNotes(e.target.value)}
                            placeholder="Add resolution notes..."
                            rows={3}
                        />
                    </Form.Item>
                </Form>
            </Modal>
        </Card>
    );
};

export default AlertList;
